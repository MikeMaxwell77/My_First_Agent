I am building a simple coding agent with rag, tools, obervables, and security protocols.

## View evaluation results

Run the evaluations and update the local report with:

```powershell
python evals/run_evals.py
```

Open `logs/eval_report.html` in a browser. The report reads the saved
`logs/eval_results.jsonl` file. Add bar, line, or pie charts for any numeric
case metric, including token usage and tool-call count. Include or exclude tags
and filter by category; the filters apply to all charts and case details. Expand
a case to inspect its prompt, final answer, and tools used. These are execution
metrics; the current JSONL does not contain correctness grades. Running
evaluations calls the model and may incur API costs.

Tag filters have their own expandable section, grouped by tag category such as
Customer, Tool, and Attack.

Click a bar, line dot, or pie slice to open and briefly highlight its case in
the details list. Pie legend entries also link to their cases.
Cases are blue by default, or red when a tool reports an error. The report
shows tool names and error codes in the details; use **Only cases with tool
errors** to focus on them. In **Case colors**, assign a suggested or custom
color to a category or tag. Tag rules take priority over category rules, and
the **All** category target colors every case. **Clear all colors** restores
the blue and red defaults.

To rebuild the report from saved results without calling the model, run
`python evals/view_results.py`.

To use other files, pass the input JSONL path and optional output HTML path:

```powershell
python evals/view_results.py path/to/results.jsonl path/to/report.html
```

## Seed the PostgreSQL database

After creating the tables with `database/schema.sql` and setting
`DATABASE_URL` in `.env`, run from the project root with your virtual
environment active:

```powershell
python -m database.seed
```

This adds five fictional customers, six transactions each (30 total), and
two fictional policies,
using parameterized SQL. All inserts commit together; a failure rolls back
the batch. The script prints the inserted customer IDs and verifies the
transaction count before committing. Each run adds another batch, so rerunning
will create duplicate sample customers. Existing records are preserved.
The transactions are illustrative samples, not complete account histories.
To add only the policies to an existing database, run
`python -m database.seed --policies-only`. Policy titles are checked before
insertion and existing policy content is refreshed, so running either command
again does not duplicate those policies.

## Database tools

`get_customer`, `get_transaction`, `get_transactions`, and `search_policy` in `tools.py` read
PostgreSQL using `DATABASE_URL`. Customer IDs are positive BIGINT values passed
as strings (for example, `"1"`). `get_transaction("1")` retrieves a single
transaction by its transaction ID, also a positive BIGINT passed as a string
(maximum `9223372036854775807`). Policy topics are literal, case-insensitive
substrings of the category, title, or content, with 1 to 200 nonblank characters.

Each tool returns a JSON string with `status`, `data`, and `truncated` on
success, or `status: "error"`, `code`, and `message` on failure. Transactions
are ordered newest first. Lists contain at most 50 rows; text fields are capped
at 4,000 characters. Truncated results must not be treated as complete evidence.
Amounts are decimal strings and dates use ISO format.

The seed script populates overdraft reversal and transaction dispute policies.
The tools do not fall back to `data.py`.

Run the deterministic tests with `python -m pytest tests -q`. Database access
is mocked, so these tests require neither a running database nor paid API calls.

## Contributors

- Codex (OpenAI) — evaluation results report
