### Skill: Agent Evaluation & Telemetry Suite Generator

#### Role & Purpose
Provides standard schema specifications, metrics tracking guidelines, and structured logging formats for agent execution evaluation suites.

#### Trigger Criteria
- User requests code generation, architecture design, or schema definitions for logging, tracing, or evaluating agent execution outputs.
- Applies to creating evaluation datasets, benchmark logging, or offline diagnostic runs.
- DO NOT trigger for live database query tools or operational runtime tool wrappers.

#### Schema & Recorded Metrics
Each evaluation record must be logged as a validated JSON object or line-delimited JSON (JSONL) entry with the following typed fields:

1. **Session Identifiers:**
   - `trace_id` (string/UUID): Unique identifier for the execution trace.
   - `timestamp` (string/ISO-8601): UTC timestamp of invocation.
2. **Input / Output Payload:**
   - `user_input` (string): The raw prompt or user query provided to the agent loop.
   - `final_response` (string): The generated output returned to the user.
   - `outcome_status` (string/Enum): Standardized result indicator (`"SUCCESS"`, `"FAILURE"`, `"HANDLED_ERROR"`).
   - `task_metadata` (object/dict): Flexible key-value store for domain-specific metrics (e.g., `{"fee_reversal_applied": true}`).
3. **Execution & Tool Telemetry:**
   - `iterations` (integer): Total number of model calls / loop iterations executed.
   - `tools_called` (array of objects): Ordered list of invoked tools:
     - `tool_name` (string): Name of the invoked tool.
     - `arguments` (object): Parameters supplied to the tool call.
     - `result_status` (string): `"SUCCESS"` or `"ERROR"`.
4. **Performance & Token Metrics:**
   - `latency_ms` (integer): End-to-end execution time in milliseconds.
   - `token_usage` (object): `{"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}`.

#### Operational Constraints
- **Asynchronous Logging:** Telemetry recording MUST run non-blocking (asynchronously) so logging overhead does not bloat end-user latency.
- **Payload Truncation:** Large tool results or prompt histories MUST be capped/truncated (e.g., max 2,000 characters per field) before persisting to evaluation storage.
- **Schema Validation:** Logged items MUST pass JSON Schema or Pydantic validation before writing to log sinks to prevent corrupt evaluation datasets.