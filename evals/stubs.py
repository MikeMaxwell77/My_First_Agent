"""Scripted fixtures exercise the harness; they do not measure model reliability."""
import json
from structures import ModelResponse, ToolCall


class ScriptedModel:
    def __init__(self, case):
        self.case, self.step = case, 0

    def generate(self, state, tools):
        self.step += 1
        case = self.case
        customer = case["customer_id"]
        def call(name, **args):
            return ToolCall(name, json.dumps(args), name)
        if case.get("repeat"):
            return ModelResponse(calls=[call("get_customer", customer_id=customer)])
        if self.step == 1:
            if case["category"] == "AUTHORIZATION":
                return ModelResponse(calls=[call(case.get("requested_tool", "get_transactions"), customer_id=customer,
                    **({"note": "test note"} if case.get("requested_tool") == "create_case_note" else {}))])
            return ModelResponse(calls=[call("get_customer", customer_id=customer),
                call("get_transactions", customer_id=customer), call("search_policy", query="overdraft"),
                call("get_customer_history", customer_id=customer)])
        if self.step == 2 and case.get("approval_required"):
            return ModelResponse(calls=[call("request_fee_reversal", customer_id=customer,
                                             transaction_id=f"{customer}-2", amount=35)])
        answers = {"ELIGIBLE": "Customer appears eligible based on the retrieved evidence.",
                   "INELIGIBLE": "Customer is ineligible because the courtesy reversal was already used.",
                   "UNKNOWN": "I cannot determine eligibility because required information is unavailable.",
                   "UNAUTHORIZED": "Access denied for this customer.",
                   "NOT_APPLICABLE": "The requested information was retrieved."}
        answer = answers[case["expected"]]
        if case.get("approval_required"):
            answer += " Approval is pending; no funds have moved."
        return ModelResponse(final_answer=answer, determination=case["expected"], reason="Scripted harness fixture")
