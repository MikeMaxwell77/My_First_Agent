# Risk-Aware Banking Agent

An educational, plain-Python prototype for investigating fake overdraft fees.
Customer 123 appears eligible; 456 already used a courtesy reversal; 999 is missing.
All names, accounts, transactions, and policies are fictional. This is not production banking software.

```text
User -> Application -> ModelClient -> proposed tool call
                           |
             Registry -> argument validation -> authorization/policy
                           |                         |
                      READ / WRITE            approval request
                           |                   (no funds moved)
                      observation -> ModelClient -> AgentResult
                           |
                     redacted JSONL trace
```

The model probabilistically chooses tools and writes the answer. Application code
owns the registry, schemas, simulated authentication, policy, execution, approvals,
limits, and logs. Each iteration calls the model, validates proposed calls, returns
observations, and stops at a final response or the limit (default 5, at most 8 calls
per iteration). OpenAI API code is isolated in `model_client.py`.

| Classification | Tools | Application behavior |
| --- | --- | --- |
| READ | get_customer, get_transactions, search_policy, get_customer_history | Validate and authorize customer access |
| WRITE | create_case_note | Require write permission and an existing customer |
| CONSEQUENTIAL | request_fee_reversal | Check fee ownership, exact amount and eligibility; create PENDING approval |

Approvals and case notes live in `BankSession`. Trusted Python callers can review
approvals with `session.review(id, approved=True, employee=True)`; review is never a
model tool. APPROVED and DENIED are recorded decisions only. There is no financial
execution path. Identity is supplied by the application, never extracted from a prompt.

## Setup and tests

Requires Python 3.10+ (verified here with 3.14).

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

Tests use scripted clients and never make paid API calls. For one optional API
smoke request: `python -c "from tests.test_llm import main; main()"`.
It skips if no key exists and disables retries. Store `OPENAI_API_KEY` in the ignored
`.env` file or environment. Optional `OPENAI_MODEL` overrides the preserved project
default `gpt-5.6-luna`; availability depends on your account.

## One interaction

```powershell
python agent.py "Determine whether customer 123 is eligible for an overdraft reversal."
python agent.py "Investigate and request reversal for customer 123."
python agent.py "Determine whether customer 456 is eligible." --customer-id 456
```

The CLI defaults to a simulated login for customer 123. `--customer-id` is a trusted
demo login selector, not real authentication. Use `--no-log` to disable file traces.
Library calls use `run_agent(prompt, client=stub)` and return an `AgentResult`
dataclass; `.to_dict()` serializes it. File logging is opt-in in library calls.

## Evaluations and experiments

```powershell
python -m evals.run
python -m evals.experiment --runs 10 --case eligible_123
python evals/view_results.py
```

Defaults run scripted offline fixtures, labeled **harness checks**, not model
reliability measurements. They write `logs/eval_results.jsonl`,
`logs/experiment_results.jsonl`, and an experiment summary JSON. Traces append to
`logs/traces.jsonl`; each run has a unique trace ID. Result files overwrite their
selected destination. Use `--output` to keep separate experiment datasets.

Explicit paid model runs (not run automatically):

```powershell
python -m evals.run --live --case eligible_123
python -m evals.experiment --live --runs 10 --case eligible_123
```

Fifteen cases cover normal, edge, service failure, adversarial, authorization, and
hallucination scenarios. Outcome checks grade the structured determination and
selected final-answer claims. Trajectory checks independently grade evidence,
authorization, approvals, and bounds without imposing a fixed read-tool order.
Per-invariant PASS/FAIL booleans and failure reasons appear in JSONL and the existing
HTML report. A correct answer with insufficient evidence fails its trajectory.

Failure injection is trusted application configuration: pass
`failures={"get_transactions": "unavailable"}` or `{"get_customer": "malformed"}`
to `run_agent`. Policy service failure uses `search_policy`. Repeated requests are
simulated by a scripted model, and unknown customers use the fake data directly.

See [architecture](docs/architecture.md) for decision ownership and limitations,
and [implementation report](docs/overnight_report.md) for validation and interview notes.
