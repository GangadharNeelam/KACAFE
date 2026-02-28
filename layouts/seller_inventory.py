"""
Seller Inventory Monitoring — full categorised view.
Shows all materials grouped by category with KPI summary and at-risk products panel.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc


def _kpi_card(title: str, icon: str, output_id: str, icon_color: str) -> html.Div:
    return html.Div([
        html.Div([
            html.I(className=f"bi {icon} me-2", style={"color": icon_color, "fontSize": "16px"}),
            html.Span(title, className="card-title-custom", style={"fontSize": "12px"}),
        ], className="card-header-custom"),
        html.Div(
            html.Span(id=output_id, style={
                "fontSize": "36px", "fontWeight": "700",
                "fontFamily": "Space Mono", "color": "var(--text-primary)",
            }),
            style={"padding": "16px 20px 20px", "textAlign": "center"},
        ),
    ], className="dash-card", style={"height": "100%"})


def get_layout():
    return html.Div([
        # ── Info banner ───────────────────────────────────────────────────────
        html.Div([
            html.I(className="bi bi-info-circle me-2", style={"color": "#60A5FA"}),
            html.Span(
                "Inventory Monitor — read-only view of all raw materials. "
                "Contact the owner to adjust stock or raise purchase orders.",
                style={"fontSize": "13px", "color": "#93C5FD"},
            ),
        ], style={
            "background": "rgba(59,130,246,0.1)",
            "border": "1px solid rgba(59,130,246,0.3)",
            "borderRadius": "8px", "padding": "12px 18px", "marginBottom": "20px",
        }),

        # ── KPI row ───────────────────────────────────────────────────────────
        dbc.Row([
            dbc.Col(_kpi_card(
                "Total Materials", "bi-boxes", "inv-kpi-total", "#60A5FA",
            ), md=4),
            dbc.Col(_kpi_card(
                "Needs Attention", "bi-exclamation-triangle-fill", "inv-kpi-low", "#F59E0B",
            ), md=4),
            dbc.Col(_kpi_card(
                "At-Risk Drinks", "bi-cup-hot", "inv-kpi-atrisk", "#EF4444",
            ), md=4),
        ], className="g-3 mb-3"),

        # ── At-Risk Products panel ────────────────────────────────────────────
        html.Div([
            html.Div([
                html.I(className="bi bi-exclamation-circle-fill me-2",
                       style={"color": "#EF4444"}),
                html.Span("At-Risk Menu Items", className="card-title-custom"),
                html.Span(
                    " — drinks/items affected by low or critical stock",
                    style={"fontSize": "11px", "color": "var(--text-muted)"},
                ),
            ], className="card-header-custom"),
            html.Div(id="seller-atrisk-products", style={"padding": "16px 20px 20px"}),
        ], className="dash-card mb-3"),

        # ── Categorised inventory ─────────────────────────────────────────────
        html.Div(id="seller-inventory-categorized"),

        dcc.Interval(id="seller-inv-refresh", interval=20000, n_intervals=0),
    ], className="page-content")
