from __future__ import annotations

from decimal import Decimal

import gradio as gr

from backend import (
    HoldingReportRow,
    PortfolioReport,
    Transaction,
    TradingError,
    TradingService,
    format_money,
    format_percent,
    holding_to_row,
    transaction_to_row,
)

service = TradingService()
DEFAULT_SYMBOLS = ["AAPL", "TSLA", "GOOGL"]


def empty_report() -> dict:
    return {
        "account_id": "",
        "owner_name": "",
        "cash_balance": "",
        "holdings_value": "",
        "total_value": "",
        "initial_deposit": "",
        "net_cash_contributions": "",
        "profit_loss": "",
        "profit_loss_percent": "",
        "as_of": "",
    }


def empty_holdings_rows() -> list[list]:
    return []


def empty_transaction_rows() -> list[list]:
    return []


def portfolio_report_to_dict(report: PortfolioReport) -> dict:
    return {
        "account_id": report.account_id,
        "owner_name": report.owner_name,
        "cash_balance": format_money(report.cash_balance),
        "holdings_value": format_money(report.holdings_value),
        "total_value": format_money(report.total_value),
        "initial_deposit": format_money(report.initial_deposit),
        "net_cash_contributions": format_money(report.net_cash_contributions),
        "profit_loss": format_money(report.profit_loss),
        "profit_loss_percent": format_percent(report.profit_loss_percent),
        "as_of": report.as_of.isoformat(),
        "holdings": [
            {
                "symbol": h.symbol,
                "quantity": h.quantity,
                "current_price": format_money(h.current_price),
                "market_value": format_money(h.market_value),
            }
            for h in report.holdings
        ],
    }


def holdings_to_rows(holdings: list[HoldingReportRow]) -> list[list]:
    return [holding_to_row(h) for h in holdings]


def transactions_to_rows(transactions: list[Transaction]) -> list[list]:
    return [transaction_to_row(t) for t in transactions]


def _status_ok(message: str) -> str:
    return f"[OK] {message}"


def _status_err(message: str) -> str:
    return f"[ERROR] {message}"


def _account_summary(account_id: str) -> dict:
    report = service.get_portfolio_report(account_id)
    return portfolio_report_to_dict(report)


def _safe_int_quantity(quantity: float | None) -> int:
    if quantity is None:
        raise ValueError("Quantity is required.")
    if int(quantity) != quantity:
        raise ValueError("Quantity must be a whole number.")
    return int(quantity)


def handle_create_account(account_id: str, owner_name: str, initial_deposit: float) -> tuple[str, dict]:
    try:
        service.create_account(account_id, owner_name, initial_deposit)
        return _status_ok(f"Account '{account_id}' created successfully."), _account_summary(account_id)
    except TradingError as exc:
        return _status_err(str(exc)), empty_report()
    except Exception as exc:
        return _status_err(str(exc)), empty_report()


def handle_deposit(account_id: str, amount: float) -> tuple[str, dict]:
    try:
        service.deposit(account_id, amount)
        return _status_ok(f"Deposited {format_money(Decimal(str(amount)))} into '{account_id}'."), _account_summary(account_id)
    except TradingError as exc:
        return _status_err(str(exc)), empty_report()
    except Exception as exc:
        return _status_err(str(exc)), empty_report()


def handle_withdraw(account_id: str, amount: float) -> tuple[str, dict]:
    try:
        service.withdraw(account_id, amount)
        return _status_ok(f"Withdrew {format_money(Decimal(str(amount)))} from '{account_id}'."), _account_summary(account_id)
    except TradingError as exc:
        return _status_err(str(exc)), empty_report()
    except Exception as exc:
        return _status_err(str(exc)), empty_report()


def handle_buy(account_id: str, symbol: str, quantity: float) -> tuple[str, dict]:
    try:
        qty = _safe_int_quantity(quantity)
        service.buy(account_id, symbol, qty)
        return _status_ok(f"Bought {qty} shares of {symbol.upper()} for '{account_id}'."), _account_summary(account_id)
    except (TradingError, ValueError) as exc:
        return _status_err(str(exc)), empty_report()
    except Exception as exc:
        return _status_err(str(exc)), empty_report()


def handle_sell(account_id: str, symbol: str, quantity: float) -> tuple[str, dict]:
    try:
        qty = _safe_int_quantity(quantity)
        service.sell(account_id, symbol, qty)
        return _status_ok(f"Sold {qty} shares of {symbol.upper()} for '{account_id}'."), _account_summary(account_id)
    except (TradingError, ValueError) as exc:
        return _status_err(str(exc)), empty_report()
    except Exception as exc:
        return _status_err(str(exc)), empty_report()


def handle_refresh_reports(account_id: str) -> tuple[str, dict, list[list], list[list]]:
    try:
        report = service.get_portfolio_report(account_id)
        holdings = service.get_holdings(account_id)
        transactions = service.list_transactions(account_id)
        return (
            _status_ok(f"Loaded reports for '{account_id}'."),
            portfolio_report_to_dict(report),
            holdings_to_rows(holdings),
            transactions_to_rows(transactions),
        )
    except TradingError as exc:
        return _status_err(str(exc)), empty_report(), empty_holdings_rows(), empty_transaction_rows()
    except Exception as exc:
        return _status_err(str(exc)), empty_report(), empty_holdings_rows(), empty_transaction_rows()


def handle_asof_report(account_id: str, transaction_id: float) -> tuple[str, dict, list[list]]:
    try:
        if transaction_id is None:
            raise ValueError("Transaction ID is required.")
        if int(transaction_id) != transaction_id:
            raise ValueError("Transaction ID must be a whole number.")
        tx_id = int(transaction_id)
        report = service.get_portfolio_report(account_id, transaction_id=tx_id)
        holdings = service.get_holdings(account_id, transaction_id=tx_id)
        return _status_ok(f"Generated as-of report for transaction {tx_id}."), portfolio_report_to_dict(report), holdings_to_rows(holdings)
    except (TradingError, ValueError) as exc:
        return _status_err(str(exc)), empty_report(), empty_holdings_rows()
    except Exception as exc:
        return _status_err(str(exc)), empty_report(), empty_holdings_rows()


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Trading Simulation Account Manager", theme=gr.themes.Soft(primary_hue="amber", secondary_hue="blue", neutral_hue="gray")) as demo:
        gr.Markdown(
            "# Trading Simulation Account Manager\n"
            "Create an account, manage cash, trade supported shares, and review current or as-of portfolio reports."
        )

        with gr.Tabs():
            with gr.Tab("Account"):
                with gr.Row():
                    account_id_input = gr.Textbox(label="Account ID", placeholder="e.g. demo-001")
                    owner_name_input = gr.Textbox(label="Owner Name", placeholder="e.g. Ada Lovelace")
                    initial_deposit_input = gr.Number(label="Initial Deposit", value=10000)
                create_account_button = gr.Button("Create Account", variant="primary")
                account_status_output = gr.Markdown()
                account_summary_output = gr.JSON(label="Account Summary")
                create_account_button.click(
                    fn=handle_create_account,
                    inputs=[account_id_input, owner_name_input, initial_deposit_input],
                    outputs=[account_status_output, account_summary_output],
                )

            with gr.Tab("Cash"):
                with gr.Row():
                    cash_account_id_input = gr.Textbox(label="Account ID", placeholder="e.g. demo-001")
                    cash_amount_input = gr.Number(label="Amount", value=1000)
                with gr.Row():
                    deposit_button = gr.Button("Deposit", variant="primary")
                    withdraw_button = gr.Button("Withdraw", variant="secondary")
                cash_status_output = gr.Markdown()
                cash_summary_output = gr.JSON(label="Updated Portfolio Summary")
                deposit_button.click(handle_deposit, inputs=[cash_account_id_input, cash_amount_input], outputs=[cash_status_output, cash_summary_output])
                withdraw_button.click(handle_withdraw, inputs=[cash_account_id_input, cash_amount_input], outputs=[cash_status_output, cash_summary_output])

            with gr.Tab("Trade"):
                with gr.Row():
                    trade_account_id_input = gr.Textbox(label="Account ID", placeholder="e.g. demo-001")
                    symbol_input = gr.Dropdown(label="Symbol", choices=DEFAULT_SYMBOLS, value="AAPL")
                    quantity_input = gr.Number(label="Quantity", value=1, precision=0)
                with gr.Row():
                    buy_button = gr.Button("Buy", variant="primary")
                    sell_button = gr.Button("Sell", variant="secondary")
                trade_status_output = gr.Markdown()
                trade_summary_output = gr.JSON(label="Updated Portfolio Summary")
                buy_button.click(handle_buy, inputs=[trade_account_id_input, symbol_input, quantity_input], outputs=[trade_status_output, trade_summary_output])
                sell_button.click(handle_sell, inputs=[trade_account_id_input, symbol_input, quantity_input], outputs=[trade_status_output, trade_summary_output])

            with gr.Tab("Reports"):
                report_account_id_input = gr.Textbox(label="Account ID", placeholder="e.g. demo-001")
                refresh_report_button = gr.Button("Refresh Reports", variant="primary")
                report_status_output = gr.Markdown()
                portfolio_report_output = gr.JSON(label="Portfolio Report")
                holdings_table_output = gr.Dataframe(
                    headers=["Symbol", "Quantity", "Current Price", "Market Value"],
                    row_count=0,
                    row_limits=None,
                    column_count=4,
                    column_limits=(4, 4),
                    interactive=False,
                    label="Holdings",
                )
                transactions_table_output = gr.Dataframe(
                    headers=["ID", "Timestamp", "Type", "Symbol", "Quantity", "Price", "Amount", "Cash Balance After", "Notes"],
                    row_count=0,
                    row_limits=None,
                    column_count=9,
                    column_limits=(9, 9),
                    interactive=False,
                    label="Transactions",
                )
                refresh_report_button.click(
                    handle_refresh_reports,
                    inputs=[report_account_id_input],
                    outputs=[report_status_output, portfolio_report_output, holdings_table_output, transactions_table_output],
                )

            with gr.Tab("As-Of Reports"):
                asof_account_id_input = gr.Textbox(label="Account ID", placeholder="e.g. demo-001")
                asof_transaction_id_input = gr.Number(label="As of Transaction ID", precision=0)
                asof_report_button = gr.Button("Generate As-Of Report", variant="primary")
                asof_status_output = gr.Markdown()
                asof_portfolio_output = gr.JSON(label="As-Of Portfolio Report")
                asof_holdings_output = gr.Dataframe(
                    headers=["Symbol", "Quantity", "Current Price", "Market Value"],
                    row_count=0,
                    row_limits=None,
                    column_count=4,
                    column_limits=(4, 4),
                    interactive=False,
                    label="As-Of Holdings",
                )
                asof_report_button.click(
                    handle_asof_report,
                    inputs=[asof_account_id_input, asof_transaction_id_input],
                    outputs=[asof_status_output, asof_portfolio_output, asof_holdings_output],
                )

    return demo


if __name__ == "__main__":
    build_app().launch()
