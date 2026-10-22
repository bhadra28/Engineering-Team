# Detailed Design: Trading Simulation Account Management System

## Overview

Build a simple in-memory account management system for a trading simulation platform.

The system will support:

- Account creation with an initial deposit.
- Deposits and withdrawals.
- Buy and sell share transactions.
- Validation to prevent:
  - Negative cash balances.
  - Buying shares without enough cash.
  - Selling more shares than currently held.
- Portfolio valuation using `get_share_price(symbol)`.
- Holdings report.
- Profit/loss report.
- Transaction history report.
- “As of” reports for holdings and profit/loss based on a point in time or transaction history cutoff.

All files will live in the same directory. No packages or subdirectories.

Only standard Python libraries and `gradio` are available.

---

# File Structure

All files are in the project root directory:

```text
backend.py
app.py
test_backend.py
README.md
```

---

# Module: `backend.py`

## Responsibility

The backend module contains all core business logic and data models.

The backend should be UI-independent and fully unit-testable.

---

## Design Principles

- Use in-memory storage only.
- Use standard library only.
- Use `dataclasses` for models.
- Use `Decimal` for money calculations.
- Store each trade with the price at execution time.
- Use the provided `get_share_price(symbol)` function for current market prices.
- Reports can be generated:
  - For the current full account state.
  - As of a given timestamp.
  - As of a given transaction id.

---

## Price Provider

### Function

```python
def get_share_price(symbol: str) -> Decimal:
    ...
```

### Behavior

Returns the current price for supported symbols.

Initial test implementation should return fixed prices:

| Symbol | Price |
|---|---:|
| AAPL | 150.00 |
| TSLA | 250.00 |
| GOOGL | 2800.00 |

### Validation

- Symbols should be normalized to uppercase.
- Unknown symbols should raise `UnknownSymbolError`.

---

# Backend Data Models

## Enum: `TransactionType`

```python
class TransactionType(Enum):
    CREATE_ACCOUNT = "CREATE_ACCOUNT"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    BUY = "BUY"
    SELL = "SELL"
```

---

## Dataclass: `Transaction`

Represents one account activity.

```python
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
```

### Field Notes

- `amount`:
  - Used for deposits and withdrawals.
  - For trades, may store total trade value.
- `symbol`:
  - Used for buy/sell.
- `quantity`:
  - Used for buy/sell.
- `price`:
  - Share price at time of transaction.
- `cash_balance_after`:
  - Cash balance immediately after this transaction.
- `notes`:
  - Optional human-readable detail.

---

## Dataclass: `Account`

Represents one user account.

```python
@dataclass
class Account:
    account_id: str
    owner_name: str
    created_at: datetime
    cash_balance: Decimal
    initial_deposit: Decimal
    holdings: dict[str, int]
    transactions: list[Transaction]
```

### Field Notes

- `cash_balance` is available uninvested cash.
- `initial_deposit` is the account creation deposit.
- `holdings` maps stock symbols to share quantities.
- `transactions` is an ordered transaction log.

---

## Dataclass: `HoldingReportRow`

```python
@dataclass(frozen=True)
class HoldingReportRow:
    symbol: str
    quantity: int
    current_price: Decimal
    market_value: Decimal
```

---

## Dataclass: `PortfolioReport`

```python
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
```

### Profit/Loss Definition

Use net cash contributions to avoid misleading results after additional deposits or withdrawals.

```text
net_cash_contributions = total_deposits - total_withdrawals
profit_loss = total_account_value - net_cash_contributions
profit_loss_percent = profit_loss / net_cash_contributions * 100
```

Where:

```text
total_account_value = cash_balance + current market value of holdings
```

If `net_cash_contributions` is zero, `profit_loss_percent` should be `None`.

The `initial_deposit` is still stored and reported separately.

---

# Backend Exceptions

Create specific exceptions for clear validation and UI error handling.

```python
class TradingError(Exception):
    ...
```

```python
class AccountNotFoundError(TradingError):
    ...
```

```python
class AccountAlreadyExistsError(TradingError):
    ...
```

```python
class ValidationError(TradingError):
    ...
```

```python
class InsufficientFundsError(TradingError):
    ...
```

```python
class InsufficientSharesError(TradingError):
    ...
```

```python
class UnknownSymbolError(TradingError):
    ...
```

---

# Backend Service Class

## Class: `TradingService`

Primary API for the app and tests.

```python
class TradingService:
    def __init__(
        self,
        price_provider: Callable[[str], Decimal] = get_share_price,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        ...
```

### Responsibilities

- Own in-memory accounts.
- Create and mutate accounts.
- Validate user actions.
- Generate reports.
- Generate transaction ids.
- Use injected price provider for testability.
- Use injected clock for deterministic tests.

---

## Account Management Methods

### `create_account`

```python
def create_account(
    self,
    account_id: str,
    owner_name: str,
    initial_deposit: Decimal | int | float | str,
) -> Account:
    ...
```

### Behavior

- Creates a new account.
- `account_id` must be unique.
- `owner_name` must be non-empty.
- `initial_deposit` must be positive.
- Cash balance starts equal to `initial_deposit`.
- Adds a `CREATE_ACCOUNT` transaction.
- The transaction amount should equal `initial_deposit`.

---

### `get_account`

```python
def get_account(self, account_id: str) -> Account:
    ...
```

### Behavior

- Returns the account.
- Raises `AccountNotFoundError` if not found.

---

### `list_accounts`

```python
def list_accounts(self) -> list[Account]:
    ...
```

### Behavior

- Returns all accounts sorted by creation time or account id.

---

## Cash Methods

### `deposit`

```python
def deposit(
    self,
    account_id: str,
    amount: Decimal | int | float | str,
) -> Transaction:
    ...
```

### Behavior

- Amount must be positive.
- Adds amount to cash balance.
- Records a `DEPOSIT` transaction.

---

### `withdraw`

```python
def withdraw(
    self,
    account_id: str,
    amount: Decimal | int | float | str,
) -> Transaction:
    ...
```

### Behavior

- Amount must be positive.
- Reject if `amount > cash_balance`.
- Deducts amount from cash balance.
- Records a `WITHDRAWAL` transaction.
- Raises `InsufficientFundsError` if withdrawal would make cash negative.

---

## Trade Methods

### `buy`

```python
def buy(
    self,
    account_id: str,
    symbol: str,
    quantity: int,
) -> Transaction:
    ...
```

### Behavior

- Symbol normalized to uppercase.
- Quantity must be a positive integer.
- Uses `price_provider(symbol)` to get current price.
- Total cost:

```text
total_cost = price * quantity
```

- Reject if `total_cost > cash_balance`.
- Deducts total cost from cash.
- Increases holdings for the symbol.
- Records a `BUY` transaction.
- Raises `InsufficientFundsError` if unaffordable.
- Raises `UnknownSymbolError` if symbol unsupported.

---

### `sell`

```python
def sell(
    self,
    account_id: str,
    symbol: str,
    quantity: int,
) -> Transaction:
    ...
```

### Behavior

- Symbol normalized to uppercase.
- Quantity must be a positive integer.
- Reject if currently held quantity is less than sell quantity.
- Uses `price_provider(symbol)` to get current price.
- Total proceeds:

```text
total_proceeds = price * quantity
```

- Adds proceeds to cash.
- Decreases holdings.
- Remove symbol from holdings if quantity becomes zero.
- Records a `SELL` transaction.
- Raises `InsufficientSharesError` if trying to sell more than held.

---

# Backend Reporting Methods

## `get_holdings`

```python
def get_holdings(
    self,
    account_id: str,
    as_of: datetime | None = None,
    transaction_id: int | None = None,
) -> list[HoldingReportRow]:
    ...
```

### Behavior

- Returns holdings with current market prices.
- If no `as_of` or `transaction_id` is provided, uses current state.
- If `as_of` is provided, reconstructs holdings from transactions up to and including that timestamp.
- If `transaction_id` is provided, reconstructs holdings from transactions up to and including that transaction id.
- Do not allow both `as_of` and `transaction_id` at the same time.
- Uses current `price_provider` for valuation.

---

## `get_portfolio_report`

```python
def get_portfolio_report(
    self,
    account_id: str,
    as_of: datetime | None = None,
    transaction_id: int | None = None,
) -> PortfolioReport:
    ...
```

### Behavior

- Calculates:
  - Cash balance.
  - Holdings.
  - Holdings market value.
  - Total account value.
  - Initial deposit.
  - Net cash contributions.
  - Profit/loss.
  - Profit/loss percent.
- Supports current, timestamp-based, or transaction-id-based reporting.
- Uses reconstructed state when `as_of` or `transaction_id` is provided.

---

## `list_transactions`

```python
def list_transactions(
    self,
    account_id: str,
    as_of: datetime | None = None,
    transaction_id: int | None = None,
) -> list[Transaction]:
    ...
```

### Behavior

- Returns transactions in chronological order.
- If `as_of` is provided, only include transactions up to and including timestamp.
- If `transaction_id` is provided, only include transactions up to and including that id.
- Do not allow both `as_of` and `transaction_id`.

---

# Backend Helper Methods

These can be private methods on `TradingService`.

## `_next_transaction_id`

```python
def _next_transaction_id(self) -> int:
    ...
```

---

## `_normalize_symbol`

```python
def _normalize_symbol(self, symbol: str) -> str:
    ...
```

---

## `_to_decimal_money`

```python
def _to_decimal_money(self, value: Decimal | int | float | str) -> Decimal:
    ...
```

### Behavior

- Converts input to `Decimal`.
- Rejects invalid numeric values.
- Money should be rounded/quantized to 2 decimal places.

---

## `_validate_positive_money`

```python
def _validate_positive_money(self, value: Decimal, field_name: str) -> None:
    ...
```

---

## `_validate_positive_quantity`

```python
def _validate_positive_quantity(self, quantity: int) -> None:
    ...
```

---

## `_record_transaction`

```python
def _record_transaction(
    self,
    account: Account,
    transaction_type: TransactionType,
    amount: Decimal | None = None,
    symbol: str | None = None,
    quantity: int | None = None,
    price: Decimal | None = None,
    notes: str = "",
) -> Transaction:
    ...
```

---

## `_filter_transactions`

```python
def _filter_transactions(
    self,
    transactions: list[Transaction],
    as_of: datetime | None = None,
    transaction_id: int | None = None,
) -> list[Transaction]:
    ...
```

---

## `_reconstruct_state`

```python
def _reconstruct_state(
    self,
    account: Account,
    as_of: datetime | None = None,
    transaction_id: int | None = None,
) -> tuple[Decimal, dict[str, int], Decimal, Decimal]:
    ...
```

### Return Value

```text
cash_balance, holdings, initial_deposit, net_cash_contributions
```

### Behavior

Replay transactions from the beginning through the requested cutoff.

---

## `_calculate_holdings_value`

```python
def _calculate_holdings_value(
    self,
    holdings: dict[str, int],
) -> tuple[Decimal, list[HoldingReportRow]]:
    ...
```

---

# Formatting Helper Functions for Frontend

These should live in `backend.py` or `app.py`. Prefer `app.py` for UI formatting, but backend can provide simple serializers if useful.

## `format_money`

```python
def format_money(value: Decimal | None) -> str:
    ...
```

---

## `format_percent`

```python
def format_percent(value: Decimal | None) -> str:
    ...
```

---

## `transaction_to_row`

```python
def transaction_to_row(transaction: Transaction) -> list[str | int | float]:
    ...
```

---

## `holding_to_row`

```python
def holding_to_row(holding: HoldingReportRow) -> list[str | int | float]:
    ...
```

---

# Module: `app.py`

## Responsibility

The frontend module provides a Gradio 6 web app.

It should import and use `TradingService` from `backend.py`.

The Gradio app should be simple and functional, not over-engineered.

---

# Gradio 6 API Guidance for Frontend Engineer

Use Gradio 6 Blocks API.

Required import:

```python
import gradio as gr
```

App structure signature:

```python
def build_app() -> gr.Blocks:
    ...
```

Launch signature:

```python
if __name__ == "__main__":
    build_app().launch()
```

Use:

```python
with gr.Blocks(title="Trading Simulation Account Manager") as demo:
    ...
```

## Event Listeners

Use `.click(...)` on buttons.

Signature pattern:

```python
button.click(
    fn=handler_function,
    inputs=[input_component_1, input_component_2],
    outputs=[output_component_1, output_component_2],
)
```

For one input or one output, Gradio accepts either the component directly or a list. Prefer lists for consistency.

Important Gradio 6 behavior:

- If there is one output, the handler should return the value directly.
- If there are multiple outputs, return a tuple or list in the exact same order as `outputs`.
- Inputs are passed as positional arguments in the same order as `inputs`.

## Dataframe Changes in Gradio 6

Gradio 6 changed `gr.Dataframe` row/column sizing.

Do **not** use old Gradio 5 style:

```python
row_count=(5, "dynamic")
col_count=(3, "fixed")
```

Use Gradio 6 style:

```python
gr.Dataframe(
    headers=["Column A", "Column B"],
    row_count=0,
    row_limits=None,
    column_count=2,
    column_limits=(2, 2),
)
```

For fixed columns:

```python
column_count=4
column_limits=(4, 4)
```

For dynamic row counts:

```python
row_count=0
row_limits=None
```

## Recommended Components

Use these component constructors:

```python
gr.Markdown(...)
gr.Textbox(label="...", value="...")
gr.Number(label="...", value=...)
gr.Dropdown(label="...", choices=[...])
gr.Button("...")
gr.Dataframe(...)
gr.JSON(label="...")
gr.Tabs()
gr.Tab("...")
gr.Row()
gr.Column()
gr.State(...)
```

## Error Display

Do not allow exceptions to crash the app.

Each handler should catch backend `TradingError` and generic `Exception`.

Return status text in a Markdown or Textbox component.

Recommended status component:

```python
status = gr.Markdown(label="Status")
```

Handlers should return messages such as:

```text
✅ Account created successfully.
❌ Error: Insufficient funds.
```

---

# Frontend App Layout

## Global State

Use one global service instance in `app.py`.

```python
service = TradingService()
```

Optional but recommended:

```python
DEFAULT_SYMBOLS = ["AAPL", "TSLA", "GOOGL"]
```

---

## Page Title

```python
gr.Markdown("# Trading Simulation Account Manager")
```

---

## Tab 1: Account

### Components

- `account_id_input`

```python
gr.Textbox(label="Account ID")
```

- `owner_name_input`

```python
gr.Textbox(label="Owner Name")
```

- `initial_deposit_input`

```python
gr.Number(label="Initial Deposit", value=10000)
```

- `create_account_button`

```python
gr.Button("Create Account")
```

- `account_status_output`

```python
gr.Markdown(label="Account Status")
```

- `account_summary_output`

```python
gr.JSON(label="Account Summary")
```

### Handler

```python
def handle_create_account(
    account_id: str,
    owner_name: str,
    initial_deposit: float,
) -> tuple[str, dict]:
    ...
```

### Outputs

```python
[account_status_output, account_summary_output]
```

---

## Tab 2: Cash

### Components

- `cash_account_id_input`

```python
gr.Textbox(label="Account ID")
```

- `cash_amount_input`

```python
gr.Number(label="Amount", value=1000)
```

- `deposit_button`

```python
gr.Button("Deposit")
```

- `withdraw_button`

```python
gr.Button("Withdraw")
```

- `cash_status_output`

```python
gr.Markdown(label="Cash Status")
```

- `cash_summary_output`

```python
gr.JSON(label="Updated Portfolio Summary")
```

### Handlers

```python
def handle_deposit(
    account_id: str,
    amount: float,
) -> tuple[str, dict]:
    ...
```

```python
def handle_withdraw(
    account_id: str,
    amount: float,
) -> tuple[str, dict]:
    ...
```

### Outputs

```python
[cash_status_output, cash_summary_output]
```

---

## Tab 3: Trade

### Components

- `trade_account_id_input`

```python
gr.Textbox(label="Account ID")
```

- `symbol_input`

Use dropdown to reduce invalid symbols:

```python
gr.Dropdown(
    label="Symbol",
    choices=["AAPL", "TSLA", "GOOGL"],
    value="AAPL",
)
```

- `quantity_input`

```python
gr.Number(label="Quantity", value=1, precision=0)
```

- `buy_button`

```python
gr.Button("Buy")
```

- `sell_button`

```python
gr.Button("Sell")
```

- `trade_status_output`

```python
gr.Markdown(label="Trade Status")
```

- `trade_summary_output`

```python
gr.JSON(label="Updated Portfolio Summary")
```

### Handlers

```python
def handle_buy(
    account_id: str,
    symbol: str,
    quantity: float,
) -> tuple[str, dict]:
    ...
```

```python
def handle_sell(
    account_id: str,
    symbol: str,
    quantity: float,
) -> tuple[str, dict]:
    ...
```

### Notes

- Gradio `Number` may pass quantities as `float`.
- Convert quantity to `int` in handler.
- Reject non-integer quantities before calling backend if desired.

---

## Tab 4: Reports

### Components

- `report_account_id_input`

```python
gr.Textbox(label="Account ID")
```

- `refresh_report_button`

```python
gr.Button("Refresh Reports")
```

- `portfolio_report_output`

```python
gr.JSON(label="Portfolio Report")
```

- `holdings_table_output`

```python
gr.Dataframe(
    headers=["Symbol", "Quantity", "Current Price", "Market Value"],
    row_count=0,
    row_limits=None,
    column_count=4,
    column_limits=(4, 4),
    interactive=False,
    label="Holdings",
)
```

- `transactions_table_output`

```python
gr.Dataframe(
    headers=[
        "ID",
        "Timestamp",
        "Type",
        "Symbol",
        "Quantity",
        "Price",
        "Amount",
        "Cash Balance After",
        "Notes",
    ],
    row_count=0,
    row_limits=None,
    column_count=9,
    column_limits=(9, 9),
    interactive=False,
    label="Transactions",
)
```

- `report_status_output`

```python
gr.Markdown(label="Report Status")
```

### Handler

```python
def handle_refresh_reports(
    account_id: str,
) -> tuple[str, dict, list[list], list[list]]:
    ...
```

### Outputs

```python
[
    report_status_output,
    portfolio_report_output,
    holdings_table_output,
    transactions_table_output,
]
```

---

## Optional Tab 5: As-Of Reports

This is useful for satisfying “at any point in time”.

### Components

- `asof_account_id_input`

```python
gr.Textbox(label="Account ID")
```

- `asof_transaction_id_input`

```python
gr.Number(label="As of Transaction ID", precision=0)
```

- `asof_report_button`

```python
gr.Button("Generate As-Of Report")
```

- `asof_status_output`

```python
gr.Markdown(label="As-Of Status")
```

- `asof_portfolio_output`

```python
gr.JSON(label="As-Of Portfolio Report")
```

- `asof_holdings_output`

```python
gr.Dataframe(
    headers=["Symbol", "Quantity", "Current Price", "Market Value"],
    row_count=0,
    row_limits=None,
    column_count=4,
    column_limits=(4, 4),
    interactive=False,
    label="As-Of Holdings",
)
```

### Handler

```python
def handle_asof_report(
    account_id: str,
    transaction_id: float,
) -> tuple[str, dict, list[list]]:
    ...
```

---

# Frontend Serialization Helpers

These live in `app.py`.

## `portfolio_report_to_dict`

```python
def portfolio_report_to_dict(report: PortfolioReport) -> dict:
    ...
```

Should return JSON-serializable values only.

Convert `Decimal` and `datetime` to strings.

Example shape:

```text
{
    "account_id": "...",
    "owner_name": "...",
    "cash_balance": "1000.00",
    "holdings_value": "500.00",
    "total_value": "1500.00",
    "initial_deposit": "1000.00",
    "net_cash_contributions": "1000.00",
    "profit_loss": "500.00",
    "profit_loss_percent": "50.00%",
    "as_of": "2026-10-22T12:00:00"
}
```

---

## `holdings_to_rows`

```python
def holdings_to_rows(holdings: list[HoldingReportRow]) -> list[list]:
    ...
```

Return rows matching:

```text
["Symbol", "Quantity", "Current Price", "Market Value"]
```

---

## `transactions_to_rows`

```python
def transactions_to_rows(transactions: list[Transaction]) -> list[list]:
    ...
```

Return rows matching:

```text
[
    "ID",
    "Timestamp",
    "Type",
    "Symbol",
    "Quantity",
    "Price",
    "Amount",
    "Cash Balance After",
    "Notes",
]
```

---

## `empty_report`

```python
def empty_report() -> dict:
    ...
```

---

## `empty_holdings_rows`

```python
def empty_holdings_rows() -> list[list]:
    ...
```

---

## `empty_transaction_rows`

```python
def empty_transaction_rows() -> list[list]:
    ...
```

---

# Module: `test_backend.py`

## Responsibility

Unit tests for `backend.py`.

Use standard library `unittest`.

No Gradio tests are required.

---

# Test Data

Use an injected deterministic price provider:

```python
def fixed_price_provider(symbol: str) -> Decimal:
    ...
```

Suggested prices:

| Symbol | Price |
|---|---:|
| AAPL | 100.00 |
| TSLA | 200.00 |
| GOOGL | 1000.00 |

Use an injected deterministic clock where needed.

---

# Required Test Cases

## Account Creation

### `test_create_account_success`

Verify:

- Account is created.
- Cash balance equals initial deposit.
- Initial deposit stored.
- Holdings empty.
- One transaction exists.
- Transaction type is `CREATE_ACCOUNT`.

---

### `test_create_account_rejects_duplicate_id`

Verify:

- Creating an account with an existing id raises `AccountAlreadyExistsError`.

---

### `test_create_account_rejects_non_positive_initial_deposit`

Verify:

- Zero and negative initial deposit raise `ValidationError`.

---

### `test_create_account_rejects_empty_owner_name`

Verify:

- Blank owner name raises `ValidationError`.

---

## Deposits

### `test_deposit_success`

Verify:

- Cash balance increases.
- Deposit transaction is recorded.

---

### `test_deposit_rejects_non_positive_amount`

Verify:

- Zero and negative deposits raise `ValidationError`.

---

## Withdrawals

### `test_withdraw_success`

Verify:

- Cash balance decreases.
- Withdrawal transaction is recorded.

---

### `test_withdraw_rejects_insufficient_funds`

Verify:

- Withdrawal greater than cash balance raises `InsufficientFundsError`.
- Cash balance remains unchanged.

---

### `test_withdraw_rejects_non_positive_amount`

Verify:

- Zero and negative withdrawal amounts raise `ValidationError`.

---

## Buying Shares

### `test_buy_success`

Setup:

- Create account with 1000.
- Price provider returns AAPL = 100.

Verify:

- Buying 3 AAPL succeeds.
- Cash decreases by 300.
- Holdings AAPL equals 3.
- Buy transaction is recorded with price 100 and amount 300.

---

### `test_buy_rejects_insufficient_funds`

Setup:

- Create account with 100.
- AAPL price 100.

Verify:

- Buying 2 AAPL raises `InsufficientFundsError`.
- Cash unchanged.
- Holdings unchanged.

---

### `test_buy_rejects_non_positive_quantity`

Verify:

- Quantity 0 and negative quantity raise `ValidationError`.

---

### `test_buy_rejects_unknown_symbol`

Verify:

- Unknown symbol raises `UnknownSymbolError`.

---

## Selling Shares

### `test_sell_success`

Setup:

- Create account with 1000.
- Buy 5 AAPL at 100.
- Sell 2 AAPL.

Verify:

- Holdings AAPL equals 3.
- Cash increases by 200.
- Sell transaction is recorded.

---

### `test_sell_rejects_insufficient_shares`

Verify:

- Selling more shares than held raises `InsufficientSharesError`.
- Holdings unchanged.
- Cash unchanged.

---

### `test_sell_removes_zero_quantity_holding`

Verify:

- Buy 1 AAPL.
- Sell 1 AAPL.
- AAPL no longer appears in holdings.

---

### `test_sell_rejects_non_positive_quantity`

Verify:

- Quantity 0 and negative quantity raise `ValidationError`.

---

## Portfolio Reports

### `test_portfolio_report_cash_only`

Setup:

- Create account with 1000.

Verify:

- Cash balance 1000.
- Holdings value 0.
- Total value 1000.
- Net cash contributions 1000.
- Profit/loss 0.

---

### `test_portfolio_report_after_buy`

Setup:

- Create account with 1000.
- Buy 2 AAPL at 100.

Verify:

- Cash 800.
- Holdings value 200.
- Total value 1000.
- Profit/loss 0 when price remains 100.

---

### `test_portfolio_report_profit_when_price_increases`

Use mutable/injected price provider.

Setup:

- AAPL price 100.
- Create account with 1000.
- Buy 2 AAPL.
- Change AAPL price to 150.

Verify:

- Cash 800.
- Holdings value 300.
- Total value 1100.
- Profit/loss 100.

---

### `test_portfolio_report_loss_when_price_decreases`

Setup:

- AAPL price 100.
- Create account with 1000.
- Buy 2 AAPL.
- Change AAPL price to 50.

Verify:

- Cash 800.
- Holdings value 100.
- Total value 900.
- Profit/loss -100.

---

## Net Contributions

### `test_profit_loss_uses_net_cash_contributions`

Setup:

- Create account with 1000.
- Deposit 500.
- Withdraw 200.

Verify:

- Net cash contributions 1300.
- If no market movement, profit/loss is 0.

---

## Holdings Report

### `test_get_holdings_returns_market_values`

Setup:

- Buy AAPL and TSLA.

Verify:

- Holdings report has correct symbols, quantities, prices, market values.

---

## Transaction History

### `test_list_transactions_returns_all_transactions_in_order`

Setup:

- Create account.
- Deposit.
- Buy.
- Sell.
- Withdraw.

Verify:

- Transactions returned in expected order.
- Transaction ids are increasing.

---

## As-Of Reporting

### `test_list_transactions_as_of_transaction_id`

Setup:

- Multiple transactions.

Verify:

- Passing transaction id returns only transactions up to that id.

---

### `test_holdings_as_of_transaction_id`

Setup:

- Create account.
- Buy 5 AAPL.
- Sell 2 AAPL.

Verify:

- As of buy transaction id, holdings AAPL is 5.
- As of sell transaction id, holdings AAPL is 3.

---

### `test_portfolio_report_as_of_transaction_id`

Setup:

- Create account with 1000.
- Buy 5 AAPL at 100.
- Sell 2 AAPL at 100.

Verify:

- As-of portfolio report correctly reconstructs cash and holdings.

---

## Account Lookup

### `test_get_missing_account_raises`

Verify:

- Unknown account id raises `AccountNotFoundError`.

---

# README.md

## Responsibility

Small usage guide.

Include:

```text
# Trading Simulation Account Manager

## Run app

uv run python app.py

## Run tests

uv run python -m unittest test_backend.py
```

---

# Engineer Assignments

## backend_engineer

Owns `backend.py`.

### Deliverables

- All backend models.
- All backend exceptions.
- `get_share_price(symbol)`.
- `TradingService`.
- All validation logic.
- Current and as-of reporting.
- Decimal-safe money calculations.
- No Gradio dependencies in backend.

### Implementation Checklist

- [ ] Create `TransactionType`.
- [ ] Create dataclasses:
  - [ ] `Transaction`
  - [ ] `Account`
  - [ ] `HoldingReportRow`
  - [ ] `PortfolioReport`
- [ ] Create exception hierarchy.
- [ ] Implement fixed `get_share_price`.
- [ ] Implement `TradingService.__init__`.
- [ ] Implement account methods.
- [ ] Implement cash methods.
- [ ] Implement trade methods.
- [ ] Implement reporting methods.
- [ ] Implement reconstruction helper for as-of reports.
- [ ] Ensure all money is handled as `Decimal`.
- [ ] Ensure invalid operations do not mutate state.
- [ ] Ensure transaction ids are monotonically increasing.

---

## frontend_engineer

Owns `app.py`.

### Deliverables

- Gradio 6 Blocks app.
- Tabs for:
  - Account creation.
  - Deposits/withdrawals.
  - Buy/sell trades.
  - Reports.
  - Optional as-of reports by transaction id.
- Handler functions that call `TradingService`.
- User-friendly success/error messages.
- JSON portfolio summaries.
- Dataframe holdings and transaction tables.

### Implementation Checklist

- [ ] Import `gradio as gr`.
- [ ] Import backend service and model types.
- [ ] Create global `TradingService`.
- [ ] Implement formatting helpers.
- [ ] Implement `portfolio_report_to_dict`.
- [ ] Implement `holdings_to_rows`.
- [ ] Implement `transactions_to_rows`.
- [ ] Implement all event handlers.
- [ ] Use `.click(fn=..., inputs=[...], outputs=[...])`.
- [ ] Catch backend `TradingError` in every handler.
- [ ] Use Gradio 6 `Dataframe` parameters:
  - [ ] `row_count`
  - [ ] `row_limits`
  - [ ] `column_count`
  - [ ] `column_limits`
- [ ] Do not use old `col_count` or tuple-style `row_count`.
- [ ] Add `if __name__ == "__main__": build_app().launch()`.

---

## test_engineer

Owns `test_backend.py`.

### Deliverables

- Unit tests for backend only.
- Use `unittest`.
- Use deterministic injected price provider.
- Test both success and failure paths.
- Test reports and transaction history.

### Implementation Checklist

- [ ] Create test class for account creation.
- [ ] Create test class for cash operations.
- [ ] Create test class for trades.
- [ ] Create test class for portfolio reports.
- [ ] Create test class for as-of reports.
- [ ] Create test class for transaction history.
- [ ] Verify failed operations do not mutate account state.
- [ ] Verify exact exception types.
- [ ] Verify Decimal values exactly.
- [ ] Ensure tests run with:

```text
uv run python -m unittest test_backend.py
```

---

# Acceptance Criteria

The system is complete when:

- Users can create accounts from the Gradio UI.
- Users can deposit and withdraw funds.
- Users cannot withdraw more cash than available.
- Users can buy and sell supported shares.
- Users cannot buy shares they cannot afford.
- Users cannot sell shares they do not own.
- Holdings are accurately tracked.
- Portfolio value is accurately calculated.
- Profit/loss is accurately calculated against net cash contributions.
- Users can view transaction history.
- Users can view current holdings.
- Users can view current profit/loss.
- Users can generate an as-of report by transaction id.
- Backend unit tests pass.
- App launches with:

```text
uv run python app.py
```

- Tests run with:

```text
uv run python -m unittest test_backend.py
```