import unittest
from datetime import datetime, timedelta

from account_backend import (
    TradingAccount,
    AccountValidationError,
    InsufficientFundsError,
    InsufficientSharesError,
    UnknownSymbolError,
)


class FakeClock:
    def __init__(self, start: datetime) -> None:
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, seconds: int = 1) -> datetime:
        self.current = self.current + timedelta(seconds=seconds)
        return self.current


class MutablePriceProvider:
    def __init__(self, prices: dict[str, float]) -> None:
        self.prices = {k.upper(): float(v) for k, v in prices.items()}

    def __call__(self, symbol: str) -> float:
        return self.prices[symbol.upper()]

    def set_price(self, symbol: str, price: float) -> None:
        self.prices[symbol.upper()] = float(price)


def fake_price_provider(symbol: str) -> float:
    prices = {"AAPL": 100.0, "TSLA": 200.0, "GOOGL": 300.0}
    return prices[symbol.upper()]


class TradingAccountTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock(datetime(2024, 1, 1, 12, 0, 0))
        self.account = TradingAccount("acct-1", "Alice", 1000.0, price_provider=fake_price_provider, clock=self.clock.now)

    def test_create_account_with_initial_deposit_sets_cash_balance(self) -> None:
        self.assertEqual(self.account.get_cash_balance(), 1000.0)
        self.assertEqual(len(self.account.list_transactions()), 1)
        self.assertAlmostEqual(self.account.get_total_portfolio_value(), 1000.0)

    def test_create_account_rejects_negative_initial_deposit(self) -> None:
        with self.assertRaises(AccountValidationError):
            TradingAccount("acct-2", "Bob", -1.0, price_provider=fake_price_provider)

    def test_create_account_rejects_empty_owner_name(self) -> None:
        with self.assertRaises(AccountValidationError):
            TradingAccount("acct-2", "", 0.0, price_provider=fake_price_provider)

    def test_deposit_increases_cash_balance(self) -> None:
        self.account.deposit(250.0)
        self.assertEqual(self.account.get_cash_balance(), 1250.0)

    def test_deposit_records_transaction(self) -> None:
        tx = self.account.deposit(250.0)
        self.assertEqual(tx.transaction_type, "DEPOSIT")
        self.assertEqual(tx.amount, 250.0)

    def test_deposit_rejects_zero_or_negative_amount(self) -> None:
        with self.assertRaises(AccountValidationError):
            self.account.deposit(0)
        with self.assertRaises(AccountValidationError):
            self.account.deposit(-1)

    def test_withdraw_decreases_cash_balance(self) -> None:
        self.account.withdraw(250.0)
        self.assertEqual(self.account.get_cash_balance(), 750.0)

    def test_withdraw_records_transaction(self) -> None:
        tx = self.account.withdraw(100.0)
        self.assertEqual(tx.transaction_type, "WITHDRAW")
        self.assertEqual(tx.amount, 100.0)

    def test_withdraw_rejects_insufficient_funds(self) -> None:
        with self.assertRaises(InsufficientFundsError):
            self.account.withdraw(2000.0)

    def test_withdraw_rejects_zero_or_negative_amount(self) -> None:
        with self.assertRaises(AccountValidationError):
            self.account.withdraw(0)
        with self.assertRaises(AccountValidationError):
            self.account.withdraw(-5)

    def test_buy_decreases_cash_and_increases_holdings(self) -> None:
        self.account.buy("AAPL", 3)
        self.assertEqual(self.account.get_cash_balance(), 700.0)
        self.assertEqual(self.account.get_holding_quantity("AAPL"), 3)

    def test_buy_records_transaction_with_price_quantity_and_amount(self) -> None:
        tx = self.account.buy("AAPL", 3)
        self.assertEqual(tx.transaction_type, "BUY")
        self.assertEqual(tx.symbol, "AAPL")
        self.assertEqual(tx.quantity, 3)
        self.assertEqual(tx.price, 100.0)
        self.assertEqual(tx.amount, 300.0)

    def test_buy_rejects_insufficient_cash(self) -> None:
        with self.assertRaises(InsufficientFundsError):
            self.account.buy("GOOGL", 4)

    def test_buy_rejects_invalid_quantity(self) -> None:
        with self.assertRaises(AccountValidationError):
            self.account.buy("AAPL", 0)
        with self.assertRaises(AccountValidationError):
            self.account.buy("AAPL", -1)
        with self.assertRaises(AccountValidationError):
            self.account.buy("AAPL", 1.5)  # type: ignore[arg-type]

    def test_buy_rejects_unknown_symbol(self) -> None:
        with self.assertRaises(UnknownSymbolError):
            self.account.buy("MSFT", 1)

    def test_sell_increases_cash_and_decreases_holdings(self) -> None:
        self.account.buy("AAPL", 5)
        self.account.sell("AAPL", 2)
        self.assertEqual(self.account.get_cash_balance(), 700.0)
        self.assertEqual(self.account.get_holding_quantity("AAPL"), 3)

    def test_sell_records_transaction_with_price_quantity_and_amount(self) -> None:
        self.account.buy("AAPL", 2)
        tx = self.account.sell("AAPL", 1)
        self.assertEqual(tx.transaction_type, "SELL")
        self.assertEqual(tx.symbol, "AAPL")
        self.assertEqual(tx.quantity, 1)
        self.assertEqual(tx.price, 100.0)
        self.assertEqual(tx.amount, 100.0)

    def test_sell_rejects_selling_more_than_owned(self) -> None:
        self.account.buy("AAPL", 1)
        with self.assertRaises(InsufficientSharesError):
            self.account.sell("AAPL", 2)

    def test_sell_rejects_invalid_quantity(self) -> None:
        with self.assertRaises(AccountValidationError):
            self.account.sell("AAPL", 0)
        with self.assertRaises(AccountValidationError):
            self.account.sell("AAPL", -1)
        with self.assertRaises(AccountValidationError):
            self.account.sell("AAPL", 1.5)  # type: ignore[arg-type]

    def test_sell_rejects_unknown_symbol(self) -> None:
        with self.assertRaises(UnknownSymbolError):
            self.account.sell("MSFT", 1)

    def test_get_holdings_excludes_zero_quantity_positions(self) -> None:
        self.account.buy("AAPL", 1)
        self.account.sell("AAPL", 1)
        self.assertNotIn("AAPL", self.account.get_holdings())

    def test_multiple_symbols_holdings_are_tracked_independently(self) -> None:
        self.account.buy("AAPL", 2)
        self.account.buy("TSLA", 1)
        self.assertEqual(self.account.get_holdings(), {"AAPL": 2, "TSLA": 1})

    def test_total_portfolio_value_includes_cash_and_holdings_market_value(self) -> None:
        self.account.buy("AAPL", 3)
        self.assertAlmostEqual(self.account.get_total_portfolio_value(), 1000.0)

    def test_holdings_market_value_uses_price_provider(self) -> None:
        self.account.buy("AAPL", 2)
        self.assertAlmostEqual(self.account.get_holdings_market_value(), 200.0)

    def test_profit_loss_zero_when_prices_unchanged_and_no_external_withdrawal_effect(self) -> None:
        self.account.buy("AAPL", 3)
        self.assertAlmostEqual(self.account.get_profit_loss(), 0.0)

    def test_profit_loss_reflects_price_change_from_price_provider(self) -> None:
        prices = MutablePriceProvider({"AAPL": 100.0, "TSLA": 200.0, "GOOGL": 300.0})
        account = TradingAccount("acct-2", "Bob", 1000.0, price_provider=prices, clock=self.clock.now)
        account.buy("AAPL", 5)
        prices.set_price("AAPL", 120.0)
        self.assertAlmostEqual(account.get_profit_loss(), 100.0)

    def test_net_cash_contribution_accounts_for_deposits_and_withdrawals(self) -> None:
        self.account.deposit(500.0)
        self.account.withdraw(200.0)
        self.assertAlmostEqual(self.account.get_net_cash_contribution(), 1300.0)

    def test_list_transactions_returns_all_transactions_in_order(self) -> None:
        self.account.deposit(50.0)
        self.account.buy("AAPL", 1)
        txs = self.account.list_transactions()
        self.assertEqual([t.transaction_type for t in txs], ["CREATE", "DEPOSIT", "BUY"])

    def test_list_transactions_returns_copy_not_internal_list(self) -> None:
        txs = self.account.list_transactions()
        txs.clear()
        self.assertEqual(len(self.account.list_transactions()), 1)

    def test_get_holdings_as_of_time(self) -> None:
        self.clock.advance()
        self.account.buy("AAPL", 5)
        t2 = self.clock.now()
        self.clock.advance()
        self.account.sell("AAPL", 2)
        self.assertEqual(self.account.get_holdings(as_of=t2), {"AAPL": 5})
        self.assertEqual(self.account.get_holdings(), {"AAPL": 3})

    def test_get_cash_balance_as_of_time(self) -> None:
        self.clock.advance()
        self.account.deposit(100.0)
        t2 = self.clock.now()
        self.clock.advance()
        self.account.withdraw(50.0)
        self.assertEqual(self.account.get_cash_balance(as_of=t2), 1100.0)
        self.assertEqual(self.account.get_cash_balance(), 1050.0)

    def test_get_profit_loss_as_of_time(self) -> None:
        self.clock.advance()
        self.account.buy("AAPL", 5)
        t2 = self.clock.now()
        self.assertAlmostEqual(self.account.get_profit_loss(as_of=t2), 0.0)
        self.account.sell("AAPL", 2)
        self.assertAlmostEqual(self.account.get_profit_loss(), 0.0)


if __name__ == "__main__":
    unittest.main()
