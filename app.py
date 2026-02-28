"""
KF-KAFE Operations Platform — Enterprise Edition
Role-Based Access Control:
  ROLE_OWNER (supervisor) — full access to all modules
  ROLE_STAFF (seller)     — Sales POS, Seller Dashboard, Inventory Monitor

Role strings are never hardcoded here; import them from constants.py.
"""
import logging
import flask
from dash import html, dcc, Input, Output
from dash.exceptions import PreventUpdate

from constants import ROLE_OWNER, ROLE_STAFF, ROLE_DISPLAY

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── DB init ────────────────────────────────────────────────────────────────────
from database.db import init_db
from database.seed import seed_data
init_db()
seed_data()

# ── Dash app ────────────────────────────────────────────────────────────────────
from server import app
server = app.server   # expose Flask WSGI app for gunicorn (app:server)

# ── Layouts ─────────────────────────────────────────────────────────────────────
from layouts import dashboard, sales, inventory, vendors, procurement
from layouts import login as login_layout
from layouts import seller_dashboard, seller_inventory, seller_menu, menu, live_sales

# ── Callbacks ───────────────────────────────────────────────────────────────────
from callbacks import (
    auth_callbacks,
    dashboard_callbacks,
    sales_callbacks,
    inventory_callbacks,
    procurement_callbacks,
    seller_dashboard_callbacks,
    menu_callbacks,
    live_sales_callbacks,
    seller_inventory_callbacks,
    seller_menu_callbacks,
)
auth_callbacks.register_callbacks()
dashboard_callbacks.register_callbacks()
sales_callbacks.register_callbacks()
inventory_callbacks.register_callbacks()
procurement_callbacks.register_callbacks()
seller_dashboard_callbacks.register_callbacks()
menu_callbacks.register_callbacks()
live_sales_callbacks.register_callbacks()
seller_inventory_callbacks.register_callbacks()
seller_menu_callbacks.register_callbacks()

# ── Page maps ───────────────────────────────────────────────────────────────────
OWNER_PAGES = {
    "#":                ("Dashboard",          dashboard.get_layout),
    "#sales":           ("Sales POS",          sales.get_layout),
    "#live-sales":      ("Live Sales Monitor", live_sales.get_layout),
    "#inventory":       ("Inventory",          inventory.get_layout),
    "#menu":            ("Menu Management",    menu.get_layout),
    "#vendors":         ("Vendors",            vendors.get_layout),
    "#procurement":     ("Procurement",        procurement.get_layout),
}

SELLER_PAGES = {
    "#seller-dashboard":   ("My Dashboard",      seller_dashboard.get_layout),
    "#sales":              ("Sales POS",          sales.get_layout),
    "#seller-inventory":   ("Inventory Monitor",  seller_inventory.get_layout),
    "#seller-menu":        ("Menu Reference",     seller_menu.get_layout),
}

OWNER_NAV = [
    ("#",                "owner-dashboard", "bi-grid-1x2",          "Dashboard"),
    ("#sales",           "owner-sales",     "bi-cart3",             "Sales POS"),
    ("#live-sales",      "owner-live",      "bi-broadcast",         "Live Sales"),
    ("#inventory",       "owner-inventory", "bi-boxes",             "Inventory"),
    ("#menu",            "owner-menu",      "bi-menu-button-wide",  "Menu"),
    ("#vendors",         "owner-vendors",   "bi-building",          "Vendors"),
    ("#procurement",     "owner-proc",      "bi-file-earmark-text", "Procurement"),
]

SELLER_NAV = [
    ("#seller-dashboard", "seller-dash", "bi-grid-1x2",         "My Dashboard"),
    ("#sales",            "seller-sales","bi-cart3",             "Sales POS"),
    ("#seller-inventory", "seller-inv",  "bi-boxes",             "Inventory"),
    ("#seller-menu",      "seller-menu", "bi-menu-button-wide",  "Menu"),
]


# ── Layout builders ─────────────────────────────────────────────────────────────

def _nav_link(icon: str, label: str, href: str, page_id: str, active: bool = False):
    return html.A(
        [html.I(className=f"bi {icon} nav-icon"), html.Span(label)],
        href=href,
        id=f"nav-{page_id}",
        className="nav-link active" if active else "nav-link",
        n_clicks=0,
    )


def build_sidebar(role: str) -> html.Div:
    if role == ROLE_OWNER:
        # Scrollable middle section keeps logout pinned at the bottom on all screens
        nav_body = html.Div([
            html.Div("MAIN MENU", className="nav-section-label"),
            *[_nav_link(icon, label, href, pid) for href, pid, icon, label in OWNER_NAV],
            html.Div(className="divider"),
            html.Div("QUICK STATS", className="nav-section-label"),
            html.Div(id="sidebar-quick-stats", style={"padding": "8px 24px"}),
        ], className="sidebar-nav-scroll")
    else:  # seller
        nav_body = html.Div([
            html.Div("MAIN MENU", className="nav-section-label"),
            *[_nav_link(icon, label, href, pid) for href, pid, icon, label in SELLER_NAV],
        ])

    return html.Div([
        # Logo
        html.Div([
            html.Div("KA", className="logo-icon",
                     style={"fontFamily": "Georgia,serif", "fontSize": "15px",
                            "fontWeight": "900", "letterSpacing": "1px"}),
            html.Div([
                html.Div("KA KAFE", className="logo-text"),
                html.Div("OPERATIONS", className="logo-sub"),
            ]),
        ], className="sidebar-logo"),

        nav_body,

        html.Div(className="divider"),

        html.A(
            [html.I(className="bi bi-box-arrow-right nav-icon"), html.Span("Logout")],
            id="logout-btn", href="#", className="nav-link logout-link", n_clicks=0,
        ),

        html.Div([
            html.Div("v2.0.0 · KAFE Enterprise",  style={"fontSize": "10px"}),
            html.Div("© 2025 Operations Team",     style={"fontSize": "10px",
                                                           "marginTop": "2px"}),
        ], className="sidebar-footer"),
    ], id="sidebar")


def build_topbar(username: str, role: str) -> html.Div:
    display_role = ROLE_DISPLAY.get(role, role.capitalize())
    badge_style_map = {
        ROLE_OWNER: {"background": "rgba(59,130,246,0.15)",
                     "color": "#3B82F6",
                     "border": "1px solid rgba(59,130,246,0.3)"},
        ROLE_STAFF: {"background": "rgba(16,185,129,0.15)",
                     "color": "#10B981",
                     "border": "1px solid rgba(16,185,129,0.3)"},
    }
    badge_style = {
        "padding": "3px 12px", "borderRadius": "20px",
        "fontSize": "11px", "fontWeight": "600", "letterSpacing": "0.3px",
        **badge_style_map.get(role, {}),
    }
    initials = "".join(p[0].upper() for p in username.split()[:2]) or "U"

    return html.Div([
        html.Div(id="page-title", className="topbar-title"),
        html.Div([
            html.Div([
                html.I(className="bi bi-person-circle me-2",
                       style={"fontSize": "16px", "color": "var(--text-muted)"}),
                html.Span(username,
                          style={"fontWeight": "600", "fontSize": "13px",
                                 "color": "var(--text-primary)", "marginRight": "8px"}),
                html.Span(display_role, style=badge_style),
            ], style={"display": "flex", "alignItems": "center"}),
            html.Div(initials, className="user-avatar"),
        ], className="topbar-right"),
    ], id="topbar")


def build_app_layout(role: str, username: str) -> html.Div:
    return html.Div([
        build_sidebar(role),
        html.Div([
            build_topbar(username, role),
            html.Div(id="page-content"),
        ], id="main-content"),
        dcc.Store(id="global-refresh", data=0),
        dcc.Interval(id="global-interval", interval=60000, n_intervals=0),
    ])


# ── Shell layout (always in DOM) ───────────────────────────────────────────────
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="auth-store", storage_type="memory"),
    html.Div(id="app-container"),
])


# ── Routing ────────────────────────────────────────────────────────────────────
@app.callback(
    Output("app-container", "children"),
    [Input("url", "pathname"), Input("auth-store", "data")],
)
def handle_routing(*_):
    user_id  = flask.session.get("user_id")
    role     = flask.session.get("role")
    username = flask.session.get("username", "User")
    if not user_id:
        return login_layout.get_layout()
    return build_app_layout(role, username)


# ── Page rendering ─────────────────────────────────────────────────────────────
@app.callback(
    [Output("page-content", "children"),
     Output("page-title",   "children")],
    Input("url", "hash"),
)
def display_page(hash_val):
    role = flask.session.get("role")
    if not role:
        raise PreventUpdate

    hash_val = hash_val or ""

    if role == ROLE_STAFF:
        default_hash = "#seller-dashboard"
        h = hash_val if hash_val in SELLER_PAGES else default_hash
        title, layout_fn = SELLER_PAGES[h]
    else:  # ROLE_OWNER
        default_hash = "#"
        h = hash_val if hash_val in OWNER_PAGES else default_hash
        title, layout_fn = OWNER_PAGES[h]

    return layout_fn(), html.Span(title)


# ── Owner nav active-state ─────────────────────────────────────────────────────
@app.callback(
    [Output(f"nav-{pid}", "className") for _, pid, _, _ in OWNER_NAV],
    Input("url", "hash"),
)
def update_owner_nav_active(hash_val):
    if flask.session.get("role") != ROLE_OWNER:
        raise PreventUpdate
    hash_val = hash_val or "#"
    return [
        "nav-link active" if href == hash_val else "nav-link"
        for href, _, _, _ in OWNER_NAV
    ]


# ── Seller nav active-state ────────────────────────────────────────────────────
@app.callback(
    [Output(f"nav-{pid}", "className") for _, pid, _, _ in SELLER_NAV],
    Input("url", "hash"),
)
def update_seller_nav_active(hash_val):
    if flask.session.get("role") != ROLE_STAFF:
        raise PreventUpdate
    hash_val = hash_val or "#seller-dashboard"
    return [
        "nav-link active" if href == hash_val else "nav-link"
        for href, _, _, _ in SELLER_NAV
    ]


# ── Sidebar quick stats (owner only) ──────────────────────────────────────────
from services.sales_service import get_kpis
from services.inventory_service import get_low_stock_materials
from utils import fmt_inr


@app.callback(
    Output("sidebar-quick-stats", "children"),
    Input("global-interval", "n_intervals"),
)
def update_sidebar_stats(_):
    if flask.session.get("role") != ROLE_OWNER:
        raise PreventUpdate
    try:
        kpis = get_kpis(1)
        low  = get_low_stock_materials()
        return html.Div([
            html.Div([
                html.Span("Today Revenue",
                          style={"fontSize": "10px", "color": "var(--text-muted)",
                                 "display": "block"}),
                html.Span(fmt_inr(kpis["total_revenue"]),
                          style={"fontFamily": "Space Mono", "fontSize": "14px",
                                 "color": "var(--primary)"}),
            ], style={"marginBottom": "8px"}),
            html.Div([
                html.Span("Low Stock",
                          style={"fontSize": "10px", "color": "var(--text-muted)",
                                 "display": "block"}),
                html.Span(f"{len(low)} items",
                          style={"fontFamily": "Space Mono", "fontSize": "14px",
                                 "color": "var(--danger)" if len(low) > 0
                                          else "var(--success)"}),
            ]),
        ])
    except Exception:
        return html.Div()


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from config import config
    logger.info(f"Starting KF-KAFE Operations Platform on port {config.PORT}")
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)
