"""Card billing."""
from shop import pricing, utils


def charge(order):
    amount = pricing.order_total(order)
    fee = round(amount * utils.CARD_FEE_RATE, 2)
    return {"order": order.id, "charged": round(amount + fee, 2), "fee": fee}
