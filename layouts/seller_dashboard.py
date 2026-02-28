"""Seller Analytics Dashboard — non-financial metrics, filterable by period."""
import dash_bootstrap_components as dbc
from dash import html, dcc

# Menu categories (hardcoded to avoid a DB call at layout render time)
_MENU_CATEGORIES = [
    "Desi Teas", "Desi Coffee", "Water Based Teas",
    "Ice Coffee", "Hot Coffee", "Cold Coffee",
    "Mocktails", "Milkshake", "Natural Juices",
    "Fruit Juices", "Fruit Bowl",
]


def get_layout():
    return html.Div([

        # ── Period filter bar ─────────────────────────────────────────────────
        html.Div([
            html.Span(
                "Period:",
                style={"fontSize": "12px", "color": "var(--text-muted)",
                       "fontWeight": "600", "marginRight": "12px"},
            ),
            dbc.RadioItems(
                id="seller-dash-filter",
                options=[
                    {"label": "Today",    "value": "today"},
                    {"label": "All Time", "value": "all_time"},
                ],
                value="today",
                inline=True,
                className="seller-dash-radio",
            ),
        ], className="seller-dash-filter-bar"),

        # ── KPI Row ───────────────────────────────────────────────────────────
        html.Div(id="seller-kpis"),

        html.Div(style={"height": "20px"}),

        # ── Row 1: Category chart + Low Stock ─────────────────────────────────
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div(id="seller-cat-chart-title", className="chart-header"),
                    dcc.Loading(
                        dcc.Graph(id="seller-category-chart",
                                  config={"displayModeBar": False}),
                        color="var(--primary)", type="circle",
                    ),
                ], className="chart-container"),
            ], md=7),

            dbc.Col([
                html.Div([
                    html.Div([
                        html.I(className="bi bi-exclamation-triangle me-2",
                               style={"color": "var(--warning)"}),
                        html.Span("Low Stock Alerts", className="card-title-custom"),
                    ], className="card-header-custom"),
                    html.Div(id="seller-low-stock-panel",
                             style={"padding": "16px", "maxHeight": "280px",
                                    "overflowY": "auto"}),
                ], className="dash-card"),
            ], md=5),
        ], className="g-3 mb-3"),

        # ── Row 2: Trend chart + Top items ────────────────────────────────────
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div(id="seller-trend-chart-title", className="chart-header"),
                    dcc.Loading(
                        dcc.Graph(id="seller-hourly-chart",
                                  config={"displayModeBar": False}),
                        color="var(--primary)", type="circle",
                    ),
                ], className="chart-container"),
            ], md=8),

            dbc.Col([
                html.Div([
                    html.Div([
                        html.I(className="bi bi-trophy me-2",
                               style={"color": "var(--accent)"}),
                        html.Span(id="seller-top-items-title",
                                  className="card-title-custom"),
                    ], className="card-header-custom"),
                    html.Div(id="seller-top-items", style={"padding": "12px"}),
                ], className="dash-card"),
            ], md=4),
        ], className="g-3 mb-3"),

        # ── Row 3: Sales by Item ──────────────────────────────────────────────
        dbc.Row([
            dbc.Col([
                html.Div([
                    # Header with category filter
                    html.Div([
                        html.Div([
                            html.I(className="bi bi-bar-chart-horizontal me-2",
                                   style={"color": "var(--primary)"}),
                            html.Span("Sales by Item", className="card-title-custom"),
                        ], style={"display": "flex", "alignItems": "center"}),
                        dbc.Select(
                            id="seller-item-cat-filter",
                            options=[
                                {"label": "All Categories (Top 25)", "value": ""},
                                *[{"label": c, "value": c} for c in _MENU_CATEGORIES],
                            ],
                            value="",
                            size="sm",
                            style={"width": "210px", "fontSize": "12px"},
                            className="seller-cat-select",
                        ),
                    ], className="card-header-custom",
                       style={"justifyContent": "space-between", "flexWrap": "wrap",
                              "gap": "8px"}),
                    dcc.Loading(
                        dcc.Graph(id="seller-items-chart",
                                  config={"displayModeBar": False}),
                        color="var(--primary)", type="circle",
                    ),
                ], className="dash-card"),
            ], md=12),
        ], className="g-3"),

        dcc.Interval(id="seller-dashboard-refresh", interval=15000, n_intervals=0),
    ], className="page-content")
