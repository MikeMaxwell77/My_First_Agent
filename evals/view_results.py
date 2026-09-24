"""Build a self-contained HTML report from saved evaluation results.

Usage: python evals/view_results.py [results.jsonl] [report.html]
"""

import json
import math
import sys
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = ROOT / "logs" / "eval_results.jsonl"
DEFAULT_REPORT = ROOT / "logs" / "eval_report.html"


def read_results(path):
    results = []
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                result = json.loads(line)
                for field in ("case_id", "final_answer", "latency_seconds", "iteration_count", "tool_calls"):
                    if field not in result:
                        raise ValueError(f"missing {field}")
                if not isinstance(result["tool_calls"], list):
                    raise ValueError("tool_calls must be a list")
                if not all(isinstance(call, dict) for call in result["tool_calls"]):
                    raise ValueError("tool_calls must contain objects")
                latency = float(result["latency_seconds"])
                iterations = result["iteration_count"]
                if not math.isfinite(latency) or latency < 0:
                    raise ValueError("latency must be a finite nonnegative number")
                if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 0:
                    raise ValueError("iteration count must be a nonnegative integer")
            except (ValueError, TypeError, KeyError) as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
            results.append(result)
    if not results:
        raise ValueError(f"{path}: no evaluation results found")
    return results


def bar(value, maximum, color, label):
    width = 100 * value / maximum if maximum else 0
    return (
        f'<span class="bar-track"><span class="bar {color}" '
        f'style="width: {width:.1f}%"></span></span>'
        f'<span class="value">{escape(label)}</span>'
    )


def format_model_name(model):
    if model.lower() == "gpt-5.6-luna":
        return "GPT-5.6 Luna"
    return model


def build_report(results):
    models = {str(row["model"]) for row in results if row.get("model")}
    if not models:
        # Older evaluation logs predate model metadata and used this project default.
        models = {"gpt-5.6-luna"}
    model_label = escape(", ".join(format_model_name(model) for model in sorted(models)))
    max_latency = max(float(row["latency_seconds"]) for row in results)
    max_activity = max(
        max(int(row["iteration_count"]), len(row["tool_calls"])) for row in results
    )
    latency_rows = []
    activity_rows = []
    detail_rows = []

    for row in results:
        case_id = escape(str(row["case_id"]))
        latency = float(row["latency_seconds"])
        iterations = int(row["iteration_count"])
        calls = row["tool_calls"]
        latency_rows.append(
            f'<div class="chart-row"><span class="case">{case_id}</span>'
            f'{bar(latency, max_latency, "latency", f"{latency:.2f} s")}</div>'
        )
        activity_rows.append(
            f'<div class="chart-row"><span class="case">{case_id}</span>'
            f'<div class="stack">'
            f'{bar(iterations, max_activity, "iterations", f"{iterations} iterations")}'
            f'{bar(len(calls), max_activity, "calls", f"{len(calls)} tool calls")}'
            f'</div></div>'
        )
        tools = ", ".join(escape(str(call.get("tool", "unknown"))) for call in calls) or "None"
        trajectory = escape(json.dumps(calls, ensure_ascii=False, indent=2))
        prompt = escape(str(row.get("prompt", "")))
        answer = escape(str(row["final_answer"]))
        detail_rows.append(
            f'<details><summary>{case_id} <span>{latency:.2f} s · '
            f'{iterations} iterations · {len(calls)} calls</span></summary>'
            f'<p><strong>Prompt:</strong> {prompt}</p>'
            f'<p><strong>Final answer:</strong> {answer}</p>'
            f'<p><strong>Tools:</strong> {tools}</p>'
            f'<pre aria-label="Tool call details">{trajectory}</pre></details>'
        )

    average_latency = sum(float(row["latency_seconds"]) for row in results) / len(results)
    average_calls = sum(len(row["tool_calls"]) for row in results) / len(results)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Evaluation Report</title>
<style>
  :root {{ color-scheme: light; font-family: system-ui, sans-serif; background: #f5f7fb; color: #17243a; }}
  body {{ max-width: 1080px; margin: 0 auto; padding: 32px 20px 64px; }}
  h1 {{ margin-bottom: 4px; }}
  .subtitle {{ color: #52627a; margin-top: 0; }}
  .report-meta {{ display: flex; flex-wrap: wrap; gap: 8px 24px; color: #34445d; margin: 16px 0 8px; }}
  .generated-note {{ color: #52627a; margin: 0 0 24px; }}
  .summary {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 24px 0; }}
  .metric, section {{ background: white; border: 1px solid #dbe2ed; border-radius: 12px; padding: 20px; }}
  .metric strong {{ display: block; font-size: 1.7rem; }}
  .metric span, .note {{ color: #52627a; font-size: .9rem; }}
  section {{ margin-top: 16px; }}
  h2 {{ margin: 0 0 18px; font-size: 1.2rem; }}
  .chart-row {{ display: grid; grid-template-columns: minmax(150px, 230px) minmax(0, 1fr); gap: 16px; align-items: center; margin: 14px 0; }}
  .case {{ font-size: .9rem; overflow-wrap: anywhere; }}
  .chart-row > .bar-track, .stack .bar-track {{ min-width: 0; }}
  .chart-row:has(> .bar-track) {{ grid-template-columns: minmax(150px, 230px) minmax(0, 1fr) 78px; }}
  .bar-track {{ display: block; height: 18px; border-radius: 5px; background: #edf1f7; overflow: hidden; }}
  .bar {{ display: block; height: 100%; border-radius: 5px; }}
  .latency {{ background: #2866c9; }}
  .iterations {{ background: #19856d; }}
  .calls {{ background: #b76528; }}
  .value {{ font-size: .85rem; white-space: nowrap; color: #52627a; }}
  .stack {{ display: grid; grid-template-columns: minmax(0, 1fr) 90px; gap: 5px 10px; align-items: center; }}
  details {{ border-top: 1px solid #dbe2ed; padding: 12px 0; }}
  details:first-of-type {{ border-top: 0; }}
  summary {{ cursor: pointer; font-weight: 600; }}
  summary span {{ float: right; font-weight: 400; color: #52627a; }}
  details p {{ line-height: 1.5; overflow-wrap: anywhere; }}
  pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #f5f7fb; padding: 12px; border-radius: 6px; font-size: .8rem; }}
  @media (max-width: 640px) {{
    .summary {{ grid-template-columns: 1fr; }}
    .chart-row, .chart-row:has(> .bar-track) {{ grid-template-columns: 1fr; gap: 5px; }}
    summary span {{ float: none; display: block; }}
  }}
</style>
</head>
<body>
<h1>Agent Evaluation Report</h1>
<p class="subtitle">Prototype evaluation results</p>
<div class="report-meta">
  <span><strong>Model:</strong> {model_label}</span>
  <span><strong>Test scenarios:</strong> {len(results)}</span>
</div>
<p class="generated-note"><em>Generated from the automated evaluation suite.</em></p>
<div class="summary">
  <div class="metric"><strong>{len(results)}</strong><span>Cases</span></div>
  <div class="metric"><strong>{average_latency:.2f} s</strong><span>Average latency</span></div>
  <div class="metric"><strong>{average_calls:.1f}</strong><span>Average tool calls</span></div>
</div>
<section aria-label="Latency by case">
  <h2>Latency by case</h2>
  {''.join(latency_rows)}
</section>
<section aria-label="Iterations and tool calls by case">
  <h2>Iterations and tool calls by case</h2>
  {''.join(activity_rows)}
</section>
<section>
  <h2>Case details</h2>
  {''.join(detail_rows)}
</section>
<p class="note">These graphs show speed and tool use. The saved results do not contain correctness grades.</p>
</body>
</html>
"""


def main():
    if len(sys.argv) > 3:
        raise SystemExit("Usage: python evals/view_results.py [results.jsonl] [report.html]")
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_RESULTS
    destination = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_REPORT
    try:
        report = build_report(read_results(source))
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report, encoding="utf-8")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
