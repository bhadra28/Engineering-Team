"""Fixed share price provider for the trading simulation platform."""

from __future__ import annotations

FIXED_SHARE_PRICES: dict[str, float] = {
    "AAPL": 150.00,
    "TSLA": 700.00,
    "GOOGL": 2800.00,
}


def get_share_price(symbol: str) -> float:
    """Return the fixed share price for a supported symbol.

    Symbols are matched case-insensitively.
    """
    if not isinstance(symbol, str):
        raise ValueError("symbol must be a string")
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("symbol cannot be empty")
    try:
        return FIXED_SHARE_PRICES[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported symbol: {symbol}") from exc
