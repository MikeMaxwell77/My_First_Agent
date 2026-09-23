# Bank Agent Project

## Purpose

Educational prototype for learning LLM agent architecture,
tool calling, evaluation, and observability.

## Architecture

- `data.py` — fake banking data
- `tools.py` — deterministic tools available to the LLM
- `agent.py` — model interaction and agent loop
- `tests/` — deterministic tests
- `evals/` — behavioral AI evaluations
- `logs/` — generated evaluation traces

## Engineering Rules

- Keep the architecture simple.
- Prefer plain Python.
- Do not introduce frameworks unless explicitly requested.
- LLMs may request tools but application code executes them.
- Only explicitly registered tools may execute.
- Agent execution must be bounded.
- Tool failures must not be converted into invented information.
- Never hardcode or log credentials.
- Tests must not make paid API calls unless explicitly requested.

## Evaluation

Agent evaluation should inspect both:
1. final response
2. execution trajectory

Record tool names, arguments, results/errors, iteration count,
latency, and final response.