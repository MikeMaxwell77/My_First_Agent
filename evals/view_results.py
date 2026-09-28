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


def numeric_metrics(row):
    """Flatten finite numeric evaluation fields and add a tool-call count."""
    metrics = {"tool_call_count": len(row["tool_calls"])}

    def collect(name, value):
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            try:
                if math.isfinite(value):
                    metrics[name] = value
            except OverflowError:
                pass  # Too large for browser chart coordinates.
        elif isinstance(value, dict):
            for key, item in value.items():
                collect(f"{name}.{key}", item)

    for key, value in row.items():
        if key not in {"tool_calls", "tools_called"}:
            collect(key, value)
    return metrics


def format_model_name(model):
    if model.lower() == "gpt-5.6-luna":
        return "GPT-5.6 Luna"
    return model


def build_report(results):
    models = {str(row["model"]) for row in results if row.get("model")}
    if not models:
        models = {"gpt-5.6-luna"}
    model_label = escape(", ".join(format_model_name(model) for model in sorted(models)))
    average_latency = sum(float(row["latency_seconds"]) for row in results) / len(results)
    average_calls = sum(len(row["tool_calls"]) for row in results) / len(results)

    chart_cases = []
    detail_rows = []
    for row in results:
        case_id = str(row["case_id"])
        category = str(row.get("category", ""))
        tags = [str(tag) for tag in row.get("tags", [])]
        name = str(row.get("name", ""))
        metrics = numeric_metrics(row)
        chart_cases.append({"id": case_id, "name": name, "category": category,
                            "tags": tags, "metrics": metrics})

        calls = row["tool_calls"]
        tools = ", ".join(escape(str(call.get("tool", "unknown"))) for call in calls) or "None"
        tag_list = " ".join(f'<span class="tag">{escape(tag)}</span>' for tag in tags) or "None"
        title = escape(case_id) + (" - " + escape(name) if name else "")
        detail_rows.append(
            f'<details class="case" data-case-index="{len(chart_cases) - 1}">'
            f'<summary>{title} <span>{len(calls)} tool calls</span></summary>'
            f'<p><strong>Category:</strong> {escape(category or "unknown")}</p>'
            f'<p><strong>Tags:</strong> {tag_list}</p>'
            f'<p><strong>Prompt:</strong> {escape(str(row.get("prompt", "")))}</p>'
            f'<p><strong>Final answer:</strong> {escape(str(row["final_answer"]))}</p>'
            f'<p><strong>Tools:</strong> {tools}</p>'
            f'<pre aria-label="Tool call details">'
            f'{escape(json.dumps(calls, ensure_ascii=False, indent=2))}</pre></details>'
        )

    categories = sorted({case["category"] for case in chart_cases if case["category"]})
    tags = sorted({tag for case in chart_cases for tag in case["tags"]})
    category_options = "".join(
        f'<option value="{escape(category, quote=True)}">{escape(category)}</option>'
        for category in categories
    )
    tag_controls = "".join(
        f'<label class="tag-control"><span>{escape(tag)}</span>'
        f'<select data-tag="{escape(tag, quote=True)}" aria-label="Filter {escape(tag, quote=True)}">'
        '<option value="">Any</option><option value="include">Include</option>'
        '<option value="exclude">Exclude</option></select></label>'
        for tag in tags
    )
    chart_data = json.dumps(chart_cases, ensure_ascii=False, allow_nan=False)
    for old, new in (("&", "\\u0026"), ("<", "\\u003c"),
                     (">", "\\u003e"), ("\u2028", "\\u2028"),
                     ("\u2029", "\\u2029")):
        chart_data = chart_data.replace(old, new)
    script = Path(__file__).with_name("report_script.js").read_text(encoding="utf-8")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Evaluation Report</title>
<style>
  :root {{ color-scheme: light; font-family: system-ui, sans-serif; background: #f5f7fb; color: #17243a; }}
  body {{ max-width: 1100px; margin: 0 auto; padding: 32px 20px 64px; }}
  h1 {{ margin-bottom: 4px; }}
  .subtitle, .note, .chart-note {{ color: #52627a; }}
  .subtitle {{ margin-top: 0; }}
  .report-meta, .controls {{ display: flex; flex-wrap: wrap; align-items: center; gap: 12px 24px; }}
  .report-meta {{ margin: 16px 0; }}
  .summary {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 24px 0; }}
  .metric, section {{ background: white; border: 1px solid #dbe2ed; border-radius: 12px; padding: 20px; }}
  .metric strong {{ display: block; font-size: 1.7rem; }}
  .metric span {{ color: #52627a; font-size: .9rem; }}
  section {{ margin-top: 16px; }}
  h2 {{ margin: 0 0 18px; font-size: 1.2rem; }}
  button, select {{ font: inherit; padding: 5px 8px; }}
  button {{ cursor: pointer; }}
  .tag-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 8px 16px; max-height: 230px; overflow: auto; padding: 12px 0; }}
  .tag-control {{ display: flex; align-items: center; justify-content: space-between; gap: 8px; }}
  .tag-control span {{ overflow-wrap: anywhere; }}
  .tag-control select {{ flex: none; }}
  .chart-card {{ border: 1px solid #dbe2ed; border-radius: 10px; padding: 16px; margin: 16px 0; }}
  .chart-card .controls {{ margin-bottom: 12px; }}
  .chart-scroll {{ overflow-x: auto; }}
  .chart-scroll svg {{ display: block; }}
  .legend {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 6px 12px; margin-top: 12px; }}
  .legend-item {{ display: flex; align-items: center; gap: 7px; overflow-wrap: anywhere; }}
  .swatch {{ flex: none; width: 12px; height: 12px; border-radius: 3px; }}
  details.case {{ border-top: 1px solid #dbe2ed; padding: 12px 0; }}
  summary {{ cursor: pointer; font-weight: 600; }}
  summary span {{ float: right; font-weight: 400; color: #52627a; }}
  details p {{ line-height: 1.5; overflow-wrap: anywhere; }}
  .tag {{ display: inline-block; margin: 2px 4px 2px 0; padding: 3px 7px; border-radius: 5px; background: #edf1f7; font-size: .8rem; }}
  pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #f5f7fb; padding: 12px; border-radius: 6px; font-size: .8rem; }}
  [hidden] {{ display: none !important; }}
  @media (max-width: 640px) {{ .summary {{ grid-template-columns: 1fr; }} summary span {{ float: none; display: block; }} }}
</style>
</head>
<body>
<h1>Agent Evaluation Report</h1>
<p class="subtitle">Prototype evaluation results</p>
<div class="report-meta">
  <span><strong>Model:</strong> {model_label}</span>
  <span><strong>Test scenarios:</strong> {len(results)}</span>
</div>
<div class="summary">
  <div class="metric"><strong>{len(results)}</strong><span>Cases</span></div>
  <div class="metric"><strong>{average_latency:.2f} s</strong><span>Average latency</span></div>
  <div class="metric"><strong>{average_calls:.1f}</strong><span>Average tool calls</span></div>
</div>
<section aria-label="Case filters">
  <h2>Filter cases</h2>
  <div class="controls"><label>Category:
    <select id="category-filter"><option value="">All categories</option>{category_options}</select>
  </label><button id="clear-filters" type="button">Clear filters</button></div>
  <details><summary>Include or exclude tags</summary><div class="tag-grid">{tag_controls or 'No tags in these results.'}</div></details>
  <p id="filter-count" aria-live="polite">Showing {len(results)} of {len(results)} cases</p>
  <p class="note">Included tags must all match. Any excluded tag removes a case.</p>
</section>
<section aria-label="Charts">
  <div class="controls"><h2>Charts</h2><button id="add-chart" type="button">Add chart</button></div>
  <div id="charts"></div>
  <p class="note">Line charts connect cases in result order. Pie charts show each case's share of a nonnegative total. Cases without the selected metric are omitted from that chart.</p>
</section>
<section aria-label="Case details">
  <h2>Case details</h2>
  <div id="case-details">{''.join(detail_rows)}</div>
</section>
<p class="note">Charts show execution metrics. These results do not contain correctness grades.</p>
<script type="application/json" id="chart-data">{chart_data}</script>
<script>{script}</script>
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
