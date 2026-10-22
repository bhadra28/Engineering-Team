from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import itertools
from typing import Callable

from prices import get_share_price

AccountId = str
Symbol = str

TRANSACTION_CREATE = "CREATE"
TRANSACTION_DEPOSIT = "DEPOSIT"
TRANSACTION_WITHDRAW = "WITHDRAW"
TRANSACTION_BUY = "BUY"
TRANSACTION_SELL = "SELL"


class TradingSimulationError(Exception):
    pass


class AccountNotFoundError(TradingSimulationError):
    pass


class InvalidAmountError(TradingSimulationError):
    pass


class InvalidQuantityError(TradingSimulationError):
    pass


class InsufficientFundsError(TradingSimulationError):
    pass


class InsufficientHoldingsError(TradingSimulationError):
    pass


class UnknownSymbolError(TradingSimulationError):
    pass


@dataclass
class Transaction:
    transaction_id: str
    account_id: str
    timestamp: datetime
    transaction_type: str
    cash_amount: float
    symbol: str | None = None
    quantity: int | None = None
    price: float | None = None
    cash_balance_after: float | None = None
    note: str = ""


@dataclass
class Account:
    account_id: str
    owner_name: str
    created_at: datetime
    initial_deposit: float
    cash_balance: float
    transactions: list[Transaction]


@dataclass
class Holding:
    symbol: str
    quantity: int
    current_price: float
    market_value: float


@dataclass
class PortfolioSnapshot:
    account_id: str
    as_of: datetime
    cash_balance: float
    holdings: dict[str, int]
    holding_details: list[Holding]
    holdings_value: float
    total_value: float
    net_cash_contributions: float
    profit_loss: float


class AccountManager:
    def __init__(self, price_lookup: Callable[[str], float] | None = None) -> None:
        self._price_lookup = price_lookup or get_share_price
        self._accounts: dict[str, Account] = {}
        self._account_counter = itertools.count(1)
        self._transaction_counter = itertools.count(1)
        self._transaction_order: dict[str, int] = {}
        self._order_counter = itertools.count(1)

    def _now(self) -> datetime:
        return datetime.now()

    def _new_account_id(self) -> str:
        return f"ACC-{next(self._account_counter):06d}"

    def _new_transaction_id(self) -> str:
        return f"TX-{next(self._transaction_counter):08d}"

    def _normalize_symbol(self, symbol: str) -> str:
        return symbol.strip().upper()

    def _get_price_or_raise(self, symbol: str) -> float:
        normalized = self._normalize_symbol(symbol)
        try:
            return float(self._price_lookup(normalized))
        except Exception as exc:
            raise UnknownSymbolError(f"Unsupported symbol: {symbol}") from exc

    def _validate_positive_amount(self, amount: float) -> None:
        if amount <= 0:
            raise InvalidAmountError("Amount must be greater than zero")

    def _validate_non_negative_amount(self, amount: float) -> None:
        if amount < 0:
            raise InvalidAmountError("Amount must be non-negative")

    def _validate_positive_quantity(self, quantity: int) -> None:
        if not isinstance(quantity, int) or quantity <= 0:
            raise InvalidQuantityError("Quantity must be a positive integer")

    def _record_transaction(self, account: Account, transaction_type: str, cash_amount: float, timestamp: datetime, symbol: str | None = None, quantity: int | None = None, price: float | None = None, note: str = "") -> Transaction:
        tx = Transaction(self._new_transaction_id(), account.account_id, timestamp, transaction_type, cash_amount, symbol, quantity, price, account.cash_balance, note)
        account.transactions.append(tx)
        self._transaction_order[tx.transaction_id] = next(self._order_counter)
        return tx

    def _transactions_up_to(self, account: Account, as_of: datetime | None) -> list[Transaction]:
        transactions = [t for t in account.transactions if as_of is None or t.timestamp <= as_of]
        return sorted(transactions, key=lambda t: (t.timestamp, self._transaction_order.get(t.transaction_id, 0)))

    def _compute_holdings_from_transactions(self, transactions: list[Transaction]) -> dict[str, int]:
        holdings: dict[str, int] = defaultdict(int)
        for tx in transactions:
            if tx.transaction_type == TRANSACTION_BUY and tx.symbol and tx.quantity:
                holdings[tx.symbol] += tx.quantity
            elif tx.transaction_type == TRANSACTION_SELL and tx.symbol and tx.quantity:
                holdings[tx.symbol] -= tx.quantity
        return {symbol: qty for symbol, qty in holdings.items() if qty != 0}

    def _compute_cash_balance_from_transactions(self, transactions: list[Transaction]) -> float:
        return sum(tx.cash_amount for tx in transactions)

    def _compute_net_cash_contributions(self, transactions: list[Transaction]) -> float:
        return sum(tx.cash_amount for tx in transactions if tx.transaction_type in {TRANSACTION_CREATE, TRANSACTION_DEPOSIT, TRANSACTION_WITHDRAW})

    def create_account(self, owner_name: str, initial_deposit: float = 0.0, timestamp: datetime | None = None) -> Account:
        if not owner_name.strip():
            raise ValueError("owner_name cannot be empty")
        self._validate_non_negative_amount(initial_deposit)
        created_at = timestamp or self._now()
        account = Account(self._new_account_id(), owner_name.strip(), created_at, initial_deposit, initial_deposit, [])
        self._accounts[account.account_id] = account
        self._record_transaction(account, TRANSACTION_CREATE, initial_deposit, created_at, note="Account created")
        return account

    def get_account(self, account_id: str) -> Account:
        try:
            return self._accounts[account_id]
        except KeyError as exc:
            raise AccountNotFoundError(account_id) from exc

    def list_accounts(self) -> list[Account]:
        return list(self._accounts.values())

    def deposit(self, account_id: str, amount: float, timestamp: datetime | None = None) -> Transaction:
        account = self.get_account(account_id)
        self._validate_positive_amount(amount)
        ts = timestamp or self._now()
        account.cash_balance += amount
        return self._record_transaction(account, TRANSACTION_DEPOSIT, amount, ts, note="Deposit")

    def withdraw(self, account_id: str, amount: float, timestamp: datetime | None = None) -> Transaction:
        account = self.get_account(account_id)
        self._validate_positive_amount(amount)
        if amount > account.cash_balance:
            raise InsufficientFundsError("Insufficient cash balance")
        ts = timestamp or self._now()
        account.cash_balance -= amount
        return self._record_transaction(account, TRANSACTION_WITHDRAW, -amount, ts, note="Withdrawal")

    def buy(self, account_id: str, symbol: str, quantity: int, timestamp: datetime | None = None) -> Transaction:
        account = self.get_account(account_id)
        self._validate_positive_quantity(quantity)
        normalized = self._normalize_symbol(symbol)
        price = self._get_price_or_raise(normalized)
        total_cost = quantity * price
        if total_cost > account.cash_balance:
            raise InsufficientFundsError("Insufficient cash balance")
        ts = timestamp or self._now()
        account.cash_balance -= total_cost
        return self._record_transaction(account, TRANSACTION_BUY, -total_cost, ts, normalized, quantity, price, note="Buy")

    def sell(self, account_id: str, symbol: str, quantity: int, timestamp: datetime | None = None) -> Transaction:
        account = self.get_account(account_id)
        self._validate_positive_quantity(quantity)
        normalized = self._normalize_symbol(symbol)
        self._get_price_or_raise(normalized)
        holdings = self.get_holdings(account_id, as_of=timestamp)
        if holdings.get(normalized, 0) < quantity:
            raise InsufficientHoldingsError("Insufficient holdings")
        price = self._get_price_or_raise(normalized)
        proceeds = quantity * price
        ts = timestamp or self._now()
        account.cash_balance += proceeds
        return self._record_transaction(account, TRANSACTION_SELL, proceeds, ts, normalized, quantity, price, note="Sell")

    def get_holdings(self, account_id: str, as_of: datetime | None = None) -> dict[str, int]:
        account = self.get_account(account_id)
        return self._compute_holdings_from_transactions(self._transactions_up_to(account, as_of))

    def get_cash_balance(self, account_id: str, as_of: datetime | None = None) -> float:
        account = self.get_account(account_id)
        if as_of is None:
            return account.cash_balance
        return self._compute_cash_balance_from_transactions(self._transactions_up_to(account, as_of))

    def get_portfolio_snapshot(self, account_id: str, as_of: datetime | None = None) -> PortfolioSnapshot:
        account = self.get_account(account_id)
        transactions = self._transactions_up_to(account, as_of)
        cash_balance = self._compute_cash_balance_from_transactions(transactions)
        holdings = self._compute_holdings_from_transactions(transactions)
        holding_details: list[Holding] = []
        holdings_value = 0.0
        for symbol, quantity in sorted(holdings.items()):
            price = self._get_price_or_raise(symbol)
            market_value = quantity * price
            holding_details.append(Holding(symbol, quantity, price, market_value))
            holdings_value += market_value
        total_value = cash_balance + holdings_value
        net_cash_contributions = self._compute_net_cash_contributions(transactions)
        profit_loss = total_value - net_cash_contributions
        return PortfolioSnapshot(account.account_id, as_of or self._now(), cash_balance, holdings, holding_details, holdings_value, total_value, net_cash_contributions, profit_loss)

    def list_transactions(self, account_id: str, as_of: datetime | None = None) -> list[Transaction]:
        account = self.get_account(account_id)
        return self._transactions_up_to(account, as_of)


def account_to_row(account: Account) -> list[str | float]:
    return [account.account_id, account.owner_name, account.created_at.isoformat(sep=" ", timespec="seconds"), account.initial_deposit, account.cash_balance]


def transactions_to_rows(transactions: list[Transaction]) -> list[list[str | int | float]]:
    rows: list[list[str | int | float]] = []
    for tx in transactions:
        rows.append([
            tx.timestamp.isoformat(sep=" ", timespec="seconds"),
            tx.transaction_type,
            tx.symbol or "",
            tx.quantity or 0,
            tx.price or 0.0,
            tx.cash_amount,
            tx.cash_balance_after or 0.0,
            tx.note,
        ])
    return rows


def holdings_to_rows(snapshot: PortfolioSnapshot) -> list[list[str | int | float]]:
    return [[h.symbol, h.quantity, h.current_price, h.market_value] for h in snapshot.holding_details]


def snapshot_to_summary(snapshot: PortfolioSnapshot) -> str:
    return (
        f"**Account ID:** {snapshot.account_id}\n\n"
        f"**Cash Balance:** ${snapshot.cash_balance:,.2f}\n\n"
        f"**Holdings Value:** ${snapshot.holdings_value:,.2f}\n\n"
        f"**Total Value:** ${snapshot.total_value:,.2f}\n\n"
        f"**Net Cash Contributions:** ${snapshot.net_cash_contributions:,.2f}\n\n"
        f"**Profit/Loss:** ${snapshot.profit_loss:,.2f}"
    )
