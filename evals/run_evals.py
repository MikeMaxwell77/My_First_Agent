"""Run evaluation cases and save JSONL results and an HTML report."""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent import TOOL_REGISTRY, run_agent  # noqa: E402
from evals.view_results import build_report  # noqa: E402


def unavailable_tool(**_arguments):
    raise RuntimeError("Tool unavailable for this evaluation case")


def repeating_customer_client(customer_id):
    """Script repeated model calls to exercise the agent's iteration limit."""
    count = 0

    def create(**_request):
        nonlocal count
        count += 1
        call = SimpleNamespace(
            type="function_call", name="get_customer",
            arguments=json.dumps({"customer_id": customer_id}),
            call_id=f"repeat-{count}",
        )
        return SimpleNamespace(
            id=f"repeat-response-{count}", output=[call],
            output_text="", usage=None,
        )

    return SimpleNamespace(responses=SimpleNamespace(create=create))


def main():
    load_dotenv(ROOT / ".env")
    cases = json.loads((ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    log_path = ROOT / "logs" / "eval_results.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    results = []

    with log_path.open("w", encoding="utf-8") as log_file:
        for case in cases:
            registry = dict(TOOL_REGISTRY)
            for tool_name in case.get("unavailable_tools", []):
                registry[tool_name] = unavailable_tool

            behavior = case.get("setup", {}).get("model_behavior")
            client = repeating_customer_client("1") if behavior == "repeat_get_customer" else None
            run = run_agent(case["prompt"], client=client,
                            tool_registry=registry, model=model)
            result = {
                "case_id": case["id"],
                "category": case["category"],
                "name": case["name"],
                "tags": case["tags"],
                "model": "scripted:repeat_get_customer" if client else model,
                "prompt": case["prompt"],
                "final_answer": run["final_answer"],
                "tools_called": [call["tool"] for call in run["tool_calls"]],
                "tool_calls": run["tool_calls"],
                "iteration_count": run["iteration_count"],
                "latency_seconds": run["latency_seconds"],
                "token_usage": run["token_usage"],
            }
            log_file.write(json.dumps(result) + "\n")
            results.append(result)

    report_path = ROOT / "logs" / "eval_report.html"
    report_path.write_text(build_report(results), encoding="utf-8")
    print(f"Ran {len(results)} cases; wrote {log_path}")
    print(f"Wrote {report_path}")
    for result in results:
        tools = ", ".join(result["tools_called"]) or "none"
        usage = result["token_usage"]
        tokens = usage["total_tokens"] if usage is not None else "unavailable"
        print(f"- {result['case_id']}: {result['iteration_count']} iterations, "
              f"tools: {tools}, tokens: {tokens}")


if __name__ == "__main__":
    main()
