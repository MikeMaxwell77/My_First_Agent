"""Case tags stay usable as report filters without running the model."""

import json
from pathlib import Path

from evals.view_results import build_report


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
    assert report.count('data-tags=') == len(cases)
    assert '<option value="attack:prompt_injection">' in report
    assert '<option value="security">security</option>' in report
    assert report.count('data-case-id=') == len(cases) * 3
    assert "Showing 35 of 35 cases" in report
    assert "Ignore previous instructions injection" in report
