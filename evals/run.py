"""Run behavioral evaluations. Default is offline; --live explicitly incurs API usage."""
import argparse
import json
import os
from pathlib import Path
from statistics import mean
from agent import run_agent
from policy import AuthContext
from tracing import redact
from evals.grading import grade
from evals.stubs import ScriptedModel

ROOT = Path(__file__).resolve().parents[1]


def load_cases(selected=None):
    cases = json.loads((ROOT / "evals/cases.json").read_text(encoding="utf-8"))
    if selected:
        unknown = set(selected) - {c["case_id"] for c in cases}
        if unknown:
            raise ValueError(f"Unknown cases: {sorted(unknown)}")
        cases = [c for c in cases if c["case_id"] in selected]
    return cases


def run_case(case, live=False):
    result = run_agent(case["prompt"], client=None if live else ScriptedModel(case),
        auth=AuthContext(frozenset(case["authorized_customers"]), case.get("can_write", True)),
        failures=case.get("failures"), trace_path=ROOT / "logs/traces.jsonl")
    row = result.to_dict()
    row.pop("events")
    row.update(case_id=case["case_id"], category=case["category"], prompt=case["prompt"],
               model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna") if live else "scripted-offline",
               expected_invariants={k: v for k, v in case.items() if k not in {"prompt", "case_id"}},
               tools_called=result.tools_requested, final_structured_outcome={
                   "determination": result.determination, "reason": result.reason, "final_answer": result.final_answer},
               **grade(case, result))
    return redact(row)


def summarize(rows):
    def percent(key):
        return round(100 * mean(r[key] for r in rows), 2)
    return {"cases": len(rows), "passed": sum(r["overall_pass"] for r in rows),
            "failed": sum(not r["overall_pass"] for r in rows),
            "outcome_success_percent": percent("outcome_pass"),
            "trajectory_success_percent": percent("trajectory_pass"),
            "policy_violations": sum(r["policy_violations"] for r in rows),
            "unauthorized_executions": sum(r["unauthorized_executions"] for r in rows),
            "average_iterations": mean(r["iteration_count"] for r in rows),
            "average_latency_seconds": mean(r["latency_seconds"] for r in rows)}


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--case", action="append")
    parser.add_argument("--output", type=Path, default=ROOT / "logs/eval_results.jsonl")
    args = parser.parse_args()
    if args.live and not os.getenv("OPENAI_API_KEY"):
        parser.error("Live evaluations require OPENAI_API_KEY")
    rows = [run_case(case, args.live) for case in load_cases(args.case)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    print("LIVE MODEL EVALUATION" if args.live else "OFFLINE HARNESS CHECK - not model reliability")
    print(json.dumps(summarize(rows), indent=2))


if __name__ == "__main__":
    main()
