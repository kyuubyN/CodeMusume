"""Customer notifications."""
from shop import mailer, utils


def send_receipt(order_id, email, amount):
    mailer.send(email, f"Receipt for order {order_id}", f"You paid {utils.money(amount)}.")
