I am building a simple coding agent with rag, tools, obervables, and security protocols.

## View evaluation results

After running `python evals/run_evals.py`, generate a local report with:

```powershell
python evals/view_results.py
```

Open `logs/eval_report.html` in a browser. The report reads the saved
`logs/eval_results.jsonl` file and shows latency plus iteration and tool-call
counts for each case. Expand a case to inspect its prompt, final answer, and
tools used. These are execution metrics; the current JSONL does not contain
correctness grades. Generating the report does not call the model.

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

This adds five fictional customers and six transactions each (30 total),
using parameterized SQL. All inserts commit together; a failure rolls back
the batch. The script prints the inserted customer IDs and verifies the
transaction count before committing. Each run adds another batch, so rerunning
will create duplicate sample customers. Existing records are preserved.
The transactions are illustrative samples, not complete account histories.

## Contributors

- Codex (OpenAI) — evaluation results report
