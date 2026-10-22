from __future__ import annotations

FIXED_SHARE_PRICES: dict[str, float] = {
    "AAPL": 150.0,
    "TSLA": 250.0,
    "GOOGL": 2800.0,
}


def get_share_price(symbol: str) -> float:
    normalized = symbol.strip().upper()
    try:
        return FIXED_SHARE_PRICES[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported symbol: {symbol!r}") from exc
