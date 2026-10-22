from __future__ import annotations

from itertools import count
from typing import Any

import gradio as gr

from account_backend import AccountError, TradingAccount
from share_prices import get_share_price

_ACCOUNT_ID_COUNTER = count(1)


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def format_summary(account: TradingAccount | None) -> str:
    if account is None:
        return (
            "### Account Summary\n\n"
            "No account has been created yet. Use the **Account** tab to begin."
        )

    summary = account.get_account_summary()
    return (
        "### Account Summary\n\n"
        f"- **Account ID:** `{summary.account_id}`\n"
        f"- **Owner:** {summary.owner_name}\n"
        f"- **Cash Balance:** {format_currency(summary.cash_balance)}\n"
        f"- **Holdings Market Value:** {format_currency(summary.holdings_market_value)}\n"
        f"- **Total Portfolio Value:** {format_currency(summary.total_portfolio_value)}\n"
        f"- **Net Cash Contribution:** {format_currency(summary.net_cash_contribution)}\n"
        f"- **Profit / Loss:** {format_currency(summary.profit_loss)}\n"
        f"- **Profit / Loss from Initial Deposit:** {format_currency(summary.profit_loss_from_initial_deposit)}\n"
        f"- **As of:** {summary.as_of.isoformat(sep=' ', timespec='seconds')}"
    )


def empty_holdings_table() -> list[list[object]]:
    return []


def empty_transactions_table() -> list[list[object]]:
    return []


def holdings_to_table(account: TradingAccount | None) -> list[list[object]]:
    if account is None:
        return empty_holdings_table()
    return [
        [row.symbol, row.quantity, row.current_price, row.market_value]
        for row in account.get_holdings_report()
    ]


def transactions_to_table(account: TradingAccount | None) -> list[list[object]]:
    if account is None:
        return empty_transactions_table()
    rows: list[list[object]] = []
    for transaction in account.list_transactions():
        rows.append(
            [
                transaction.id,
                transaction.timestamp.isoformat(sep=" ", timespec="seconds"),
                transaction.transaction_type,
                transaction.symbol,
                transaction.quantity,
                transaction.price,
                transaction.amount,
                transaction.cash_balance_after,
                transaction.notes,
            ]
        )
    return rows


def parse_quantity(value: float | int | None) -> int:
    if value is None:
        raise ValueError("Quantity is required")
    if isinstance(value, bool):
        raise ValueError("Quantity must be a whole number")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    raise ValueError("Quantity must be a whole number")


def generate_account_id() -> str:
    return f"acct-{next(_ACCOUNT_ID_COUNTER)}"


def _safe_refresh(account: TradingAccount | None) -> tuple[str, list[list[object]], list[list[object]]]:
    return format_summary(account), holdings_to_table(account), transactions_to_table(account)


def _error_response(
    message: str,
    account: TradingAccount | None = None,
) -> tuple[Any, str, str, list[list[object]], list[list[object]]]:
    summary, holdings, transactions = _safe_refresh(account)
    return account, f"Error: {message}", summary, holdings, transactions


def handle_create_account(
    owner_name: str,
    initial_deposit: float,
) -> tuple[TradingAccount | None, str, str, list[list[object]], list[list[object]]]:
    try:
        account = TradingAccount(
            generate_account_id(),
            owner_name,
            float(initial_deposit or 0.0),
            price_provider=get_share_price,
        )
        summary, holdings, transactions = _safe_refresh(account)
        return account, "Account created successfully.", summary, holdings, transactions
    except AccountError as exc:
        return _error_response(str(exc), None)
    except Exception:
        return _error_response("Unexpected error creating account", None)


def handle_deposit(
    account: TradingAccount | None,
    amount: float,
) -> tuple[TradingAccount | None, str, str, list[list[object]], list[list[object]]]:
    if account is None:
        return _error_response("No account exists. Create an account first.")
    try:
        tx = account.deposit(float(amount))
        summary, holdings, transactions = _safe_refresh(account)
        return account, f"Deposit successful: {format_currency(tx.amount)}", summary, holdings, transactions
    except AccountError as exc:
        return _error_response(str(exc), account)
    except Exception:
        return _error_response("Unexpected error during deposit", account)


def handle_withdraw(
    account: TradingAccount | None,
    amount: float,
) -> tuple[TradingAccount | None, str, str, list[list[object]], list[list[object]]]:
    if account is None:
        return _error_response("No account exists. Create an account first.")
    try:
        tx = account.withdraw(float(amount))
        summary, holdings, transactions = _safe_refresh(account)
        return account, f"Withdrawal successful: {format_currency(tx.amount)}", summary, holdings, transactions
    except AccountError as exc:
        return _error_response(str(exc), account)
    except Exception:
        return _error_response("Unexpected error during withdrawal", account)


def handle_buy(
    account: TradingAccount | None,
    symbol: str,
    quantity: float,
) -> tuple[TradingAccount | None, str, str, list[list[object]], list[list[object]]]:
    if account is None:
        return _error_response("No account exists. Create an account first.")
    try:
        qty = parse_quantity(quantity)
        tx = account.buy(symbol, qty)
        summary, holdings, transactions = _safe_refresh(account)
        return (
            account,
            f"Buy successful: {qty} {tx.symbol} at {format_currency(tx.price or 0.0)}",
            summary,
            holdings,
            transactions,
        )
    except (ValueError, AccountError) as exc:
        return _error_response(str(exc), account)
    except Exception:
        return _error_response("Unexpected error during buy", account)


def handle_sell(
    account: TradingAccount | None,
    symbol: str,
    quantity: float,
) -> tuple[TradingAccount | None, str, str, list[list[object]], list[list[object]]]:
    if account is None:
        return _error_response("No account exists. Create an account first.")
    try:
        qty = parse_quantity(quantity)
        tx = account.sell(symbol, qty)
        summary, holdings, transactions = _safe_refresh(account)
        return (
            account,
            f"Sell successful: {qty} {tx.symbol} at {format_currency(tx.price or 0.0)}",
            summary,
            holdings,
            transactions,
        )
    except (ValueError, AccountError) as exc:
        return _error_response(str(exc), account)
    except Exception:
        return _error_response("Unexpected error during sell", account)


def handle_refresh_reports(account: TradingAccount | None) -> tuple[str, list[list[object]], list[list[object]]]:
    return _safe_refresh(account)


def build_app() -> gr.Blocks:
    with gr.Blocks(
        title="Trading Simulation Account Manager",
        theme=gr.themes.Soft(
            primary_hue="amber",
            secondary_hue="cyan",
            neutral_hue="slate",
        ),
        css="""
        .gradio-container {
            background: linear-gradient(180deg, rgba(236,173,10,0.07) 0%, rgba(32,157,215,0.04) 42%, rgba(117,57,145,0.05) 100%);
        }
        .hero-card {
            border: 1px solid rgba(128,128,128,0.18);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            background: rgba(255,255,255,0.55);
            box-shadow: 0 10px 30px rgba(0,0,0,0.06);
        }
        .dark .hero-card {
            background: rgba(18,18,18,0.55);
        }
        .section-title {
            color: #753991;
            font-weight: 700;
        }
        """,
    ) as demo:
        gr.Markdown(
            "# Trading Simulation Account Manager\n\n"
            "A polished single-user demo for creating an account, funding it, trading supported shares, and reviewing your portfolio."
        )
        account_state = gr.State(None)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown(
                    "<div class='hero-card'>"
                    "<div class='section-title'>Quick Start</div>"
                    "<ul>"
                    "<li>Create an account with an initial deposit.</li>"
                    "<li>Deposit or withdraw cash.</li>"
                    "<li>Buy or sell AAPL, TSLA, and GOOGL.</li>"
                    "<li>Review holdings, value, and transactions.</li>"
                    "</ul>"
                    "</div>"
                )
            with gr.Column(scale=1):
                summary_output = gr.Markdown(
                    value="### Account Summary\n\nNo account has been created yet. Use the **Account** tab to begin."
                )

        with gr.Tab("Account"):
            gr.Markdown("### Create your trading account")
            owner_name_input = gr.Textbox(label="Owner Name", placeholder="Enter your name")
            initial_deposit_input = gr.Number(label="Initial Deposit", value=10000)
            create_account_button = gr.Button("Create Account", variant="primary")
            account_status_output = gr.Markdown()

        with gr.Tab("Funding"):
            gr.Markdown("### Add or remove cash")
            funding_amount_input = gr.Number(label="Amount", value=1000)
            with gr.Row():
                deposit_button = gr.Button("Deposit", variant="primary")
                withdraw_button = gr.Button("Withdraw", variant="secondary")
            funding_status_output = gr.Markdown()

        with gr.Tab("Trading"):
            gr.Markdown("### Trade supported symbols")
            symbol_input = gr.Dropdown(
                choices=["AAPL", "TSLA", "GOOGL"],
                value="AAPL",
                label="Symbol",
            )
            quantity_input = gr.Number(label="Quantity", value=1)
            with gr.Row():
                buy_button = gr.Button("Buy", variant="primary")
                sell_button = gr.Button("Sell", variant="secondary")
            trade_status_output = gr.Markdown()

        with gr.Tab("Reports"):
            gr.Markdown("### Portfolio reports and transaction history")
            refresh_reports_button = gr.Button("Refresh Reports", variant="primary")
            holdings_table = gr.Dataframe(
                headers=["Symbol", "Quantity", "Current Price", "Market Value"],
                datatype=["str", "number", "number", "number"],
                interactive=False,
                buttons=["copy", "fullscreen"],
                label="Holdings",
            )
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

        create_account_button.click(
            fn=handle_create_account,
            inputs=[owner_name_input, initial_deposit_input],
            outputs=[account_state, account_status_output, summary_output, holdings_table, transactions_table],
            queue=False,
        )
        deposit_button.click(
            fn=handle_deposit,
            inputs=[account_state, funding_amount_input],
            outputs=[account_state, funding_status_output, summary_output, holdings_table, transactions_table],
            queue=False,
        )
        withdraw_button.click(
            fn=handle_withdraw,
            inputs=[account_state, funding_amount_input],
            outputs=[account_state, funding_status_output, summary_output, holdings_table, transactions_table],
            queue=False,
        )
        buy_button.click(
            fn=handle_buy,
            inputs=[account_state, symbol_input, quantity_input],
            outputs=[account_state, trade_status_output, summary_output, holdings_table, transactions_table],
            queue=False,
        )
        sell_button.click(
            fn=handle_sell,
            inputs=[account_state, symbol_input, quantity_input],
            outputs=[account_state, trade_status_output, summary_output, holdings_table, transactions_table],
            queue=False,
        )
        refresh_reports_button.click(
            fn=handle_refresh_reports,
            inputs=[account_state],
            outputs=[summary_output, holdings_table, transactions_table],
            queue=False,
        )

    return demo


if __name__ == "__main__":
    build_app().launch()
