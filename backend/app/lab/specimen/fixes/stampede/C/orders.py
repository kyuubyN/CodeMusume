"""Order history page."""
from functools import lru_cache


@lru_cache(maxsize=None)
def get_customer(conn, customer_id):
    row = conn.execute(
        "SELECT id, name FROM customers WHERE id = ?", (customer_id,)
    ).fetchone()
    return {"id": row[0], "name": row[1]}


def render_orders(conn):
    orders = conn.execute("SELECT id, customer_id, total FROM orders").fetchall()
    page = []
    for order_id, customer_id, total in orders:
        customer = get_customer(conn, customer_id)
        page.append({"order": order_id, "customer": customer["name"], "total": total})
    return page
