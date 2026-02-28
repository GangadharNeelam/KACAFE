"""Seller Menu Reference — read-only drill-down: category → products → recipe."""
from dash import html, dcc


def get_layout():
    return html.Div([
        # ── Info banner ───────────────────────────────────────────────────────
        html.Div([
            html.I(className="bi bi-book-half me-2", style={"color": "#A78BFA"}),
            html.Span(
                "Menu Reference — browse categories, view items and check recipe ingredients. "
                "This is a read-only reference view.",
                style={"fontSize": "13px", "color": "#C4B5FD"},
            ),
        ], style={
            "background": "rgba(167,139,250,0.1)",
            "border": "1px solid rgba(167,139,250,0.3)",
            "borderRadius": "8px", "padding": "12px 18px", "marginBottom": "20px",
        }),

        # ── Main content — driven by the state store ──────────────────────────
        html.Div(id="seller-menu-content"),

        # ── State store  view ∈ {"categories", "products", "recipe"} ─────────
        dcc.Store(
            id="seller-menu-state",
            data={"view": "categories", "category": None, "product_id": None},
        ),
    ], className="page-content")
