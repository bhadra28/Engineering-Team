from __future__ import annotations

import gradio as gr

from trading_backend import (
    AccountManager,
    AccountNotFoundError,
    InsufficientFundsError,
    InsufficientHoldingsError,
    InvalidAmountError,
    InvalidQuantityError,
    UnknownSymbolError,
    account_to_row,
    holdings_to_rows,
    snapshot_to_summary,
    transactions_to_rows,
)


PALETTE_CSS = """
:root {
  --brand-gold: #ecad0a;
  --brand-blue: #209dd7;
  --brand-purple: #753991;
  --bg-soft: #f7f8fb;
  --bg-card: rgba(255, 255, 255, 0.82);
  --border: rgba(32, 157, 215, 0.18);
  --text-muted: #5f6777;
}
.dark {
  --bg-soft: #111318;
  --bg-card: rgba(24, 27, 34, 0.84);
  --border: rgba(236, 173, 10, 0.18);
  --text-muted: #b3bac7;
}
.gradio-container {
  background: linear-gradient(180deg, var(--bg-soft) 0%, color-mix(in srgb, var(--bg-soft) 82%, var(--brand-blue) 18%) 100%);
}
#hero {
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 18px 20px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--brand-purple) 12%, transparent) 0%, color-mix(in srgb, var(--brand-blue) 10%, transparent) 50%, color-mix(in srgb, var(--brand-gold) 11%, transparent) 100%), var(--bg-card);
  box-shadow: 0 10px 30px rgba(0,0,0,0.08);
}
#hero h1 { margin: 0; }
#hero .subtle { color: var(--text-muted); }
.section-card {
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 16px;
  background: var(--bg-card);
  box-shadow: 0 8px 24px rgba(0,0,0,0.06);
}
button.primary {
  background: linear-gradient(90deg, var(--brand-blue), var(--brand-purple)) !important;
  color: white !important;
  border: none !important;
}
"""


def get_account_choices(manager: AccountManager) -> list[str]:
    return [account.account_id for account in manager.list_accounts()]


def build_accounts_rows(manager: AccountManager) -> list[list[str | float]]:
    return [account_to_row(account) for account in manager.list_accounts()]


def build_transactions_rows(manager: AccountManager, account_id: str | None) -> list[list[str | int | float]]:
    if not account_id:
        return []
    return transactions_to_rows(manager.list_transactions(account_id))


def build_holdings_rows(manager: AccountManager, account_id: str | None) -> list[list[str | int | float]]:
    if not account_id:
        return []
    return holdings_to_rows(manager.get_portfolio_snapshot(account_id))


def build_portfolio_summary(manager: AccountManager, account_id: str | None) -> str:
    if not account_id:
        return "Select an account to view portfolio details."
    return snapshot_to_summary(manager.get_portfolio_snapshot(account_id))


def safe_status_message(error: Exception) -> str:
    if isinstance(error, AccountNotFoundError):
        return "❌ Please select an account"
    if isinstance(error, InsufficientFundsError):
        return "❌ Insufficient funds"
    if isinstance(error, InsufficientHoldingsError):
        return "❌ Insufficient holdings"
    if isinstance(error, (InvalidAmountError, InvalidQuantityError, UnknownSymbolError, ValueError)):
        return f"❌ {error}"
    return f"❌ {error}"


def _quantity_as_int(quantity: float) -> int:
    if quantity is None:
        raise InvalidQuantityError("Quantity must be provided")
    if int(quantity) != quantity:
        raise InvalidQuantityError("Quantity must be a positive integer")
    return int(quantity)


def handle_create_account(manager: AccountManager, owner_name: str, initial_deposit: float):
    try:
        account = manager.create_account(owner_name, float(initial_deposit))
        selected = account.account_id
        status = f"✅ Account created: {selected}"
        return (
            manager,
            gr.Dropdown(choices=get_account_choices(manager), value=selected),
            status,
            build_accounts_rows(manager),
            build_transactions_rows(manager, selected),
            build_holdings_rows(manager, selected),
            build_portfolio_summary(manager, selected),
        )
    except Exception as exc:
        return (
            manager,
            gr.Dropdown(choices=get_account_choices(manager), value=None),
            safe_status_message(exc),
            build_accounts_rows(manager),
            [],
            [],
            "Select an account to view portfolio details.",
        )


def handle_deposit(manager: AccountManager, account_id: str, amount: float):
    try:
        manager.deposit(account_id, float(amount))
        status = f"✅ Deposited ${float(amount):,.2f}"
    except Exception as exc:
        return manager, safe_status_message(exc), build_transactions_rows(manager, account_id), build_holdings_rows(manager, account_id), build_portfolio_summary(manager, account_id)
    return manager, status, build_transactions_rows(manager, account_id), build_holdings_rows(manager, account_id), build_portfolio_summary(manager, account_id)


def handle_withdraw(manager: AccountManager, account_id: str, amount: float):
    try:
        manager.withdraw(account_id, float(amount))
        status = f"✅ Withdrew ${float(amount):,.2f}"
    except Exception as exc:
        return manager, safe_status_message(exc), build_transactions_rows(manager, account_id), build_holdings_rows(manager, account_id), build_portfolio_summary(manager, account_id)
    return manager, status, build_transactions_rows(manager, account_id), build_holdings_rows(manager, account_id), build_portfolio_summary(manager, account_id)


def handle_buy(manager: AccountManager, account_id: str, symbol: str, quantity: float):
    try:
        qty = _quantity_as_int(quantity)
        manager.buy(account_id, symbol, qty)
        status = f"✅ Bought {qty} {symbol.upper()}"
    except Exception as exc:
        return manager, safe_status_message(exc), build_transactions_rows(manager, account_id), build_holdings_rows(manager, account_id), build_portfolio_summary(manager, account_id)
    return manager, status, build_transactions_rows(manager, account_id), build_holdings_rows(manager, account_id), build_portfolio_summary(manager, account_id)


def handle_sell(manager: AccountManager, account_id: str, symbol: str, quantity: float):
    try:
        qty = _quantity_as_int(quantity)
        manager.sell(account_id, symbol, qty)
        status = f"✅ Sold {qty} {symbol.upper()}"
    except Exception as exc:
        return manager, safe_status_message(exc), build_transactions_rows(manager, account_id), build_holdings_rows(manager, account_id), build_portfolio_summary(manager, account_id)
    return manager, status, build_transactions_rows(manager, account_id), build_holdings_rows(manager, account_id), build_portfolio_summary(manager, account_id)


def handle_refresh(manager: AccountManager, account_id: str):
    try:
        return (
            "✅ Refreshed",
            build_accounts_rows(manager),
            build_transactions_rows(manager, account_id),
            build_holdings_rows(manager, account_id),
            build_portfolio_summary(manager, account_id),
        )
    except Exception as exc:
        return safe_status_message(exc), build_accounts_rows(manager), [], [], "Select an account to view portfolio details."


with gr.Blocks(title="Trading Simulation Account Manager") as demo:
    gr.HTML(f"<style>{PALETTE_CSS}</style>")
    manager_state = gr.State(value=AccountManager())

    with gr.Column(elem_id="hero"):
        gr.Markdown(
            "# Trading Simulation Account Manager\n"
            "<span class='subtle'>Create an account, manage cash, trade supported shares, and review holdings, transactions, and P/L.</span>"
        )
        status_output = gr.Markdown(value="Ready.")
        account_dropdown = gr.Dropdown(choices=[], label="Selected Account", interactive=True)

    with gr.Row():
        with gr.Column(scale=1):
            with gr.Group(elem_classes=["section-card"]):
                gr.Markdown("### Create Account")
                owner_name_input = gr.Textbox(label="Owner Name", placeholder="e.g. Ada Lovelace")
                initial_deposit_input = gr.Number(label="Initial Deposit", value=10000, precision=2, minimum=0, step=100)
                create_account_button = gr.Button("Create Account", variant="primary")
        with gr.Column(scale=1):
            with gr.Group(elem_classes=["section-card"]):
                gr.Markdown("### Cash Operations")
                cash_amount_input = gr.Number(label="Cash Amount", value=1000, precision=2, minimum=0, step=100)
                with gr.Row():
                    deposit_button = gr.Button("Deposit", variant="primary")
                    withdraw_button = gr.Button("Withdraw")

    with gr.Row():
        with gr.Column(scale=1):
            with gr.Group(elem_classes=["section-card"]):
                gr.Markdown("### Trade Operations")
                symbol_dropdown = gr.Dropdown(choices=["AAPL", "TSLA", "GOOGL"], label="Symbol", value="AAPL")
                quantity_input = gr.Number(label="Quantity", value=1, precision=0, minimum=1, step=1)
                with gr.Row():
                    buy_button = gr.Button("Buy", variant="primary")
                    sell_button = gr.Button("Sell")
        with gr.Column(scale=1):
            with gr.Group(elem_classes=["section-card"]):
                gr.Markdown("### Portfolio Overview")
                refresh_button = gr.Button("Refresh Reports")
                portfolio_summary = gr.Markdown(value="Select an account to view portfolio details.")

    with gr.Group(elem_classes=["section-card"]):
        gr.Markdown("### Accounts")
        accounts_table = gr.Dataframe(
            headers=["Account ID", "Owner", "Created At", "Initial Deposit", "Cash Balance"],
            datatype=["str", "str", "str", "number", "number"],
            row_count=0,
            column_count=5,
            interactive=False,
            buttons=["copy", "fullscreen"],
        )

    with gr.Row():
        with gr.Column():
            with gr.Group(elem_classes=["section-card"]):
                gr.Markdown("### Holdings")
                holdings_table = gr.Dataframe(
                    headers=["Symbol", "Quantity", "Current Price", "Market Value"],
                    datatype=["str", "number", "number", "number"],
                    row_count=0,
                    column_count=4,
                    interactive=False,
                    buttons=["copy", "fullscreen"],
                )
        with gr.Column():
            with gr.Group(elem_classes=["section-card"]):
                gr.Markdown("### Transactions")
                transactions_table = gr.Dataframe(
                    headers=["Timestamp", "Type", "Symbol", "Quantity", "Price", "Cash Amount", "Cash Balance After", "Note"],
                    datatype=["str", "str", "str", "number", "number", "number", "number", "str"],
                    row_count=0,
                    column_count=8,
                    interactive=False,
                    buttons=["copy", "fullscreen"],
                )

    create_account_button.click(handle_create_account, inputs=[manager_state, owner_name_input, initial_deposit_input], outputs=[manager_state, account_dropdown, status_output, accounts_table, transactions_table, holdings_table, portfolio_summary])
    deposit_button.click(handle_deposit, inputs=[manager_state, account_dropdown, cash_amount_input], outputs=[manager_state, status_output, transactions_table, holdings_table, portfolio_summary])
    withdraw_button.click(handle_withdraw, inputs=[manager_state, account_dropdown, cash_amount_input], outputs=[manager_state, status_output, transactions_table, holdings_table, portfolio_summary])
    buy_button.click(handle_buy, inputs=[manager_state, account_dropdown, symbol_dropdown, quantity_input], outputs=[manager_state, status_output, transactions_table, holdings_table, portfolio_summary])
    sell_button.click(handle_sell, inputs=[manager_state, account_dropdown, symbol_dropdown, quantity_input], outputs=[manager_state, status_output, transactions_table, holdings_table, portfolio_summary])
    refresh_button.click(handle_refresh, inputs=[manager_state, account_dropdown], outputs=[status_output, accounts_table, transactions_table, holdings_table, portfolio_summary])


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, show_error=True)
