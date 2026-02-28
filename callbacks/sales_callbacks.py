"""
Sales POS callbacks — cart-based system.
Handles: add to cart, modify qty, Record Sale, payment mode, summary panel.
"""
from __future__ import annotations
import json
import flask
from dash import Input, Output, State, html, dcc, callback_context, ALL, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from server import app
from services.sales_service import record_cart_sale, get_today_sales, get_seller_kpis_today
from database.db import get_connection
from utils import fmt_inr, CATEGORY_COLORS
from constants import ROLE_OWNER


# ── Helper: fetch product from DB ────────────────────────────────────────────
def _get_product(product_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, category, price FROM products WHERE id=?", (product_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def register_callbacks():

    # ── 1. Add product to cart ────────────────────────────────────────────
    @app.callback(
        Output("cart-store", "data"),
        Input({"type": "add-to-cart", "index": ALL}, "n_clicks"),
        [State("cart-store", "data"),
         State({"type": "add-to-cart", "index": ALL}, "id")],
        prevent_initial_call=True,
    )
    def add_to_cart(n_clicks_list, cart, btn_ids):
        ctx = callback_context
        if not ctx.triggered or not any(n for n in (n_clicks_list or []) if n):
            raise PreventUpdate

        triggered_raw = ctx.triggered[0]["prop_id"]
        try:
            btn_data = json.loads(triggered_raw.split(".")[0])
            product_id = btn_data["index"]
        except Exception:
            raise PreventUpdate

        cart = cart or {}
        pid_str = str(product_id)

        if pid_str in cart:
            cart[pid_str]["qty"] += 1
        else:
            product = _get_product(product_id)
            if not product:
                raise PreventUpdate
            cart[pid_str] = {
                "name": product["name"],
                "price": product["price"],
                "qty": 1,
                "category": product["category"],
            }
        return cart

    # ── 2. Cart item modifications (+, -, remove) + clear ────────────────
    @app.callback(
        Output("cart-store", "data", allow_duplicate=True),
        [Input({"type": "cart-plus",   "index": ALL}, "n_clicks"),
         Input({"type": "cart-minus",  "index": ALL}, "n_clicks"),
         Input({"type": "cart-remove", "index": ALL}, "n_clicks"),
         Input("clear-cart-btn", "n_clicks")],
        [State("cart-store", "data"),
         State({"type": "cart-plus",   "index": ALL}, "id"),
         State({"type": "cart-minus",  "index": ALL}, "id"),
         State({"type": "cart-remove", "index": ALL}, "id")],
        prevent_initial_call=True,
    )
    def modify_cart(plus_clicks, minus_clicks, remove_clicks, clear_n,
                    cart, plus_ids, minus_ids, remove_ids):
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        # Dash fires ALL pattern-matching callbacks whenever matching components
        # are dynamically added to the DOM (n_clicks=0, value=0).
        # Ignore those spurious fires — only process genuine user clicks (value ≥ 1).
        if ctx.triggered[0].get("value", 0) == 0:
            raise PreventUpdate

        cart = cart or {}
        triggered = ctx.triggered[0]["prop_id"]

        # Clear cart
        if "clear-cart-btn" in triggered:
            return {}

        try:
            id_part = triggered.split(".")[0]
            btn_data = json.loads(id_part)
            btn_type = btn_data["type"]
            pid_str = str(btn_data["index"])
        except Exception:
            raise PreventUpdate

        if pid_str not in cart:
            raise PreventUpdate

        if btn_type == "cart-plus":
            cart[pid_str]["qty"] += 1
        elif btn_type == "cart-minus":
            cart[pid_str]["qty"] -= 1
            if cart[pid_str]["qty"] <= 0:
                del cart[pid_str]
        elif btn_type == "cart-remove":
            del cart[pid_str]

        return cart

    # ── 2b. Manual qty input (Enter key or blur after typing) ────────────
    @app.callback(
        Output("cart-store", "data", allow_duplicate=True),
        Input({"type": "cart-qty-input", "index": ALL}, "value"),
        [State({"type": "cart-qty-input", "index": ALL}, "id"),
         State("cart-store", "data")],
        prevent_initial_call=True,
    )
    def update_cart_qty(qty_values, input_ids, cart):
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        cart = cart or {}

        try:
            id_part = ctx.triggered[0]["prop_id"].split(".")[0]
            btn_data = json.loads(id_part)
            pid_str = str(btn_data["index"])
        except Exception:
            raise PreventUpdate

        triggered_val = ctx.triggered[0].get("value")
        if triggered_val is None or pid_str not in cart:
            raise PreventUpdate

        new_qty = int(triggered_val) if triggered_val else 0

        # Guard: skip if value already matches cart (spurious fire from render)
        if new_qty == cart[pid_str].get("qty", 0):
            raise PreventUpdate

        if new_qty <= 0:
            del cart[pid_str]
        else:
            cart[pid_str]["qty"] = new_qty

        return cart

    # ── 3. Render cart display ────────────────────────────────────────────
    @app.callback(
        [Output("cart-display", "children"),
         Output("cart-total", "children"),
         Output("cart-count-badge", "children")],
        Input("cart-store", "data"),
    )
    def render_cart(cart):
        cart = cart or {}
        if not cart:
            empty = html.Div([
                html.I(className="bi bi-cart3",
                       style={"fontSize": "36px", "color": "var(--text-muted)",
                              "display": "block", "textAlign": "center",
                              "marginBottom": "8px"}),
                html.Div("Cart is empty",
                         style={"textAlign": "center", "color": "var(--text-muted)",
                                "fontSize": "13px"}),
                html.Div("Tap a product to add",
                         style={"textAlign": "center", "color": "var(--text-muted)",
                                "fontSize": "11px", "marginTop": "4px"}),
            ], style={"padding": "32px 16px"})
            return empty, "₹0", "0 items"

        total = sum(v["price"] * v["qty"] for v in cart.values())
        total_items = sum(v["qty"] for v in cart.values())
        rows = []

        for pid_str, item in cart.items():
            pid = int(pid_str)
            color = CATEGORY_COLORS.get(item["category"], "#8B5CF6")
            line_total = item["price"] * item["qty"]
            rows.append(html.Div([
                html.Div([
                    html.Div(item["name"],
                             style={"fontSize": "12px", "fontWeight": "600",
                                    "color": "var(--text-primary)",
                                    "lineHeight": "1.3", "marginBottom": "2px"}),
                    html.Div(fmt_inr(item["price"]) + " each",
                             style={"fontSize": "11px", "color": color}),
                ], style={"flex": "1", "minWidth": "0"}),
                html.Div([
                    # Minus
                    html.Button("-",
                                id={"type": "cart-minus", "index": pid},
                                className="cart-qty-btn cart-qty-minus", n_clicks=0),
                    # Editable qty — type a number and press Enter or click away
                    dcc.Input(
                        id={"type": "cart-qty-input", "index": pid},
                        type="number",
                        value=item["qty"],
                        min=1,
                        step=1,
                        debounce=True,
                        className="cart-qty-input",
                    ),
                    # Plus
                    html.Button("+",
                                id={"type": "cart-plus", "index": pid},
                                className="cart-qty-btn cart-qty-plus", n_clicks=0),
                ], style={"display": "flex", "alignItems": "center", "gap": "6px",
                          "marginLeft": "8px"}),
                html.Div([
                    html.Div(fmt_inr(line_total),
                             style={"fontFamily": "Space Mono", "fontSize": "13px",
                                    "fontWeight": "700", "color": "var(--primary)",
                                    "textAlign": "right"}),
                    html.Button(html.I(className="bi bi-x"),
                                id={"type": "cart-remove", "index": pid},
                                className="cart-remove-btn", n_clicks=0),
                ], style={"display": "flex", "flexDirection": "column",
                          "alignItems": "flex-end", "gap": "4px",
                          "marginLeft": "8px"}),
            ], style={"display": "flex", "alignItems": "center",
                      "padding": "8px 0",
                      "borderBottom": "1px solid var(--border-light)"}))

        return (
            html.Div(rows),
            fmt_inr(total),
            f"{total_items} item{'s' if total_items != 1 else ''}",
        )

    # ── 4. Payment mode toggle ────────────────────────────────────────────
    @app.callback(
        [Output("payment-mode-store", "data"),
         Output("pay-cash", "className"),
         Output("pay-upi", "className"),
         Output("pay-card", "className")],
        [Input("pay-cash", "n_clicks"),
         Input("pay-upi", "n_clicks"),
         Input("pay-card", "n_clicks")],
        prevent_initial_call=True,
    )
    def select_payment_mode(cash_n, upi_n, card_n):
        ctx = callback_context
        if not ctx.triggered:
            return "Cash", "pay-mode-btn active", "pay-mode-btn", "pay-mode-btn"
        triggered = ctx.triggered[0]["prop_id"]
        if "pay-cash" in triggered:
            mode = "Cash"
        elif "pay-upi" in triggered:
            mode = "UPI"
        elif "pay-card" in triggered:
            mode = "Card"
        else:
            mode = "Cash"
        active = "pay-mode-btn active"
        inactive = "pay-mode-btn"
        return (
            mode,
            active if mode == "Cash" else inactive,
            active if mode == "UPI"  else inactive,
            active if mode == "Card" else inactive,
        )

    # ── 5. Record Sale ──────────────────────────────────────────────────
    @app.callback(
        [Output("sale-toast", "children"),
         Output("sale-toast", "header"),
         Output("sale-toast", "is_open"),
         Output("sale-toast", "icon"),
         Output("cart-store", "data", allow_duplicate=True),
         Output("sale-trigger", "data")],
        Input("complete-sale-btn", "n_clicks"),
        [State("cart-store", "data"),
         State("payment-mode-store", "data"),
         State("sale-trigger", "data")],
        prevent_initial_call=True,
    )
    def complete_sale(n, cart, payment_mode, trigger):
        if not n:
            raise PreventUpdate
        cart = cart or {}
        if not cart:
            return ("Cart is empty — add items first.",
                    "Warning", True, "warning", cart, trigger or 0)

        seller_name = flask.session.get("username", "Unknown")
        payment_mode = payment_mode or "Cash"

        result = record_cart_sale(cart, payment_mode, seller_name)

        if result["success"]:
            msg = result["message"]
            if result.get("low_stock"):
                items = ", ".join(result["low_stock"][:3])
                msg += f" | ⚠ Low stock: {items}"
            return msg, "Sale Complete!", True, "success", {}, (trigger or 0) + 1
        else:
            return (result["message"], "Sale Failed", True, "danger",
                    cart, trigger or 0)

    # ── 6. Today's summary panel (role-aware) ────────────────────────────
    @app.callback(
        Output("today-summary-panel", "children"),
        [Input("sales-refresh", "n_intervals"),
         Input("sale-trigger", "data")],
    )
    def update_today_summary(_, trigger):
        role = flask.session.get("role")
        df = get_today_sales()

        total_items = int(df["quantity"].sum()) if not df.empty else 0
        total_txns = len(df["transaction_ref"].unique()) if (not df.empty and "transaction_ref" in df.columns) else len(df)

        # Common elements for both roles
        items = [
            html.Div([
                html.Div("Items Sold",    className="summary-label"),
                html.Div(str(total_items), className="summary-value"),
            ], className="summary-stat"),
            html.Div([
                html.Div("Transactions", className="summary-label"),
                html.Div(str(total_txns), className="summary-value"),
            ], className="summary-stat"),
        ]

        # Owner sees revenue too
        if role == ROLE_OWNER:
            total_rev = df["total_amount"].sum() if not df.empty else 0
            items.insert(0, html.Div([
                html.Div("Today's Revenue", className="summary-label"),
                html.Div(fmt_inr(total_rev),
                         className="summary-value",
                         style={"color": "var(--primary)"}),
            ], className="summary-stat"))

        # Recent 5 transactions
        recent = df.head(5)
        if recent.empty:
            recent_panel = html.Div(
                "No sales recorded today.",
                style={"color": "var(--text-muted)", "fontSize": "12px",
                       "textAlign": "center", "padding": "16px 0"},
            )
        else:
            txn_rows = []
            for _, row in recent.iterrows():
                right = fmt_inr(row["total_amount"]) if role == ROLE_OWNER \
                    else f"x{row['quantity']}"
                txn_rows.append(html.Div([
                    html.Div([
                        html.Div(row["product_name"],
                                 style={"fontSize": "12px", "fontWeight": "600",
                                        "color": "var(--text-primary)"}),
                        html.Div(f"Qty: {row['quantity']}  ·  {row.get('payment_mode','—')}",
                                 style={"fontSize": "11px", "color": "var(--text-muted)"}),
                    ]),
                    html.Div(right,
                             style={"fontFamily": "Space Mono", "fontSize": "12px",
                                    "color": "var(--primary)", "fontWeight": "600"}),
                ], style={"display": "flex", "justifyContent": "space-between",
                          "alignItems": "center",
                          "padding": "6px 0",
                          "borderBottom": "1px solid var(--border-light)"}))
            recent_panel = html.Div(txn_rows)

        return html.Div([
            html.Div(items, style={"marginBottom": "16px"}),
            html.Div("Recent Transactions",
                     style={"fontSize": "11px", "fontWeight": "600",
                            "letterSpacing": "0.5px", "textTransform": "uppercase",
                            "color": "var(--text-muted)", "marginBottom": "10px"}),
            recent_panel,
        ])
