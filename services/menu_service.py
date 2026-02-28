"""Menu and recipe management service."""
import pandas as pd
import logging
from database.db import get_connection

logger = logging.getLogger(__name__)


def get_full_menu() -> pd.DataFrame:
    """Return all products with recipe counts."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT p.*,
               COUNT(pmm.id) as recipe_items
        FROM products p
        LEFT JOIN product_material_map pmm ON pmm.product_id = p.id
        GROUP BY p.id
        ORDER BY p.category, p.name
    """, conn)
    conn.close()
    return df


def get_product_recipe(product_id: int) -> pd.DataFrame:
    """Return recipe (ingredients) for a product."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT m.id as material_id, m.name as material_name, m.unit,
               pmm.quantity_required
        FROM product_material_map pmm
        JOIN materials m ON m.id = pmm.material_id
        WHERE pmm.product_id = ?
        ORDER BY m.name
    """, conn, params=(product_id,))
    conn.close()
    return df


def get_all_materials_for_recipe() -> pd.DataFrame:
    """Return all materials for recipe selection dropdown."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, name, unit FROM materials ORDER BY name", conn)
    conn.close()
    return df


def add_product(name: str, category: str, price: float, description: str = "") -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (name, category, price, description) VALUES (?,?,?,?)",
            (name.strip(), category, price, description),
        )
        conn.commit()
        return {"success": True, "message": f"Product '{name}' added!", "id": cur.lastrowid}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def update_product_price(product_id: int, price: float) -> dict:
    conn = get_connection()
    try:
        conn.execute("UPDATE products SET price=? WHERE id=?", (price, product_id))
        conn.commit()
        return {"success": True, "message": f"Price updated to ₹{price:.0f}"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def toggle_product_active(product_id: int, is_active: int) -> dict:
    conn = get_connection()
    try:
        conn.execute("UPDATE products SET is_active=? WHERE id=?", (is_active, product_id))
        conn.commit()
        status = "activated" if is_active else "deactivated"
        return {"success": True, "message": f"Product {status}"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def delete_product(product_id: int) -> dict:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
        return {"success": True, "message": "Product deleted"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def save_recipe(product_id: int, ingredients: list) -> dict:
    """
    Save recipe for a product.
    ingredients = [{"material_id": int, "quantity": float}, ...]
    Replaces all existing recipe items for this product.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM product_material_map WHERE product_id=?", (product_id,))
        for item in ingredients:
            cur.execute(
                "INSERT INTO product_material_map (product_id, material_id, quantity_required) VALUES (?,?,?)",
                (product_id, item["material_id"], item["quantity"]),
            )
        conn.commit()
        return {"success": True, "message": f"Recipe saved ({len(ingredients)} ingredients)"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def get_categories() -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM products ORDER BY category")
    cats = [r[0] for r in cur.fetchall()]
    conn.close()
    return cats
