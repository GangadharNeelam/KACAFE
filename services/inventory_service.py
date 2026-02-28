"""Inventory business logic."""
from __future__ import annotations
import pandas as pd
import logging
from database.db import get_connection

logger = logging.getLogger(__name__)

# ── Material category registry (single source of truth for grouping) ─────────
MATERIAL_CATEGORIES: dict[str, dict] = {
    "Dairy": {
        "icon": "bi-droplet-fill", "color": "#60A5FA",
        "materials": ["Milk", "Whipped Cream"],
    },
    "Tea & Coffee": {
        "icon": "bi-cup-hot-fill", "color": "#A78BFA",
        "materials": ["Tea Powder", "Coffee Powder", "Green Tea Leaves"],
    },
    "Spices & Flavours": {
        "icon": "bi-stars", "color": "#34D399",
        "materials": ["Ginger", "Cardamom / Elaichi", "Masala Mix"],
    },
    "Sweeteners & Acids": {
        "icon": "bi-droplet-half", "color": "#FCD34D",
        "materials": ["Sugar", "Lemon Juice"],
    },
    "Cold & Beverages": {
        "icon": "bi-snow", "color": "#67E8F9",
        "materials": ["Ice", "Soda Water", "Fruit Syrup Assorted", "Orange Juice"],
    },
    "Coffee Extras": {
        "icon": "bi-cup-fill", "color": "#FB923C",
        "materials": ["Chocolate Powder", "Hazelnut Syrup"],
    },
    "Milkshake Mix-ins": {
        "icon": "bi-cup-straw", "color": "#F472B6",
        "materials": ["Biscoff Spread", "Nutella", "Oreo Cookies",
                      "Brownie", "Dry Fruits Mix", "Banana"],
    },
    "Fresh Fruits": {
        "icon": "bi-tree", "color": "#4ADE80",
        "materials": ["Watermelon", "Apple", "Carrot", "Beetroot", "Pineapple",
                      "Mixed Seasonal Fruits", "Mixed Fruits", "Mint Leaves"],
    },
    "Packaging": {
        "icon": "bi-box-seam", "color": "#94A3B8",
        "materials": ["Tea Cups", "Coffee Cups", "Milkshake Cups",
                      "Juice Cups", "Mocktail Glasses", "Straws"],
    },
}

# Reverse map: material name → category name
_MAT_TO_CAT: dict[str, str] = {
    mat: cat
    for cat, cfg in MATERIAL_CATEGORIES.items()
    for mat in cfg["materials"]
}

def get_inventory_df() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM materials ORDER BY name", conn)
    conn.close()
    df["status"] = df.apply(lambda r: 
        "Critical" if r["current_stock"] < r["safety_stock"] * 0.5
        else ("Low" if r["current_stock"] <= r["safety_stock"]
        else "OK"), axis=1)
    df["days_remaining"] = (df["current_stock"] / df["avg_daily_usage"].replace(0,1)).round(1)
    return df

def get_low_stock_materials() -> list:
    df = get_inventory_df()
    return df[df["status"].isin(["Low", "Critical"])]["name"].tolist()

def adjust_stock(material_id: int, adjustment: float, reason: str = "Manual") -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE materials SET current_stock = MAX(0, current_stock + ?) WHERE id=?",
                    (adjustment, material_id))
        conn.commit()
        return {"success": True, "message": f"Stock adjusted by {adjustment:+.1f}"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}
    finally:
        conn.close()

def get_consumption_summary() -> pd.DataFrame:
    """Returns estimated daily consumption per material."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT name, avg_daily_usage, current_stock, unit FROM materials ORDER BY avg_daily_usage DESC LIMIT 10", conn)
    conn.close()
    return df


def get_inventory_df_with_category() -> pd.DataFrame:
    """get_inventory_df() augmented with a 'category' column from MATERIAL_CATEGORIES."""
    df = get_inventory_df()
    df["category"] = df["name"].map(_MAT_TO_CAT).fillna("Other")
    return df


def get_at_risk_products() -> pd.DataFrame:
    """Products with ≥1 Critical or Low material in their recipe.

    Returns columns: product_name, product_category, material_name,
                     current_stock, safety_stock, material_status
    """
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT DISTINCT
            p.name     AS product_name,
            p.category AS product_category,
            m.name     AS material_name,
            m.current_stock,
            m.safety_stock,
            CASE
                WHEN m.current_stock < m.safety_stock * 0.5 THEN 'Critical'
                ELSE 'Low'
            END AS material_status
        FROM products p
        JOIN product_material_map pmm ON p.id = pmm.product_id
        JOIN materials m              ON pmm.material_id = m.id
        WHERE m.current_stock <= m.safety_stock
        ORDER BY p.name, material_status
    """, conn)
    conn.close()
    return df
