"""
FreightTiger shipping-cost anomaly detector
Run: python main.py
Input CSVs must be in the same folder as this file.
"""
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
SHIPMENTS_FILE = BASE_DIR / "shipment_records.csv"
NOTES_FILE = BASE_DIR / "context_notes.csv"
OUTPUT_FILE = BASE_DIR / "output.csv"

# The assignment does not specify a numeric flagging threshold.
# This is a transparent starting heuristic; adjust and document it.
ANOMALY_THRESHOLD = 0.10  # 10% above either baseline


def monday_of_week(dates):
    """Return the Monday date for each shipment date."""
    return dates.dt.to_period("W-SUN").dt.start_time.dt.normalize()


def load_and_validate():
    shipments = pd.read_csv(SHIPMENTS_FILE)
    notes = pd.read_csv(NOTES_FILE)

    required_ship = {
        "origin", "destination", "route_type", "quantity_tonnes",
        "distance_km", "freight_cost_inr", "shipment_date"
    }
    missing = required_ship - set(shipments.columns)
    if missing:
        raise ValueError(f"Shipment CSV is missing columns: {sorted(missing)}")

    required_notes = {"note_id", "date", "applies_to", "note"}
    missing = required_notes - set(notes.columns)
    if missing:
        raise ValueError(f"Notes CSV is missing columns: {sorted(missing)}")

    shipments["shipment_date"] = pd.to_datetime(
        shipments["shipment_date"], errors="raise"
    )
    notes["date"] = pd.to_datetime(notes["date"], errors="raise")

    numeric_cols = ["quantity_tonnes", "distance_km", "freight_cost_inr"]
    for col in numeric_cols:
        shipments[col] = pd.to_numeric(shipments[col], errors="raise")

    if (shipments["quantity_tonnes"] <= 0).any():
        raise ValueError("quantity_tonnes must be positive.")
    if (shipments["distance_km"] <= 0).any():
        raise ValueError("distance_km must be positive.")
    if (shipments["freight_cost_inr"] < 0).any():
        raise ValueError("freight_cost_inr cannot be negative.")

    shipments["route"] = shipments["origin"] + "-" + shipments["destination"]
    shipments["week_of"] = monday_of_week(shipments["shipment_date"])
    shipments["tonne_km"] = (
        shipments["quantity_tonnes"] * shipments["distance_km"]
    )
    return shipments, notes


def make_weekly_costs(shipments):
    """
    Weekly route cost = sum of freight costs / sum of tonne-km.
    This correctly weights shipments with different quantities/distances.
    """
    weekly = (
        shipments.groupby(
            ["route", "route_type", "week_of"], as_index=False, sort=True
        )
        .agg(
            total_cost=("freight_cost_inr", "sum"),
            total_tonne_km=("tonne_km", "sum"),
        )
    )
    weekly["cost_per_tonne_km"] = (
        weekly["total_cost"] / weekly["total_tonne_km"]
    )
    weekly = weekly.sort_values(["route", "week_of"]).reset_index(drop=True)

    # History baseline: up to the previous 8 observed weeks, never current/future.
    history_values = []
    history_counts = []
    for _, group in weekly.groupby("route", sort=False):
        costs = group["cost_per_tonne_km"].tolist()
        for i in range(len(costs)):
            previous = costs[max(0, i - 8):i]
            history_values.append(sum(previous) / len(previous) if previous else float("nan"))
            history_counts.append(len(previous))
    weekly["vs_own_history_baseline"] = history_values
    weekly["history_weeks_used"] = history_counts

    # Peer baseline: same week and route type, excluding this route.
    peer_means = []
    for row in weekly.itertuples(index=False):
        peers = weekly[
            (weekly["week_of"] == row.week_of)
            & (weekly["route_type"] == row.route_type)
            & (weekly["route"] != row.route)
        ]["cost_per_tonne_km"]
        peer_means.append(peers.mean() if not peers.empty else float("nan"))
    weekly["vs_similar_routes_baseline"] = peer_means

    weekly["own_change"] = (
        weekly["cost_per_tonne_km"] / weekly["vs_own_history_baseline"] - 1
    )
    weekly["peer_change"] = (
        weekly["cost_per_tonne_km"] / weekly["vs_similar_routes_baseline"] - 1
    )
    return weekly


def note_window(note_row):
    """
    Conservative event windows based on the supplied notes.
    Only notes that actually describe a cost-increasing event can justify a rise.
    """
    note_id = note_row["note_id"]
    start = note_row["date"].normalize()

    if note_id == "N001":  # Flooding explicitly lasted Feb 24 to Mar 8.
        return start, pd.Timestamp("2025-03-08")
    if note_id == "N002":  # Temporary festival surcharge: dated week.
        return start, start + pd.Timedelta(days=6)
    if note_id == "N003":  # Nationwide diesel increase: starting week.
        return start, start + pd.Timedelta(days=6)
    if note_id == "N005":  # Note says costs were not significantly affected.
        return start, start + pd.Timedelta(days=6)
    # Other notes report stable/no disruption, improved conditions, or absorbed costs.
    return start, start


def find_justifying_note(route, week_of, notes):
    """Return the first relevant note that explicitly supports a cost increase."""
    positive_ids = {"N001", "N002", "N003"}
    week_end = week_of + pd.Timedelta(days=6)

    for _, note in notes.iterrows():
        if note["note_id"] not in positive_ids:
            continue

        applies = str(note["applies_to"]).strip()
        route_matches = applies == "All Routes" or applies == route
        if not route_matches:
            continue

        start, end = note_window(note)
        if start <= week_end and end >= week_of:
            return note
    return None


def explain_row(row, note):
    own = row["own_change"]
    peer = row["peer_change"]
    own_text = (
        f"{own:+.1%} vs this route's past average"
        if pd.notna(own) else "not available (no prior week)"
    )
    peer_text = (
        f"{peer:+.1%} vs similar-length routes this week"
        if pd.notna(peer) else "not available (no other same-type route)"
    )

    if note is not None:
        reason = (
            f"Matches note {note['note_id']} dated "
            f"{note['date'].date()}: {note['note']} "
            "This note supports the increase for this route and period."
        )
        flag = "No (justified)"
        note_id = note["note_id"]
    else:
        reason = (
            "Cost rise exceeds the configured anomaly threshold, but no note "
            "was found that both applies to this route and period and explicitly "
            "explains a cost increase. Unexplained; human review recommended."
        )
        flag = "Yes"
        note_id = ""

    return own_text, peer_text, flag, note_id, reason


def main():
    shipments, notes = load_and_validate()
    weekly = make_weekly_costs(shipments)

    # Candidate if the cost is at least 10% above either available baseline.
    # A baseline must exist, and the current cost must be higher.
    own_candidate = (
        weekly["own_change"].notna()
        & (weekly["own_change"] >= ANOMALY_THRESHOLD)
    )
    peer_candidate = (
        weekly["peer_change"].notna()
        & (weekly["peer_change"] >= ANOMALY_THRESHOLD)
    )
    candidates = weekly[own_candidate | peer_candidate].copy()

    output_rows = []
    for row in candidates.itertuples(index=False):
        row_dict = row._asdict()
        row_series = pd.Series(row_dict)
        note = find_justifying_note(row.route, row.week_of, notes)
        own_text, peer_text, flag, note_id, reason = explain_row(row_series, note)
        output_rows.append({
            "route": row.route,
            "week_of": row.week_of.strftime("%Y-%m-%d"),
            "cost_per_tonne_km": f"{row.cost_per_tonne_km:.2f}",
            "vs_own_history": own_text,
            "vs_similar_routes": peer_text,
            "flagged": flag,
            "matched_note_id": note_id,
            "reason": reason,
        })

    columns = [
        "route", "week_of", "cost_per_tonne_km", "vs_own_history",
        "vs_similar_routes", "flagged", "matched_note_id", "reason"
    ]
    output = pd.DataFrame(output_rows, columns=columns)
    output.to_csv(OUTPUT_FILE, index=False)
    print(f"Read {len(shipments)} shipment records and {len(notes)} notes.")
    print(f"Weekly route groups: {len(weekly)}")
    print(f"Candidate weeks written: {len(output)}")
    print(f"Output saved to: {OUTPUT_FILE}")
    print(f"Threshold used: {ANOMALY_THRESHOLD:.0%} above either available baseline.")
    print("Important: review the threshold and note matching assumptions before submission.")


if __name__ == "__main__":
    main()
