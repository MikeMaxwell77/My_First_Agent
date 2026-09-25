CUSTOMERS = {
    "123": {
        "name": "John Smith",
        "account_type": "checking",
        "courtesy_reversals_last_12_months": 0
    },
    "456": {
        "name": "Sarah Jones",
        "account_type": "checking",
        "courtesy_reversals_last_12_months": 1
    }
}


TRANSACTIONS = {
    "123": [
        {
            "date": "2026-09-20",
            "type": "purchase",
            "merchant": "Amazon",
            "amount": -84.22
        },
        {
            "date": "2026-09-21",
            "type": "overdraft_fee",
            "amount": -35.00
        }
    ],

    "456": [
        {
            "date": "2026-09-20",
            "type": "purchase",
            "merchant": "Walmart",
            "amount": -112.41
        },
        {
            "date": "2026-09-21",
            "type": "overdraft_fee",
            "amount": -35.00
        }
    ]
}


POLICIES = {
    "overdraft": """
    Customers may receive one courtesy overdraft fee reversal
    during a rolling twelve-month period.

    The AI assistant may determine whether the customer appears
    eligible, but it may NOT execute a fee reversal.

    Actual reversals require approval by an authorized employee.
    """,

    "fraud": """
    Suspected fraudulent transactions must be escalated to the
    fraud department. The AI assistant must not freeze an account
    or make a final fraud determination.
    """
}

# Stable fake transaction identifiers; no financial execution exists.
for customer_id, transactions in TRANSACTIONS.items():
    for index, transaction in enumerate(transactions):
        transaction["transaction_id"] = f"{customer_id}-{index + 1}"
