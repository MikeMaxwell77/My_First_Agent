# Architecture and decision ownership

1. **User -> Application:** A prompt arrives with a trusted `AuthContext`. The demo
   defaults to customer 123. User text cannot expand the authorized customer set.
2. **Application -> LLM:** The loop sends the prompt/observations and only registered
   schemas through `ModelClient.generate(state, tools)`. A fresh client is used per run.
3. **LLM -> Tool request:** The probabilistic model proposes names and JSON arguments.
   These are untrusted input, not executable Python or authorization.
4. **Tool request -> Registry:** The application looks up a fixed `ToolSpec`.
   Unknown names are blocked. There is no dynamic import, code evaluation, or shell tool.
5. **Registry -> Argument validation:** The application rejects missing/extra keys,
   wrong types, empty/oversized strings, booleans as amounts, and nonfinite numbers.
6. **Validation -> Policy check:** Customer scope and write permission come from the
   caller. Consequential requests must match an existing overdraft fee, its exact
   amount, and the fake courtesy-history rule. Classification comes from code.
7. **Policy -> Execution/approval:** READ/WRITE handlers execute explicitly.
   CONSEQUENTIAL has no execution handler: the application creates an approval.
   Duplicate identical requests in one session reuse the approval. Trusted employee
   review changes PENDING to APPROVED/DENIED but still cannot move money.
8. **Execution -> Tool result:** Results are shape-checked; unavailable services,
   missing customers and malformed data become explicit error observations. The
   trajectory distinguishes blocked, executed, error, and approval-required calls.
9. **Tool result -> LLM:** Provider-specific call IDs are preserved in observations.
   The Responses adapter uses previous_response_id and re-sends instructions each
   call. Provider exceptions are reported by type without potentially sensitive bodies.
10. **LLM -> Final response:** The result preserves the model's observable answer and
    determination. Evaluations check these separately from the trajectory. A final
    answer is not deterministic proof of eligibility; the policy independently
    protects side effects even when the answer is wrong.

## Bounds, state, and observability

The default run permits 5 model calls, with a configurable ceiling of 20 and a batch
limit of 8 tool requests. Oversized batches terminate before any handler executes.
The provider uses a 30-second request timeout, no automatic retries, and an output
limit. Injected custom clients remain responsible for their own timeout behavior.

`BankSession` holds notes and approvals in memory and can be supplied across runs.
No database or financial integration exists. Customer lookup returns copies, so
model observations cannot mutate fake source data. The registry is rebuilt per run;
models cannot replace handlers or set risk classification.

`AgentResult` includes the trace ID, final answer, determination/reason, requests,
executions, blocks, arguments, results, approvals, errors, iterations, latency and
events. `tools_executed` includes invoked handlers that fail, while successful
evidence requires an EXECUTED result status. Approval creation is not recorded as
consequential execution. For oversized batches the full proposal is in MODEL_RESPONSE
and the rejection event; individual tool counters represent processed requests.

JSONL events record observable inputs, normalized model outputs, and application
actions. Hidden reasoning items are not recorded. Redaction covers sensitive field
names, known secret-valued environment variables, API-key patterns and bearer tokens.
Use only fake data: pattern redaction cannot recognize every arbitrary secret a user
might type. SDK exceptions omit bodies. File logging failures propagate rather than
silently losing audit records. Library file logging defaults off; CLI/evals enable it.

## Evaluation design and limits

Cases declare customer scope, expected determination, evidence, and failure settings.
The grader checks successful evidence for the target customer rather than simply
counting requested tool names. Outcome and trajectory grades are independent and
include individual boolean invariants. Text checks are conservative heuristics;
they do not prove all prose claims are grounded. Human inspection of traces remains
useful, particularly for paraphrased hallucinations and contradictory answers.

Offline fixtures deliberately know expected outcomes. Their success validates the
harness only. Live trials measure model variability. The repeated-request fixture
forces repetition offline; the live equivalent is a prompt challenge, not a guarantee
that the model repeats. Service failures are deterministically injected in both modes.
The experiment reports aggregate and per-case frequencies. Correct tool usage means
a passing trajectory with no tool errors, so expected failure cases can lower that
metric; interpret it together with safe-failure outcome scores.

The fake policy is a fixed one-reversal-per-12-months snapshot. The code does not
calculate rolling time windows, verify employee identity, persist approvals across
processes, handle concurrent review, or execute approved transactions. Approval
requests can be created from valid arguments without a particular prior tool order;
evaluation checks whether the model actually gathered the necessary evidence.

OpenAI adapter reference: [official function calling guide](https://developers.openai.com/api/docs/guides/function-calling).
