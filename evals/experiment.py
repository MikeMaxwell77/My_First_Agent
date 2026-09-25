"""Repeated trials; --live is required to measure probabilistic model variability."""
import argparse
import json
import os
from pathlib import Path
from statistics import mean
from evals.run import ROOT, load_cases, run_case, summarize


def reliability(rows):
    def frequency(test):
        return round(100 * mean(test(r) for r in rows), 2)
    return {**summarize(rows),
        "correct_outcome_percent": frequency(lambda r: r["outcome_pass"]),
        "required_evidence_percent": frequency(lambda r: r["trajectory_invariants"]["required_evidence"]),
        "correct_tool_usage_percent": frequency(lambda r: r["trajectory_pass"] and not r["errors"]),
        "policy_compliance_percent": frequency(lambda r: not r["policy_violations"] and not r["unauthorized_executions"]),
        "unauthorized_execution_percent": frequency(lambda r: bool(r["unauthorized_executions"])),
        "average_tool_calls": mean(len(r["tools_requested"]) for r in rows)}


def main():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--case", action="append")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "logs/experiment_results.jsonl")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    if args.live and not os.getenv("OPENAI_API_KEY"):
        parser.error("Live experiments require OPENAI_API_KEY")
    cases = load_cases(args.case)
    rows = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        for run in range(1, args.runs + 1):
            for case in cases:
                row = dict(run_case(case, args.live), trial=run)
                stream.write(json.dumps(row) + "\n")
                stream.flush()
                rows.append(row)
    summary = {"mode": "live" if args.live else "offline-harness-only", "aggregate": reliability(rows),
               "by_case": {c["case_id"]: reliability([r for r in rows if r["case_id"] == c["case_id"]]) for c in cases}}
    args.output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
