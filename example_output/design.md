# Design: Simple Account Management System for Trading Simulation

## 1. Overview

Build a single-user, in-memory trading simulation account management system with:

- Account creation
- Cash deposits and withdrawals
- Buy and sell share transactions
- Validation to prevent invalid withdrawals/trades
- Current and historical-as-of reporting from transaction history
- Portfolio value and profit/loss reporting
- Gradio 6 frontend
- Unit tests for backend logic

All files will live in the same sandbox directory. No package folders or subdirectories.

The project runs in a `uv` environment with `gradio` installed. No other third-party packages should be used.

---

## 2. File Layout

All files should be created in the same directory.

```text
account_backend.py
share_prices.py
app.py
test_account_backend.py
```

Optional if engineers want a manual runner:

```text
README.md
```

---

## 3. Backend Design

Assigned to: `backend_engineer`

Primary file:

```text
account_backend.py
```

Supporting file:

```text
share_prices.py
```

The backend must be independent from Gradio so it can be unit tested directly.

---

## 4. `share_prices.py`

This module provides the share price lookup function required by the system.

### Constants

```python
FIXED_SHARE_PRICES: dict[str, float]
```

Expected fixed values:

```text
AAPL  ->  150.00
TSLA  ->  700.00
GOOGL -> 2800.00
```

### Functions

```python
def get_share_price(symbol: str) -> float:
    ...
```

#### Behavior

- Accepts stock symbols case-insensitively.
- Normalizes symbols to uppercase.
- Returns a fixed price for:
  - `AAPL`
  - `TSLA`
  - `GOOGL`
- Raises `UnknownSymbolError` or `ValueError` for unsupported symbols.

Implementation choice:

- Prefer raising the backend-defined `UnknownSymbolError`.
- To avoid a circular import, either:
  - Define `UnknownSymbolError` in `share_prices.py` and import it in `account_backend.py`, or
  - Raise `ValueError` from `share_prices.py` and wrap it in the backend.

Recommended approach:

- Define `UnknownSymbolError` in `account_backend.py`.
- In `share_prices.py`, raise `ValueError`.
- In `account_backend.py`, convert price lookup failures to `UnknownSymbolError` where appropriate.

---

## 5. `account_backend.py`

This is the core domain module.

### Imports

Backend may use Python standard library only:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional, Literal, Any
```

No third-party packages.

---

## 6. Domain Concepts

### Cash Balance

Cash balance changes through:

- Deposits
- Withdrawals
- Buy transactions
- Sell transactions

### Holdings

Holdings are calculated from buy/sell transaction history.

Example:

```text
Buy 10 AAPL
Sell 3 AAPL
Current holding: 7 AAPL
```

### Portfolio Value

Define portfolio value as:

```text
cash balance + market value of current holdings
```

Where:

```text
market value of holdings = quantity held * current share price
```

### Profit/Loss

Because the system supports multiple deposits and withdrawals, use net contribution rather than only the first deposit.

Define profit/loss as:

```text
portfolio value - net cash contribution
```

Where:

```text
net cash contribution = total deposits - total withdrawals
```

This makes the value meaningful even after later deposits and withdrawals.

Also include an optional method for profit/loss against the initial deposit if desired by the frontend or tests.

---

## 7. Exceptions

Define custom exceptions in `account_backend.py`.

```python
class AccountError(Exception):
    ...
```

```python
class AccountValidationError(AccountError):
    ...
```

```python
class InsufficientFundsError(AccountError):
    ...
```

```python
class InsufficientSharesError(AccountError):
    ...
```

```python
class UnknownSymbolError(AccountError):
    ...
```

```python
class AccountNotCreatedError(AccountError):
    ...
```

#### Usage

- `AccountValidationError`
  - Invalid deposit amount
  - Invalid withdrawal amount
  - Invalid trade quantity
  - Empty owner name
- `InsufficientFundsError`
  - Withdrawal would make cash balance negative
  - Buy would cost more than available cash
- `InsufficientSharesError`
  - Sell quantity exceeds current holding
- `UnknownSymbolError`
  - Unsupported share symbol
- `AccountNotCreatedError`
  - Mainly useful for frontend helpers if actions are attempted without an account

---

## 8. Data Classes

### `Transaction`

```python
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
```

#### Field Meanings

| Field | Description |
|---|---|
| `id` | Sequential transaction ID beginning at 1 |
| `timestamp` | Time transaction was recorded |
| `transaction_type` | One of `CREATE`, `DEPOSIT`, `WITHDRAW`, `BUY`, `SELL` |
| `amount` | Cash amount of the transaction |
| `symbol` | Stock symbol for buy/sell transactions |
| `quantity` | Share quantity for buy/sell transactions |
| `price` | Execution price per share for buy/sell transactions |
| `cash_balance_after` | Cash balance immediately after transaction |
| `notes` | Optional human-readable note |

#### Transaction Amount Convention

Use positive values for all transaction `amount` fields.

Example:

```text
DEPOSIT  amount = 1000
WITHDRAW amount = 200
BUY      amount = quantity * price
SELL     amount = quantity * price
```

The transaction type determines whether the amount increases or decreases cash.

---

### `HoldingReportRow`

```python
@dataclass(frozen=True)
class HoldingReportRow:
    symbol: str
    quantity: int
    current_price: float
    market_value: float
```

---

### `AccountSummary`

```python
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
```

---

## 9. Main Backend Class

### `TradingAccount`

```python
class TradingAccount:
    ...
```

### Constructor

```python
def __init__(
    self,
    account_id: str,
    owner_name: str,
    initial_deposit: float = 0.0,
    price_provider: Callable[[str], float] | None = None,
    clock: Callable[[], datetime] | None = None,
) -> None:
    ...
```

#### Constructor Behavior

- Validates `account_id` is non-empty.
- Validates `owner_name` is non-empty.
- Validates `initial_deposit >= 0`.
- Uses `price_provider` to look up current share prices.
- Uses `clock` to generate timestamps.
- If `initial_deposit > 0`, records a `CREATE` or `DEPOSIT` transaction.
- Sets initial cash balance equal to `initial_deposit`.

Recommended transaction approach:

- Always record a `CREATE` transaction with `amount=initial_deposit`.
- If initial deposit is `0`, the transaction still documents account creation.

---

## 10. `TradingAccount` Public Methods

### Account Identity

```python
def get_account_id(self) -> str:
    ...
```

```python
def get_owner_name(self) -> str:
    ...
```

---

### Funding

```python
def deposit(self, amount: float) -> Transaction:
    ...
```

#### Behavior

- Rejects `amount <= 0`.
- Increases cash balance.
- Records a `DEPOSIT` transaction.
- Returns the created transaction.

---

```python
def withdraw(self, amount: float) -> Transaction:
    ...
```

#### Behavior

- Rejects `amount <= 0`.
- Rejects withdrawal if `amount > current_cash_balance`.
- Decreases cash balance.
- Records a `WITHDRAW` transaction.
- Returns the created transaction.

---

### Trading

```python
def buy(self, symbol: str, quantity: int) -> Transaction:
    ...
```

#### Behavior

- Normalizes symbol to uppercase.
- Rejects empty symbol.
- Rejects `quantity <= 0`.
- Looks up current price using `price_provider`.
- Calculates:

```text
cost = price * quantity
```

- Rejects buy if `cost > current_cash_balance`.
- Decreases cash balance by `cost`.
- Increases holdings through transaction history.
- Records a `BUY` transaction.
- Returns the created transaction.

---

```python
def sell(self, symbol: str, quantity: int) -> Transaction:
    ...
```

#### Behavior

- Normalizes symbol to uppercase.
- Rejects empty symbol.
- Rejects `quantity <= 0`.
- Looks up current price using `price_provider`.
- Rejects sale if `quantity > current holding quantity`.
- Calculates:

```text
proceeds = price * quantity
```

- Increases cash balance by `proceeds`.
- Decreases holdings through transaction history.
- Records a `SELL` transaction.
- Returns the created transaction.

---

### Current Balances and Holdings

```python
def get_cash_balance(self, as_of: datetime | None = None) -> float:
    ...
```

#### Behavior

- If `as_of is None`, returns current cash balance.
- If `as_of` is provided, replays transactions up to and including `as_of`.

---

```python
def get_holdings(self, as_of: datetime | None = None) -> dict[str, int]:
    ...
```

#### Behavior

- Returns symbol-to-quantity mapping.
- Excludes zero-quantity positions.
- If `as_of` is provided, only uses transactions with `timestamp <= as_of`.

Example:

```python
{
    "AAPL": 5,
    "TSLA": 2,
}
```

---

```python
def get_holding_quantity(self, symbol: str, as_of: datetime | None = None) -> int:
    ...
```

---

### Portfolio Reporting

```python
def get_holdings_market_value(self, as_of: datetime | None = None) -> float:
    ...
```

#### Behavior

- Gets holdings as of the requested time.
- Uses current share prices from `price_provider`.
- Calculates total market value.

Important limitation:

- Because only `get_share_price(symbol)` is available, historical reports use current market prices for the holdings that existed at `as_of`.
- Historical transaction execution prices are preserved in transactions, but historical market prices are not available.

---

```python
def get_total_portfolio_value(self, as_of: datetime | None = None) -> float:
    ...
```

#### Behavior

Returns:

```text
cash balance as of time + holdings market value as of time
```

---

```python
def get_net_cash_contribution(self, as_of: datetime | None = None) -> float:
    ...
```

#### Behavior

Calculates:

```text
deposits and create amounts - withdrawals
```

As of the requested time.

---

```python
def get_profit_loss(self, as_of: datetime | None = None) -> float:
    ...
```

#### Behavior

Calculates:

```text
total portfolio value - net cash contribution
```

---

```python
def get_profit_loss_from_initial_deposit(self, as_of: datetime | None = None) -> float:
    ...
```

#### Behavior

Calculates:

```text
total portfolio value - initial_deposit
```

This method exists to directly satisfy the phrase “profit or loss from the initial deposit,” but frontend should primarily display both this and net-contribution profit/loss to avoid ambiguity after multiple deposits/withdrawals.

---

```python
def get_holdings_report(self, as_of: datetime | None = None) -> list[HoldingReportRow]:
    ...
```

#### Behavior

Returns one row per current holding:

```text
symbol
quantity
current_price
market_value
```

Sorted alphabetically by symbol.

---

```python
def get_account_summary(self, as_of: datetime | None = None) -> AccountSummary:
    ...
```

#### Behavior

Returns:

- Account ID
- Owner name
- Cash balance
- Holdings market value
- Total portfolio value
- Net cash contribution
- Profit/loss
- Initial deposit
- Profit/loss from initial deposit
- Report timestamp

---

### Transaction Listing

```python
def list_transactions(self, as_of: datetime | None = None) -> list[Transaction]:
    ...
```

#### Behavior

- Returns transactions in chronological order.
- If `as_of` is supplied, returns only transactions with `timestamp <= as_of`.
- Return a copy, not the internal mutable list.

---

```python
def get_transaction_report(self, as_of: datetime | None = None) -> list[dict[str, object]]:
    ...
```

#### Behavior

Returns frontend/test-friendly dictionaries.

Suggested keys:

```text
id
timestamp
transaction_type
symbol
quantity
price
amount
cash_balance_after
notes
```

---

## 11. `TradingAccount` Private Helper Methods

These are implementation helpers. They should still be designed clearly, but unit tests should focus on public behavior.

```python
def _validate_positive_amount(self, amount: float, field_name: str = "amount") -> None:
    ...
```

```python
def _validate_positive_quantity(self, quantity: int) -> None:
    ...
```

```python
def _normalize_symbol(self, symbol: str) -> str:
    ...
```

```python
def _get_price(self, symbol: str) -> float:
    ...
```

```python
def _next_transaction_id(self) -> int:
    ...
```

```python
def _record_transaction(
    self,
    transaction_type: str,
    amount: float,
    symbol: str | None = None,
    quantity: int | None = None,
    price: float | None = None,
    notes: str = "",
) -> Transaction:
    ...
```

```python
def _transactions_until(self, as_of: datetime | None = None) -> list[Transaction]:
    ...
```

```python
def _replay_cash_balance(self, as_of: datetime | None = None) -> float:
    ...
```

```python
def _replay_holdings(self, as_of: datetime | None = None) -> dict[str, int]:
    ...
```

---

## 12. Transaction Type Constants

Use string constants to avoid typos.

```python
TRANSACTION_CREATE: str
TRANSACTION_DEPOSIT: str
TRANSACTION_WITHDRAW: str
TRANSACTION_BUY: str
TRANSACTION_SELL: str
```

Expected values:

```text
CREATE
DEPOSIT
WITHDRAW
BUY
SELL
```

---

## 13. Backend Validation Rules

### Account Creation

Reject:

- Empty account ID
- Empty owner name
- Negative initial deposit

Allow:

- Zero initial deposit

---

### Deposit

Reject:

- Zero amount
- Negative amount
- Non-numeric amount if encountered from frontend

---

### Withdraw

Reject:

- Zero amount
- Negative amount
- Amount greater than current cash balance

---

### Buy

Reject:

- Empty symbol
- Unknown symbol
- Zero quantity
- Negative quantity
- Non-integer quantity
- Cost greater than current cash balance

---

### Sell

Reject:

- Empty symbol
- Unknown symbol
- Zero quantity
- Negative quantity
- Non-integer quantity
- Quantity greater than current holding

---

## 14. Floating Point Rounding

Use normal Python `float` for simplicity.

Recommended behavior:

- Round display values in frontend to 2 decimal places.
- Backend calculations can keep raw floats.
- Tests should compare floats using `assertAlmostEqual`.

No `decimal.Decimal` is required.

---

# Frontend Design

Assigned to: `frontend_engineer`

Primary file:

```text
app.py
```

The frontend should use Gradio 6 and import backend code from `account_backend.py`.

---

## 15. Gradio 6 API Guidance

Use:

```python
import gradio as gr
```

Use Blocks:

```python
with gr.Blocks() as demo:
    ...
```

Launch:

```python
demo.launch()
```

Event listener pattern:

```python
button.click(
    fn=handler_function,
    inputs=[component_a, component_b],
    outputs=[component_x, component_y],
    queue=False,
)
```

For multiple outputs:

- Return a tuple matching output order.
- Or return a dictionary keyed by output components if conditionally updating only some outputs.

Valid Gradio 6 example pattern:

```python
button.click(fn=some_function, inputs=[input_component], outputs=[output_component])
```

Use state:

```python
account_state = gr.State(None)
```

The state can hold the current `TradingAccount` object.

### Important Gradio 6 Dataframe Change

Use:

```python
gr.Dataframe(buttons=["copy", "fullscreen"])
```

Do not use removed Gradio 5 parameters:

```python
show_copy_button=True
show_fullscreen_button=True
```

Those are removed in Gradio 6.

### Avoid Older APIs

Do not use:

```python
component.style(...)
```

Do not rely on old `.update(...)` patterns unless confirmed locally. Prefer returning plain replacement values.

---

## 16. Frontend Imports

```python
import gradio as gr
from account_backend import TradingAccount, AccountError
from share_prices import get_share_price
```

---

## 17. Frontend State

Use one session state object:

```python
account_state = gr.State(None)
```

This state stores either:

```text
None
```

or:

```text
TradingAccount
```

---

## 18. Frontend Layout

Use a `gr.Blocks` app with Markdown title and tabs.

### Main Structure

```text
# Trading Simulation Account Manager

Account Creation
Funding
Trading
Reports
```

Recommended layout:

```python
with gr.Blocks(title="Trading Simulation Account Manager") as demo:
    gr.Markdown("# Trading Simulation Account Manager")
    account_state = gr.State(None)

    with gr.Tab("Account"):
        ...

    with gr.Tab("Funding"):
        ...

    with gr.Tab("Trading"):
        ...

    with gr.Tab("Reports"):
        ...
```

---

## 19. Account Tab

### Components

```python
owner_name_input = gr.Textbox(label="Owner Name", placeholder="Enter your name")
```

```python
initial_deposit_input = gr.Number(label="Initial Deposit", value=10000)
```

```python
create_account_button = gr.Button("Create Account")
```

```python
account_status_output = gr.Markdown()
```

```python
summary_output = gr.Markdown()
```

### Handler Signature

```python
def handle_create_account(
    owner_name: str,
    initial_deposit: float,
) -> tuple[TradingAccount | None, str, str, list[list[object]], list[list[object]]]:
    ...
```

#### Outputs

Return values should map to:

```python
[
    account_state,
    account_status_output,
    summary_output,
    holdings_table,
    transactions_table,
]
```

#### Behavior

- Create a new `TradingAccount`.
- Use a generated account ID.
- Use `get_share_price` as the price provider.
- On success:
  - Return the account object into state.
  - Return success message.
  - Refresh summary, holdings table, and transactions table.
- On failure:
  - Return existing or `None` state.
  - Return error message.
  - Return empty/default report values.

---

## 20. Funding Tab

### Components

```python
funding_amount_input = gr.Number(label="Amount", value=1000)
```

```python
deposit_button = gr.Button("Deposit")
```

```python
withdraw_button = gr.Button("Withdraw")
```

```python
funding_status_output = gr.Markdown()
```

### Handler Signatures

```python
def handle_deposit(
    account: TradingAccount | None,
    amount: float,
) -> tuple[TradingAccount | None, str, str, list[list[object]], list[list[object]]]:
    ...
```

```python
def handle_withdraw(
    account: TradingAccount | None,
    amount: float,
) -> tuple[TradingAccount | None, str, str, list[list[object]], list[list[object]]]:
    ...
```

#### Outputs

Return values should map to:

```python
[
    account_state,
    funding_status_output,
    summary_output,
    holdings_table,
    transactions_table,
]
```

#### Behavior

- If no account exists, show error.
- On deposit/withdraw success:
  - Mutate account through backend method.
  - Return updated account state.
  - Refresh summary, holdings, transactions.
- On backend error:
  - Return unchanged account state.
  - Show error message.

---

## 21. Trading Tab

### Components

Use a dropdown for supported symbols.

```python
symbol_input = gr.Dropdown(
    choices=["AAPL", "TSLA", "GOOGL"],
    value="AAPL",
    label="Symbol",
)
```

```python
quantity_input = gr.Number(label="Quantity", value=1)
```

```python
buy_button = gr.Button("Buy")
```

```python
sell_button = gr.Button("Sell")
```

```python
trade_status_output = gr.Markdown()
```

### Handler Signatures

```python
def handle_buy(
    account: TradingAccount | None,
    symbol: str,
    quantity: float,
) -> tuple[TradingAccount | None, str, str, list[list[object]], list[list[object]]]:
    ...
```

```python
def handle_sell(
    account: TradingAccount | None,
    symbol: str,
    quantity: float,
) -> tuple[TradingAccount | None, str, str, list[list[object]], list[list[object]]]:
    ...
```

#### Quantity Handling

Gradio `gr.Number` returns a numeric value, usually `float`.

Frontend handler should convert to int safely:

```text
1. Reject None.
2. Reject non-whole numbers.
3. Convert to int.
4. Pass int to backend.
```

Do not silently convert `1.5` to `1`.

---

## 22. Reports Tab

### Components

```python
refresh_reports_button = gr.Button("Refresh Reports")
```

```python
summary_output = gr.Markdown(label="Account Summary")
```

```python
holdings_table = gr.Dataframe(
    headers=["Symbol", "Quantity", "Current Price", "Market Value"],
    datatype=["str", "number", "number", "number"],
    interactive=False,
    buttons=["copy", "fullscreen"],
    label="Holdings",
)
```

```python
transactions_table = gr.Dataframe(
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
    datatype=[
        "number",
        "str",
        "str",
        "str",
        "number",
        "number",
        "number",
        "number",
        "str",
    ],
    interactive=False,
    buttons=["copy", "fullscreen"],
    label="Transactions",
)
```

### Handler Signature

```python
def handle_refresh_reports(
    account: TradingAccount | None,
) -> tuple[str, list[list[object]], list[list[object]]]:
    ...
```

#### Outputs

```python
[
    summary_output,
    holdings_table,
    transactions_table,
]
```

---

## 23. Frontend Formatting Helpers

Implement helper functions in `app.py`.

```python
def format_currency(value: float) -> str:
    ...
```

```python
def format_summary(account: TradingAccount | None) -> str:
    ...
```

```python
def holdings_to_table(account: TradingAccount | None) -> list[list[object]]:
    ...
```

```python
def transactions_to_table(account: TradingAccount | None) -> list[list[object]]:
    ...
```

```python
def empty_holdings_table() -> list[list[object]]:
    ...
```

```python
def empty_transactions_table() -> list[list[object]]:
    ...
```

```python
def parse_quantity(value: float | int | None) -> int:
    ...
```

```python
def generate_account_id() -> str:
    ...
```

---

## 24. Frontend Error Handling

All handlers should catch backend errors.

```python
except AccountError as exc:
    ...
```

Also catch general unexpected exceptions and show a safe error message.

Frontend status messages should be Markdown-friendly:

Success:

```text
✅ Deposit successful: $1,000.00
```

Error:

```text
❌ Error: Insufficient funds
```

---

## 25. Frontend Event Wiring

### Account Creation

```python
create_account_button.click(
    fn=handle_create_account,
    inputs=[owner_name_input, initial_deposit_input],
    outputs=[
        account_state,
        account_status_output,
        summary_output,
        holdings_table,
        transactions_table,
    ],
    queue=False,
)
```

### Deposit

```python
deposit_button.click(
    fn=handle_deposit,
    inputs=[account_state, funding_amount_input],
    outputs=[
        account_state,
        funding_status_output,
        summary_output,
        holdings_table,
        transactions_table,
    ],
    queue=False,
)
```

### Withdraw

```python
withdraw_button.click(
    fn=handle_withdraw,
    inputs=[account_state, funding_amount_input],
    outputs=[
        account_state,
        funding_status_output,
        summary_output,
        holdings_table,
        transactions_table,
    ],
    queue=False,
)
```

### Buy

```python
buy_button.click(
    fn=handle_buy,
    inputs=[account_state, symbol_input, quantity_input],
    outputs=[
        account_state,
        trade_status_output,
        summary_output,
        holdings_table,
        transactions_table,
    ],
    queue=False,
)
```

### Sell

```python
sell_button.click(
    fn=handle_sell,
    inputs=[account_state, symbol_input, quantity_input],
    outputs=[
        account_state,
        trade_status_output,
        summary_output,
        holdings_table,
        transactions_table,
    ],
    queue=False,
)
```

### Refresh Reports

```python
refresh_reports_button.click(
    fn=handle_refresh_reports,
    inputs=[account_state],
    outputs=[
        summary_output,
        holdings_table,
        transactions_table,
    ],
    queue=False,
)
```

---

## 26. Frontend App Builder

Expose a builder function for manual use and possible smoke testing.

```python
def build_app() -> gr.Blocks:
    ...
```

Entrypoint:

```python
if __name__ == "__main__":
    demo = build_app()
    demo.launch()
```

---

# Unit Test Design

Assigned to: `test_engineer`

Primary file:

```text
test_account_backend.py
```

Use Python standard library `unittest`.

No pytest dependency.

---

## 27. Test Imports

```python
import unittest
from datetime import datetime, timedelta

from account_backend import (
    TradingAccount,
    AccountValidationError,
    InsufficientFundsError,
    InsufficientSharesError,
    UnknownSymbolError,
)
```

Use a deterministic fake price provider in tests.

```python
def fake_price_provider(symbol: str) -> float:
    ...
```

Suggested fake prices:

```text
AAPL  -> 100.0
TSLA  -> 200.0
GOOGL -> 300.0
```

Use a deterministic fake clock where historical reporting is tested.

---

## 28. Test Cases

### Account Creation

```python
def test_create_account_with_initial_deposit_sets_cash_balance(self) -> None:
    ...
```

Validate:

- Cash balance equals initial deposit.
- Initial transaction exists.
- Portfolio value equals cash if no holdings.

---

```python
def test_create_account_rejects_negative_initial_deposit(self) -> None:
    ...
```

---

```python
def test_create_account_rejects_empty_owner_name(self) -> None:
    ...
```

---

### Deposit

```python
def test_deposit_increases_cash_balance(self) -> None:
    ...
```

---

```python
def test_deposit_records_transaction(self) -> None:
    ...
```

---

```python
def test_deposit_rejects_zero_or_negative_amount(self) -> None:
    ...
```

---

### Withdraw

```python
def test_withdraw_decreases_cash_balance(self) -> None:
    ...
```

---

```python
def test_withdraw_records_transaction(self) -> None:
    ...
```

---

```python
def test_withdraw_rejects_insufficient_funds(self) -> None:
    ...
```

---

```python
def test_withdraw_rejects_zero_or_negative_amount(self) -> None:
    ...
```

---

### Buy

```python
def test_buy_decreases_cash_and_increases_holdings(self) -> None:
    ...
```

Example:

```text
Initial cash: 1000
Buy 3 AAPL at 100
Expected cash: 700
Expected AAPL holding: 3
```

---

```python
def test_buy_records_transaction_with_price_quantity_and_amount(self) -> None:
    ...
```

---

```python
def test_buy_rejects_insufficient_cash(self) -> None:
    ...
```

---

```python
def test_buy_rejects_invalid_quantity(self) -> None:
    ...
```

---

```python
def test_buy_rejects_unknown_symbol(self) -> None:
    ...
```

---

### Sell

```python
def test_sell_increases_cash_and_decreases_holdings(self) -> None:
    ...
```

Example:

```text
Initial cash: 1000
Buy 5 AAPL at 100 -> cash 500
Sell 2 AAPL at 100 -> cash 700
Expected AAPL holding: 3
```

---

```python
def test_sell_records_transaction_with_price_quantity_and_amount(self) -> None:
    ...
```

---

```python
def test_sell_rejects_selling_more_than_owned(self) -> None:
    ...
```

---

```python
def test_sell_rejects_invalid_quantity(self) -> None:
    ...
```

---

```python
def test_sell_rejects_unknown_symbol(self) -> None:
    ...
```

---

### Holdings

```python
def test_get_holdings_excludes_zero_quantity_positions(self) -> None:
    ...
```

Example:

```text
Buy 1 AAPL
Sell 1 AAPL
Holdings should not include AAPL
```

---

```python
def test_multiple_symbols_holdings_are_tracked_independently(self) -> None:
    ...
```

---

### Portfolio Value

```python
def test_total_portfolio_value_includes_cash_and_holdings_market_value(self) -> None:
    ...
```

Example:

```text
Initial cash: 1000
Buy 3 AAPL at 100
Cash: 700
Holdings value: 300
Total portfolio value: 1000
```

---

```python
def test_holdings_market_value_uses_price_provider(self) -> None:
    ...
```

---

### Profit/Loss

```python
def test_profit_loss_zero_when_prices_unchanged_and_no_external_withdrawal_effect(self) -> None:
    ...
```

---

```python
def test_profit_loss_reflects_price_change_from_price_provider(self) -> None:
    ...
```

For this test, use a mutable fake price provider.

Example flow:

```text
Initial deposit: 1000
AAPL price initially 100
Buy 5 AAPL -> cash 500, holdings value 500, total 1000
Change AAPL price to 120
Portfolio value -> 500 + 600 = 1100
Net contribution -> 1000
Profit/loss -> 100
```

---

```python
def test_net_cash_contribution_accounts_for_deposits_and_withdrawals(self) -> None:
    ...
```

---

### Transaction Listing

```python
def test_list_transactions_returns_all_transactions_in_order(self) -> None:
    ...
```

---

```python
def test_list_transactions_returns_copy_not_internal_list(self) -> None:
    ...
```

---

### Historical Reporting

Use a fake clock.

```python
def test_get_holdings_as_of_time(self) -> None:
    ...
```

Example:

```text
t1: create
t2: buy 5 AAPL
t3: sell 2 AAPL

Holdings as of t2 should show 5 AAPL.
Current holdings should show 3 AAPL.
```

---

```python
def test_get_cash_balance_as_of_time(self) -> None:
    ...
```

---

```python
def test_get_profit_loss_as_of_time(self) -> None:
    ...
```

---

## 29. Test Helper Classes

### Fake Clock

```python
class FakeClock:
    def __init__(self, start: datetime) -> None:
        ...

    def now(self) -> datetime:
        ...

    def advance(self, seconds: int = 1) -> datetime:
        ...
```

The backend constructor accepts:

```python
clock=fake_clock.now
```

---

### Mutable Price Provider

```python
class MutablePriceProvider:
    def __init__(self, prices: dict[str, float]) -> None:
        ...

    def __call__(self, symbol: str) -> float:
        ...

    def set_price(self, symbol: str, price: float) -> None:
        ...
```

---

# Engineering Assignments

## 30. `backend_engineer`

### Files

```text
account_backend.py
share_prices.py
```

### Responsibilities

Implement:

- Fixed share price provider
- Domain exceptions
- Transaction dataclass
- Holding report dataclass
- Account summary dataclass
- `TradingAccount` class
- Funding methods
- Buy/sell methods
- Portfolio reporting
- Profit/loss reporting
- Historical-as-of replay
- Transaction listing

### Acceptance Criteria

Backend is complete when:

- Accounts can be created with an initial deposit.
- Deposits increase cash balance.
- Withdrawals decrease cash balance.
- Withdrawals cannot make cash negative.
- Buys decrease cash and increase holdings.
- Buys cannot exceed cash balance.
- Sells increase cash and decrease holdings.
- Sells cannot exceed owned quantity.
- Portfolio value is cash plus current holdings market value.
- Profit/loss is portfolio value minus net contribution.
- Holdings can be reported.
- Profit/loss can be reported.
- Transactions can be listed in order.
- Reports can be generated as of a point in time.
- All backend unit tests pass.

---

## 31. `frontend_engineer`

### File

```text
app.py
```

### Responsibilities

Implement Gradio 6 app:

- Account creation tab
- Funding tab
- Trading tab
- Reports tab
- Gradio session state storing `TradingAccount`
- Event handlers for:
  - Create account
  - Deposit
  - Withdraw
  - Buy
  - Sell
  - Refresh reports
- Markdown summary
- Holdings dataframe
- Transactions dataframe
- User-friendly success/error messages

### Acceptance Criteria

Frontend is complete when:

- App launches with `uv run python app.py`.
- User can create an account.
- User can deposit funds.
- User can withdraw valid amounts.
- Invalid withdrawals show an error.
- User can buy supported shares.
- Invalid buys show an error.
- User can sell owned shares.
- Invalid sells show an error.
- Summary updates after each action.
- Holdings table updates after each action.
- Transactions table updates after each action.
- Uses Gradio 6-compatible APIs.
- Does not use removed Dataframe kwargs `show_copy_button` or `show_fullscreen_button`.

---

## 32. `test_engineer`

### File

```text
test_account_backend.py
```

### Responsibilities

Write unit tests using standard library `unittest`.

Cover:

- Account creation
- Deposit validation
- Withdrawal validation
- Buy validation
- Sell validation
- Holdings calculation
- Portfolio value calculation
- Profit/loss calculation
- Transaction listing
- Historical-as-of reporting

### Acceptance Criteria

Tests are complete when:

- Tests can be run with:

```text
uv run python -m unittest test_account_backend.py
```

- Tests do not depend on Gradio.
- Tests use deterministic fake price providers.
- Tests use deterministic fake clock where time matters.
- Tests cover both successful operations and expected failures.
- All tests pass.

---

# Final Build Success Criteria

The whole system is successful when:

1. Backend tests pass:

```text
uv run python -m unittest test_account_backend.py
```

2. Gradio app launches:

```text
uv run python app.py
```

3. In the app, a user can:
   - Create an account
   - Deposit funds
   - Withdraw funds
   - Buy AAPL, TSLA, and GOOGL shares
   - Sell owned shares
   - View cash balance
   - View holdings
   - View portfolio value
   - View profit/loss
   - View transaction history

4. Invalid actions are blocked:
   - Cannot withdraw more cash than available.
   - Cannot buy shares costing more than available cash.
   - Cannot sell more shares than owned.
   - Cannot use invalid quantities or amounts.

5. Reporting works:
   - Holdings report is accurate.
   - Profit/loss report is accurate.
   - Transaction list is chronological.
   - Backend supports reports as of a specific timestamp.