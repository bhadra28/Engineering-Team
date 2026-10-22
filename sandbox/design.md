# Design: Simple Account Management System for Trading Simulation

## Goals

Build a simple single-process account management system for a trading simulation platform.

The system must allow users to:

- Create an account.
- Deposit funds.
- Withdraw funds.
- Record share purchases and sales.
- Prevent invalid withdrawals, purchases, and sales.
- Calculate current holdings.
- Calculate account value.
- Calculate profit/loss at any point in time.
- List all transactions over time.
- Use a provided `get_share_price(symbol)` function with fixed test prices for `AAPL`, `TSLA`, and `GOOGL`.
- Interact with the system through a Gradio app.
- Validate backend behavior with unit tests.

All files will live in the same directory. No packages or subdirectories.

---

# File Structure

```text
prices.py
trading_backend.py
app.py
test_trading_backend.py
```

---

# Backend Design

## File: `prices.py`

### Responsibility

Provide share price lookup functionality.

This file should contain the test implementation of `get_share_price(symbol)` that returns fixed prices for known symbols.

### Constants

```python
FIXED_SHARE_PRICES: dict[str, float]
```

Suggested fixed prices:

```text
AAPL  -> 150.00
TSLA  -> 250.00
GOOGL -> 2800.00
```

### Functions

```python
def get_share_price(symbol: str) -> float:
    """
    Return the current price for a supported share symbol.

    Supported symbols:
    - AAPL
    - TSLA
    - GOOGL

    Args:
        symbol: Share ticker symbol.

    Returns:
        Current share price as a float.

    Raises:
        UnknownSymbolError or ValueError if the symbol is unsupported.
    """
```

Backend engineer may either define `UnknownSymbolError` in this file or import it from `trading_backend.py`. To avoid circular imports, prefer raising `ValueError` from `prices.py` and translating it in service code if needed.

---

## File: `trading_backend.py`

### Responsibility

Implement the core account, transaction, holdings, valuation, and validation logic.

This module must be independent of Gradio.

It should be fully testable through unit tests.

---

## Domain Rules

### Account Creation

- A user can create an account with an owner name and optional initial deposit.
- Initial deposit must be non-negative.
- Account starts with:
  - Cash balance equal to the initial deposit.
  - Empty holdings.
  - A transaction recording account creation and/or initial deposit.

### Deposits

- Deposit amount must be greater than zero.
- Deposits increase cash balance.
- Deposit transactions are recorded.

### Withdrawals

- Withdrawal amount must be greater than zero.
- Withdrawal is rejected if it would make cash balance negative.
- Withdrawals decrease cash balance.
- Withdrawal transactions are recorded.

### Buying Shares

- Symbol must be valid.
- Quantity must be a positive integer.
- Current price is retrieved using `get_share_price(symbol)`.
- Total cost is `quantity * price`.
- Buy is rejected if total cost exceeds cash balance.
- Buy decreases cash balance.
- Buy increases holdings for the symbol.
- Buy transaction is recorded with symbol, quantity, price, and cash amount.

### Selling Shares

- Symbol must be valid.
- Quantity must be a positive integer.
- User must own at least the quantity being sold.
- Current price is retrieved using `get_share_price(symbol)`.
- Proceeds are `quantity * price`.
- Sell increases cash balance.
- Sell decreases holdings for the symbol.
- Sell transaction is recorded with symbol, quantity, price, and cash amount.
- Holdings with zero quantity may be omitted from reports.

### Holdings at a Point in Time

- Holdings should be computed from transactions whose timestamp is less than or equal to `as_of`.
- Only buy and sell transactions affect holdings.
- Deposits and withdrawals do not affect holdings.

### Cash Balance at a Point in Time

- Cash balance should be computed from transactions whose timestamp is less than or equal to `as_of`.
- Deposits and sells increase cash.
- Withdrawals and buys decrease cash.
- Initial deposit/account creation increases cash.

### Portfolio Value

For a point in time:

```text
holdings_value = sum(quantity * current_share_price(symbol))
total_value = cash_balance + holdings_value
```

Because the available price function returns current fixed prices only, historical valuation should use the current fixed price function even when `as_of` is in the past.

### Profit/Loss

Use capital-adjusted profit/loss:

```text
net_cash_contributions = deposits + initial_deposit - withdrawals
profit_loss = total_value - net_cash_contributions
```

This avoids incorrectly treating deposits as investment gains or withdrawals as investment losses.

The UI can label this as:

```text
Profit/Loss = Account Value - Net Cash Contributions
```

---

# Backend Types

## Exceptions

Define these custom exceptions in `trading_backend.py`.

```python
class TradingSimulationError(Exception):
    """Base exception for trading simulation errors."""
```

```python
class AccountNotFoundError(TradingSimulationError):
    """Raised when an account ID does not exist."""
```

```python
class InvalidAmountError(TradingSimulationError):
    """Raised when a deposit, withdrawal, or cash amount is invalid."""
```

```python
class InvalidQuantityError(TradingSimulationError):
    """Raised when a share quantity is invalid."""
```

```python
class InsufficientFundsError(TradingSimulationError):
    """Raised when cash balance is insufficient for withdrawal or purchase."""
```

```python
class InsufficientHoldingsError(TradingSimulationError):
    """Raised when attempting to sell more shares than owned."""
```

```python
class UnknownSymbolError(TradingSimulationError):
    """Raised when a share symbol is unsupported."""
```

---

## Type Aliases

```python
AccountId = str
Symbol = str
```

---

## Transaction Type Values

Use string constants or an enum.

Preferred simple approach: string constants.

```python
TRANSACTION_CREATE: str
TRANSACTION_DEPOSIT: str
TRANSACTION_WITHDRAW: str
TRANSACTION_BUY: str
TRANSACTION_SELL: str
```

Allowed values:

```text
CREATE
DEPOSIT
WITHDRAW
BUY
SELL
```

---

## Dataclass: `Transaction`

```python
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
```

### Field Semantics

| Field | Meaning |
|---|---|
| `transaction_id` | Unique transaction identifier |
| `account_id` | Account this transaction belongs to |
| `timestamp` | Transaction timestamp |
| `transaction_type` | One of `CREATE`, `DEPOSIT`, `WITHDRAW`, `BUY`, `SELL` |
| `cash_amount` | Positive cash impact amount for deposits/sells, negative for withdrawals/buys, initial deposit positive |
| `symbol` | Share symbol for buy/sell transactions |
| `quantity` | Share quantity for buy/sell transactions |
| `price` | Execution price for buy/sell transactions |
| `cash_balance_after` | Cash balance immediately after transaction |
| `note` | Human-readable note |

---

## Dataclass: `Account`

```python
@dataclass
class Account:
    account_id: str
    owner_name: str
    created_at: datetime
    initial_deposit: float
    cash_balance: float
    transactions: list[Transaction]
```

### Notes

- `cash_balance` is the current live cash balance.
- Holdings do not need to be stored separately; they can be derived from transactions.
- If backend engineer wants performance optimization, holdings can be cached internally, but tests should validate behavior through public methods only.

---

## Dataclass: `Holding`

```python
@dataclass
class Holding:
    symbol: str
    quantity: int
    current_price: float
    market_value: float
```

---

## Dataclass: `PortfolioSnapshot`

```python
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
```

---

# Backend Service Class

## Class: `AccountManager`

```python
class AccountManager:
    """
    In-memory account manager for the trading simulation platform.

    Stores accounts and transactions in process memory.
    """
```

### Constructor

```python
def __init__(self, price_lookup: Callable[[str], float] | None = None) -> None:
    """
    Initialize account manager.

    Args:
        price_lookup: Optional function used to retrieve share prices.
                      Defaults to prices.get_share_price.
    """
```

---

## Public Methods

### `create_account`

```python
def create_account(
    self,
    owner_name: str,
    initial_deposit: float = 0.0,
    timestamp: datetime | None = None,
) -> Account:
    """
    Create a new account.

    Args:
        owner_name: Name of account owner.
        initial_deposit: Initial cash deposit. Must be >= 0.
        timestamp: Optional creation timestamp.

    Returns:
        Created Account.

    Raises:
        InvalidAmountError: If initial_deposit is negative.
        ValueError: If owner_name is empty.
    """
```

---

### `get_account`

```python
def get_account(self, account_id: str) -> Account:
    """
    Return account by ID.

    Raises:
        AccountNotFoundError if the account does not exist.
    """
```

---

### `list_accounts`

```python
def list_accounts(self) -> list[Account]:
    """
    Return all accounts.
    """
```

---

### `deposit`

```python
def deposit(
    self,
    account_id: str,
    amount: float,
    timestamp: datetime | None = None,
) -> Transaction:
    """
    Deposit cash into an account.

    Raises:
        AccountNotFoundError
        InvalidAmountError
    """
```

---

### `withdraw`

```python
def withdraw(
    self,
    account_id: str,
    amount: float,
    timestamp: datetime | None = None,
) -> Transaction:
    """
    Withdraw cash from an account.

    Raises:
        AccountNotFoundError
        InvalidAmountError
        InsufficientFundsError
    """
```

---

### `buy`

```python
def buy(
    self,
    account_id: str,
    symbol: str,
    quantity: int,
    timestamp: datetime | None = None,
) -> Transaction:
    """
    Buy shares.

    Raises:
        AccountNotFoundError
        UnknownSymbolError
        InvalidQuantityError
        InsufficientFundsError
    """
```

---

### `sell`

```python
def sell(
    self,
    account_id: str,
    symbol: str,
    quantity: int,
    timestamp: datetime | None = None,
) -> Transaction:
    """
    Sell shares.

    Raises:
        AccountNotFoundError
        UnknownSymbolError
        InvalidQuantityError
        InsufficientHoldingsError
    """
```

---

### `get_holdings`

```python
def get_holdings(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> dict[str, int]:
    """
    Return holdings for an account at a point in time.

    Args:
        account_id: Account ID.
        as_of: Optional timestamp. If None, use current state.

    Returns:
        Dict mapping symbol to quantity.

    Raises:
        AccountNotFoundError
    """
```

---

### `get_cash_balance`

```python
def get_cash_balance(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> float:
    """
    Return cash balance for an account at a point in time.

    Args:
        account_id: Account ID.
        as_of: Optional timestamp. If None, return current account cash balance.

    Raises:
        AccountNotFoundError
    """
```

---

### `get_portfolio_snapshot`

```python
def get_portfolio_snapshot(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> PortfolioSnapshot:
    """
    Return full portfolio snapshot including holdings, value, and P/L.

    Args:
        account_id: Account ID.
        as_of: Optional timestamp. If None, use now/current state.

    Returns:
        PortfolioSnapshot.

    Raises:
        AccountNotFoundError
        UnknownSymbolError
    """
```

---

### `list_transactions`

```python
def list_transactions(
    self,
    account_id: str,
    as_of: datetime | None = None,
) -> list[Transaction]:
    """
    Return transactions for an account.

    Args:
        account_id: Account ID.
        as_of: Optional timestamp. If provided, return transactions up to and including as_of.

    Returns:
        Transactions sorted by timestamp, then insertion order if needed.

    Raises:
        AccountNotFoundError
    """
```

---

# Backend Helper Methods

These can be private methods on `AccountManager`.

```python
def _now(self) -> datetime:
    """
    Return current datetime.
    """
```

```python
def _new_account_id(self) -> str:
    """
    Generate unique account ID.
    """
```

```python
def _new_transaction_id(self) -> str:
    """
    Generate unique transaction ID.
    """
```

```python
def _normalize_symbol(self, symbol: str) -> str:
    """
    Normalize ticker symbol by stripping whitespace and uppercasing.
    """
```

```python
def _get_price_or_raise(self, symbol: str) -> float:
    """
    Return share price or raise UnknownSymbolError.
    """
```

```python
def _validate_positive_amount(self, amount: float) -> None:
    """
    Validate amount is greater than zero.
    """
```

```python
def _validate_non_negative_amount(self, amount: float) -> None:
    """
    Validate amount is greater than or equal to zero.
    """
```

```python
def _validate_positive_quantity(self, quantity: int) -> None:
    """
    Validate quantity is a positive integer.
    """
```

```python
def _record_transaction(
    self,
    account: Account,
    transaction_type: str,
    cash_amount: float,
    timestamp: datetime,
    symbol: str | None = None,
    quantity: int | None = None,
    price: float | None = None,
    note: str = "",
) -> Transaction:
    """
    Create and append a transaction.
    """
```

```python
def _transactions_up_to(
    self,
    account: Account,
    as_of: datetime | None,
) -> list[Transaction]:
    """
    Return transactions up to as_of.
    """
```

```python
def _compute_holdings_from_transactions(
    self,
    transactions: list[Transaction],
) -> dict[str, int]:
    """
    Compute holdings from buy and sell transactions.
    """
```

```python
def _compute_cash_balance_from_transactions(
    self,
    transactions: list[Transaction],
) -> float:
    """
    Compute cash balance from transaction cash_amount values.
    """
```

```python
def _compute_net_cash_contributions(
    self,
    transactions: list[Transaction],
) -> float:
    """
    Compute net cash contributions.

    Include:
    - CREATE cash_amount
    - DEPOSIT cash_amount
    - WITHDRAW cash_amount, which is negative

    Exclude:
    - BUY
    - SELL
    """
```

---

# Formatting Helpers for UI

Backend engineer may provide simple conversion helpers to keep frontend clean.

```python
def account_to_row(account: Account) -> list[str | float]:
    """
    Convert account to table row.
    """
```

```python
def transactions_to_rows(transactions: list[Transaction]) -> list[list[str | int | float]]:
    """
    Convert transactions to rows suitable for gr.Dataframe.
    """
```

```python
def holdings_to_rows(snapshot: PortfolioSnapshot) -> list[list[str | int | float]]:
    """
    Convert holdings to rows suitable for gr.Dataframe.
    """
```

```python
def snapshot_to_summary(snapshot: PortfolioSnapshot) -> str:
    """
    Convert portfolio snapshot to Markdown summary.
    """
```

These are optional but recommended.

---

# Frontend Design

## File: `app.py`

### Responsibility

Build a Gradio app that allows users to interact with the backend.

The app should:

- Create account.
- Select existing account.
- Deposit funds.
- Withdraw funds.
- Buy shares.
- Sell shares.
- View holdings.
- View profit/loss.
- View transaction history.
- Refresh all visible account data after each operation.

---

# Gradio 6 API Guidance

The frontend engineer must use Gradio 6-compatible APIs.

## Imports

```python
import gradio as gr
from trading_backend import AccountManager
```

## Blocks

Use:

```python
with gr.Blocks(title="Trading Simulation Account Manager") as demo:
    ...
```

Then:

```python
if __name__ == "__main__":
    demo.launch()
```

Optional launch configuration:

```python
demo.launch(
    server_name="127.0.0.1",
    server_port=7860,
    show_error=True,
)
```

Do not rely on old Gradio APIs removed in Gradio 6.

---

## Gradio State

Use `gr.State` to store the backend manager instance for the user session.

```python
manager_state = gr.State(value=AccountManager())
```

Important Gradio 6 behavior:

- `gr.State` is hidden.
- It must be passed as both input and output if the function returns an updated state.
- Event handlers can also mutate the manager object in place and return it as the state output.
- State values must be deepcopy-compatible.

Recommended event pattern:

```python
button.click(
    fn=handler_function,
    inputs=[manager_state, other_input],
    outputs=[manager_state, output_component_1, output_component_2],
)
```

---

## Component Constructor Notes for Gradio 6

### `gr.Number`

Use:

```python
gr.Number(
    label="Amount",
    value=0,
    precision=2,
    minimum=0,
    step=1,
)
```

Relevant Gradio 6 signature supports:

```python
gr.Number(
    value=None,
    label=None,
    placeholder=None,
    precision=None,
    minimum=None,
    maximum=None,
    step=1,
    interactive=None,
)
```

### `gr.Textbox`

Use:

```python
gr.Textbox(label="Owner Name")
```

For read-only output:

```python
gr.Textbox(label="Status", interactive=False)
```

### `gr.Dropdown`

Use a dropdown for account selection and symbols.

For symbols:

```python
gr.Dropdown(
    choices=["AAPL", "TSLA", "GOOGL"],
    label="Symbol",
    value="AAPL",
)
```

For accounts, choices need to be refreshed after account creation.

In Gradio 6, update components by returning a new component instance or update object as supported by installed Gradio. Safer design approach:

- Return `gr.Dropdown(choices=..., value=...)` for dropdown output updates.

Example handler output type:

```python
return manager, gr.Dropdown(choices=account_choices, value=selected_account_id), status_text, ...
```

### `gr.Dataframe`

Use Gradio 6 parameters.

Do not use old Gradio 5 tuple forms like:

```python
row_count=(5, "dynamic")
col_count=(3, "fixed")
```

In Gradio 6, use:

```python
gr.Dataframe(
    headers=["Symbol", "Quantity", "Price", "Market Value"],
    datatype=["str", "number", "number", "number"],
    row_count=0,
    column_count=4,
    interactive=False,
    buttons=["copy", "fullscreen"],
)
```

Important Gradio 6 migration notes:

- `show_copy_button=True` is removed.
- `show_fullscreen_button=True` is removed.
- Use:

```python
buttons=["copy", "fullscreen"]
```

- `col_count` is replaced by `column_count`.
- Fixed/dynamic tuple forms are replaced by:
  - `row_count`
  - `row_limits`
  - `column_count`
  - `column_limits`

### Events

Use:

```python
button.click(fn=handler, inputs=[...], outputs=[...])
```

Do not use deprecated event patterns.

Inputs and outputs can be a single component or a list of components.

---

# UI Layout

## Top-Level Components

```python
manager_state = gr.State(value=AccountManager())
```

```python
status_output = gr.Markdown()
```

```python
account_dropdown = gr.Dropdown(
    choices=[],
    label="Selected Account",
    interactive=True,
)
```

---

## Section: Create Account

Components:

```python
owner_name_input = gr.Textbox(label="Owner Name")
initial_deposit_input = gr.Number(
    label="Initial Deposit",
    value=10000,
    precision=2,
    minimum=0,
    step=100,
)
create_account_button = gr.Button("Create Account")
```

Handler:

```python
def handle_create_account(
    manager: AccountManager,
    owner_name: str,
    initial_deposit: float,
) -> tuple[
    AccountManager,
    gr.Dropdown,
    str,
    list[list[str | float]],
    list[list[str | int | float]],
    str,
]:
    """
    Create account and refresh account dropdown, accounts table,
    transactions table, and summary.
    """
```

Outputs:

```text
manager_state
account_dropdown
status_output
accounts_table
transactions_table
portfolio_summary
```

---

## Section: Cash Operations

Components:

```python
cash_amount_input = gr.Number(
    label="Cash Amount",
    value=1000,
    precision=2,
    minimum=0,
    step=100,
)
deposit_button = gr.Button("Deposit")
withdraw_button = gr.Button("Withdraw")
```

Handlers:

```python
def handle_deposit(
    manager: AccountManager,
    account_id: str,
    amount: float,
) -> tuple[
    AccountManager,
    str,
    list[list[str | int | float]],
    list[list[str | int | float]],
    str,
]:
    """
    Deposit funds and refresh UI.
    """
```

```python
def handle_withdraw(
    manager: AccountManager,
    account_id: str,
    amount: float,
) -> tuple[
    AccountManager,
    str,
    list[list[str | int | float]],
    list[list[str | int | float]],
    str,
]:
    """
    Withdraw funds and refresh UI.
    """
```

Outputs:

```text
manager_state
status_output
transactions_table
holdings_table
portfolio_summary
```

---

## Section: Trade Operations

Components:

```python
symbol_dropdown = gr.Dropdown(
    choices=["AAPL", "TSLA", "GOOGL"],
    label="Symbol",
    value="AAPL",
)
quantity_input = gr.Number(
    label="Quantity",
    value=1,
    precision=0,
    minimum=1,
    step=1,
)
buy_button = gr.Button("Buy")
sell_button = gr.Button("Sell")
```

Handlers:

```python
def handle_buy(
    manager: AccountManager,
    account_id: str,
    symbol: str,
    quantity: float,
) -> tuple[
    AccountManager,
    str,
    list[list[str | int | float]],
    list[list[str | int | float]],
    str,
]:
    """
    Buy shares and refresh UI.
    """
```

```python
def handle_sell(
    manager: AccountManager,
    account_id: str,
    symbol: str,
    quantity: float,
) -> tuple[
    AccountManager,
    str,
    list[list[str | int | float]],
    list[list[str | int | float]],
    str,
]:
    """
    Sell shares and refresh UI.
    """
```

Implementation notes:

- `gr.Number` may pass quantity as `float`.
- Convert quantity to `int` in handler.
- Reject non-integer quantities in backend or handler.

Outputs:

```text
manager_state
status_output
transactions_table
holdings_table
portfolio_summary
```

---

## Section: Portfolio Reports

Components:

```python
refresh_button = gr.Button("Refresh Reports")
```

```python
portfolio_summary = gr.Markdown()
```

```python
holdings_table = gr.Dataframe(
    headers=["Symbol", "Quantity", "Current Price", "Market Value"],
    datatype=["str", "number", "number", "number"],
    row_count=0,
    column_count=4,
    interactive=False,
    buttons=["copy", "fullscreen"],
)
```

```python
transactions_table = gr.Dataframe(
    headers=[
        "Timestamp",
        "Type",
        "Symbol",
        "Quantity",
        "Price",
        "Cash Amount",
        "Cash Balance After",
        "Note",
    ],
    datatype=["str", "str", "str", "number", "number", "number", "number", "str"],
    row_count=0,
    column_count=8,
    interactive=False,
    buttons=["copy", "fullscreen"],
)
```

```python
accounts_table = gr.Dataframe(
    headers=["Account ID", "Owner", "Created At", "Initial Deposit", "Cash Balance"],
    datatype=["str", "str", "str", "number", "number"],
    row_count=0,
    column_count=5,
    interactive=False,
    buttons=["copy", "fullscreen"],
)
```

Handler:

```python
def handle_refresh(
    manager: AccountManager,
    account_id: str,
) -> tuple[
    str,
    list[list[str | float]],
    list[list[str | int | float]],
    list[list[str | int | float]],
]:
    """
    Refresh status, accounts table, transactions table, holdings table, and summary.
    """
```

Outputs:

```text
status_output
accounts_table
transactions_table
holdings_table
portfolio_summary
```

---

# Frontend Helper Functions

Define these in `app.py`.

```python
def format_account_choice(account_id: str, owner_name: str) -> str:
    """
    Return display string for account dropdown if needed.
    """
```

Simpler recommended approach:

- Use account IDs directly as dropdown values.
- Show details in accounts table.

```python
def get_account_choices(manager: AccountManager) -> list[str]:
    """
    Return list of account IDs for dropdown.
    """
```

```python
def build_accounts_rows(manager: AccountManager) -> list[list[str | float]]:
    """
    Build rows for accounts table.
    """
```

```python
def build_transactions_rows(
    manager: AccountManager,
    account_id: str | None,
) -> list[list[str | int | float]]:
    """
    Build rows for transactions table.
    """
```

```python
def build_holdings_rows(
    manager: AccountManager,
    account_id: str | None,
) -> list[list[str | int | float]]:
    """
    Build rows for holdings table.
    """
```

```python
def build_portfolio_summary(
    manager: AccountManager,
    account_id: str | None,
) -> str:
    """
    Build Markdown summary of cash balance, holdings value, total value,
    net cash contributions, and profit/loss.
    """
```

```python
def safe_status_message(error: Exception) -> str:
    """
    Convert backend exception to a user-friendly status message.
    """
```

---

# UI Error Handling

Every handler should catch backend exceptions and return a user-friendly status message without crashing the Gradio app.

Example status strings:

```text
✅ Account created: <account_id>
✅ Deposited $1,000.00
✅ Withdrew $500.00
✅ Bought 3 AAPL at $150.00
✅ Sold 1 TSLA at $250.00
❌ Insufficient funds
❌ Insufficient holdings
❌ Please select an account
❌ Unsupported symbol
```

---

# Unit Test Design

## File: `test_trading_backend.py`

### Responsibility

Test backend behavior only.

Do not test Gradio UI.

Use Python standard library only.

Recommended test framework: `unittest`.

---

# Test Fixtures

Use a deterministic price lookup function in tests.

```python
def fixed_price_lookup(symbol: str) -> float:
    """
    Return deterministic prices for tests.
    """
```

Suggested values:

```text
AAPL  -> 100.00
TSLA  -> 200.00
GOOGL -> 1000.00
```

For unknown symbols, raise `ValueError`.

Each test should instantiate a fresh manager:

```python
manager = AccountManager(price_lookup=fixed_price_lookup)
```

---

# Required Unit Tests

## Account Creation

```python
def test_create_account_with_initial_deposit(self) -> None:
    """
    Account has expected owner, initial deposit, cash balance, and create transaction.
    """
```

```python
def test_create_account_rejects_negative_initial_deposit(self) -> None:
    """
    Negative initial deposit raises InvalidAmountError.
    """
```

```python
def test_create_account_rejects_empty_owner_name(self) -> None:
    """
    Empty owner name raises ValueError.
    """
```

---

## Deposits

```python
def test_deposit_increases_cash_balance(self) -> None:
    """
    Deposit updates cash balance and records transaction.
    """
```

```python
def test_deposit_rejects_zero_or_negative_amount(self) -> None:
    """
    Zero and negative deposits raise InvalidAmountError.
    """
```

---

## Withdrawals

```python
def test_withdraw_decreases_cash_balance(self) -> None:
    """
    Withdrawal updates cash balance and records transaction.
    """
```

```python
def test_withdraw_rejects_insufficient_funds(self) -> None:
    """
    Cannot withdraw more than cash balance.
    """
```

```python
def test_withdraw_rejects_zero_or_negative_amount(self) -> None:
    """
    Zero and negative withdrawals raise InvalidAmountError.
    """
```

---

## Buying

```python
def test_buy_decreases_cash_and_increases_holdings(self) -> None:
    """
    Buying shares subtracts cash and increases holdings.
    """
```

```python
def test_buy_rejects_insufficient_funds(self) -> None:
    """
    Cannot buy more shares than cash allows.
    """
```

```python
def test_buy_rejects_invalid_quantity(self) -> None:
    """
    Quantity must be positive integer.
    """
```

```python
def test_buy_rejects_unknown_symbol(self) -> None:
    """
    Unknown symbol raises UnknownSymbolError.
    """
```

---

## Selling

```python
def test_sell_increases_cash_and_decreases_holdings(self) -> None:
    """
    Selling shares adds cash and reduces holdings.
    """
```

```python
def test_sell_rejects_insufficient_holdings(self) -> None:
    """
    Cannot sell more shares than owned.
    """
```

```python
def test_sell_rejects_invalid_quantity(self) -> None:
    """
    Quantity must be positive integer.
    """
```

```python
def test_sell_rejects_unknown_symbol(self) -> None:
    """
    Unknown symbol raises UnknownSymbolError.
    """
```

---

## Portfolio Snapshot

```python
def test_portfolio_snapshot_calculates_total_value(self) -> None:
    """
    Snapshot total value equals cash plus holdings market value.
    """
```

```python
def test_profit_loss_uses_net_cash_contributions(self) -> None:
    """
    Profit/loss equals total value minus deposits plus withdrawals adjustment.
    """
```

Suggested scenario:

```text
Initial deposit: 1000
Buy 5 AAPL at 100 = 500
Cash = 500
Holdings value = 500
Total value = 1000
Net cash contributions = 1000
P/L = 0
```

Then if price lookup is changed or custom manager uses different current price, validate P/L changes accordingly.

Since price lookup is fixed in a manager instance, another test can use:

```text
Initial deposit: 1000
AAPL price = 100
Buy 5 AAPL
Then use a separate price lookup or mutable price lookup returning AAPL = 120
Snapshot:
Cash = 500
Holdings value = 600
Total value = 1100
P/L = 100
```

If implementing mutable prices is too much for tests, test zero P/L with fixed prices.

---

## Historical Reports

```python
def test_holdings_as_of_timestamp(self) -> None:
    """
    Holdings at a prior timestamp exclude later trades.
    """
```

```python
def test_cash_balance_as_of_timestamp(self) -> None:
    """
    Cash balance at a prior timestamp excludes later transactions.
    """
```

```python
def test_transactions_as_of_timestamp(self) -> None:
    """
    Transaction listing at a prior timestamp excludes later transactions.
    """
```

Use explicit timestamps:

```python
t1 = datetime(2024, 1, 1, 9, 0, 0)
t2 = datetime(2024, 1, 2, 9, 0, 0)
t3 = datetime(2024, 1, 3, 9, 0, 0)
```

---

## Account Lookup

```python
def test_get_unknown_account_raises(self) -> None:
    """
    Unknown account ID raises AccountNotFoundError.
    """
```

---

# Engineer Assignments

## backend_engineer

### Files

```text
prices.py
trading_backend.py
```

### Responsibilities

Implement:

- Fixed share price lookup.
- Backend domain models.
- Backend exceptions.
- In-memory account manager.
- Account creation.
- Deposits.
- Withdrawals.
- Buys.
- Sells.
- Holdings computation.
- Cash balance computation.
- Portfolio snapshot computation.
- Profit/loss computation.
- Transaction listing.
- Historical `as_of` support.
- UI formatting helper functions if desired.

### Required Public API

The backend must expose at least:

```python
class AccountManager:
    def __init__(self, price_lookup: Callable[[str], float] | None = None) -> None: ...

    def create_account(
        self,
        owner_name: str,
        initial_deposit: float = 0.0,
        timestamp: datetime | None = None,
    ) -> Account: ...

    def get_account(self, account_id: str) -> Account: ...

    def list_accounts(self) -> list[Account]: ...

    def deposit(
        self,
        account_id: str,
        amount: float,
        timestamp: datetime | None = None,
    ) -> Transaction: ...

    def withdraw(
        self,
        account_id: str,
        amount: float,
        timestamp: datetime | None = None,
    ) -> Transaction: ...

    def buy(
        self,
        account_id: str,
        symbol: str,
        quantity: int,
        timestamp: datetime | None = None,
    ) -> Transaction: ...

    def sell(
        self,
        account_id: str,
        symbol: str,
        quantity: int,
        timestamp: datetime | None = None,
    ) -> Transaction: ...

    def get_holdings(
        self,
        account_id: str,
        as_of: datetime | None = None,
    ) -> dict[str, int]: ...

    def get_cash_balance(
        self,
        account_id: str,
        as_of: datetime | None = None,
    ) -> float: ...

    def get_portfolio_snapshot(
        self,
        account_id: str,
        as_of: datetime | None = None,
    ) -> PortfolioSnapshot: ...

    def list_transactions(
        self,
        account_id: str,
        as_of: datetime | None = None,
    ) -> list[Transaction]: ...
```

### Backend Acceptance Criteria

- All unit tests pass.
- Invalid operations raise clear custom exceptions.
- Account manager has no dependency on Gradio.
- Historical reporting works using transaction timestamps.
- Profit/loss is calculated as total account value minus net cash contributions.
- Symbols are normalized to uppercase.

---

## frontend_engineer

### Files

```text
app.py
```

### Responsibilities

Implement a Gradio 6 app using the backend.

### Required Features

- Create account form.
- Account selector dropdown.
- Deposit form.
- Withdraw form.
- Buy form.
- Sell form.
- Accounts table.
- Holdings table.
- Transactions table.
- Portfolio summary.
- Refresh button.
- Clear user-facing success/error messages.

### Required Gradio Components

Use:

```python
gr.Blocks
gr.State
gr.Markdown
gr.Textbox
gr.Number
gr.Dropdown
gr.Button
gr.Dataframe
gr.Row
gr.Column
gr.Tab or gr.Accordion if helpful
```

### Required Handler Signatures

```python
def handle_create_account(
    manager: AccountManager,
    owner_name: str,
    initial_deposit: float,
) -> tuple:
    ...
```

```python
def handle_deposit(
    manager: AccountManager,
    account_id: str,
    amount: float,
) -> tuple:
    ...
```

```python
def handle_withdraw(
    manager: AccountManager,
    account_id: str,
    amount: float,
) -> tuple:
    ...
```

```python
def handle_buy(
    manager: AccountManager,
    account_id: str,
    symbol: str,
    quantity: float,
) -> tuple:
    ...
```

```python
def handle_sell(
    manager: AccountManager,
    account_id: str,
    symbol: str,
    quantity: float,
) -> tuple:
    ...
```

```python
def handle_refresh(
    manager: AccountManager,
    account_id: str,
) -> tuple:
    ...
```

### Frontend Acceptance Criteria

- App launches with `uv run python app.py`.
- Creating an account updates account dropdown and tables.
- Deposit/withdraw/buy/sell operations update:
  - Status message.
  - Holdings table.
  - Transactions table.
  - Portfolio summary.
- Invalid operations show friendly errors and do not crash the app.
- Gradio 6-compatible APIs are used.
- `gr.Dataframe` uses `column_count`, not deprecated `col_count`.
- `gr.Dataframe` uses `buttons=["copy", "fullscreen"]`, not removed `show_copy_button` or `show_fullscreen_button`.

---

## test_engineer

### Files

```text
test_trading_backend.py
```

### Responsibilities

Implement backend unit tests using Python standard library `unittest`.

### Scope

Test only:

```text
prices.py
trading_backend.py
```

Do not test:

```text
app.py
Gradio UI
```

### Required Test Command

The tests should run with:

```bash
uv run python -m unittest test_trading_backend.py
```

or:

```bash
uv run python -m unittest
```

### Test Acceptance Criteria

- Tests are deterministic.
- Tests use custom price lookup where useful.
- Tests cover all validation rules.
- Tests cover all major account operations.
- Tests cover historical `as_of` reports.
- Tests verify transaction records are created.
- Tests verify profit/loss calculation.
- Tests pass without launching Gradio.

---

# End-to-End Acceptance Criteria

The complete system is successful when:

1. Backend unit tests pass.
2. `uv run python app.py` launches the Gradio app.
3. User can create an account with an initial deposit.
4. User can deposit funds.
5. User can withdraw funds only when enough cash exists.
6. User can buy shares only when enough cash exists.
7. User can sell shares only when enough holdings exist.
8. User can view holdings.
9. User can view transactions.
10. User can view account value and profit/loss.
11. Historical backend reports work through `as_of` timestamps.
12. Unsupported symbols are rejected.
13. No third-party libraries are required beyond Gradio.