"""Explicit registered capabilities and isolated in-memory application state."""
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from uuid import uuid4
import math
from data import CUSTOMERS, TRANSACTIONS, POLICIES
from structures import ApprovalRequest


def get_customer(customer_id):
    return deepcopy(CUSTOMERS.get(customer_id, {"error": "Customer not found"}))


def get_transactions(customer_id):
    return deepcopy(TRANSACTIONS.get(customer_id, {"error": "Transactions not found"}))


def search_policy(query):
    for key, policy in POLICIES.items():
        if key in query.lower():
            return policy
    return "No relevant policy found."


def get_customer_history(customer_id):
    customer = get_customer(customer_id)
    if "error" in customer:
        return customer
    return {"courtesy_reversals_last_12_months": customer["courtesy_reversals_last_12_months"]}


@dataclass
class BankSession:
    notes: list = field(default_factory=list)
    approvals: list = field(default_factory=list)

    def create_case_note(self, customer_id, note):
        entry = {"customer_id": customer_id, "note": note, "note_id": str(uuid4())}
        self.notes.append(entry)
        return deepcopy(entry)

    def request_fee_reversal(self, customer_id, transaction_id, amount):
        arguments = dict(customer_id=customer_id, transaction_id=transaction_id, amount=amount)
        for approval in self.approvals:
            if approval.arguments == arguments:
                return asdict(approval)
        approval = ApprovalRequest(str(uuid4()), "request_fee_reversal", arguments,
                                   "Authorized employee approval required; no funds moved.",
                                   "PENDING", datetime.now(timezone.utc).isoformat())
        self.approvals.append(approval)
        return asdict(approval)

    def review(self, approval_id, *, approved, employee=False):
        # Called by trusted application code, never registered as a model tool.
        if not employee:
            raise PermissionError("Employee authorization required")
        approval = next(a for a in self.approvals if a.approval_id == approval_id)
        if approval.status != "PENDING":
            raise ValueError("Approval already reviewed")
        approval.status = "APPROVED" if approved else "DENIED"
        return asdict(approval)  # Still no financial execution.


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    arguments: dict
    risk: str
    handler: object

    def definition(self):
        return {"type": "function", "name": self.name, "description": self.description,
                "strict": True, "parameters": {"type": "object", "properties": self.arguments,
                "required": list(self.arguments), "additionalProperties": False}}

    def validate(self, arguments):
        if not isinstance(arguments, dict) or set(arguments) != set(self.arguments):
            raise ValueError("Arguments must exactly match the registered schema")
        for key, schema in self.arguments.items():
            value = arguments[key]
            if schema["type"] == "string":
                if not isinstance(value, str) or not value.strip() or len(value) > 2000:
                    raise ValueError("Expected nonempty string of at most 2000 characters")
            elif type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError("Expected positive finite amount")


def build_registry(session):
    string = {"type": "string"}
    customer = {"customer_id": string}
    specs = [
        ToolSpec("get_customer", "Verify a fake customer.", customer, "READ", get_customer),
        ToolSpec("get_transactions", "Retrieve fake transactions.", customer, "READ", get_transactions),
        ToolSpec("search_policy", "Search bank policy by query.", {"query": string}, "READ", search_policy),
        ToolSpec("get_customer_history", "Retrieve courtesy reversal history.", customer, "READ", get_customer_history),
        ToolSpec("create_case_note", "Save a case note.", {**customer, "note": string}, "WRITE", session.create_case_note),
        ToolSpec("request_fee_reversal", "Request human approval; never move money.",
                 {**customer, "transaction_id": string, "amount": {"type": "number"}},
                 "CONSEQUENTIAL", None),
    ]
    return {spec.name: spec for spec in specs}


def validate_result(name, result):
    if isinstance(result, dict) and "error" in result:
        raise ValueError(str(result["error"]))
    valid = isinstance(result, dict)
    if name == "get_customer":
        valid = valid and isinstance(result.get("name"), str) and type(result.get("courtesy_reversals_last_12_months")) is int
    elif name == "get_customer_history":
        valid = valid and type(result.get("courtesy_reversals_last_12_months")) is int
    elif name == "get_transactions":
        valid = isinstance(result, list) and all(isinstance(t, dict) and
            isinstance(t.get("transaction_id"), str) and isinstance(t.get("type"), str) and
            type(t.get("amount")) in (int, float) and math.isfinite(t["amount"]) for t in result)
    elif name == "search_policy":
        valid = isinstance(result, str) and "courtesy overdraft fee reversal" in result.lower()
    if not valid:
        raise ValueError("Malformed or unavailable tool result")
