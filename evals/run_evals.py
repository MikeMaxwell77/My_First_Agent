"""Run all five evaluation cases and save one result per JSON line."""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent import TOOL_REGISTRY, run_agent  # noqa: E402


def unavailable_tool(**_arguments):
    raise RuntimeError("Transaction data unavailable")


def main():
    load_dotenv(ROOT / ".env")
    cases = json.loads((ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))
    log_path = ROOT / "logs" / "eval_results.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    results = []

    with log_path.open("w", encoding="utf-8") as log_file:
        for case in cases:
            registry = dict(TOOL_REGISTRY)
            for tool_name in case.get("unavailable_tools", []):
                registry[tool_name] = unavailable_tool

            run = run_agent(case["prompt"], tool_registry=registry)
            result = {
                "case_id": case["case_id"],
                "prompt": case["prompt"],
                "final_answer": run["final_answer"],
                "tools_called": [call["tool"] for call in run["tool_calls"]],
                "tool_calls": run["tool_calls"],
                "iteration_count": run["iteration_count"],
                "latency_seconds": run["latency_seconds"],
            }
            log_file.write(json.dumps(result) + "\n")
            results.append(result)

    print(f"Ran {len(results)} cases; wrote {log_path}")
    for result in results:
        tools = ", ".join(result["tools_called"]) or "none"
        print(f"- {result['case_id']}: {result['iteration_count']} iterations, tools: {tools}")


if __name__ == "__main__":
    main()
