from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import Callable


MONEY_QUANT = Decimal("0.01")


class TradingError(Exception):
    pass


class AccountNotFoundError(TradingError):
    pass


class AccountAlreadyExistsError(TradingError):
    pass


class ValidationError(TradingError):
    pass


class InsufficientFundsError(TradingError):
    pass


class InsufficientSharesError(TradingError):
    pass


class UnknownSymbolError(TradingError):
    pass


class TransactionType(Enum):
    CREATE_ACCOUNT = "CREATE_ACCOUNT"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Transaction:
    transaction_id: int
    account_id: str
    transaction_type: TransactionType
    timestamp: datetime
    amount: Decimal | None = None
    symbol: str | None = None
    quantity: int | None = None
    price: Decimal | None = None
    cash_balance_after: Decimal | None = None
    notes: str = ""


@dataclass
class Account:
    account_id: str
    owner_name: str
    created_at: datetime
    cash_balance: Decimal
    initial_deposit: Decimal
    holdings: dict[str, int]
    transactions: list[Transaction]


@dataclass(frozen=True)
class HoldingReportRow:
    symbol: str
    quantity: int
    current_price: Decimal
    market_value: Decimal


@dataclass(frozen=True)
class PortfolioReport:
    account_id: str
    owner_name: str
    cash_balance: Decimal
    holdings_value: Decimal
    total_value: Decimal
    initial_deposit: Decimal
    net_cash_contributions: Decimal
    profit_loss: Decimal
    profit_loss_percent: Decimal | None
    holdings: list[HoldingReportRow]
    as_of: datetime


def get_share_price(symbol: str) -> Decimal:
    normalized = symbol.upper()
    prices = {
        "AAPL": Decimal("150.00"),
        "TSLA": Decimal("250.00"),
        "GOOGL": Decimal("2800.00"),
    }
    try:
        return prices[normalized]
    except KeyError as exc:
        raise UnknownSymbolError(f"Unknown symbol: {symbol}") from exc


def format_money(value: Decimal | None) -> str:
    if value is None:
        return ""
    return f"{value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP):.2f}"


def format_percent(value: Decimal | None) -> str:
    if value is None:
        return ""
    return f"{value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP):.2f}%"


def transaction_to_row(transaction: Transaction) -> list[str | int | float]:
    return [
        transaction.transaction_id,
        transaction.timestamp.isoformat(),
        transaction.transaction_type.value,
        transaction.symbol or "",
        transaction.quantity if transaction.quantity is not None else "",
        format_money(transaction.price),
        format_money(transaction.amount),
        format_money(transaction.cash_balance_after),
        transaction.notes,
    ]


def holding_to_row(holding: HoldingReportRow) -> list[str | int | float]:
    return [
        holding.symbol,
        holding.quantity,
        format_money(holding.current_price),
        format_money(holding.market_value),
    ]


class TradingService:
    def __init__(self, price_provider: Callable[[str], Decimal] = get_share_price, clock: Callable[[], datetime] | None = None) -> None:
        self.price_provider = price_provider
        self.clock = clock or datetime.utcnow
        self._accounts: dict[str, Account] = {}
        self._transaction_id = 0

    def _next_transaction_id(self) -> int:
        self._transaction_id += 1
        return self._transaction_id

    def _normalize_symbol(self, symbol: str) -> str:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValidationError("Symbol must be a non-empty string.")
        return symbol.strip().upper()

    def _to_decimal_money(self, value: Decimal | int | float | str) -> Decimal:
        try:
            dec = value if isinstance(value, Decimal) else Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValidationError("Invalid money value.") from exc
        return dec.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

    def _validate_positive_money(self, value: Decimal, field_name: str) -> None:
        if value <= 0:
            raise ValidationError(f"{field_name} must be positive.")

    def _validate_positive_quantity(self, quantity: int) -> None:
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValidationError("Quantity must be a positive integer.")

    def _record_transaction(self, account: Account, transaction_type: TransactionType, amount: Decimal | None = None, symbol: str | None = None, quantity: int | None = None, price: Decimal | None = None, notes: str = "") -> Transaction:
        transaction = Transaction(
            transaction_id=self._next_transaction_id(),
            account_id=account.account_id,
            transaction_type=transaction_type,
            timestamp=self.clock(),
            amount=amount,
            symbol=symbol,
            quantity=quantity,
            price=price,
            cash_balance_after=account.cash_balance,
            notes=notes,
        )
        account.transactions.append(transaction)
        return transaction

    def _filter_transactions(self, transactions: list[Transaction], as_of: datetime | None = None, transaction_id: int | None = None) -> list[Transaction]:
        if as_of is not None and transaction_id is not None:
            raise ValidationError("Provide either as_of or transaction_id, not both.")
        if as_of is not None:
            return [t for t in transactions if t.timestamp <= as_of]
        if transaction_id is not None:
            return [t for t in transactions if t.transaction_id <= transaction_id]
        return list(transactions)

    def _reconstruct_state(self, account: Account, as_of: datetime | None = None, transaction_id: int | None = None) -> tuple[Decimal, dict[str, int], Decimal, Decimal]:
        filtered = self._filter_transactions(account.transactions, as_of=as_of, transaction_id=transaction_id)
        cash = Decimal("0.00")
        holdings: dict[str, int] = {}
        initial_deposit = Decimal("0.00")
        total_deposits = Decimal("0.00")
        total_withdrawals = Decimal("0.00")
        for tx in filtered:
            if tx.transaction_type == TransactionType.CREATE_ACCOUNT:
                cash += tx.amount or Decimal("0.00")
                initial_deposit = tx.amount or Decimal("0.00")
                total_deposits += tx.amount or Decimal("0.00")
            elif tx.transaction_type == TransactionType.DEPOSIT:
                cash += tx.amount or Decimal("0.00")
                total_deposits += tx.amount or Decimal("0.00")
            elif tx.transaction_type == TransactionType.WITHDRAWAL:
                cash -= tx.amount or Decimal("0.00")
                total_withdrawals += tx.amount or Decimal("0.00")
            elif tx.transaction_type == TransactionType.BUY:
                cash -= tx.amount or Decimal("0.00")
                holdings[tx.symbol or ""] = holdings.get(tx.symbol or "", 0) + (tx.quantity or 0)
            elif tx.transaction_type == TransactionType.SELL:
                cash += tx.amount or Decimal("0.00")
                sym = tx.symbol or ""
                holdings[sym] = holdings.get(sym, 0) - (tx.quantity or 0)
                if holdings[sym] == 0:
                    holdings.pop(sym)
        return cash, holdings, initial_deposit, total_deposits - total_withdrawals

    def _calculate_holdings_value(self, holdings: dict[str, int]) -> tuple[Decimal, list[HoldingReportRow]]:
        total = Decimal("0.00")
        rows: list[HoldingReportRow] = []
        for symbol in sorted(holdings):
            qty = holdings[symbol]
            price = self.price_provider(symbol)
            market_value = (price * qty).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            total += market_value
            rows.append(HoldingReportRow(symbol=symbol, quantity=qty, current_price=price.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP), market_value=market_value))
        return total.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP), rows

    def create_account(self, account_id: str, owner_name: str, initial_deposit: Decimal | int | float | str) -> Account:
        if account_id in self._accounts:
            raise AccountAlreadyExistsError(f"Account already exists: {account_id}")
        if not isinstance(owner_name, str) or not owner_name.strip():
            raise ValidationError("Owner name must be non-empty.")
        deposit = self._to_decimal_money(initial_deposit)
        self._validate_positive_money(deposit, "Initial deposit")
        account = Account(account_id=account_id, owner_name=owner_name.strip(), created_at=self.clock(), cash_balance=deposit, initial_deposit=deposit, holdings={}, transactions=[])
        self._accounts[account_id] = account
        self._record_transaction(account, TransactionType.CREATE_ACCOUNT, amount=deposit, notes="Account created")
        return account

    def get_account(self, account_id: str) -> Account:
        try:
            return self._accounts[account_id]
        except KeyError as exc:
            raise AccountNotFoundError(f"Account not found: {account_id}") from exc

    def list_accounts(self) -> list[Account]:
        return sorted(self._accounts.values(), key=lambda a: (a.created_at, a.account_id))

    def deposit(self, account_id: str, amount: Decimal | int | float | str) -> Transaction:
        account = self.get_account(account_id)
        amt = self._to_decimal_money(amount)
        self._validate_positive_money(amt, "Deposit amount")
        account.cash_balance += amt
        return self._record_transaction(account, TransactionType.DEPOSIT, amount=amt, notes="Deposit")

    def withdraw(self, account_id: str, amount: Decimal | int | float | str) -> Transaction:
        account = self.get_account(account_id)
        amt = self._to_decimal_money(amount)
        self._validate_positive_money(amt, "Withdrawal amount")
        if amt > account.cash_balance:
            raise InsufficientFundsError("Insufficient cash balance.")
        account.cash_balance -= amt
        return self._record_transaction(account, TransactionType.WITHDRAWAL, amount=amt, notes="Withdrawal")

    def buy(self, account_id: str, symbol: str, quantity: int) -> Transaction:
        account = self.get_account(account_id)
        sym = self._normalize_symbol(symbol)
        self._validate_positive_quantity(quantity)
        try:
            price = self.price_provider(sym).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        except UnknownSymbolError:
            raise
        total_cost = (price * quantity).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        if total_cost > account.cash_balance:
            raise InsufficientFundsError("Insufficient funds to buy shares.")
        account.cash_balance -= total_cost
        account.holdings[sym] = account.holdings.get(sym, 0) + quantity
        return self._record_transaction(account, TransactionType.BUY, amount=total_cost, symbol=sym, quantity=quantity, price=price, notes="Buy")

    def sell(self, account_id: str, symbol: str, quantity: int) -> Transaction:
        account = self.get_account(account_id)
        sym = self._normalize_symbol(symbol)
        self._validate_positive_quantity(quantity)
        if account.holdings.get(sym, 0) < quantity:
            raise InsufficientSharesError("Insufficient shares to sell.")
        price = self.price_provider(sym).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        total_proceeds = (price * quantity).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        account.cash_balance += total_proceeds
        remaining = account.holdings.get(sym, 0) - quantity
        if remaining:
            account.holdings[sym] = remaining
        else:
            account.holdings.pop(sym, None)
        return self._record_transaction(account, TransactionType.SELL, amount=total_proceeds, symbol=sym, quantity=quantity, price=price, notes="Sell")

    def list_transactions(self, account_id: str, as_of: datetime | None = None, transaction_id: int | None = None) -> list[Transaction]:
        account = self.get_account(account_id)
        return self._filter_transactions(account.transactions, as_of=as_of, transaction_id=transaction_id)

    def get_holdings(self, account_id: str, as_of: datetime | None = None, transaction_id: int | None = None) -> list[HoldingReportRow]:
        account = self.get_account(account_id)
        _, holdings, _, _ = self._reconstruct_state(account, as_of=as_of, transaction_id=transaction_id)
        _, rows = self._calculate_holdings_value(holdings)
        return rows

    def get_portfolio_report(self, account_id: str, as_of: datetime | None = None, transaction_id: int | None = None) -> PortfolioReport:
        account = self.get_account(account_id)
        cash_balance, holdings, initial_deposit, net_cash_contributions = self._reconstruct_state(account, as_of=as_of, transaction_id=transaction_id)
        holdings_value, rows = self._calculate_holdings_value(holdings)
        total_value = (cash_balance + holdings_value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        profit_loss = (total_value - net_cash_contributions).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        profit_loss_percent = None if net_cash_contributions == 0 else (profit_loss / net_cash_contributions * Decimal("100")).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        cutoff = as_of or (account.transactions[-1].timestamp if account.transactions else account.created_at)
        return PortfolioReport(account_id=account.account_id, owner_name=account.owner_name, cash_balance=cash_balance.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP), holdings_value=holdings_value, total_value=total_value, initial_deposit=initial_deposit.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP), net_cash_contributions=net_cash_contributions.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP), profit_loss=profit_loss, profit_loss_percent=profit_loss_percent, holdings=rows, as_of=cutoff)
