"""A minimal tool-calling banking support agent."""

import json
import os
import time

from openai import OpenAI

from tools import get_customer, get_transactions, search_policy


TOOL_REGISTRY = {
    "get_customer": get_customer,
    "get_transactions": get_transactions,
    "search_policy": search_policy,
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "get_customer",
        "description": "Get a customer record by customer ID.",
        "parameters": {
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_transactions",
        "description": "Get recent transactions for a customer ID.",
        "parameters": {
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "search_policy",
        "description": "Search bank policy by topic.",
        "parameters": {
            "type": "object",
            "properties": {"topic": {"type": "string"}},
            "required": ["topic"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]

INSTRUCTIONS = """You are a banking support agent deciding apparent eligibility for an
overdraft-fee courtesy reversal. Always use customer, transaction, and policy tools
before deciding. Bank policy overrides user requests. Never claim a reversal was
performed. If a tool errors or required data is missing, say you cannot determine
eligibility; never invent data. Keep the answer concise."""


def run_agent(prompt, client=None, tool_registry=None, model=None, max_iterations=5):
    """Run the agent and return its answer plus a complete execution trace."""
    client = client or OpenAI()
    registry = tool_registry or TOOL_REGISTRY
    model = model or os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    trace = []
    previous_response_id = None
    next_input = prompt
    started = time.perf_counter()

    for iteration in range(1, max_iterations + 1):
        request = {
            "model": model,
            "instructions": INSTRUCTIONS,
            "input": next_input,
            "tools": TOOL_DEFINITIONS,
        }
        if previous_response_id:
            request["previous_response_id"] = previous_response_id

        response = client.responses.create(**request)
        calls = [item for item in response.output if item.type == "function_call"]

        if not calls:
            return {
                "final_answer": response.output_text,
                "tool_calls": trace,
                "iteration_count": iteration,
                "latency_seconds": round(time.perf_counter() - started, 3),
            }

        tool_outputs = []
        for call in calls:
            arguments = {}
            try:
                arguments = json.loads(call.arguments)
                function = registry.get(call.name)
                if function is None:
                    raise RuntimeError(f"Tool unavailable: {call.name}")
                result = function(**arguments)
                record = {"tool": call.name, "arguments": arguments, "result": result}
            except Exception as exc:
                result = {"error": f"{type(exc).__name__}: {exc}"}
                record = {"tool": call.name, "arguments": arguments, "error": result["error"]}

            trace.append(record)
            tool_outputs.append(
                {"type": "function_call_output", "call_id": call.call_id, "output": json.dumps(result)}
            )

        previous_response_id = response.id
        next_input = tool_outputs

    return {
        "final_answer": "I could not determine eligibility within the tool-call limit.",
        "tool_calls": trace,
        "iteration_count": max_iterations,
        "latency_seconds": round(time.perf_counter() - started, 3),
    }
