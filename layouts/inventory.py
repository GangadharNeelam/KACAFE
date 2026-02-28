"""Owner Inventory — same visual design as seller inventory with full edit capabilities."""
from __future__ import annotations
import dash_bootstrap_components as dbc
from dash import html, dcc


def _kpi_card(title: str, icon: str, output_id: str, icon_color: str,
              extra_style: dict | None = None) -> html.Div:
    return html.Div([
        html.Div([
            html.I(className=f"bi {icon} me-2",
                   style={"color": icon_color, "fontSize": "16px"}),
            html.Span(title, className="card-title-custom",
                      style={"fontSize": "12px"}),
        ], className="card-header-custom"),
        html.Div(
            html.Span(id=output_id, style={
                "fontSize": "32px", "fontWeight": "700",
                "fontFamily": "Space Mono", "color": "var(--text-primary)",
            }),
            style={"padding": "16px 20px 20px", "textAlign": "center"},
        ),
    ], className="dash-card", style={"height": "100%", **(extra_style or {})})


def get_layout():
    return html.Div([

        # ── KPI row ───────────────────────────────────────────────────────────
        dbc.Row([
            dbc.Col(_kpi_card(
                "Total Materials", "bi-boxes",
                "owner-inv-kpi-total", "#60A5FA",
            ), md=3),
            dbc.Col(_kpi_card(
                "Needs Attention", "bi-exclamation-triangle-fill",
                "owner-inv-kpi-attention", "#F59E0B",
            ), md=3),
            dbc.Col(_kpi_card(
                "At-Risk Drinks", "bi-cup-hot",
                "owner-inv-kpi-atrisk", "#EF4444",
            ), md=3),
            dbc.Col(_kpi_card(
                "Stock Value", "bi-currency-rupee",
                "owner-inv-kpi-value", "#2DD4BF",
            ), md=3),
        ], className="g-3 mb-3"),

        # ── At-Risk Products panel ────────────────────────────────────────────
        html.Div([
            html.Div([
                html.I(className="bi bi-exclamation-circle-fill me-2",
                       style={"color": "#EF4444"}),
                html.Span("At-Risk Menu Items", className="card-title-custom"),
                html.Span(
                    " — drinks affected by low or critical stock",
                    style={"fontSize": "11px", "color": "var(--text-muted)"},
                ),
                html.Div([
                    dbc.Button(
                        [html.I(className="bi bi-download me-1"), "Export CSV"],
                        id="export-inventory-btn",
                        size="sm", outline=True, color="secondary",
                        style={"fontSize": "12px"},
                    ),
                ], style={"marginLeft": "auto"}),
            ], className="card-header-custom"),
            html.Div(id="owner-atrisk-products",
                     style={"padding": "16px 20px 20px"}),
        ], className="dash-card mb-3"),

        # ── Categorised inventory with edit actions ───────────────────────────
        html.Div(id="owner-inventory-categorized"),

        # ── Adjust Stock Modal ─────────────────────────────────────────────────
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle([
                html.I(className="bi bi-pencil-square me-2",
                       style={"color": "var(--primary)"}),
                "Adjust Stock Level",
            ])),
            dbc.ModalBody([
                html.Div(id="owner-adjust-material-name", style={
                    "fontSize": "14px", "fontWeight": "600",
                    "color": "var(--text-primary)", "marginBottom": "16px",
                }),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Material"),
                        dcc.Dropdown(id="adjust-material-dropdown",
                                     placeholder="Select material…",
                                     style={"fontSize": "13px"}),
                    ], md=12, className="mb-3"),
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Adjustment (+ to add / − to deduct)"),
                        dbc.Input(id="adjust-amount", type="number",
                                  placeholder="e.g. 50 or -10",
                                  className="custom-input"),
                    ], md=6),
                    dbc.Col([
                        dbc.Label("Reason"),
                        dbc.Input(id="adjust-reason", type="text",
                                  placeholder="e.g. New delivery",
                                  className="custom-input"),
                    ], md=6),
                ]),
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="close-adjust-modal",
                           outline=True, color="secondary", className="me-2"),
                dbc.Button("Apply", id="apply-adjustment",
                           style={"background": "var(--primary)", "border": "none",
                                  "color": "#0F172A", "fontWeight": "600"}),
            ]),
        ], id="adjust-modal", is_open=False),

        # ── Toast ──────────────────────────────────────────────────────────────
        dbc.Toast(
            id="inventory-toast", header="", is_open=False,
            dismissable=True, duration=3000,
            style={"position": "fixed", "top": "80px", "right": "20px",
                   "zIndex": 9999, "minWidth": "300px"},
        ),

        dcc.Download(id="download-inventory"),
        dcc.Interval(id="inventory-refresh", interval=15000, n_intervals=0),
    ], className="page-content")
