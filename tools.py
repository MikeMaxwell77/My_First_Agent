"""Validated, read-only database tools returning bounded JSON payloads."""

import json
import re
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from database.db import get_connection


MAX_ROWS = 50
MAX_TEXT_LENGTH = 4000


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    raise TypeError(f"Unsupported database value type: {type(value).__name__}")


def _error(code, message):
    return json.dumps({"status": "error", "code": code, "message": message})


def _valid_bigint_id(value):
    # Preserve the public string parameter; PostgreSQL uses positive BIGINTs.
    return (
        isinstance(value, str)
        and re.fullmatch(r"[1-9][0-9]{0,18}", value) is not None
        and int(value) <= 9223372036854775807
    )


def _select(query, parameters, *, single=False):
    try:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, parameters)
                rows = cursor.fetchmany(MAX_ROWS + 1)
        if not rows:
            return _error("NOT_FOUND", "No matching records found.")
        truncated = len(rows) > MAX_ROWS
        bounded_rows = []
        for row in rows[:MAX_ROWS]:
            bounded = {}
            for key, value in row.items():
                if isinstance(value, str) and len(value) > MAX_TEXT_LENGTH:
                    value = value[:MAX_TEXT_LENGTH]
                    truncated = True
                bounded[key] = value
            bounded_rows.append(bounded)
        return json.dumps(
            {"status": "ok", "data": bounded_rows[0] if single else bounded_rows,
             "truncated": truncated},
            default=_json_default,
        )
    except psycopg.Error:
        return _error("DATABASE_ERROR", "Database query failed.")
    except RuntimeError:
        return _error("DATABASE_UNAVAILABLE", "Database connection is not configured or available.")
    except (TypeError, ValueError):
        return _error("SERIALIZATION_ERROR", "Database results could not be serialized.")


def get_customer(customer_id: str) -> str:
    """Retrieve one customer using a positive BIGINT ID encoded as a string."""
    if not _valid_bigint_id(customer_id):
        return _error("INVALID_INPUT", "customer_id must be a positive BIGINT encoded as a string.")
    return _select(
        "SELECT customer_id, name, account_type, courtesy_reversals, created_at "
        "FROM customers WHERE customer_id = %s LIMIT 1",
        (int(customer_id),), single=True,
    )


def get_transactions(customer_id: str) -> str:
    """Retrieve up to 50 transactions, newest first, for a validated customer ID."""
    if not _valid_bigint_id(customer_id):
        return _error("INVALID_INPUT", "customer_id must be a positive BIGINT encoded as a string.")
    return _select(
        "SELECT transaction_id, customer_id, merchant, amount, transaction_type, "
        "status, transaction_date FROM transactions WHERE customer_id = %s "
        "ORDER BY transaction_date DESC, transaction_id DESC LIMIT %s",
        (int(customer_id), MAX_ROWS + 1),
    )


def get_transaction(transaction_id: str) -> str:
    """Retrieve one transaction using a positive BIGINT ID encoded as a string."""
    if not _valid_bigint_id(transaction_id):
        return _error("INVALID_INPUT", "transaction_id must be a positive BIGINT encoded as a string.")
    return _select(
        "SELECT transaction_id, customer_id, merchant, amount, transaction_type, "
        "status, transaction_date FROM transactions WHERE transaction_id = %s LIMIT 1",
        (int(transaction_id),), single=True,
    )


def search_policy(topic: str) -> str:
    """Find up to 50 policies containing a literal topic (1-200 characters)."""
    if not isinstance(topic, str) or not 1 <= len(topic.strip()) <= 200:
        return _error("INVALID_INPUT", "topic must contain 1 to 200 nonblank characters.")
    if "\x00" in topic:
        return _error("INVALID_INPUT", "topic must not contain null characters.")
    # Escape LIKE wildcards so the topic is a literal substring, not a pattern.
    literal = topic.strip().replace("!", "!!").replace("%", "!%").replace("_", "!_")
    pattern = "%" + literal + "%"
    return _select(
        "SELECT policy_id, category, title, content FROM policies "
        "WHERE category ILIKE %s ESCAPE '!' OR title ILIKE %s ESCAPE '!' "
        "OR content ILIKE %s ESCAPE '!' ORDER BY policy_id LIMIT %s",
        (pattern, pattern, pattern, MAX_ROWS + 1),
    )
