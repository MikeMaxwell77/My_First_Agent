"""Insert fictional bank records: python -m database.seed."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from db import get_connection


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


def seed_database():
    """Add five customers and thirty transactions atomically.

    Every invocation adds another batch. Existing records are preserved.
    These sample transactions are not a complete account ledger.
    """
    customer_ids = []
    start = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)

    with get_connection() as connection:
        with connection.cursor() as cursor:
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
    seed_database()
