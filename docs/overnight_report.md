# Overnight implementation report

## Implemented

- Six explicitly registered tools with READ, WRITE and CONSEQUENTIAL classifications.
- Provider-independent dataclasses, a bounded loop, strict arguments, scoped customer
  authorization and deterministic reversal validation.
- In-memory notes and idempotent approval requests, with trusted employee review and
  PENDING/APPROVED/DENIED states. No financial execution exists.
- Redacted observable JSONL traces and structured run results.
- Fifteen behavioral cases, separate outcome/trajectory invariants, offline fixtures,
  opt-in live evaluations, and repeated experiments with per-case frequencies.
- Preserved OpenAI Responses integration, tool tests, and HTML report generator;
  added grade details to the existing report without adding a new UI.

## Branch and architectural decisions

Created `feature/risk-aware-banking-agent` directly from local `development`.
The active `testing-scenarios` branch contained later working agent/evaluation code,
so those source files were carried forward before extending them. Changes are grouped
into core architecture, evaluation/testing, and documentation commits.

Plain Python and dataclasses keep execution decisions visible. `ToolSpec` contains
metadata, while `check_policy` owns authorization. CONSEQUENTIAL tools have no
handler; the loop can only create approval records. A `BankSession` isolates mutable
notes/approvals and can be deliberately reused by an application caller.

## Assumptions

- Fake names/data from the original repository remain fictional fixtures.
- Default identity is customer 123. The application can explicitly authorize other
  IDs, including nonexistent 999 for missing-customer tests.
- The CLI identity selector and employee flag simulate authentication; neither is
  a production security mechanism.
- The existing model default is preserved and can be configured by environment.
- Default evaluation commands are offline to avoid accidental paid batches.
- Existing `ReadMe.MD` casing is retained on Windows rather than creating a duplicate.
- Existing saved evaluation logs/reports are preserved; validation used `risk_` files.

## Validation and failures

- Final deterministic test suite: **58 passed**, with no API calls.
- Offline evaluation: **15/15 passed**, outcome and trajectory rates both 100%, zero
  policy violations or unauthorized executions. This measures fixture/harness
  behavior, not probabilistic model reliability.
- Repeated offline experiment: two trials each of eligible_123 and request_reversal,
  four results, all passed. JSONL and aggregate/per-case summary generation verified.
- HTML report generated successfully from the new evaluation schema at
  `logs/risk_eval_report.html`.
- Exactly one basic API smoke request was attempted because credentials were available.
  It failed with `APIConnectionError`; no retry or large paid batch was performed.
  Live model behavior remains unverified in this environment.
- Initial test collection exposed a Windows text-encoding issue; converted the source
  to UTF-8/ASCII. Pytest temporary-directory access was blocked by the sandbox;
  running the same offline tests with normal filesystem access passed.
- Final checks include compilation through test imports, provider adapter stubs,
  malformed/nonfinite arguments, unknown tools, customer scope, approval review,
  repeated requests, tool/model errors, redaction, and independent grader failures.

## Known limitations

The prototype is not production-ready. Approvals and notes are in memory, authorization
is simulated, and policy/history are static snapshots. The model can still give a
wrong final answer; deterministic controls protect side effects and evaluation makes
some answer failures visible. Text grading and secret redaction are heuristics,
not comprehensive proofs. Custom model clients must implement their own timeouts.
There is no concurrent approval handling or execution after approval. No financial
service, framework, database, or new frontend was added.

## Recommended next experiments

1. Run one explicitly selected live eligibility case after resolving API connectivity.
2. Repeat that case ten times and inspect outcome/evidence variability.
3. Compare normal requests with injection and unavailable-service variants.
4. Manually review paraphrased hallucinations that heuristic text checks can miss.
5. Compare model configurations using separate output files and per-case summaries.

## How to explain this system in an interview

1. The model proposes actions; application code owns execution.
2. A fixed registry defines tools, schemas and risk classifications.
3. Strict validation rejects malformed and unexpected arguments.
4. Trusted caller context controls customer access independently of prompts.
5. Read, write and consequential requests follow different policy paths.
6. Consequential requests create human approvals and never move money.
7. A five-iteration loop and batch limit bound agent activity.
8. Typed results and redacted traces expose observable execution without hidden reasoning.
9. Deterministic tests verify controls; behavioral evals separate answers from trajectories.
10. Repeated live trials can measure model variability; scripted trials only validate the harness.

## Final project tree

```text
My_First_Agent/
|-- AGENTS.md
|-- ReadMe.MD
|-- requirements.txt
|-- pytest.ini
|-- data.py
|-- tools.py
|-- policy.py
|-- structures.py
|-- tracing.py
|-- model_client.py
|-- agent.py
|-- test_tools.py                 # original development demo
|-- tests/
|   |-- test_tools.py
|   |-- test_llm.py               # manual smoke only
|   |-- test_model_client.py
|   `-- test_agent.py
|-- evals/
|   |-- __init__.py
|   |-- cases.json
|   |-- grading.py
|   |-- stubs.py
|   |-- run.py
|   |-- run_evals.py              # compatibility entry point
|   |-- experiment.py
|   `-- view_results.py
|-- docs/
|   |-- architecture.md
|   `-- overnight_report.md
`-- logs/                        # ignored generated artifacts
    |-- traces.jsonl
    |-- risk_eval_results.jsonl
    |-- risk_eval_report.html
    |-- risk_experiment.jsonl
    `-- risk_experiment.summary.json
```

Environment files, dependencies, caches, Git internals and historical generated
reports are omitted from this source tree.
