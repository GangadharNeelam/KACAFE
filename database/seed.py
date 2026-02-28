"""Seed database with KAFE menu, materials, recipes, vendors, and sample data."""
import sqlite3
import random
from datetime import date, timedelta, datetime
from config import config


def _purge_sample_sales(conn) -> None:
    """Delete seeded/sample sales identified by NULL transaction_ref.

    Every real POS sale written by record_cart_sale() / record_sale() always
    carries a UUID transaction_ref.  Seeded rows omit this field (NULL).
    Running this on every startup is safe and idempotent.
    """
    conn.execute("DELETE FROM sales WHERE transaction_ref IS NULL")
    conn.commit()


def _reset_stocks_to_healthy(conn) -> None:
    """Reset any materials sitting below safety_stock back to healthy seed values.

    Ensures all products can actually be sold after a fresh setup.
    Only updates materials that are currently below their safety threshold
    so that real sales-driven deductions are never silently overwritten.
    """
    cur = conn.cursor()
    healthy_stocks = [
        ("Brownie",          300),
        ("Green Tea Leaves", 2000),
        ("Biscoff Spread",   2000),
        ("Whipped Cream",    1500),
        ("Banana",           500),
        ("Mint Leaves",      500),
    ]
    for name, stock in healthy_stocks:
        cur.execute(
            "UPDATE materials SET current_stock=? WHERE name=? AND current_stock < safety_stock",
            (stock, name),
        )
    conn.commit()


def seed_data():
    conn = sqlite3.connect(config.DB_PATH)
    _purge_sample_sales(conn)   # always runs — removes NULL-ref seeded sales
    cur = conn.cursor()

    # ── Sync users to current credentials (always idempotent) ────────────────
    from werkzeug.security import generate_password_hash
    # Remove obsolete 'owner' account replaced by 'Dorababu'
    cur.execute("DELETE FROM users WHERE username = 'owner'")
    desired_users = [
        ("Dorababu", "dora123",   "supervisor"),
        ("seller",   "seller123", "seller"),
        ("ravi",     "ravi123",   "seller"),
        ("ramana",   "ramana123", "seller"),
    ]
    for uname, pwd, role in desired_users:
        cur.execute("SELECT id FROM users WHERE username=?", (uname,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
                (uname, generate_password_hash(pwd), role),
            )
    conn.commit()
    print("[OK] Users synced: Dorababu (owner), seller, ravi, ramana (staff)")

    # ── Reset any critically-low stocks to healthy levels ────────────────────
    _reset_stocks_to_healthy(conn)

    # ── Skip remaining seed if products already exist ─────────────────────────
    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] > 0:
        conn.close()
        return

    # ══════════════════════════════════════════════════════════════════════════
    # VENDORS (Indian context)
    # ══════════════════════════════════════════════════════════════════════════
    vendors = [
        ("Kiran Dairy Supply",    "+91-98765-10001", "kiran@dairy.in",      1),
        ("Raj Coffee Traders",    "+91-98765-10002", "raj@coffeetraders.in",3),
        ("Fresh Fruits Hub",      "+91-98765-10003", "fresh@fruitshub.in",  1),
        ("Vijay Beverages",       "+91-98765-10004", "vijay@beverages.in",  2),
        ("Kitchen Essentials Co.","+91-98765-10005", "kitchen@essentials.in",4),
        ("Packaging World",       "+91-98765-10006", "pack@world.in",       5),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO vendors (name, phone, email, lead_time_days) VALUES (?,?,?,?)",
        vendors,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # RAW MATERIALS (with UOM, stock levels, costs in INR)
    # ══════════════════════════════════════════════════════════════════════════
    # (name, unit, current_stock, safety_stock, avg_daily_usage, cost_per_unit)
    materials = [
        # id 1 – Beverages base
        ("Milk",                  "ml",   50000, 10000, 5000,  0.07),
        ("Tea Powder",            "gm",    2000,   500,  200,  0.50),
        ("Coffee Powder",         "gm",    3000,   600,  300,  1.50),
        ("Green Tea Leaves",      "gm",      40,   100,   50,  2.00),   # demo: critical
        # id 5 – Spices / flavours
        ("Ginger",                "gm",    1000,   200,  100,  0.30),
        ("Cardamom / Elaichi",    "gm",     500,   100,   50,  1.20),
        ("Masala Mix",            "gm",     800,   200,   80,  0.80),
        ("Sugar",                 "gm",   10000,  2000, 1000,  0.06),
        ("Lemon Juice",           "ml",    2000,   500,  200,  0.40),
        # id 10 – Cold/ice
        ("Ice",                   "gm",   30000,  5000, 3000,  0.02),
        # id 11 – Hot coffee extras
        ("Chocolate Powder",      "gm",    2000,   400,  200,  1.20),
        ("Hazelnut Syrup",        "ml",    1000,   200,  100,  1.80),
        ("Whipped Cream",         "gm",     120,   300,  150,  1.50),   # demo: low
        # id 14 – Milkshake spreads
        ("Biscoff Spread",        "gm",     180,   400,  200,  2.50),   # demo: low
        ("Nutella",               "gm",    2000,   400,  200,  3.00),
        ("Oreo Cookies",          "pcs",   1000,   200,  100,  0.50),
        ("Brownie",               "pcs",     25,    60,   30,  8.00),   # demo: critical
        ("Dry Fruits Mix",        "gm",    2000,   400,  200,  4.00),
        ("Banana",                "pcs",     80,   100,   50,  4.00),   # demo: low
        # id 20 – Mocktail ingredients
        ("Soda Water",            "ml",   10000,  2000, 1000,  0.05),
        ("Mint Leaves",           "gm",      60,   100,   50,  2.50),   # demo: low
        ("Fruit Syrup Assorted",  "ml",    5000,  1000,  500,  0.80),
        ("Orange Juice",          "ml",    5000,  1000,  500,  0.60),
        # id 24 – Juice fruits
        ("Watermelon",            "kg",     100,    20,   10, 25.00),
        ("Apple",                 "pcs",    500,   100,   50,  8.00),
        ("Carrot",                "pcs",    500,   100,   50,  3.00),
        ("Beetroot",              "pcs",    300,    60,   30,  6.00),
        ("Pineapple",             "pcs",    200,    40,   20, 35.00),
        ("Mixed Seasonal Fruits", "gm",    5000,  1000,  500,  0.30),
        ("Mixed Fruits",          "gm",    5000,  1000,  500,  0.25),
        # id 31 – Packaging
        ("Tea Cups",              "pcs",   2000,   500,  200,  1.50),
        ("Coffee Cups",           "pcs",   2000,   500,  200,  2.00),
        ("Milkshake Cups",        "pcs",   1500,   300,  150,  2.50),
        ("Juice Cups",            "pcs",   2000,   500,  200,  1.50),
        ("Mocktail Glasses",      "pcs",   1000,   200,  100,  5.00),
        ("Straws",                "pcs",   5000,  1000,  500,  0.30),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO materials "
        "(name, unit, current_stock, safety_stock, avg_daily_usage, cost_per_unit) "
        "VALUES (?,?,?,?,?,?)",
        materials,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # KAFE MENU PRODUCTS
    # ══════════════════════════════════════════════════════════════════════════
    products = [
        # ── Desi Teas ──────────────────────────────────────────────────────
        ("Normal Tea",           "Desi Teas",        20,  "Classic milk tea"),
        ("Ginger Tea",           "Desi Teas",        25,  "Tea with fresh ginger"),
        ("Masala Tea",           "Desi Teas",        25,  "Spiced Indian masala chai"),
        ("Ilaichi Tea",          "Desi Teas",        25,  "Cardamom flavoured tea"),
        # ── Desi Coffee ────────────────────────────────────────────────────
        ("Filter Coffee",        "Desi Coffee",      30,  "South Indian style filter coffee"),
        # ── Water Based Teas ───────────────────────────────────────────────
        ("Lemon Tea",            "Water Based Teas", 25,  "Refreshing lemon tea"),
        ("Ginger Lemon Tea",     "Water Based Teas", 30,  "Ginger & lemon blend"),
        ("Green Tea",            "Water Based Teas", 25,  "Pure green tea"),
        # ── Ice Coffee ─────────────────────────────────────────────────────
        ("Ice Coffee",           "Ice Coffee",       125, "Chilled coffee blend"),
        ("Ice Americano",        "Ice Coffee",       135, "Espresso over ice"),
        ("Ice Latte",            "Ice Coffee",       125, "Iced milk latte"),
        ("Ice Mocha",            "Ice Coffee",       125, "Iced mocha coffee"),
        ("Ice Hazelnut",         "Ice Coffee",       135, "Hazelnut iced coffee"),
        # ── Hot Coffee ─────────────────────────────────────────────────────
        ("Espresso",             "Hot Coffee",       150, "Single shot espresso"),
        ("Doppio",               "Hot Coffee",       150, "Double shot espresso"),
        ("Americano",            "Hot Coffee",       160, "Espresso with hot water"),
        ("Cappuccino",           "Hot Coffee",       160, "Espresso with steamed milk foam"),
        ("Cafe Latte",           "Hot Coffee",       170, "Espresso with steamed milk"),
        ("Cafe Mocha",           "Hot Coffee",       160, "Chocolate espresso latte"),
        ("Hot Chocolate",        "Hot Coffee",       180, "Rich hot chocolate drink"),
        # ── Cold Coffee ────────────────────────────────────────────────────
        ("Classic Cold Coffee",  "Cold Coffee",      170, "Blended chilled coffee"),
        ("Chocolate Frappe",     "Cold Coffee",      180, "Chocolate blended frappe"),
        ("Biscoff Frappe",       "Cold Coffee",      180, "Biscoff blended frappe"),
        ("Nutella Frappe",       "Cold Coffee",      180, "Nutella blended frappe"),
        # ── Mocktails ──────────────────────────────────────────────────────
        ("Siberian Love",        "Mocktails",        125, "Exotic chilled mocktail"),
        ("Virgin Mojito",        "Mocktails",        110, "Mint & lime classic"),
        ("Strawberry Delight",   "Mocktails",        125, "Strawberry mocktail"),
        ("Blue Ocean",           "Mocktails",        125, "Blue lagoon mocktail"),
        ("Chilly Guava",         "Mocktails",        135, "Guava with chilli kick"),
        ("Berry Blast",          "Mocktails",        135, "Mixed berry mocktail"),
        ("Mango Masala",         "Mocktails",        125, "Mango with masala twist"),
        ("Orange Froska",        "Mocktails",        125, "Orange sparkling mocktail"),
        # ── Milkshake ──────────────────────────────────────────────────────
        ("Biscoff Milkshake",    "Milkshake",        180, "Creamy biscoff shake"),
        ("Oreo Milkshake",       "Milkshake",        180, "Oreo cookie shake"),
        ("Banana Milkshake",     "Milkshake",        160, "Fresh banana shake"),
        ("Chocolate Milkshake",  "Milkshake",        160, "Rich chocolate shake"),
        ("Nutella Milkshake",    "Milkshake",        170, "Nutella hazelnut shake"),
        ("Brownie Milkshake",    "Milkshake",        180, "Brownie blended shake"),
        ("Badam Milkshake",      "Milkshake",        169, "Almond rich milkshake"),
        ("Kaju Milkshake",       "Milkshake",        169, "Cashew creamy milkshake"),
        ("Dry Fruit Milkshake",  "Milkshake",        169, "Mixed dry fruit shake"),
        # ── Natural Juices ─────────────────────────────────────────────────
        ("ABC Juice",            "Natural Juices",    70, "Apple, Beetroot & Carrot"),
        ("Watermelon Juice",     "Natural Juices",    60, "Fresh watermelon juice"),
        ("Muskmelon Juice",      "Natural Juices",    60, "Sweet muskmelon juice"),
        ("Orange Juice",         "Natural Juices",    70, "Fresh squeezed orange"),
        ("Mosambi Juice",        "Natural Juices",    60, "Sweet lime juice"),
        ("Carrot Juice",         "Natural Juices",    60, "Fresh carrot juice"),
        ("Beetroot Juice",       "Natural Juices",    60, "Fresh beetroot juice"),
        ("Carrot Beetroot Mix",  "Natural Juices",    70, "Carrot & beetroot blend"),
        # ── Fruit Juices ───────────────────────────────────────────────────
        ("Apple Juice",          "Fruit Juices",      70, "Fresh apple juice"),
        ("Pineapple Juice",      "Fruit Juices",      60, "Fresh pineapple juice"),
        ("Banana Juice",         "Fruit Juices",      60, "Banana blend juice"),
        ("Grapes Juice",         "Fruit Juices",      60, "Fresh grape juice"),
        ("Papaya Juice",         "Fruit Juices",      60, "Fresh papaya juice"),
        ("Pomegranate Juice",    "Fruit Juices",      90, "Fresh pomegranate juice"),
        ("Sapota Juice",         "Fruit Juices",      60, "Fresh chikoo juice"),
        # ── Fruit Bowl ─────────────────────────────────────────────────────
        ("Classic Fruit Bowl",   "Fruit Bowl",        70, "Seasonal mixed fruit bowl"),
        ("Exotic Fruit Bowl",    "Fruit Bowl",        90, "Premium exotic fruit bowl"),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO products (name, category, price, description) VALUES (?,?,?,?)",
        products,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # RECIPES (product_material_map)
    # Material IDs:
    #  1=Milk, 2=Tea Powder, 3=Coffee Powder, 4=Green Tea Leaves, 5=Ginger,
    #  6=Cardamom/Elaichi, 7=Masala Mix, 8=Sugar, 9=Lemon Juice, 10=Ice,
    # 11=Chocolate Powder, 12=Hazelnut Syrup, 13=Whipped Cream, 14=Biscoff Spread,
    # 15=Nutella, 16=Oreo Cookies, 17=Brownie, 18=Dry Fruits Mix, 19=Banana,
    # 20=Soda Water, 21=Mint Leaves, 22=Fruit Syrup Assorted, 23=Orange Juice,
    # 24=Watermelon, 25=Apple, 26=Carrot, 27=Beetroot, 28=Pineapple,
    # 29=Mixed Seasonal Fruits, 30=Mixed Fruits,
    # 31=Tea Cups, 32=Coffee Cups, 33=Milkshake Cups, 34=Juice Cups,
    # 35=Mocktail Glasses, 36=Straws
    # ══════════════════════════════════════════════════════════════════════════
    pmm = [
        # Normal Tea (1)
        (1, 2, 3), (1, 1, 100), (1, 8, 10), (1, 31, 1),
        # Ginger Tea (2)
        (2, 2, 3), (2, 1, 100), (2, 5, 5), (2, 8, 10), (2, 31, 1),
        # Masala Tea (3)
        (3, 2, 3), (3, 1, 100), (3, 7, 3), (3, 8, 10), (3, 31, 1),
        # Ilaichi Tea (4)
        (4, 2, 3), (4, 1, 100), (4, 6, 2), (4, 8, 10), (4, 31, 1),
        # Filter Coffee (5)
        (5, 3, 15), (5, 1, 100), (5, 8, 10), (5, 31, 1),
        # Lemon Tea (6)
        (6, 2, 2), (6, 9, 20), (6, 8, 10), (6, 31, 1),
        # Ginger Lemon Tea (7)
        (7, 2, 2), (7, 5, 5), (7, 9, 20), (7, 8, 10), (7, 31, 1),
        # Green Tea (8)
        (8, 4, 3), (8, 8, 5), (8, 31, 1),
        # Ice Coffee (9)
        (9, 3, 18), (9, 1, 150), (9, 10, 100), (9, 8, 10), (9, 32, 1), (9, 36, 1),
        # Ice Americano (10)
        (10, 3, 18), (10, 10, 100), (10, 32, 1), (10, 36, 1),
        # Ice Latte (11)
        (11, 3, 18), (11, 1, 150), (11, 10, 100), (11, 8, 10), (11, 32, 1), (11, 36, 1),
        # Ice Mocha (12)
        (12, 3, 18), (12, 1, 150), (12, 11, 15), (12, 10, 100), (12, 32, 1), (12, 36, 1),
        # Ice Hazelnut (13)
        (13, 3, 18), (13, 1, 150), (13, 12, 30), (13, 10, 100), (13, 32, 1), (13, 36, 1),
        # Espresso (14)
        (14, 3, 18), (14, 32, 1),
        # Doppio (15)
        (15, 3, 36), (15, 32, 1),
        # Americano (16)
        (16, 3, 18), (16, 32, 1),
        # Cappuccino (17)
        (17, 3, 18), (17, 1, 150), (17, 32, 1),
        # Cafe Latte (18)
        (18, 3, 18), (18, 1, 200), (18, 32, 1),
        # Cafe Mocha (19)
        (19, 3, 18), (19, 1, 150), (19, 11, 15), (19, 32, 1),
        # Hot Chocolate (20)
        (20, 11, 30), (20, 1, 200), (20, 8, 15), (20, 32, 1),
        # Classic Cold Coffee (21)
        (21, 3, 18), (21, 1, 200), (21, 8, 15), (21, 10, 150), (21, 32, 1), (21, 36, 1),
        # Chocolate Frappe (22)
        (22, 3, 18), (22, 1, 200), (22, 11, 20), (22, 10, 150), (22, 13, 30), (22, 32, 1), (22, 36, 1),
        # Biscoff Frappe (23)
        (23, 3, 18), (23, 1, 200), (23, 14, 30), (23, 10, 150), (23, 13, 30), (23, 32, 1), (23, 36, 1),
        # Nutella Frappe (24)
        (24, 3, 18), (24, 1, 200), (24, 15, 30), (24, 10, 150), (24, 13, 30), (24, 32, 1), (24, 36, 1),
        # Siberian Love (25)
        (25, 22, 50), (25, 9, 20), (25, 20, 150), (25, 10, 100), (25, 35, 1), (25, 36, 1),
        # Virgin Mojito (26)
        (26, 21, 10), (26, 9, 30), (26, 8, 15), (26, 20, 150), (26, 10, 100), (26, 35, 1), (26, 36, 1),
        # Strawberry Delight (27)
        (27, 22, 50), (27, 9, 15), (27, 20, 100), (27, 10, 100), (27, 35, 1), (27, 36, 1),
        # Blue Ocean (28)
        (28, 22, 50), (28, 9, 20), (28, 20, 150), (28, 10, 100), (28, 35, 1), (28, 36, 1),
        # Chilly Guava (29)
        (29, 22, 60), (29, 9, 15), (29, 20, 100), (29, 10, 100), (29, 35, 1), (29, 36, 1),
        # Berry Blast (30)
        (30, 22, 60), (30, 9, 20), (30, 20, 150), (30, 10, 100), (30, 35, 1), (30, 36, 1),
        # Mango Masala (31)
        (31, 22, 60), (31, 9, 15), (31, 20, 100), (31, 10, 100), (31, 35, 1), (31, 36, 1),
        # Orange Froska (32)
        (32, 23, 100), (32, 20, 100), (32, 8, 10), (32, 10, 100), (32, 35, 1), (32, 36, 1),
        # Biscoff Milkshake (33)
        (33, 14, 40), (33, 1, 250), (33, 8, 15), (33, 10, 100), (33, 33, 1), (33, 36, 1),
        # Oreo Milkshake (34)
        (34, 16, 4), (34, 1, 250), (34, 8, 15), (34, 10, 100), (34, 33, 1), (34, 36, 1),
        # Banana Milkshake (35)
        (35, 19, 2), (35, 1, 250), (35, 8, 15), (35, 10, 100), (35, 33, 1), (35, 36, 1),
        # Chocolate Milkshake (36)
        (36, 11, 25), (36, 1, 250), (36, 8, 15), (36, 10, 100), (36, 33, 1), (36, 36, 1),
        # Nutella Milkshake (37)
        (37, 15, 40), (37, 1, 250), (37, 8, 15), (37, 10, 100), (37, 33, 1), (37, 36, 1),
        # Brownie Milkshake (38)
        (38, 17, 1), (38, 1, 250), (38, 11, 15), (38, 10, 100), (38, 33, 1), (38, 36, 1),
        # Badam Milkshake (39)
        (39, 18, 40), (39, 1, 250), (39, 8, 15), (39, 10, 100), (39, 33, 1), (39, 36, 1),
        # Kaju Milkshake (40)
        (40, 18, 40), (40, 1, 250), (40, 8, 15), (40, 10, 100), (40, 33, 1), (40, 36, 1),
        # Dry Fruit Milkshake (41)
        (41, 18, 50), (41, 1, 250), (41, 8, 15), (41, 10, 100), (41, 33, 1), (41, 36, 1),
        # ABC Juice (42)
        (42, 25, 1), (42, 26, 1), (42, 27, 1), (42, 8, 10), (42, 34, 1), (42, 36, 1),
        # Watermelon Juice (43)
        (43, 24, 0.2), (43, 8, 10), (43, 34, 1), (43, 36, 1),
        # Muskmelon Juice (44)
        (44, 29, 150), (44, 8, 10), (44, 34, 1), (44, 36, 1),
        # Orange Juice (natural) (45)
        (45, 23, 100), (45, 8, 5), (45, 34, 1), (45, 36, 1),
        # Mosambi Juice (46)
        (46, 29, 150), (46, 8, 5), (46, 34, 1), (46, 36, 1),
        # Carrot Juice (47)
        (47, 26, 3), (47, 8, 5), (47, 34, 1), (47, 36, 1),
        # Beetroot Juice (48)
        (48, 27, 2), (48, 8, 5), (48, 34, 1), (48, 36, 1),
        # Carrot Beetroot Mix (49)
        (49, 26, 2), (49, 27, 1), (49, 8, 5), (49, 34, 1), (49, 36, 1),
        # Apple Juice (50)
        (50, 25, 2), (50, 8, 10), (50, 34, 1), (50, 36, 1),
        # Pineapple Juice (51)
        (51, 28, 0.25), (51, 8, 10), (51, 34, 1), (51, 36, 1),
        # Banana Juice (52)
        (52, 19, 2), (52, 1, 100), (52, 8, 10), (52, 34, 1), (52, 36, 1),
        # Grapes Juice (53)
        (53, 29, 150), (53, 8, 10), (53, 34, 1), (53, 36, 1),
        # Papaya Juice (54)
        (54, 29, 150), (54, 8, 10), (54, 34, 1), (54, 36, 1),
        # Pomegranate Juice (55)
        (55, 29, 200), (55, 8, 5), (55, 34, 1), (55, 36, 1),
        # Sapota Juice (56)
        (56, 29, 150), (56, 8, 10), (56, 34, 1), (56, 36, 1),
        # Classic Fruit Bowl (57)
        (57, 30, 200), (57, 34, 1),
        # Exotic Fruit Bowl (58)
        (58, 30, 300), (58, 29, 100), (58, 34, 1),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO product_material_map "
        "(product_id, material_id, quantity_required) VALUES (?,?,?)",
        pmm,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # VENDOR–MATERIAL MAPPINGS
    # ══════════════════════════════════════════════════════════════════════════
    vm = [
        # Kiran Dairy (1): milk, whipped cream
        (1, 1,  0.065), (1, 13, 1.40),
        # Raj Coffee (2): coffee, tea, green tea
        (2, 2, 0.45), (2, 3, 1.40), (2, 4, 1.80),
        # Fresh Fruits Hub (3): fruits, banana, carrot, beetroot, watermelon, mixed
        (3, 19, 3.50), (3, 24, 22.00), (3, 25, 7.50), (3, 26, 2.80),
        (3, 27, 5.50), (3, 28, 32.00), (3, 29, 0.28), (3, 30, 0.22),
        # Vijay Beverages (4): soda, fruit syrup, hazelnut, biscoff, nutella
        (4, 20, 0.045), (4, 22, 0.75), (4, 12, 1.70), (4, 14, 2.30), (4, 15, 2.80),
        # Kitchen Essentials (5): sugar, choc powder, masala, oreo, brownie, dry fruits, spices
        (5, 8, 0.055), (5, 11, 1.10), (5, 7, 0.75), (5, 16, 0.45),
        (5, 17, 7.50), (5, 18, 3.80), (5, 5, 0.28), (5, 6, 1.10),
        (5, 9, 0.38), (5, 21, 2.30),
        # Packaging World (6): cups, straws
        (6, 31, 1.40), (6, 32, 1.85), (6, 33, 2.30), (6, 34, 1.40),
        (6, 35, 4.80), (6, 36, 0.28),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO vendor_materials (vendor_id, material_id, price_per_unit) VALUES (?,?,?)",
        vm,
    )

    # ══════════════════════════════════════════════════════════════════════════
    # PURCHASE ORDERS (new status vocabulary)
    # ══════════════════════════════════════════════════════════════════════════
    pos = [
        ("PO-2024-001", 1, "Kiran Dairy Supply",     1,  "Milk",              50000, 0.065, 3250.00, "Delivered",           "2024-01-15", 50000, 0),
        ("PO-2024-002", 2, "Raj Coffee Traders",     3,  "Coffee Powder",      3000, 1.40,  4200.00, "Partially Delivered", "2024-02-01", 3000, 1500),
        ("PO-2024-003", 3, "Fresh Fruits Hub",       19, "Banana",              500, 3.50,  1750.00, "Initiated",           "2024-02-10", 500,  0),
        ("PO-2024-004", 6, "Packaging World",        31, "Tea Cups",           2000, 1.40,  2800.00, "Delivered",           "2024-01-20", 2000, 0),
        ("PO-2024-005", 4, "Vijay Beverages",        22, "Fruit Syrup Assorted",5000, 0.75, 3750.00, "Initiated",           "2024-02-15", 5000, 0),
    ]
    for po in pos:
        qty_ordered = po[10]
        qty_delivered = po[11]
        remaining = qty_ordered - qty_delivered
        cur.execute("""
            INSERT OR IGNORE INTO purchase_orders
            (po_number, vendor_id, vendor_name, material_id, material_name,
             qty_ordered, unit_cost, total_cost, status, expected_delivery,
             qty_delivered, remaining_qty)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (po[0], po[1], po[2], po[3], po[4],
              qty_ordered, po[6], po[7], po[8], po[9],
              qty_delivered, remaining))

    conn.commit()
    conn.close()
    print("[OK] KAFE database seeded successfully! (58 products, 37 materials, 6 vendors)")


if __name__ == "__main__":
    seed_data()
