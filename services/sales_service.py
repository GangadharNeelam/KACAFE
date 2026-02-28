"""Sales business logic and data access."""
import pandas as pd
import logging
import uuid
from datetime import date, timedelta
from database.db import get_connection
from utils import fmt_inr

logger = logging.getLogger(__name__)


def record_cart_sale(cart_items: dict, payment_mode: str, seller_name: str) -> dict:
    """
    Record all items in cart as one transaction.
    cart_items = {str(product_id): {"name": str, "price": float, "qty": int, "category": str}}
    Returns result dict with success, total, low_stock alerts.
    """
    if not cart_items:
        return {"success": False, "message": "Cart is empty"}

    conn = get_connection()
    try:
        cur = conn.cursor()
        transaction_ref = str(uuid.uuid4())[:8].upper()
        today_str = date.today().isoformat()
        grand_total = 0.0
        low_stock_alerts = []

        for pid_str, item in cart_items.items():
            product_id = int(pid_str)
            qty = int(item.get("qty", 1))
            price = float(item.get("price", 0))
            name = item.get("name", "")
            category = item.get("category", "")
            total = price * qty
            grand_total += total

            # Verify product exists
            cur.execute("SELECT id FROM products WHERE id=?", (product_id,))
            if not cur.fetchone():
                continue

            # Insert sale
            cur.execute("""
                INSERT INTO sales
                (product_id, product_name, category, quantity, unit_price, total_amount,
                 payment_mode, seller_name, transaction_ref, sale_date)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (product_id, name, category, qty, price, total,
                  payment_mode, seller_name, transaction_ref, today_str))

            # Deduct materials
            cur.execute("""
                SELECT pmm.material_id, pmm.quantity_required,
                       m.name as mat_name, m.current_stock, m.safety_stock
                FROM product_material_map pmm
                JOIN materials m ON m.id = pmm.material_id
                WHERE pmm.product_id = ?
            """, (product_id,))
            for row in cur.fetchall():
                deduct = row["quantity_required"] * qty
                new_stock = max(0.0, row["current_stock"] - deduct)
                cur.execute("UPDATE materials SET current_stock=? WHERE id=?",
                            (new_stock, row["material_id"]))
                if new_stock <= row["safety_stock"] and row["mat_name"] not in low_stock_alerts:
                    low_stock_alerts.append(row["mat_name"])

        conn.commit()
        items_count = sum(int(v.get("qty", 1)) for v in cart_items.values())
        return {
            "success": True,
            "message": f"Sale recorded! {items_count} items — {fmt_inr(grand_total)}",
            "total": grand_total,
            "transaction_ref": transaction_ref,
            "low_stock": low_stock_alerts,
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Error recording cart sale: {e}")
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def record_sale(product_id: int, quantity: int,
                payment_mode: str = "Cash", seller_name: str = "Unknown") -> dict:
    """Record a single product sale (legacy/direct use)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM products WHERE id=?", (product_id,))
        product = cur.fetchone()
        if not product:
            return {"success": False, "message": "Product not found"}

        total = product["price"] * quantity
        transaction_ref = str(uuid.uuid4())[:8].upper()

        cur.execute("""
            INSERT INTO sales
            (product_id, product_name, category, quantity, unit_price, total_amount,
             payment_mode, seller_name, transaction_ref, sale_date)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (product["id"], product["name"], product["category"], quantity,
              product["price"], total, payment_mode, seller_name,
              transaction_ref, date.today().isoformat()))

        # Deduct materials
        cur.execute("""
            SELECT pmm.material_id, pmm.quantity_required, m.name, m.current_stock, m.safety_stock
            FROM product_material_map pmm
            JOIN materials m ON m.id = pmm.material_id
            WHERE pmm.product_id = ?
        """, (product_id,))
        mappings = cur.fetchall()

        low_stock_alerts = []
        for row in mappings:
            deduct = row["quantity_required"] * quantity
            new_stock = max(0, row["current_stock"] - deduct)
            cur.execute("UPDATE materials SET current_stock=? WHERE id=?",
                        (new_stock, row["material_id"]))
            if new_stock <= row["safety_stock"]:
                low_stock_alerts.append(row["name"])

        conn.commit()
        return {
            "success": True,
            "message": f"Sale recorded! {quantity}x {product['name']} — {fmt_inr(total)}",
            "low_stock": low_stock_alerts,
            "total": total,
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Error recording sale: {e}")
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def get_sales_df(days: int = 30) -> pd.DataFrame:
    """Return sales dataframe for the last N days."""
    conn = get_connection()
    start = (date.today() - timedelta(days=days)).isoformat()
    df = pd.read_sql_query(
        "SELECT * FROM sales WHERE sale_date >= ? ORDER BY created_at DESC",
        conn, params=(start,)
    )
    conn.close()
    return df


def get_today_sales() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM sales WHERE sale_date = ? ORDER BY created_at DESC",
        conn, params=(date.today().isoformat(),)
    )
    conn.close()
    return df


def get_live_sales(limit: int = 50) -> pd.DataFrame:
    """Return most recent sales for live monitoring (Owner)."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM sales ORDER BY created_at DESC LIMIT ?",
        conn, params=(limit,)
    )
    conn.close()
    return df


def get_kpis(days: int = 30) -> dict:
    df = get_sales_df(days)
    prev_df = get_sales_df(days * 2)
    prev_df = prev_df[
        prev_df["sale_date"] < (date.today() - timedelta(days=days)).isoformat()
    ]

    total_rev = df["total_amount"].sum()
    prev_rev = prev_df["total_amount"].sum()
    growth = ((total_rev - prev_rev) / prev_rev * 100) if prev_rev > 0 else 0

    top_product = (
        df.groupby("product_name")["quantity"].sum().idxmax()
        if not df.empty else "N/A"
    )
    top_category = (
        df.groupby("category")["total_amount"].sum().idxmax()
        if not df.empty else "N/A"
    )

    # Payment mode breakdown
    payment_counts = (
        df.groupby("payment_mode")["total_amount"].sum().to_dict()
        if not df.empty else {}
    )

    return {
        "total_revenue": total_rev,
        "total_items": int(df["quantity"].sum()),
        "num_transactions": len(df),
        "top_product": top_product,
        "top_category": top_category,
        "revenue_growth": growth,
        "payment_counts": payment_counts,
    }


def get_staff_tile_data() -> dict:
    """Per-seller today: items, unique txns, revenue, top-5 products."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM sales WHERE sale_date = ?",
        conn, params=(date.today().isoformat(),)
    )
    conn.close()
    if df.empty:
        return {}
    result = {}
    for seller, sdf in df.groupby("seller_name"):
        top = (
            sdf.groupby("product_name")["quantity"].sum()
            .sort_values(ascending=False)
            .head(5)
            .reset_index()
            .values.tolist()
        )
        result[seller] = {
            "items":     int(sdf["quantity"].sum()),
            "txns":      int(sdf["transaction_ref"].nunique()),
            "revenue":   float(sdf["total_amount"].sum()),
            "top_items": top,
        }
    return result


def get_all_time_sales() -> pd.DataFrame:
    """Return all sales ever recorded."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM sales ORDER BY created_at DESC", conn)
    conn.close()
    return df


def get_seller_kpis(filter_type: str = "today") -> dict:
    """Non-financial KPIs for seller dashboard.

    filter_type: 'today' → only today's sales; 'all_time' → all recorded sales.
    """
    df = get_today_sales() if filter_type == "today" else get_all_time_sales()
    if df.empty:
        return {
            "total_items": 0,
            "top_item": "N/A",
            "top_category": "N/A",
            "peak_hour": "N/A",
        }

    top_item = df.groupby("product_name")["quantity"].sum().idxmax()
    top_cat  = df.groupby("category")["quantity"].sum().idxmax()

    peak_hour = "N/A"
    if filter_type == "today" and "created_at" in df.columns:
        df2 = df.copy()
        df2["hour"] = pd.to_datetime(df2["created_at"], errors="coerce").dt.hour
        hourly = df2.groupby("hour")["quantity"].sum()
        if not hourly.empty:
            ph = int(hourly.idxmax())
            peak_hour = f"{ph:02d}:00 – {ph+1:02d}:00"

    return {
        "total_items": int(df["quantity"].sum()),
        "top_item":    top_item,
        "top_category": top_cat,
        "peak_hour":   peak_hour,
    }


def get_seller_kpis_today() -> dict:
    """Legacy wrapper — use get_seller_kpis('today') instead."""
    return get_seller_kpis("today")
