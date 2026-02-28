"""
Cart-based POS layout for both Seller and Owner.
Left: Category accordion with product buttons.
Right: Cart panel + payment mode + Record Sale.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc
from database.db import get_connection
import pandas as pd
from utils import CATEGORY_COLORS, CATEGORY_ORDER, fmt_inr


def get_products_by_category():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, name, category, price FROM products WHERE is_active=1 ORDER BY category, name",
        conn
    )
    conn.close()
    return df


def build_product_accordion(df: pd.DataFrame) -> list:
    """Build accordion items with product button grid per category."""
    items = []
    # Order categories per KAFE menu
    cats_in_order = [c for c in CATEGORY_ORDER if c in df["category"].values]
    # Append any remaining categories not in CATEGORY_ORDER
    for c in df["category"].unique():
        if c not in cats_in_order:
            cats_in_order.append(c)

    for cat in cats_in_order:
        cat_df = df[df["category"] == cat]
        color = CATEGORY_COLORS.get(cat, "#8B5CF6")
        count = len(cat_df)

        buttons = []
        for _, row in cat_df.iterrows():
            buttons.append(
                dbc.Col(
                    html.Button(
                        [
                            html.Div(row["name"], className="pos-btn-name"),
                            html.Div(fmt_inr(row["price"]), className="pos-btn-price"),
                        ],
                        id={"type": "add-to-cart", "index": row["id"]},
                        className="pos-product-btn",
                        n_clicks=0,
                        **{"data-price": row["price"],
                           "data-name": row["name"],
                           "data-cat": cat},
                    ),
                    xs=6, sm=4, md=4, lg=3, className="mb-2"
                )
            )

        items.append(
            dbc.AccordionItem(
                dbc.Row(buttons, className="g-2 pt-2"),
                title=html.Span([
                    html.Span(cat, style={"fontWeight": "600", "fontSize": "13px"}),
                    html.Span(f" ({count})", style={"fontSize": "11px",
                                                     "color": "var(--text-muted)",
                                                     "marginLeft": "4px"}),
                ]),
                item_id=f"cat-{cat.replace(' ', '-')}",
                style={"borderLeft": f"3px solid {color}"},
            )
        )
    return items


def get_layout():
    df = get_products_by_category()
    accordion_items = build_product_accordion(df)

    return html.Div([
        dbc.Row([
            # ── Left: Product Accordion ───────────────────────────────────
            dbc.Col([
                html.Div([
                    html.Div([
                        html.Div([
                            html.Span(className="live-indicator me-2"),
                            html.Span("Sales POS", className="card-title-custom"),
                        ], style={"display": "flex", "alignItems": "center"}),
                        html.Div(
                            f"{len(df)} active products",
                            style={"fontSize": "11px", "color": "var(--text-muted)"}
                        ),
                    ], className="card-header-custom"),
                    html.Div([
                        dbc.Accordion(
                            accordion_items,
                            id="menu-accordion",
                            always_open=False,
                            start_collapsed=False,
                            active_item="cat-Desi-Teas",
                            className="pos-accordion",
                        )
                    ], style={"padding": "12px", "maxHeight": "calc(100vh - 180px)",
                              "overflowY": "auto"}),
                ], className="dash-card"),
            ], md=8),

            # ── Right: Cart Panel ─────────────────────────────────────────
            dbc.Col([
                html.Div([
                    # Cart header
                    html.Div([
                        html.Div([
                            html.I(className="bi bi-cart3 me-2",
                                   style={"color": "var(--primary)", "fontSize": "16px"}),
                            html.Span("Order Cart", className="card-title-custom"),
                        ], style={"display": "flex", "alignItems": "center"}),
                        html.Span(id="cart-count-badge",
                                  style={"fontSize": "11px", "color": "var(--text-muted)"}),
                    ], className="card-header-custom"),

                    # Cart items
                    html.Div(
                        id="cart-display",
                        style={"minHeight": "200px", "maxHeight": "340px",
                               "overflowY": "auto", "padding": "8px 16px"},
                    ),

                    html.Div(className="divider", style={"margin": "0"}),

                    # Cart total
                    html.Div([
                        html.Div([
                            html.Span("SUBTOTAL",
                                      style={"fontSize": "11px", "fontWeight": "600",
                                             "letterSpacing": "0.5px",
                                             "color": "var(--text-muted)"}),
                            html.Span(id="cart-total",
                                      style={"fontFamily": "Space Mono",
                                             "fontSize": "22px", "fontWeight": "700",
                                             "color": "var(--primary)"}),
                        ], style={"display": "flex", "justifyContent": "space-between",
                                  "alignItems": "center", "marginBottom": "16px"}),

                        # Payment mode
                        html.Div([
                            html.Div("PAYMENT MODE",
                                     style={"fontSize": "11px", "fontWeight": "600",
                                            "letterSpacing": "0.5px",
                                            "color": "var(--text-muted)",
                                            "marginBottom": "8px"}),
                            dbc.ButtonGroup([
                                dbc.Button("💵 Cash",  id="pay-cash",  n_clicks=0,
                                           className="pay-mode-btn active", size="sm"),
                                dbc.Button("📱 UPI",   id="pay-upi",   n_clicks=0,
                                           className="pay-mode-btn", size="sm"),
                                dbc.Button("💳 Card",  id="pay-card",  n_clicks=0,
                                           className="pay-mode-btn", size="sm"),
                            ], style={"width": "100%"}),
                        ], style={"marginBottom": "16px"}),

                        # Record Sale button
                        dbc.Button(
                            [html.I(className="bi bi-check2-circle me-2"),
                             "Record Sale"],
                            id="complete-sale-btn",
                            style={
                                "width": "100%",
                                "background": "var(--primary)",
                                "border": "none",
                                "color": "#0F172A",
                                "fontWeight": "700",
                                "fontSize": "15px",
                                "padding": "12px",
                                "borderRadius": "8px",
                            },
                            n_clicks=0,
                        ),

                        # Clear cart button (html.Button — no href, no page navigation)
                        html.Div(
                            html.Button(
                                "Clear Cart",
                                id="clear-cart-btn",
                                n_clicks=0,
                                style={
                                    "fontSize": "12px",
                                    "color": "var(--danger)",
                                    "background": "none",
                                    "border": "none",
                                    "cursor": "pointer",
                                    "padding": "0",
                                    "textDecoration": "underline",
                                },
                            ),
                            style={"textAlign": "center", "marginTop": "10px"},
                        ),
                    ], style={"padding": "16px"}),
                ], className="dash-card", style={"marginBottom": "16px"}),

                # Today's Summary (role-aware via callback)
                html.Div([
                    html.Div("Today's Summary", className="card-header-custom"),
                    html.Div(id="today-summary-panel", style={"padding": "16px"}),
                    dcc.Interval(id="sales-refresh", interval=8000, n_intervals=0),
                ], className="dash-card"),
            ], md=4),
        ], className="g-3"),

        # Stores & hidden
        dcc.Store(id="cart-store", data={}),
        dcc.Store(id="payment-mode-store", data="Cash"),
        dcc.Store(id="sale-trigger", data=0),

        # Toast
        dbc.Toast(
            id="sale-toast",
            header="",
            is_open=False,
            dismissable=True,
            duration=4000,
            style={"position": "fixed", "top": "80px", "right": "20px",
                   "zIndex": 9999, "minWidth": "320px"},
        ),
    ], className="page-content")
