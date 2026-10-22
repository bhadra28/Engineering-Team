from __future__ import annotations

import unittest
from datetime import datetime

from trading_backend import (
    AccountManager,
    AccountNotFoundError,
    InsufficientFundsError,
    InsufficientHoldingsError,
    InvalidAmountError,
    InvalidQuantityError,
    UnknownSymbolError,
)


def fixed_price_lookup(symbol: str) -> float:
    prices = {"AAPL": 100.0, "TSLA": 200.0, "GOOGL": 1000.0}
    try:
        return prices[symbol.strip().upper()]
    except KeyError as exc:
        raise ValueError(symbol) from exc


class TradingBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = AccountManager(price_lookup=fixed_price_lookup)

    def test_create_account_with_initial_deposit(self) -> None:
        account = self.manager.create_account("Alice", 1000)
        self.assertEqual(account.owner_name, "Alice")
        self.assertEqual(account.initial_deposit, 1000)
        self.assertEqual(account.cash_balance, 1000)
        self.assertEqual(len(account.transactions), 1)
        self.assertEqual(account.transactions[0].cash_amount, 1000)

    def test_create_account_rejects_negative_initial_deposit(self) -> None:
        with self.assertRaises(InvalidAmountError):
            self.manager.create_account("Alice", -1)

    def test_create_account_rejects_empty_owner_name(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.create_account("")

    def test_deposit_increases_cash_balance(self) -> None:
        account = self.manager.create_account("Alice", 100)
        tx = self.manager.deposit(account.account_id, 50)
        self.assertEqual(self.manager.get_account(account.account_id).cash_balance, 150)
        self.assertEqual(tx.cash_amount, 50)

    def test_deposit_rejects_zero_or_negative_amount(self) -> None:
        account = self.manager.create_account("Alice", 100)
        with self.assertRaises(InvalidAmountError):
            self.manager.deposit(account.account_id, 0)
        with self.assertRaises(InvalidAmountError):
            self.manager.deposit(account.account_id, -1)

    def test_withdraw_decreases_cash_balance(self) -> None:
        account = self.manager.create_account("Alice", 100)
        tx = self.manager.withdraw(account.account_id, 40)
        self.assertEqual(self.manager.get_account(account.account_id).cash_balance, 60)
        self.assertEqual(tx.cash_amount, -40)

    def test_withdraw_rejects_insufficient_funds(self) -> None:
        account = self.manager.create_account("Alice", 100)
        with self.assertRaises(InsufficientFundsError):
            self.manager.withdraw(account.account_id, 101)

    def test_withdraw_rejects_zero_or_negative_amount(self) -> None:
        account = self.manager.create_account("Alice", 100)
        with self.assertRaises(InvalidAmountError):
            self.manager.withdraw(account.account_id, 0)
        with self.assertRaises(InvalidAmountError):
            self.manager.withdraw(account.account_id, -1)

    def test_buy_decreases_cash_and_increases_holdings(self) -> None:
        account = self.manager.create_account("Alice", 1000)
        tx = self.manager.buy(account.account_id, "AAPL", 5)
        self.assertEqual(self.manager.get_account(account.account_id).cash_balance, 500)
        self.assertEqual(self.manager.get_holdings(account.account_id), {"AAPL": 5})
        self.assertEqual(tx.symbol, "AAPL")

    def test_buy_rejects_insufficient_funds(self) -> None:
        account = self.manager.create_account("Alice", 100)
        with self.assertRaises(InsufficientFundsError):
            self.manager.buy(account.account_id, "AAPL", 2)

    def test_buy_rejects_invalid_quantity(self) -> None:
        account = self.manager.create_account("Alice", 1000)
        with self.assertRaises(InvalidQuantityError):
            self.manager.buy(account.account_id, "AAPL", 0)
        with self.assertRaises(InvalidQuantityError):
            self.manager.buy(account.account_id, "AAPL", -1)
        with self.assertRaises(InvalidQuantityError):
            self.manager.buy(account.account_id, "AAPL", 1.5)  # type: ignore[arg-type]

    def test_buy_rejects_unknown_symbol(self) -> None:
        account = self.manager.create_account("Alice", 1000)
        with self.assertRaises(UnknownSymbolError):
            self.manager.buy(account.account_id, "MSFT", 1)

    def test_sell_increases_cash_and_decreases_holdings(self) -> None:
        account = self.manager.create_account("Alice", 1000)
        self.manager.buy(account.account_id, "AAPL", 5)
        tx = self.manager.sell(account.account_id, "AAPL", 2)
        self.assertEqual(self.manager.get_account(account.account_id).cash_balance, 700)
        self.assertEqual(self.manager.get_holdings(account.account_id), {"AAPL": 3})
        self.assertEqual(tx.cash_amount, 200)

    def test_sell_rejects_insufficient_holdings(self) -> None:
        account = self.manager.create_account("Alice", 1000)
        self.manager.buy(account.account_id, "AAPL", 1)
        with self.assertRaises(InsufficientHoldingsError):
            self.manager.sell(account.account_id, "AAPL", 2)

    def test_sell_rejects_invalid_quantity(self) -> None:
        account = self.manager.create_account("Alice", 1000)
        with self.assertRaises(InvalidQuantityError):
            self.manager.sell(account.account_id, "AAPL", 0)
        with self.assertRaises(InvalidQuantityError):
            self.manager.sell(account.account_id, "AAPL", -1)

    def test_sell_rejects_unknown_symbol(self) -> None:
        account = self.manager.create_account("Alice", 1000)
        with self.assertRaises(UnknownSymbolError):
            self.manager.sell(account.account_id, "MSFT", 1)

    def test_portfolio_snapshot_calculates_total_value(self) -> None:
        account = self.manager.create_account("Alice", 1000)
        self.manager.buy(account.account_id, "AAPL", 5)
        snapshot = self.manager.get_portfolio_snapshot(account.account_id)
        self.assertEqual(snapshot.cash_balance, 500)
        self.assertEqual(snapshot.holdings_value, 500)
        self.assertEqual(snapshot.total_value, 1000)
        self.assertEqual(snapshot.profit_loss, 0)

    def test_profit_loss_uses_net_cash_contributions(self) -> None:
        account = self.manager.create_account("Alice", 1000)
        self.manager.buy(account.account_id, "AAPL", 5)
        self.manager.deposit(account.account_id, 200)
        self.manager.withdraw(account.account_id, 100)
        snapshot = self.manager.get_portfolio_snapshot(account.account_id)
        self.assertEqual(snapshot.net_cash_contributions, 1100)
        self.assertEqual(snapshot.total_value, 1100)
        self.assertEqual(snapshot.profit_loss, 0)

    def test_holdings_as_of_timestamp(self) -> None:
        t1 = datetime(2024, 1, 1, 9, 0, 0)
        t2 = datetime(2024, 1, 2, 9, 0, 0)
        t3 = datetime(2024, 1, 3, 9, 0, 0)
        account = self.manager.create_account("Alice", 1000, timestamp=t1)
        self.manager.buy(account.account_id, "AAPL", 5, timestamp=t2)
        self.manager.sell(account.account_id, "AAPL", 2, timestamp=t3)
        self.assertEqual(self.manager.get_holdings(account.account_id, as_of=t2), {"AAPL": 5})
        self.assertEqual(self.manager.get_holdings(account.account_id, as_of=t3), {"AAPL": 3})

    def test_cash_balance_as_of_timestamp(self) -> None:
        t1 = datetime(2024, 1, 1, 9, 0, 0)
        t2 = datetime(2024, 1, 2, 9, 0, 0)
        t3 = datetime(2024, 1, 3, 9, 0, 0)
        account = self.manager.create_account("Alice", 1000, timestamp=t1)
        self.manager.deposit(account.account_id, 200, timestamp=t2)
        self.manager.withdraw(account.account_id, 100, timestamp=t3)
        self.assertEqual(self.manager.get_cash_balance(account.account_id, as_of=t1), 1000)
        self.assertEqual(self.manager.get_cash_balance(account.account_id, as_of=t2), 1200)
        self.assertEqual(self.manager.get_cash_balance(account.account_id, as_of=t3), 1100)

    def test_transactions_as_of_timestamp(self) -> None:
        t1 = datetime(2024, 1, 1, 9, 0, 0)
        t2 = datetime(2024, 1, 2, 9, 0, 0)
        t3 = datetime(2024, 1, 3, 9, 0, 0)
        account = self.manager.create_account("Alice", 1000, timestamp=t1)
        self.manager.deposit(account.account_id, 200, timestamp=t2)
        self.manager.withdraw(account.account_id, 100, timestamp=t3)
        self.assertEqual(len(self.manager.list_transactions(account.account_id, as_of=t1)), 1)
        self.assertEqual(len(self.manager.list_transactions(account.account_id, as_of=t2)), 2)
        self.assertEqual(len(self.manager.list_transactions(account.account_id, as_of=t3)), 3)

    def test_get_unknown_account_raises(self) -> None:
        with self.assertRaises(AccountNotFoundError):
            self.manager.get_account("missing")


if __name__ == "__main__":
    unittest.main()
