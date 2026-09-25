"""Bounded application-owned execution of model-proposed banking tools."""
import argparse
from dataclasses import asdict
import json
import time
from uuid import uuid4

from model_client import OpenAIModelClient
from policy import AuthContext, check_policy
from structures import AgentResult
from tools import BankSession, build_registry, validate_result
from tracing import TraceRecorder, redact

MAX_CALLS_PER_ITERATION = 8


def run_agent(prompt, client=None, *, auth=None, session=None, model=None,
              max_iterations=5, trace_path=None, failures=None):
    """Failures is a trusted test hook: tool name -> unavailable or malformed.

    A fresh provider client belongs to one run. Authorization never comes from
    the prompt. File logging is opt-in; sanitized in-memory events always exist.
    """
    if type(max_iterations) is not int or not 1 <= max_iterations <= 20:
        raise ValueError("max_iterations must be between 1 and 20")
    started = time.perf_counter()
    result = AgentResult(trace_id=str(uuid4()))
    recorder = TraceRecorder(result.trace_id, trace_path)
    session = session if session is not None else BankSession()
    auth = auth if auth is not None else AuthContext()
    registry = build_registry(session)
    definitions = [spec.definition() for spec in registry.values()]
    state = [{"input": prompt}]
    failures = failures or {}

    for iteration in range(1, max_iterations + 1):
        result.iteration_count = iteration
        recorder.record("MODEL_REQUEST", iteration=iteration, input=state[-1]["input"], tools=definitions)
        try:
            if client is None:
                client = OpenAIModelClient(model=model)
            response = client.generate(state, definitions)
            recorder.record("MODEL_RESPONSE", iteration=iteration, response=asdict(response))
        except Exception as exc:
            # Exception bodies can contain provider headers or credentials.
            error = f"Model request failed ({type(exc).__name__})"
            result.errors.append(error)
            recorder.record("MODEL_ERROR", error=error)
            result.reason = error
            break

        if not response.calls:
            result.final_answer = response.final_answer
            result.determination = response.determination
            result.reason = response.reason
            break
        if len(response.calls) > MAX_CALLS_PER_ITERATION:
            result.errors.append("Tool batch limit exceeded")
            result.reason = result.errors[-1]
            recorder.record("TOOL_BLOCKED", reason=result.reason, count=len(response.calls))
            break

        observations = []
        for call in response.calls:
            result.tools_requested.append(call.name)
            record = {"tool": call.name, "arguments": call.arguments, "status": "BLOCKED"}
            recorder.record("TOOL_REQUESTED", tool=call.name, arguments=call.arguments)
            try:
                spec = registry.get(call.name)
                if spec is None:
                    raise ValueError("Unknown tool name")
                arguments = json.loads(call.arguments)
                record["arguments"] = arguments
                spec.validate(arguments)
                decision = check_policy(spec, arguments, auth)
            except (ValueError, TypeError, PermissionError) as exc:
                output = {"error": str(exc)}
                result.tools_blocked.append(call.name)
                recorder.record("TOOL_BLOCKED", tool=call.name, reason=str(exc))
            else:
                recorder.record("TOOL_ALLOWED", tool=call.name, decision=decision, risk=spec.risk)
                if decision == "APPROVAL":
                    # No consequential handler is invoked, even if the model asks.
                    output = session.request_fee_reversal(**arguments)
                    record["status"] = "APPROVAL_REQUIRED"
                    if not any(a["approval_id"] == output["approval_id"] for a in result.approval_requests):
                        result.approval_requests.append(output)
                    recorder.record("APPROVAL_CREATED", approval=output)
                else:
                    try:
                        result.tools_executed.append(call.name)
                        recorder.record("TOOL_EXECUTED", tool=call.name, arguments=arguments, risk=spec.risk)
                        if failures.get(call.name) == "unavailable":
                            raise RuntimeError("Simulated service unavailable")
                        output = None if failures.get(call.name) == "malformed" else spec.handler(**arguments)
                        validate_result(call.name, output)
                        record["status"] = "EXECUTED"
                    except Exception as exc:
                        output = {"error": f"Tool failed ({type(exc).__name__})"}
                        record["status"] = "ERROR"
                        recorder.record("TOOL_ERROR", tool=call.name, error=output["error"])
            record["result"] = output
            if isinstance(output, dict) and "error" in output:
                record["error"] = output["error"]
                result.errors.append(output["error"])
            result.tool_calls.append(redact(record))
            result.tool_arguments.append(redact(record["arguments"]))
            result.tool_results.append(redact(output))
            recorder.record("TOOL_RESULT", tool=call.name, result=output, status=record["status"])
            observations.append({"type": "function_call_output", "call_id": call.call_id,
                                 "output": json.dumps(output)})
        state.append({"input": observations})
    else:
        result.reason = "Maximum iteration limit reached"
        result.errors.append(result.reason)

    if not result.final_answer:
        result.final_answer = "I could not determine the answer safely. " + result.reason
    result.latency_seconds = round(time.perf_counter() - started, 4)
    recorder.record("FINAL_RESPONSE", final_answer=result.final_answer,
                    determination=result.determination, reason=result.reason,
                    iteration_count=result.iteration_count, latency_seconds=result.latency_seconds)
    result.events = recorder.events
    return result


def main():
    from dotenv import load_dotenv
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt")
    parser.add_argument("--customer-id", default="123", help="Simulated authenticated customer")
    parser.add_argument("--trace-path", default="logs/traces.jsonl")
    parser.add_argument("--no-log", action="store_true")
    args = parser.parse_args()
    result = run_agent(args.prompt, auth=AuthContext(frozenset({args.customer_id})),
                       trace_path=None if args.no_log else args.trace_path)
    print(json.dumps(redact(result.to_dict()), indent=2))


if __name__ == "__main__":
    main()
