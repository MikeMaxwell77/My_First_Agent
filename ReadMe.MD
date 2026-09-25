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

## Contributors

- Codex (OpenAI) — evaluation results report
