---
name: agent-evaluation
description: Revise this learning project's offline tests and evaluation logs, including token tracking.
---

# Agent Evaluation for a Learning Project

Keep the suite small and readable, using plain Python and pytest. Apply this
guidance to testing and evaluation logging, not database tool design.

## Tests and evaluations

- Use fake model responses and mocked tools in tests; no paid API calls or live
  database access during pytest runs.
- Check final responses and execution trajectories together: tool names,
  arguments, results/errors, and the iteration limit.
- Keep live behavioral evaluations in `evals/` as manually invoked runs.
  Review whether answers follow policy and are supported by tool results.
  A plausible answer or short runtime alone does not prove correctness.

## Minimal evaluation record

Keep the existing JSONL format and field names:

- `case_id`, `model`, `prompt`, and `final_answer`
- `tools_called`: ordered tool names
- `tool_calls`: ordered tool names, arguments, and results or errors
- `iteration_count` and `latency_seconds`
- `token_usage`: `input_tokens`, `output_tokens`, and `total_tokens`, summed
  across every model response, including the final answer and runs that reach
  the iteration limit. Use API-reported counts, not text-length estimates.
  If any response lacks usage, record `null` for the run rather than partial
  totals. Older logs may omit this field.

Simple synchronous JSONL writing is sufficient. Do not require schema libraries,
async logging, trace IDs, outcome enums, or a telemetry framework for this
prototype. Add complexity only for a concrete learning goal.
Never log credentials. Consider payload caps if log size becomes a problem.
