from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from share_prices import get_share_price

TRANSACTION_CREATE = "CREATE"
TRANSACTION_DEPOSIT = "DEPOSIT"
TRANSACTION_WITHDRAW = "WITHDRAW"
TRANSACTION_BUY = "BUY"
TRANSACTION_SELL = "SELL"


class AccountError(Exception):
    pass


class AccountValidationError(AccountError):
    pass


class InsufficientFundsError(AccountError):
    pass


class InsufficientSharesError(AccountError):
    pass


class UnknownSymbolError(AccountError):
    pass


class AccountNotCreatedError(AccountError):
    pass


@dataclass(frozen=True)
class Transaction:
    id: int
    timestamp: datetime
    transaction_type: str
    amount: float
    symbol: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    cash_balance_after: Optional[float] = None
    notes: str = ""


@dataclass(frozen=True)
class HoldingReportRow:
    symbol: str
    quantity: int
    current_price: float
    market_value: float


@dataclass(frozen=True)
class AccountSummary:
    account_id: str
    owner_name: str
    cash_balance: float
    holdings_market_value: float
    total_portfolio_value: float
    net_cash_contribution: float
    profit_loss: float
    initial_deposit: float
    profit_loss_from_initial_deposit: float
    as_of: datetime


class TradingAccount:
    def __init__(
        self,
        account_id: str,
        owner_name: str,
        initial_deposit: float = 0.0,
        price_provider: Callable[[str], float] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(account_id, str) or not account_id.strip():
            raise AccountValidationError("account_id cannot be empty")
        if not isinstance(owner_name, str) or not owner_name.strip():
            raise AccountValidationError("owner_name cannot be empty")
        if not isinstance(initial_deposit, (int, float)):
            raise AccountValidationError("initial_deposit must be numeric")
        if initial_deposit < 0:
            raise AccountValidationError("initial_deposit cannot be negative")

        self._account_id = account_id.strip()
        self._owner_name = owner_name.strip()
        self._cash_balance = float(initial_deposit)
        self._initial_deposit = float(initial_deposit)
        self._transactions: list[Transaction] = []
        self._price_provider = price_provider or get_share_price
        self._clock = clock or datetime.now
        self._record_transaction(TRANSACTION_CREATE, float(initial_deposit), notes="Account created")

    def get_account_id(self) -> str:
        return self._account_id

    def get_owner_name(self) -> str:
        return self._owner_name

    def deposit(self, amount: float) -> Transaction:
        self._validate_positive_amount(amount)
        self._cash_balance += float(amount)
        return self._record_transaction(TRANSACTION_DEPOSIT, float(amount))

    def withdraw(self, amount: float) -> Transaction:
        self._validate_positive_amount(amount)
        if float(amount) > self._cash_balance:
            raise InsufficientFundsError("Withdrawal would make cash balance negative")
        self._cash_balance -= float(amount)
        return self._record_transaction(TRANSACTION_WITHDRAW, float(amount))

    def buy(self, symbol: str, quantity: int) -> Transaction:
        symbol = self._normalize_symbol(symbol)
        self._validate_positive_quantity(quantity)
        price = self._get_price(symbol)
        cost = price * quantity
        if cost > self._cash_balance:
            raise InsufficientFundsError("Buy would cost more than available cash")
        self._cash_balance -= cost
        return self._record_transaction(TRANSACTION_BUY, cost, symbol=symbol, quantity=quantity, price=price)

    def sell(self, symbol: str, quantity: int) -> Transaction:
        symbol = self._normalize_symbol(symbol)
        self._validate_positive_quantity(quantity)
        price = self._get_price(symbol)
        owned = self.get_holding_quantity(symbol)
        if quantity > owned:
            raise InsufficientSharesError("Cannot sell more shares than owned")
        proceeds = price * quantity
        self._cash_balance += proceeds
        return self._record_transaction(TRANSACTION_SELL, proceeds, symbol=symbol, quantity=quantity, price=price)

    def get_cash_balance(self, as_of: datetime | None = None) -> float:
        if as_of is None:
            return self._cash_balance
        return self._replay_cash_balance(as_of)

    def get_holdings(self, as_of: datetime | None = None) -> dict[str, int]:
        return self._replay_holdings(as_of)

    def get_holding_quantity(self, symbol: str, as_of: datetime | None = None) -> int:
        normalized = self._normalize_symbol(symbol)
        return self.get_holdings(as_of).get(normalized, 0)

    def get_holdings_market_value(self, as_of: datetime | None = None) -> float:
        holdings = self.get_holdings(as_of)
        total = 0.0
        for symbol, quantity in holdings.items():
            total += self._get_price(symbol) * quantity
        return total

    def get_total_portfolio_value(self, as_of: datetime | None = None) -> float:
        return self.get_cash_balance(as_of) + self.get_holdings_market_value(as_of)

    def get_net_cash_contribution(self, as_of: datetime | None = None) -> float:
        total = 0.0
        for transaction in self._transactions_until(as_of):
            if transaction.transaction_type in (TRANSACTION_CREATE, TRANSACTION_DEPOSIT):
                total += transaction.amount
            elif transaction.transaction_type == TRANSACTION_WITHDRAW:
                total -= transaction.amount
        return total

    def get_profit_loss(self, as_of: datetime | None = None) -> float:
        return self.get_total_portfolio_value(as_of) - self.get_net_cash_contribution(as_of)

    def get_profit_loss_from_initial_deposit(self, as_of: datetime | None = None) -> float:
        return self.get_total_portfolio_value(as_of) - self._initial_deposit

    def get_holdings_report(self, as_of: datetime | None = None) -> list[HoldingReportRow]:
        rows = []
        for symbol, quantity in sorted(self.get_holdings(as_of).items()):
            price = self._get_price(symbol)
            rows.append(HoldingReportRow(symbol=symbol, quantity=quantity, current_price=price, market_value=price * quantity))
        return rows

    def get_account_summary(self, as_of: datetime | None = None) -> AccountSummary:
        cash = self.get_cash_balance(as_of)
        holdings_market_value = self.get_holdings_market_value(as_of)
        total = cash + holdings_market_value
        net = self.get_net_cash_contribution(as_of)
        return AccountSummary(
            account_id=self._account_id,
            owner_name=self._owner_name,
            cash_balance=cash,
            holdings_market_value=holdings_market_value,
            total_portfolio_value=total,
            net_cash_contribution=net,
            profit_loss=total - net,
            initial_deposit=self._initial_deposit,
            profit_loss_from_initial_deposit=total - self._initial_deposit,
            as_of=as_of or self._clock(),
        )

    def list_transactions(self, as_of: datetime | None = None) -> list[Transaction]:
        return list(self._transactions_until(as_of))

    def get_transaction_report(self, as_of: datetime | None = None) -> list[dict[str, object]]:
        report = []
        for transaction in self._transactions_until(as_of):
            report.append({
                "id": transaction.id,
                "timestamp": transaction.timestamp,
                "transaction_type": transaction.transaction_type,
                "symbol": transaction.symbol,
                "quantity": transaction.quantity,
                "price": transaction.price,
                "amount": transaction.amount,
                "cash_balance_after": transaction.cash_balance_after,
                "notes": transaction.notes,
            })
        return report

    def _validate_positive_amount(self, amount: float, field_name: str = "amount") -> None:
        if not isinstance(amount, (int, float)):
            raise AccountValidationError(f"{field_name} must be numeric")
        if amount <= 0:
            raise AccountValidationError(f"{field_name} must be greater than zero")

    def _validate_positive_quantity(self, quantity: int) -> None:
        if not isinstance(quantity, int):
            raise AccountValidationError("quantity must be an integer")
        if quantity <= 0:
            raise AccountValidationError("quantity must be greater than zero")

    def _normalize_symbol(self, symbol: str) -> str:
        if not isinstance(symbol, str):
            raise AccountValidationError("symbol must be a string")
        normalized = symbol.strip().upper()
        if not normalized:
            raise AccountValidationError("symbol cannot be empty")
        return normalized

    def _get_price(self, symbol: str) -> float:
        try:
            return float(self._price_provider(symbol))
        except Exception as exc:
            raise UnknownSymbolError(f"Unsupported symbol: {symbol}") from exc

    def _next_transaction_id(self) -> int:
        return len(self._transactions) + 1

    def _record_transaction(
        self,
        transaction_type: str,
        amount: float,
        symbol: str | None = None,
        quantity: int | None = None,
        price: float | None = None,
        notes: str = "",
    ) -> Transaction:
        transaction = Transaction(
            id=self._next_transaction_id(),
            timestamp=self._clock(),
            transaction_type=transaction_type,
            amount=float(amount),
            symbol=symbol,
            quantity=quantity,
            price=price,
            cash_balance_after=self._cash_balance,
            notes=notes,
        )
        self._transactions.append(transaction)
        return transaction

    def _transactions_until(self, as_of: datetime | None = None) -> list[Transaction]:
        if as_of is None:
            return list(self._transactions)
        return [t for t in self._transactions if t.timestamp <= as_of]

    def _replay_cash_balance(self, as_of: datetime | None = None) -> float:
        balance = 0.0
        for transaction in self._transactions_until(as_of):
            if transaction.transaction_type in (TRANSACTION_CREATE, TRANSACTION_DEPOSIT):
                balance += transaction.amount
            elif transaction.transaction_type in (TRANSACTION_WITHDRAW, TRANSACTION_BUY):
                balance -= transaction.amount
            elif transaction.transaction_type == TRANSACTION_SELL:
                balance += transaction.amount
        return balance

    def _replay_holdings(self, as_of: datetime | None = None) -> dict[str, int]:
        holdings: dict[str, int] = {}
        for transaction in self._transactions_until(as_of):
            if transaction.transaction_type == TRANSACTION_BUY and transaction.symbol:
                holdings[transaction.symbol] = holdings.get(transaction.symbol, 0) + int(transaction.quantity or 0)
            elif transaction.transaction_type == TRANSACTION_SELL and transaction.symbol:
                holdings[transaction.symbol] = holdings.get(transaction.symbol, 0) - int(transaction.quantity or 0)
        return {symbol: qty for symbol, qty in holdings.items() if qty != 0}
