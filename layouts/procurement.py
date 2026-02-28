"""Procurement Management — with partial delivery and vendor call button."""
import dash_bootstrap_components as dbc
from dash import html, dcc
from services.procurement_service import PO_STATUSES


def get_layout():
    return html.Div([
        # Toolbar
        html.Div([
            dbc.Button(
                [html.I(className="bi bi-plus-lg me-2"), "Create Purchase Order"],
                id="open-po-modal",
                style={"background": "var(--primary)", "border": "none",
                       "color": "#0F172A", "fontWeight": "700", "fontSize": "14px",
                       "padding": "10px 24px"},
            ),
            html.Div([
                dcc.Dropdown(
                    id="po-status-filter",
                    options=[{"label": "All Statuses", "value": "All"}] +
                            [{"label": s, "value": s} for s in PO_STATUSES],
                    value="All",
                    clearable=False,
                    style={"width": "200px", "fontSize": "13px",
                           "color": "#0F172A"},
                ),
            ], style={"position": "relative", "zIndex": 1000}),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "alignItems": "center", "marginBottom": "20px",
                  "position": "relative", "zIndex": 100}),

        # PO Table
        html.Div([
            html.Div([
                html.Span("Purchase Orders", className="card-title-custom"),
                html.Div(id="po-count-badge"),
            ], className="card-header-custom"),
            html.Div(id="po-table-container", style={"padding": "0"}),
        ], className="dash-card"),

        # ── Create PO Modal ───────────────────────────────────────────────
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Create Purchase Order")),
            dbc.ModalBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Vendor *"),
                        dcc.Dropdown(id="po-vendor", placeholder="Select vendor...",
                                     clearable=False),
                    ], md=12, className="mb-3"),
                    dbc.Col([
                        dbc.Label("Material *"),
                        dcc.Dropdown(id="po-material", placeholder="Select material...",
                                     clearable=False),
                    ], md=12, className="mb-3"),
                    dbc.Col([
                        dbc.Label("Quantity Ordered *"),
                        dbc.Input(id="po-quantity", type="number", min=1,
                                  placeholder="e.g. 100"),
                    ], md=6, className="mb-3"),
                    dbc.Col([
                        dbc.Label("Unit Cost (₹)"),
                        dbc.Input(id="po-unit-cost", type="number", min=0,
                                  placeholder="Auto from vendor"),
                    ], md=6, className="mb-3"),
                    dbc.Col([
                        dbc.Label("Expected Delivery"),
                        dbc.Input(id="po-delivery-date", type="date"),
                    ], md=6, className="mb-3"),
                    dbc.Col([
                        dbc.Label("Notes"),
                        dbc.Input(id="po-notes", type="text",
                                  placeholder="Optional notes"),
                    ], md=6, className="mb-3"),
                ]),
                html.Div(id="po-preview"),
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="close-po-modal",
                           outline=True, color="secondary"),
                dbc.Button("Create PO", id="save-po",
                           style={"background": "var(--primary)", "border": "none",
                                  "color": "#0F172A", "fontWeight": "600"}),
            ]),
        ], id="po-modal", is_open=False),

        # ── Record Delivery Modal ─────────────────────────────────────────
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Record Delivery")),
            dbc.ModalBody([
                dcc.Store(id="delivery-po-id"),
                html.Div(id="delivery-po-info",
                         style={"marginBottom": "16px", "fontSize": "13px",
                                "color": "var(--text-secondary)"}),
                dbc.Label("Quantity Received *"),
                dbc.Input(id="delivery-qty-input", type="number", min=0.01,
                          step=0.01, placeholder="Enter received qty"),
                html.Div(id="delivery-feedback", style={"marginTop": "8px"}),
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="close-delivery-modal",
                           outline=True, color="secondary"),
                dbc.Button("Confirm Delivery", id="save-delivery",
                           style={"background": "var(--success)", "border": "none",
                                  "color": "#fff", "fontWeight": "600"}),
            ]),
        ], id="delivery-modal", is_open=False),

        dbc.Toast(id="po-toast", header="", is_open=False,
                  dismissable=True, duration=4000,
                  style={"position": "fixed", "top": "80px", "right": "20px",
                         "zIndex": 9999, "minWidth": "300px"}),

        dcc.Interval(id="procurement-refresh", interval=15000, n_intervals=0),
    ], className="page-content")
