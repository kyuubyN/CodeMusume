"""Shared helpers."""
from datetime import datetime, timezone

CURRENCY = "USD"
CARD_FEE_RATE = 0.029


def money(amount):
    return f"{amount:,.2f} {CURRENCY}"


def now_iso():
    return datetime.now(timezone.utc).isoformat()
