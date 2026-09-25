from data import CUSTOMERS, TRANSACTIONS, POLICIES


def get_customer(customer_id):
    """Retrieve customer information."""

    return CUSTOMERS.get(
        customer_id,
        {"error": "Customer not found"}
    )


def get_transactions(customer_id):
    """Retrieve recent customer transactions."""

    return TRANSACTIONS.get(
        customer_id,
        {"error": "Transactions not found"}
    )


def search_policy(topic):
    """Search bank policies."""

    topic = topic.lower()

    for key, policy in POLICIES.items():
        if key in topic:
            return policy

    return "No relevant policy found."