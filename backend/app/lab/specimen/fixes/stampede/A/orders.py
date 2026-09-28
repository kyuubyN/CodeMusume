"""Order history page."""


def get_customer(conn, customer_id):
    row = conn.execute(
        "SELECT id, name FROM customers WHERE id = ?", (customer_id,)
    ).fetchone()
    return {"id": row[0], "name": row[1]}


def render_orders(conn):
    rows = conn.execute(
        "SELECT o.id, c.name, o.total FROM orders o JOIN customers c ON c.id = o.customer_id"
    ).fetchall()
    return [{"order": oid, "customer": name, "total": total} for oid, name, total in rows]
