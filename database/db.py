"""Database connection and schema management."""
import sqlite3
import logging
from config import config

logger = logging.getLogger(__name__)

def get_connection():
    """Get SQLite database connection."""
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initialize database schema."""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            phone TEXT,
            email TEXT,
            lead_time_days INTEGER DEFAULT 3,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            unit TEXT NOT NULL DEFAULT 'units',
            current_stock REAL NOT NULL DEFAULT 0,
            safety_stock REAL NOT NULL DEFAULT 10,
            avg_daily_usage REAL DEFAULT 1,
            cost_per_unit REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS vendor_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
            material_id INTEGER NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
            price_per_unit REAL DEFAULT 0,
            UNIQUE(vendor_id, material_id)
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL DEFAULT 'General',
            price REAL NOT NULL,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS product_material_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            material_id INTEGER NOT NULL REFERENCES materials(id) ON DELETE CASCADE,
            quantity_required REAL NOT NULL DEFAULT 1,
            UNIQUE(product_id, material_id)
        );

        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL REFERENCES products(id),
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL,
            total_amount REAL NOT NULL,
            payment_mode TEXT NOT NULL DEFAULT 'Cash',
            seller_name TEXT NOT NULL DEFAULT 'Unknown',
            transaction_ref TEXT,
            sale_date DATE DEFAULT (date('now')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS purchase_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            po_number TEXT NOT NULL UNIQUE,
            vendor_id INTEGER NOT NULL REFERENCES vendors(id),
            vendor_name TEXT NOT NULL,
            material_id INTEGER NOT NULL REFERENCES materials(id),
            material_name TEXT NOT NULL,
            qty_ordered REAL NOT NULL DEFAULT 0,
            qty_delivered REAL NOT NULL DEFAULT 0,
            remaining_qty REAL NOT NULL DEFAULT 0,
            unit_cost REAL DEFAULT 0,
            total_cost REAL DEFAULT 0,
            status TEXT DEFAULT 'Initiated',
            expected_delivery DATE,
            delivered_at TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'seller',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Migrate existing tables (safe ALTER TABLE for new columns)
    migrations = [
        ("sales", "payment_mode", "TEXT NOT NULL DEFAULT 'Cash'"),
        ("sales", "seller_name", "TEXT NOT NULL DEFAULT 'Unknown'"),
        ("sales", "transaction_ref", "TEXT"),
        ("purchase_orders", "qty_ordered", "REAL NOT NULL DEFAULT 0"),
        ("purchase_orders", "qty_delivered", "REAL NOT NULL DEFAULT 0"),
        ("purchase_orders", "remaining_qty", "REAL NOT NULL DEFAULT 0"),
        ("purchase_orders", "notes", "TEXT"),
    ]
    for table, col, col_def in migrations:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    # Back-fill qty_ordered / remaining_qty for legacy POs that used 'quantity' column
    cur.execute("""
        UPDATE purchase_orders
        SET qty_ordered = COALESCE(qty_ordered, 0),
            remaining_qty = COALESCE(remaining_qty, 0)
        WHERE qty_ordered IS NULL
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")
