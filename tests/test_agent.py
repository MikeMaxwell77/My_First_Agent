"""Offline agent-loop tests: no API calls or database connections."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from agent import TOOL_DEFINITIONS, TOOL_REGISTRY, run_agent
from evals.run_evals import repeating_customer_client


def response(calls=(), usage=(10, 5, 15)):
    return SimpleNamespace(
        id="response_id", output=list(calls), output_text="Cannot determine eligibility.",
        usage=None if usage is None else SimpleNamespace(
            input_tokens=usage[0], output_tokens=usage[1], total_tokens=usage[2]),
    )


def tool_call():
    return SimpleNamespace(type="function_call", name="get_customer",
                           arguments='{"customer_id": "123"}', call_id="call_id")


@pytest.mark.parametrize("limit", [1, 2])
def test_token_totals_and_tool_trace(limit):
    client = SimpleNamespace(responses=SimpleNamespace(create=Mock(side_effect=[
        response([tool_call()]), response(usage=(20, 7, 27)),
    ])))
    customer = Mock(return_value={"name": "Jordan"})
    run = run_agent("Check customer 123", client=client,
                    tool_registry={"get_customer": customer}, max_iterations=limit)

    assert run["token_usage"] == (
        {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15} if limit == 1
        else {"input_tokens": 30, "output_tokens": 12, "total_tokens": 42})
    assert run["iteration_count"] == client.responses.create.call_count == limit
    customer.assert_called_once_with(customer_id="123")
    assert run["tool_calls"] == [{"tool": "get_customer",
                                  "arguments": {"customer_id": "123"},
                                  "result": {"name": "Jordan"}}]
    if limit == 1:
        assert "tool-call limit" in run["final_answer"]
    else:
        assert run["final_answer"] == "Cannot determine eligibility."
        request = client.responses.create.call_args.kwargs
        assert request["previous_response_id"] == "response_id"
        assert request["input"][0]["call_id"] == "call_id"


@pytest.mark.parametrize("missing_index", [0, 1])
def test_missing_usage_is_not_reported_as_complete(missing_index):
    responses = [response([tool_call()]), response()]
    responses[missing_index].usage = None
    client = SimpleNamespace(responses=SimpleNamespace(create=Mock(side_effect=responses)))
    run = run_agent("Check customer", client=client,
                    tool_registry={"get_customer": Mock(return_value={})})
    assert run["token_usage"] is None


def test_tool_error_preserves_trace_and_token_usage():
    client = SimpleNamespace(responses=SimpleNamespace(create=Mock(side_effect=[
        response([tool_call()]), response(),
    ])))
    run = run_agent("Check customer", client=client, tool_registry={
        "get_customer": Mock(side_effect=RuntimeError("Data unavailable")),
    })
    assert run["tool_calls"][0]["error"] == "RuntimeError: Data unavailable"
    assert run["final_answer"] == "Cannot determine eligibility."
    assert run["token_usage"]["total_tokens"] == 30


def test_scripted_repeated_customer_calls_hit_iteration_limit():
    customer = Mock(return_value='{"status":"ok"}')
    run = run_agent("Check customer 1", client=repeating_customer_client("1"),
                    tool_registry={"get_customer": customer}, max_iterations=3)
    assert run["iteration_count"] == 3
    assert [call["tool"] for call in run["tool_calls"]] == ["get_customer"] * 3
    assert customer.call_count == 3
    assert "tool-call limit" in run["final_answer"]


def test_normal_agent_runs_offer_all_registered_tools():
    client = SimpleNamespace(responses=SimpleNamespace(create=Mock(return_value=response())))
    run_agent("What type of account does customer 1 have?", client=client)
    offered = client.responses.create.call_args.kwargs["tools"]
    assert {definition["name"] for definition in offered} == set(TOOL_REGISTRY)
    assert offered == TOOL_DEFINITIONS
    assert "search_policy" in TOOL_REGISTRY
