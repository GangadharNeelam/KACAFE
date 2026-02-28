"""Procurement and vendor business logic — with partial delivery support."""
import pandas as pd
import logging
from datetime import datetime
from database.db import get_connection

logger = logging.getLogger(__name__)

PO_STATUSES = ["Initiated", "Partially Delivered", "Delivered", "Cancelled"]


def generate_po_number() -> str:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM purchase_orders")
    cnt = cur.fetchone()["cnt"]
    conn.close()
    return f"PO-{datetime.now().year}-{cnt + 1:04d}"


def get_vendors_df() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM vendors ORDER BY name", conn)
    conn.close()
    return df


def get_vendor_materials(vendor_id: int = None) -> pd.DataFrame:
    conn = get_connection()
    query = """
        SELECT vm.vendor_id, v.name as vendor_name, v.phone,
               vm.material_id, m.name as material_name,
               m.unit, vm.price_per_unit
        FROM vendor_materials vm
        JOIN vendors v ON v.id = vm.vendor_id
        JOIN materials m ON m.id = vm.material_id
    """
    if vendor_id:
        query += " WHERE vm.vendor_id = ?"
        df = pd.read_sql_query(query, conn, params=(vendor_id,))
    else:
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def get_purchase_orders_df() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM purchase_orders ORDER BY created_at DESC", conn
    )
    conn.close()
    # Ensure new columns exist for legacy rows
    for col in ["qty_ordered", "qty_delivered", "remaining_qty"]:
        if col not in df.columns:
            df[col] = 0.0
    return df


def create_purchase_order(vendor_id, material_id, qty_ordered, expected_delivery,
                          unit_cost: float = 0.0, notes: str = "") -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name, phone FROM vendors WHERE id=?", (vendor_id,))
        vendor = cur.fetchone()
        cur.execute("SELECT name, cost_per_unit FROM materials WHERE id=?", (material_id,))
        material = cur.fetchone()

        if not vendor or not material:
            return {"success": False, "message": "Invalid vendor or material"}

        if unit_cost <= 0:
            unit_cost = material["cost_per_unit"] or 0.0

        po_number = generate_po_number()
        total_cost = float(qty_ordered) * unit_cost

        cur.execute("""
            INSERT INTO purchase_orders
            (po_number, vendor_id, vendor_name, material_id, material_name,
             qty_ordered, qty_delivered, remaining_qty,
             unit_cost, total_cost, status, expected_delivery, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,'Initiated',?,?)
        """, (po_number, vendor_id, vendor["name"], material_id, material["name"],
              float(qty_ordered), 0.0, float(qty_ordered),
              unit_cost, total_cost, expected_delivery, notes))

        conn.commit()
        return {"success": True, "message": f"PO {po_number} created!", "po_number": po_number}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def update_po_delivery(po_id: int, qty_received: float) -> dict:
    """
    Record a delivery (full or partial).
    - Adds qty_received to qty_delivered
    - Recalculates remaining_qty
    - Sets status to 'Delivered' if remaining_qty == 0, else 'Partially Delivered'
    - Updates material stock
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM purchase_orders WHERE id=?", (po_id,))
        po = cur.fetchone()
        if not po:
            return {"success": False, "message": "PO not found"}
        if po["status"] in ("Delivered", "Cancelled"):
            return {"success": False, "message": f"Cannot receive delivery for a {po['status']} PO"}

        new_delivered = float(po["qty_delivered"] or 0) + float(qty_received)
        new_remaining = max(0.0, float(po["qty_ordered"] or 0) - new_delivered)
        new_status = "Delivered" if new_remaining == 0 else "Partially Delivered"

        cur.execute("""
            UPDATE purchase_orders
            SET qty_delivered=?, remaining_qty=?, status=?,
                delivered_at=CASE WHEN ? = 'Delivered' THEN CURRENT_TIMESTAMP ELSE delivered_at END
            WHERE id=?
        """, (new_delivered, new_remaining, new_status, new_status, po_id))

        # Update material stock
        cur.execute("UPDATE materials SET current_stock = current_stock + ? WHERE id=?",
                    (float(qty_received), po["material_id"]))

        conn.commit()
        return {
            "success": True,
            "message": f"Received {qty_received:.0f} units. "
                       f"Status: {new_status}. Remaining: {new_remaining:.0f}",
            "status": new_status,
            "remaining": new_remaining,
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def cancel_po(po_id: int) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM purchase_orders WHERE id=?", (po_id,))
        po = cur.fetchone()
        if not po:
            return {"success": False, "message": "PO not found"}
        if po["status"] == "Delivered":
            return {"success": False, "message": "Cannot cancel a delivered PO"}
        cur.execute("UPDATE purchase_orders SET status='Cancelled' WHERE id=?", (po_id,))
        conn.commit()
        return {"success": True, "message": "PO cancelled"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def add_vendor(name, phone, email, lead_time) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO vendors (name, phone, email, lead_time_days) VALUES (?,?,?,?)",
            (name, phone, email, lead_time),
        )
        conn.commit()
        return {"success": True, "message": f"Vendor '{name}' added!"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def delete_vendor(vendor_id: int) -> dict:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM vendors WHERE id=?", (vendor_id,))
        conn.commit()
        return {"success": True, "message": "Vendor deleted"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        conn.close()
