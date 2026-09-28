"""Card billing."""
from shop import orders, utils


def charge(order):
    amount = orders.order_total(order)
    fee = round(amount * utils.CARD_FEE_RATE, 2)
    return {"order": order.id, "charged": round(amount + fee, 2), "fee": fee}
