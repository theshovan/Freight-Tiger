
# FreightTiger Shipping Cost Anomaly Detector

## 1. Project Overview

This project analyses shipment records to identify unusual increases in transportation costs.

It calculates the cost per tonne-kilometre for each route every week, compares it with historical costs and similar routes, and checks context notes for possible explanations.

The goal is to identify unusual cost increases and provide explanations supported by the available evidence.

## 2. Problem Statement

Transportation costs can increase because of fuel price changes, toll updates, weather disruptions, festival surcharges, or other factors.

This project helps identify routes where transportation costs are rising unusually and determines whether the provided context notes explain the increase.

## 3. Technologies Used

- Python
- Pandas
- CSV files

The current implementation uses rule-based calculations and note matching. It does not currently use a Large Language Model (LLM) or a vector database.

## 4. Project Structure

```text
freighttiger-project/
├── main.py
├── shipment_records.csv
├── context_notes.csv
├── sample_output_format_v2.csv
├── output.csv
└── README.md
```

## 5. Requirements

- Python 3.10 or later recommended
- Pandas

Install Pandas using:

```bash
python -m pip install pandas
```

## 6. How to Run the Project

1. Install Python and Pandas.
2. Place `main.py` and the input CSV files in the same directory.
3. Open a terminal in the project directory.
4. Run the following command:

```bash
python main.py
```

5. The program reads the shipment records and context notes.
6. It processes the shipment data and generates `output.csv`.

## 7. How the System Works

### Step 1: Read Input Data

The program reads:

- `shipment_records.csv`: Shipment details, including route, quantity, distance, freight cost, and shipment date.
- `context_notes.csv`: Notes describing possible reasons for transportation cost changes.

### Step 2: Group Shipments

Shipment records are grouped by:

- Origin and destination
- Route type (Short, Medium, or Long)
- Week of shipment

Weeks run from Monday to Sunday. The `week_of` field represents the Monday of the relevant week.

### Step 3: Calculate Cost per Tonne-Kilometre

The formula is:

Cost per tonne-kilometre = Total freight cost / Total tonne-kilometres

For each shipment:

Tonne-kilometres = Quantity in tonnes × Distance in kilometres

Weekly route costs are calculated using the total freight cost divided by the total tonne-kilometres for that route and week.

### Step 4: Compare Historical Costs

The current week's cost is compared with the route's previous costs.

The assignment requires a trailing eight-week historical average using only weeks before the current week. When fewer than eight prior weeks are available, the available history should be used.

### Step 5: Compare Similar Routes

The current week's cost is compared with the average cost of other routes of the same route type during that week.

The route being evaluated must be excluded from its own peer average.

### Step 6: Detect Unusual Increases

The current implementation uses a configurable 10% threshold above either available baseline to identify candidate increases.

This threshold is an implementation choice, not a threshold specified in the assignment. It must be validated and documented before submission.

### Step 7: Check Context Notes

The program checks the available context notes for a possible explanation.

A note should only justify an increase when its content, route applicability, and date range support that explanation.

If no suitable note is found, the increase should remain unexplained rather than being assigned an invented reason.

### Step 8: Generate Output

The program writes the results to `output.csv`.

The expected output fields are:

- `route`
- `week_of`
- `cost_per_tonne_km`
- `vs_own_history`
- `vs_similar_routes`
- `flagged`
- `matched_note_id`
- `reason`

The output column names, order, and data types must match the supplied output template.

## 8. Testing and Validation

The following checks should be completed before submission:

- Verify that the weekly cost calculations are correct.
- Verify that weekly grouping uses Monday as the start of the week.
- Verify that the historical baseline does not include the current or future weeks.
- Verify that the peer baseline excludes the current route.
- Verify that matched notes support the relevant route and time period.
- Verify that unexplained increases have no unsupported note IDs.
- Verify that the output follows the required CSV schema.
- Run the program three times on identical input files and compare the outputs.

### Reproducibility Results

Update this section after completing the tests.

- Run 1: Pending
- Run 2: Pending
- Run 3: Pending
- Identical flags and numbers across all three runs: Pending

## 9. AI Usage and Limitations

The current implementation uses deterministic Python calculations and rule-based context-note matching.

It does not currently implement:

- Vector database retrieval
- Retrieval-Augmented Generation (RAG)
- LLM-generated explanations
- Natural-language question answering

These can be added as enhancements after the core calculations and note-matching logic have been validated.

## 10. Token and Cost Log

The current implementation does not make LLM calls.

For the current rule-based run:

- LLM input tokens: 0
- LLM output tokens: 0
- LLM calls: 0
- LLM cost: 0

If an LLM is added later, record the actual token usage, number of calls, model used, published pricing, and estimated cost for one complete run.

## 11. Assumptions and Limitations

- The 10% anomaly threshold is configurable and requires validation.
- Historical averages must follow the assignment's trailing eight-week definition.
- Missing weeks must be handled consistently with the documented baseline method.
- Context notes must be matched using the actual route applicability, dates, and content.
- A cost increase without supporting evidence must not be given a fabricated explanation.
- Results must be checked against the supplied examples and other validation cases.

## 12. Future Improvements

- Improve context-note retrieval and route/date matching.
- Add an evaluation dataset with expected results.
- Add automated tests for historical and peer baselines.
- Add evidence-grounded AI explanations.
- Add a natural-language interface for asking questions about detected cost increases.

## 13. Conclusion

This project provides a starting point for monitoring transportation costs, comparing weekly route performance, and identifying unusual increases.

Before final submission, the calculation logic, anomaly threshold, context-note matching, output format, and reproducibility results must be validated against the assignment requirements.
