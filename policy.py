"""Trusted caller context and deterministic enforcement, outside the model."""
from dataclasses import dataclass
from data import CUSTOMERS, TRANSACTIONS


@dataclass(frozen=True)
class AuthContext:
    customer_ids: frozenset = frozenset({"123"})
    can_write: bool = True


def check_policy(spec, arguments, auth):
    customer_id = arguments.get("customer_id")
    if customer_id is not None and customer_id not in auth.customer_ids:
        raise PermissionError("Customer access denied")
    if spec.risk not in {"READ", "WRITE", "CONSEQUENTIAL"}:
        raise PermissionError("Unknown risk classification")
    if spec.risk != "READ":
        if not auth.can_write:
            raise PermissionError("Write access denied")
        if customer_id not in CUSTOMERS:
            raise ValueError("Customer not found")
    if spec.risk == "CONSEQUENTIAL":
        transaction = next((t for t in TRANSACTIONS[customer_id]
                            if t["transaction_id"] == arguments["transaction_id"]), None)
        if not transaction or transaction["type"] != "overdraft_fee" or -transaction["amount"] != arguments["amount"]:
            raise ValueError("Reversal must match the customer's overdraft fee exactly")
        if CUSTOMERS[customer_id]["courtesy_reversals_last_12_months"] != 0:
            raise PermissionError("Courtesy reversal already used")
        return "APPROVAL"
    return "ALLOW"
