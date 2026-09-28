---
name: eval-report
description: Maintain the bank agent's local HTML evaluation report built from saved JSONL results.
---

# Evaluation Report

Use this guidance when changing `evals/view_results.py` or the report generated
by `evals/run_evals.py`. Keep the report self-contained and readable in a browser.

## Current behavior

- `python evals/run_evals.py` writes `logs/eval_results.jsonl` and refreshes
  `logs/eval_report.html` after a completed evaluation run. This command calls
  the model.
- `python evals/view_results.py` rebuilds the report from saved JSONL without
  calling the model. It accepts optional input and output paths.
- `evals/eval_report.html` is maintained manually. Do not update it as part of
  report generation.
- The report shows the model and case count, average latency and tool calls,
  latency and activity charts, and expandable case details. Details include
  the case name (when present), category, tags, prompt, final answer, tools
  called, and the tool-call trace.
- Category and tag selectors can be combined. They filter both charts and case
  details, and the report shows how many cases match. Older log entries without
  category, name, or tags still render.
- The report does not grade answers for correctness. Latency and tool activity
  describe execution, not whether the agent followed policy.

## When editing

Keep HTML text escaped, and retain support for existing JSONL logs that lack
newer metadata. Test rendering with saved or synthetic results; report tests
must not call the model or database.
