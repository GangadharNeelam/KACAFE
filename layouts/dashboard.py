"""Owner Analytics Dashboard — full financial visibility."""
import dash_bootstrap_components as dbc
from dash import html, dcc


def get_layout():
    return html.Div([
        # KPI Row
        html.Div(id="dashboard-kpis"),

        html.Div(style={"height": "24px"}),

        # Period filter
        html.Div([
            html.Span("Period: ",
                      style={"color": "var(--text-muted)", "fontSize": "13px",
                             "fontWeight": "600"}),
            dcc.RadioItems(
                id="dashboard-period",
                options=[
                    {"label": "Today",   "value": 1},
                    {"label": "7 Days",  "value": 7},
                    {"label": "30 Days", "value": 30},
                    {"label": "90 Days", "value": 90},
                ],
                value=30,
                inline=True,
                className="filter-bar",
                inputStyle={"display": "none"},
                labelStyle={
                    "padding": "6px 14px", "borderRadius": "20px",
                    "fontSize": "12px", "fontWeight": "500",
                    "border": "1px solid var(--border-light)",
                    "backgroundColor": "transparent",
                    "color": "var(--text-secondary)",
                    "cursor": "pointer", "marginRight": "6px",
                    "transition": "all 0.2s",
                },
            ),
        ], style={"display": "flex", "alignItems": "center", "gap": "12px",
                  "marginBottom": "20px"}),

        # Row 1: Revenue Trend + Category Pie
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div([
                        html.Span("Revenue Trend", className="card-title-custom"),
                        html.Span(id="revenue-trend-label",
                                  style={"fontSize": "11px", "color": "var(--text-muted)"}),
                    ], className="chart-header"),
                    dcc.Loading(
                        dcc.Graph(id="revenue-trend-chart",
                                  config={"displayModeBar": False}),
                        color="var(--primary)", type="circle"
                    ),
                ], className="chart-container"),
            ], md=8),
            dbc.Col([
                html.Div([
                    html.Div("Sales by Category", className="chart-header"),
                    dcc.Loading(
                        dcc.Graph(id="category-pie-chart",
                                  config={"displayModeBar": False}),
                        color="var(--primary)", type="circle"
                    ),
                ], className="chart-container"),
            ], md=4),
        ], className="g-3 mb-3"),

        # Row 2: Top Products + Payment Split + Category Perf
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div("Top 10 Products", className="chart-header"),
                    dcc.Loading(
                        dcc.Graph(id="top-products-chart",
                                  config={"displayModeBar": False}),
                        color="var(--primary)", type="circle"
                    ),
                ], className="chart-container"),
            ], md=6),
            dbc.Col([
                html.Div([
                    html.Div("Payment Mode Split", className="chart-header"),
                    dcc.Loading(
                        dcc.Graph(id="payment-mode-chart",
                                  config={"displayModeBar": False}),
                        color="var(--primary)", type="circle"
                    ),
                ], className="chart-container"),
            ], md=3),
            dbc.Col([
                html.Div([
                    html.Div("Category Performance", className="chart-header"),
                    dcc.Loading(
                        dcc.Graph(id="category-perf-chart",
                                  config={"displayModeBar": False}),
                        color="var(--primary)", type="circle"
                    ),
                ], className="chart-container"),
            ], md=3),
        ], className="g-3"),

        dcc.Interval(id="dashboard-refresh", interval=30000, n_intervals=0),
    ], className="page-content")
