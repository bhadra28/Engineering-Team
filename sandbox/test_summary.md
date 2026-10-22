from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from backend import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    InsufficientFundsError,
    InsufficientSharesError,
    TransactionType,
    TradingService,
    UnknownSymbolError,
    ValidationError,
)


class MutablePriceProvider:
    def __init__(self):
        self.prices = {"AAPL": Decimal("100.00"), "TSLA": Decimal("200.00"), "GOOGL": Decimal("1000.00")}

    def __call__(self, symbol: str) -> Decimal:
        symbol = symbol.upper()
        if symbol not in self.prices:
            raise UnknownSymbolError(symbol)
        return self.prices[symbol]


def fixed_price_provider(symbol: str) -> Decimal:
    prices = {"AAPL": Decimal("100.00"), "TSLA": Decimal("200.00"), "GOOGL": Decimal("1000.00")}
    symbol = symbol.upper()
    if symbol not in prices:
        raise UnknownSymbolError(symbol)
    return prices[symbol]


class TestTradingService(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 1, 1, 12, 0, 0)
        self.counter = 0

        def clock():
            self.counter += 1
            return self.now + timedelta(seconds=self.counter)

        self.service = TradingService(price_provider=fixed_price_provider, clock=clock)

    def test_create_account_success(self):
        account = self.service.create_account("a1", "Alice", 1000)
        self.assertEqual(account.cash_balance, Decimal("1000.00"))
        self.assertEqual(account.initial_deposit, Decimal("1000.00"))
        self.assertEqual(account.holdings, {})
        self.assertEqual(len(account.transactions), 1)
        self.assertEqual(account.transactions[0].transaction_type, TransactionType.CREATE_ACCOUNT)
        self.assertEqual(account.transactions[0].amount, Decimal("1000.00"))

    def test_create_account_rejects_duplicate_id(self):
        self.service.create_account("a1", "Alice", 1000)
        with self.assertRaises(AccountAlreadyExistsError):
            self.service.create_account("a1", "Bob", 500)

    def test_create_account_rejects_non_positive_initial_deposit(self):
        with self.assertRaises(ValidationError):
            self.service.create_account("a1", "Alice", 0)
        with self.assertRaises(ValidationError):
            self.service.create_account("a2", "Alice", -1)

    def test_create_account_rejects_empty_owner_name(self):
        with self.assertRaises(ValidationError):
            self.service.create_account("a1", "   ", 100)

    def test_deposit_success(self):
        self.service.create_account("a1", "Alice", 100)
        tx = self.service.deposit("a1", 50)
        account = self.service.get_account("a1")
        self.assertEqual(account.cash_balance, Decimal("150.00"))
        self.assertEqual(tx.transaction_type, TransactionType.DEPOSIT)
        self.assertEqual(tx.amount, Decimal("50.00"))

    def test_deposit_rejects_non_positive_amount(self):
        self.service.create_account("a1", "Alice", 100)
        with self.assertRaises(ValidationError):
            self.service.deposit("a1", 0)
        with self.assertRaises(ValidationError):
            self.service.deposit("a1", -1)

    def test_withdraw_success(self):
        self.service.create_account("a1", "Alice", 100)
        tx = self.service.withdraw("a1", 40)
        account = self.service.get_account("a1")
        self.assertEqual(account.cash_balance, Decimal("60.00"))
        self.assertEqual(tx.transaction_type, TransactionType.WITHDRAWAL)
        self.assertEqual(tx.amount, Decimal("40.00"))

    def test_withdraw_rejects_insufficient_funds(self):
        self.service.create_account("a1", "Alice", 100)
        with self.assertRaises(InsufficientFundsError):
            self.service.withdraw("a1", 101)
        self.assertEqual(self.service.get_account("a1").cash_balance, Decimal("100.00"))

    def test_withdraw_rejects_non_positive_amount(self):
        self.service.create_account("a1", "Alice", 100)
        with self.assertRaises(ValidationError):
            self.service.withdraw("a1", 0)
        with self.assertRaises(ValidationError):
            self.service.withdraw("a1", -1)

    def test_buy_success(self):
        self.service.create_account("a1", "Alice", 1000)
        tx = self.service.buy("a1", "AAPL", 3)
        account = self.service.get_account("a1")
        self.assertEqual(account.cash_balance, Decimal("700.00"))
        self.assertEqual(account.holdings["AAPL"], 3)
        self.assertEqual(tx.transaction_type, TransactionType.BUY)
        self.assertEqual(tx.price, Decimal("100.00"))
        self.assertEqual(tx.amount, Decimal("300.00"))

    def test_buy_rejects_insufficient_funds(self):
        self.service.create_account("a1", "Alice", 100)
        with self.assertRaises(InsufficientFundsError):
            self.service.buy("a1", "AAPL", 2)
        account = self.service.get_account("a1")
        self.assertEqual(account.cash_balance, Decimal("100.00"))
        self.assertEqual(account.holdings, {})

    def test_buy_rejects_non_positive_quantity(self):
        self.service.create_account("a1", "Alice", 1000)
        with self.assertRaises(ValidationError):
            self.service.buy("a1", "AAPL", 0)
        with self.assertRaises(ValidationError):
            self.service.buy("a1", "AAPL", -1)

    def test_buy_rejects_unknown_symbol(self):
        self.service.create_account("a1", "Alice", 1000)
        with self.assertRaises(UnknownSymbolError):
            self.service.buy("a1", "MSFT", 1)

    def test_sell_success(self):
        self.service.create_account("a1", "Alice", 1000)
        self.service.buy("a1", "AAPL", 5)
        tx = self.service.sell("a1", "AAPL", 2)
        account = self.service.get_account("a1")
        self.assertEqual(account.holdings["AAPL"], 3)
        self.assertEqual(account.cash_balance, Decimal("700.00"))
        self.assertEqual(tx.transaction_type, TransactionType.SELL)
        self.assertEqual(tx.amount, Decimal("200.00"))

    def test_sell_rejects_insufficient_shares(self):
        self.service.create_account("a1", "Alice", 1000)
        self.service.buy("a1", "AAPL", 1)
        with self.assertRaises(InsufficientSharesError):
            self.service.sell("a1", "AAPL", 2)
        account = self.service.get_account("a1")
        self.assertEqual(account.holdings["AAPL"], 1)
        self.assertEqual(account.cash_balance, Decimal("900.00"))

    def test_sell_removes_zero_quantity_holding(self):
        self.service.create_account("a1", "Alice", 1000)
        self.service.buy("a1", "AAPL", 1)
        self.service.sell("a1", "AAPL", 1)
        self.assertNotIn("AAPL", self.service.get_account("a1").holdings)

    def test_sell_rejects_non_positive_quantity(self):
        self.service.create_account("a1", "Alice", 1000)
        with self.assertRaises(ValidationError):
            self.service.sell("a1", "AAPL", 0)
        with self.assertRaises(ValidationError):
            self.service.sell("a1", "AAPL", -1)

    def test_portfolio_report_cash_only(self):
        self.service.create_account("a1", "Alice", 1000)
        report = self.service.get_portfolio_report("a1")
        self.assertEqual(report.cash_balance, Decimal("1000.00"))
        self.assertEqual(report.holdings_value, Decimal("0.00"))
        self.assertEqual(report.total_value, Decimal("1000.00"))
        self.assertEqual(report.net_cash_contributions, Decimal("1000.00"))
        self.assertEqual(report.profit_loss, Decimal("0.00"))

    def test_portfolio_report_after_buy(self):
        self.service.create_account("a1", "Alice", 1000)
        self.service.buy("a1", "AAPL", 2)
        report = self.service.get_portfolio_report("a1")
        self.assertEqual(report.cash_balance, Decimal("800.00"))
        self.assertEqual(report.holdings_value, Decimal("200.00"))
        self.assertEqual(report.total_value, Decimal("1000.00"))
        self.assertEqual(report.profit_loss, Decimal("0.00"))

    def test_portfolio_report_profit_when_price_increases(self):
        provider = MutablePriceProvider()
        service = TradingService(price_provider=provider, clock=lambda: self.now)
        service.create_account("a1", "Alice", 1000)
        service.buy("a1", "AAPL", 2)
        provider.prices["AAPL"] = Decimal("150.00")
        report = service.get_portfolio_report("a1")
        self.assertEqual(report.cash_balance, Decimal("800.00"))
        self.assertEqual(report.holdings_value, Decimal("300.00"))
        self.assertEqual(report.total_value, Decimal("1100.00"))
        self.assertEqual(report.profit_loss, Decimal("100.00"))

    def test_portfolio_report_loss_when_price_decreases(self):
        provider = MutablePriceProvider()
        service = TradingService(price_provider=provider, clock=lambda: self.now)
        service.create_account("a1", "Alice", 1000)
        service.buy("a1", "AAPL", 2)
        provider.prices["AAPL"] = Decimal("50.00")
        report = service.get_portfolio_report("a1")
        self.assertEqual(report.cash_balance, Decimal("800.00"))
        self.assertEqual(report.holdings_value, Decimal("100.00"))
        self.assertEqual(report.total_value, Decimal("900.00"))
        self.assertEqual(report.profit_loss, Decimal("-100.00"))

    def test_profit_loss_uses_net_cash_contributions(self):
        self.service.create_account("a1", "Alice", 1000)
        self.service.deposit("a1", 500)
        self.service.withdraw("a1", 200)
        report = self.service.get_portfolio_report("a1")
        self.assertEqual(report.net_cash_contributions, Decimal("1300.00"))
        self.assertEqual(report.profit_loss, Decimal("0.00"))

    def test_get_holdings_returns_market_values(self):
        self.service.create_account("a1", "Alice", 1000)
        self.service.buy("a1", "AAPL", 2)
        self.service.buy("a1", "TSLA", 1)
        holdings = self.service.get_holdings("a1")
        self.assertEqual(len(holdings), 2)
        self.assertEqual(holdings[0].symbol, "AAPL")
        self.assertEqual(holdings[0].quantity, 2)
        self.assertEqual(holdings[0].current_price, Decimal("100.00"))
        self.assertEqual(holdings[0].market_value, Decimal("200.00"))

    def test_list_transactions_returns_all_transactions_in_order(self):
        self.service.create_account("a1", "Alice", 1000)
        self.service.deposit("a1", 100)
        self.service.buy("a1", "AAPL", 1)
        self.service.sell("a1", "AAPL", 1)
        self.service.withdraw("a1", 50)
        txs = self.service.list_transactions("a1")
        self.assertEqual([t.transaction_type for t in txs], [TransactionType.CREATE_ACCOUNT, TransactionType.DEPOSIT, TransactionType.BUY, TransactionType.SELL, TransactionType.WITHDRAWAL])
        self.assertEqual([t.transaction_id for t in txs], sorted(t.transaction_id for t in txs))

    def test_list_transactions_as_of_transaction_id(self):
        self.service.create_account("a1", "Alice", 1000)
        self.service.deposit("a1", 100)
        tx = self.service.buy("a1", "AAPL", 1)
        self.service.withdraw("a1", 50)
        txs = self.service.list_transactions("a1", transaction_id=tx.transaction_id)
        self.assertEqual(len(txs), 3)
        self.assertEqual(txs[-1].transaction_id, tx.transaction_id)

    def test_holdings_as_of_transaction_id(self):
        self.service.create_account("a1", "Alice", 1000)
        buy_tx = self.service.buy("a1", "AAPL", 5)
        sell_tx = self.service.sell("a1", "AAPL", 2)
        holdings_buy = self.service.get_holdings("a1", transaction_id=buy_tx.transaction_id)
        holdings_sell = self.service.get_holdings("a1", transaction_id=sell_tx.transaction_id)
        self.assertEqual(holdings_buy[0].quantity, 5)
        self.assertEqual(holdings_sell[0].quantity, 3)

    def test_portfolio_report_as_of_transaction_id(self):
        self.service.create_account("a1", "Alice", 1000)
        buy_tx = self.service.buy("a1", "AAPL", 5)
        sell_tx = self.service.sell("a1", "AAPL", 2)
        report_buy = self.service.get_portfolio_report("a1", transaction_id=buy_tx.transaction_id)
        report_sell = self.service.get_portfolio_report("a1", transaction_id=sell_tx.transaction_id)
        self.assertEqual(report_buy.cash_balance, Decimal("500.00"))
        self.assertEqual(report_buy.holdings_value, Decimal("500.00"))
        self.assertEqual(report_sell.cash_balance, Decimal("700.00"))
        self.assertEqual(report_sell.holdings_value, Decimal("300.00"))

    def test_get_missing_account_raises(self):
        with self.assertRaises(AccountNotFoundError):
            self.service.get_account("missing")


if __name__ == "__main__":
    unittest.main()