import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID

import psycopg
import pytest

import tools


@pytest.fixture
def database(monkeypatch):
    connect = MagicMock()
    cursor = connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
    cursor.fetchmany.return_value = []
    monkeypatch.setattr(tools, "get_connection", connect)
    return connect, cursor


def test_get_existing_customer(database):
    _, cursor = database
    cursor.fetchmany.return_value = [{"customer_id": 123, "name": "Jordan Avery",
                                     "courtesy_reversals": 0}]
    result = json.loads(tools.get_customer("123"))
    assert result["data"]["name"] == "Jordan Avery"
    assert result["status"] == "ok"
    assert result["truncated"] is False
    query, params = cursor.execute.call_args.args
    assert "WHERE customer_id = %s" in query
    assert params == (123,)


@pytest.mark.parametrize("function,arg", [
    (tools.get_customer, "999"), (tools.get_transactions, "999"),
    (tools.search_policy, "mortgage"),
])
def test_missing_records(database, function, arg):
    result = json.loads(function(arg))
    assert result["status"] == "error"
    assert result["code"] == "NOT_FOUND"


@pytest.mark.parametrize("value", [None, {}, 123, True, "", "0", "-1", "1.0",
                                   "1 OR 1=1", "9223372036854775808", "1" * 100])
@pytest.mark.parametrize("function", [tools.get_customer, tools.get_transactions])
def test_invalid_customer_id_does_not_connect(database, function, value):
    connect, _ = database
    assert json.loads(function(value))["code"] == "INVALID_INPUT"
    connect.assert_not_called()


@pytest.mark.parametrize("value", [None, {}, 123, "", "   ", "x" * 201, "a\x00b"])
def test_invalid_topic_does_not_connect(database, value):
    connect, _ = database
    assert json.loads(tools.search_policy(value))["code"] == "INVALID_INPUT"
    connect.assert_not_called()


def test_transactions_serialization_and_order(database):
    _, cursor = database
    timestamp = datetime(2026, 9, 20, tzinfo=timezone.utc)
    cursor.fetchmany.return_value = [{"amount": Decimal("-35.00"),
                                     "transaction_date": timestamp,
                                     "transaction_id": UUID(int=1)}]
    result = json.loads(tools.get_transactions("123"))
    assert result["data"][0] == {"amount": "-35.00",
                                  "transaction_date": timestamp.isoformat(),
                                  "transaction_id": str(UUID(int=1))}
    query, params = cursor.execute.call_args.args
    assert "ORDER BY transaction_date DESC, transaction_id DESC" in query
    assert params == (123, 51)


def test_policy_topic_is_literal_parameter(database):
    _, cursor = database
    topic = "overdraft' OR 1=1 -- %_!"
    cursor.fetchmany.return_value = [{"content": "Policy text"}]
    assert json.loads(tools.search_policy(topic))["data"][0]["content"] == "Policy text"
    query, params = cursor.execute.call_args.args
    assert topic not in query
    assert params == ("%overdraft' OR 1=1 -- !%!_!!%",) * 3 + (51,)


@pytest.mark.parametrize("function,arg", [(tools.get_transactions, "123"),
                                         (tools.search_policy, "overdraft")])
def test_row_limit_reports_truncation(database, function, arg):
    _, cursor = database
    cursor.fetchmany.return_value = [{"id": i} for i in range(51)]
    result = json.loads(function(arg))
    assert len(result["data"]) == 50
    assert result["truncated"] is True
    cursor.fetchmany.assert_called_once_with(51)


def test_long_policy_is_bounded(database):
    _, cursor = database
    cursor.fetchmany.return_value = [{"content": "x" * 4001}]
    result = json.loads(tools.search_policy("overdraft"))
    assert len(result["data"][0]["content"]) == 4000
    assert result["truncated"] is True


@pytest.mark.parametrize("function,arg", [(tools.get_customer, "123"),
    (tools.get_transactions, "123"), (tools.search_policy, "overdraft")])
@pytest.mark.parametrize("stage", ["connect", "query"])
def test_database_error_is_sanitized(database, function, arg, stage):
    connect, cursor = database
    target = connect if stage == "connect" else cursor.execute
    target.side_effect = psycopg.OperationalError("secret connection details")
    result = function(arg)
    assert json.loads(result)["code"] == "DATABASE_ERROR"
    assert "secret" not in result


def test_missing_configuration_is_structured(database):
    connect, _ = database
    connect.side_effect = RuntimeError("DATABASE_URL is not configured")
    assert json.loads(tools.get_customer("123"))["code"] == "DATABASE_UNAVAILABLE"
