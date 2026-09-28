"""Case tags stay usable as report filters without running the model."""

import json
import re
from pathlib import Path

from evals.view_results import build_report, numeric_metrics, tool_errors


def test_case_tags_cover_expected_tools_and_render_in_report():
    cases = json.loads((Path(__file__).resolve().parents[1] / "evals" / "cases.json")
                       .read_text(encoding="utf-8"))
    tool_tags = {"get_customer": "tool:customer",
                 "get_transactions": "tool:transactions",
                 "get_transaction": "tool:transaction",
                 "search_policy": "tool:policy"}
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        tags = case["tags"]
        assert len(tags) == len(set(tags))
        assert sum(tag.startswith("customer:") for tag in tags) == 1
        expected = {tool_tags[name] for name in case["expected"]["required_tools"]}
        assert {tag for tag in tags if tag.startswith("tool:")} == (expected or {"tool:none"})

    rows = [{"case_id": case["id"], "name": case["name"],
             "category": case["category"],
             "tags": case["tags"], "model": "offline", "final_answer": "sample",
             "latency_seconds": 0.1, "iteration_count": 1, "tool_calls": []}
            for case in cases]
    report = build_report(rows)
    assert report.count('<details class="case" data-case-index=') == len(cases)
    assert 'data-tag="attack:prompt_injection"' in report
    assert '<option value="security">security</option>' in report
    assert '<section aria-label="Tag categories">' in report
    assert report.index('<legend>Customer</legend>') < report.index('<legend>Tool</legend>')
    assert report.index('<legend>Tool</legend>') < report.index('<legend>Attack</legend>')
    assert 'max-height: min(70vh, 720px)' in report
    assert "Showing 35 of 35 cases" in report
    assert "Ignore previous instructions injection" in report
    assert 'class="metric-select"' in report
    assert 'class="type-select"' in report
    assert 'value="pie"' in report
    assert 'function jumpToCase(index)' in report
    assert 'data-case-index="0"' in report


def test_report_exposes_numeric_metrics_and_escapes_embedded_data():
    first = {"case_id": "case-1", "model": "offline", "category": "basic",
             "tags": ["tool:customer"], "latency_seconds": 0.2,
             "iteration_count": 2, "tool_calls": [{"tool": "get_customer"}],
             "final_answer": "Checked", "token_usage": {"input_tokens": 12,
             "output_tokens": 3, "total_tokens": 15},
             "task_metadata": {"quality_score": 0.75, "is_correct": True}}
    second = {"case_id": "</script><script>alert(1)</script>",
              "model": "offline", "latency_seconds": 0.4,
              "iteration_count": 1, "tool_calls": [],
              "final_answer": "Unknown", "token_usage": None}
    report = build_report([first, second])
    match = re.search(r'<script type="application/json" id="chart-data">(.*?)</script>',
                      report, re.S)
    assert match is not None
    data = json.loads(match.group(1))
    assert data[0]["metrics"]["token_usage.total_tokens"] == 15
    assert data[0]["metrics"]["task_metadata.quality_score"] == 0.75
    assert data[0]["metrics"]["tool_call_count"] == 1
    assert "task_metadata.is_correct" not in data[0]["metrics"]
    assert "token_usage.total_tokens" not in data[1]["metrics"]
    assert data[1]["id"] == second["case_id"]
    assert second["case_id"] not in report
    assert numeric_metrics(first)["iteration_count"] == 2


def test_tool_errors_are_visible_and_distinct_from_successful_results():
    row = {"case_id": "error-case", "model": "offline", "latency_seconds": 0.2,
           "iteration_count": 1, "final_answer": "Cannot determine eligibility.",
           "tool_calls": [
               {"tool": "get_customer", "result": json.dumps({
                   "status": "error", "code": "NOT_FOUND", "message": "No record"})},
               {"tool": "get_transactions", "error": "RuntimeError: unavailable"},
               {"tool": "search_policy", "result": '{"status":"ok","data":[]}'},
           ]}
    errors = tool_errors(row)
    assert [(error["tool"], error["code"]) for error in errors] == [
        ("get_customer", "NOT_FOUND"), ("get_transactions", "EXCEPTION")]
    assert numeric_metrics(row)["tool_error_count"] == 2

    report = build_report([row])
    assert 'id="errors-only"' in report
    assert 'class="case has-error"' in report
    assert '<strong>get_customer: NOT_FOUND</strong>' in report
    assert '<strong>get_transactions: EXCEPTION</strong>' in report
    assert 'Cases with tool errors' in report
    data = json.loads(re.search(
        r'<script type="application/json" id="chart-data">(.*?)</script>',
        report, re.S).group(1))
    assert data[0]["errorCount"] == 2
