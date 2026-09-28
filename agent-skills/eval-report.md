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
  configurable charts, and expandable case details. Details include the case
  name (when present), category, tags, prompt, final answer, tools called, and
  the tool-call trace.
- A chart can use any finite numeric value saved for a case, including nested
  token usage, or the derived tool-call count. Users can add multiple charts
  and choose bar, line, or pie for each. Cases missing the selected metric are
  counted and omitted from that chart. Pie charts require nonnegative values
  with a positive total and show each case's share. Line charts connect cases
  in the saved result order; they do not imply a time series.
- Clicking a bar, line dot, pie slice, or pie legend item opens the matching
  case in the details list, scrolls to it, and highlights it briefly. Chart
  points support Enter and Space for keyboard use.
- Category and tag selectors filter all charts and case details together.
  Included tags all must match; any excluded tag removes a case. The report
  groups tag controls by their prefix in a separate, taller expandable section
  and shows how many cases match. Older log entries without category, name,
  tags, or token usage still render.
- The report does not grade answers for correctness. Latency and tool activity
  describe execution, not whether the agent followed policy.

## When editing

Keep HTML text escaped and embedded chart data safe for a `<script>` element.
`evals/report_script.js` is embedded into the generated HTML so the report
still opens as one file. Retain support for existing JSONL logs that lack newer
metadata. Test rendering with saved or synthetic results; report tests must not
call the model or database.
