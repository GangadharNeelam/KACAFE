"""Live Sales Monitor — Owner only. Real-time staff activity tiles."""
import dash_bootstrap_components as dbc
from dash import html, dcc


def get_layout():
    return html.Div([
        # Summary KPIs (today)
        html.Div(id="live-sales-kpis"),

        html.Div(style={"height": "20px"}),

        dbc.Row([
            # Staff activity tiles
            dbc.Col([
                html.Div([
                    html.Div([
                        html.Div([
                            html.Span(className="live-indicator me-2"),
                            html.Span("Staff Activity Today", className="card-title-custom"),
                        ], style={"display": "flex", "alignItems": "center"}),
                        dcc.Dropdown(
                            id="live-sales-seller-filter",
                            placeholder="Filter by seller...",
                            clearable=True,
                            style={"width": "160px", "fontSize": "12px"},
                        ),
                    ], className="card-header-custom"),
                    html.Div(
                        id="seller-tiles-area",
                        style={"padding": "16px", "minHeight": "120px"},
                    ),
                ], className="dash-card"),
            ], md=8),

            # Payment breakdown + seller stats
            dbc.Col([
                html.Div([
                    html.Div([
                        html.Span("Payment Breakdown (Today)",
                                  className="card-title-custom"),
                        dcc.Dropdown(
                            id="live-sales-payment-filter",
                            options=[
                                {"label": "All Payments", "value": "All"},
                                {"label": "Cash",         "value": "Cash"},
                                {"label": "UPI",          "value": "UPI"},
                                {"label": "Card",         "value": "Card"},
                            ],
                            value="All",
                            clearable=False,
                            style={"width": "130px", "fontSize": "12px"},
                        ),
                    ], className="card-header-custom",
                       style={"display": "flex", "alignItems": "center",
                              "justifyContent": "space-between"}),
                    dcc.Loading(
                        dcc.Graph(id="live-payment-pie",
                                  config={"displayModeBar": False}),
                        color="var(--primary)", type="circle"
                    ),
                ], className="dash-card", style={"marginBottom": "16px"}),

                html.Div([
                    html.Div("Seller Performance", className="card-header-custom"),
                    html.Div(id="live-seller-perf",
                             style={"padding": "16px"}),
                ], className="dash-card"),
            ], md=4),
        ], className="g-3"),

        dcc.Interval(id="live-sales-refresh", interval=5000, n_intervals=0),
    ], className="page-content")
