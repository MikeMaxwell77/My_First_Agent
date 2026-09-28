"""Insert fictional bank records: python -m database.seed."""

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from database.db import get_connection


CUSTOMERS = [
    ("Jordan Avery", "checking", 0),
    ("Morgan Ellis", "checking", 1),
    ("Taylor Brooks", "checking", 0),
    ("Casey Rowan", "checking", 1),
    ("Riley Quinn", "checking", 0),
]

# Negative amounts are debits; positive amounts are credits.
TRANSACTIONS = [
    ("Fictional Payroll", "1500.00", "deposit", "posted"),
    ("Fictional Grocery", "-42.50", "purchase", "posted"),
    ("Fictional Cafe", "-8.25", "purchase", "posted"),
    ("Fictional Utilities", "-95.00", "payment", "posted"),
    (None, "-35.00", "overdraft_fee", "posted"),
    ("Fictional Bookshop", "-18.75", "purchase", "pending"),
]

POLICIES = [
    (
        "overdraft",
        "Courtesy overdraft fee reversal",
        "Courtesy overdraft reversal policy: A customer may be considered for "
        "one courtesy reversal if their transaction "
        "history shows a posted overdraft fee and their customer record shows zero "
        "prior courtesy reversals. An employee must review and approve the request. "
        "The agent may explain apparent eligibility but must not approve or perform "
        "a reversal. If the records are missing or incomplete, eligibility cannot "
        "be determined.",
    ),
    (
        "dispute",
        "Transaction dispute investigation",
        "When a customer questions a transaction, compare the details they provide "
        "with the recorded transaction ID, merchant, amount, date, and status. "
        "If a transaction matches, explain what the records show and direct the "
        "customer to an employee for dispute review. If details conflict or do "
        "not identify one transaction, ask for clarification. The agent must not "
        "declare a charge fraudulent or claim a dispute or refund has been completed.",
    ),
]


def insert_policies(cursor):
    """Refresh fictional policies without duplicating existing titles."""
    for category, title, content in POLICIES:
        cursor.execute(
            """
            UPDATE policies SET category = %s, content = %s WHERE title = %s
            """,
            (category, content, title),
        )
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT INTO policies (category, title, content) VALUES (%s, %s, %s)",
                (category, title, content),
            )


def seed_policies():
    """Populate policies without adding another customer batch."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            insert_policies(cursor)
    print("Ensured fictional policies are present.")


def seed_database():
    """Add five customers, thirty transactions, and missing policies atomically.

    Every invocation adds another batch. Existing records are preserved.
    These sample transactions are not a complete account ledger.
    """
    customer_ids = []
    start = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            insert_policies(cursor)
            for customer in CUSTOMERS:
                cursor.execute(
                    """
                    INSERT INTO customers (name, account_type, courtesy_reversals)
                    VALUES (%s, %s, %s)
                    RETURNING customer_id
                    """,
                    customer,
                )
                customer_id = cursor.fetchone()[0]
                customer_ids.append(customer_id)
                cursor.executemany(
                    """
                    INSERT INTO transactions
                        (customer_id, merchant, amount, transaction_type,
                         status, transaction_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (customer_id, merchant, Decimal(amount), kind, status,
                         start + timedelta(days=day))
                        for day, (merchant, amount, kind, status)
                        in enumerate(TRANSACTIONS)
                    ],
                )

            cursor.execute(
                "SELECT COUNT(*) FROM transactions WHERE customer_id = ANY(%s)",
                (customer_ids,),
            )
            transaction_count = cursor.fetchone()[0]
            if transaction_count != 30:
                raise RuntimeError("Expected 30 transactions; rolling back seed batch")

    print(f"Added {len(customer_ids)} customers and {transaction_count} transactions.")
    print(f"Customer IDs: {customer_ids}")


if __name__ == "__main__":
    if sys.argv[1:] == ["--policies-only"]:
        seed_policies()
    elif not sys.argv[1:]:
        seed_database()
    else:
        raise SystemExit("Usage: python -m database.seed [--policies-only]")
