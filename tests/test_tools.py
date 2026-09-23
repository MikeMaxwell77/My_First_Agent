from tools import get_customer, get_transactions, search_policy


def test_get_existing_customer():
    customer = get_customer("123")

    assert customer["name"] == "John Smith"
    assert customer["courtesy_reversals_last_12_months"] == 0


def test_get_missing_customer():
    customer = get_customer("999")

    assert "error" in customer


def test_get_transactions():
    transactions = get_transactions("123")

    assert len(transactions) > 0
    assert transactions[1]["type"] == "overdraft_fee"


def test_find_overdraft_policy():
    policy = search_policy("overdraft")

    assert "courtesy overdraft fee reversal" in policy.lower()


def test_missing_policy():
    policy = search_policy("mortgage")

    assert policy == "No relevant policy found."