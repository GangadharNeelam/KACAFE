"""Vendor Management layout."""
import dash_bootstrap_components as dbc
from dash import html, dcc

def get_layout():
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div([
                        html.Span("Vendors", className="card-title-custom"),
                        dbc.Button(
                            [html.I(className="bi bi-plus-lg me-2"), "Add Vendor"],
                            id="open-vendor-modal",
                            style={"background": "var(--primary)", "border": "none",
                                   "color": "#0F172A", "fontWeight": "600", "fontSize": "13px"},
                        ),
                    ], className="card-header-custom"),
                    html.Div([
                        html.Div(id="vendors-table-container"),
                    ], style={"padding": "0"}),
                ], className="dash-card"),
            ], md=8),
            
            dbc.Col([
                html.Div([
                    html.Div("Vendor Stats", className="card-header-custom"),
                    html.Div(id="vendor-stats", className="card-body-custom"),
                ], className="dash-card"),
            ], md=4),
        ], className="g-3"),
        
        # Add Vendor Modal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Add New Vendor")),
            dbc.ModalBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Vendor Name *"),
                        dbc.Input(id="vendor-name", placeholder="e.g. Fresh Farms Ltd."),
                    ], md=12, className="mb-3"),
                    dbc.Col([
                        dbc.Label("Phone"),
                        dbc.Input(id="vendor-phone", placeholder="+1-555-0100"),
                    ], md=6, className="mb-3"),
                    dbc.Col([
                        dbc.Label("Email"),
                        dbc.Input(id="vendor-email", type="email", placeholder="vendor@email.com"),
                    ], md=6, className="mb-3"),
                    dbc.Col([
                        dbc.Label("Lead Time (Days)"),
                        dbc.Input(id="vendor-lead-time", type="number", min=1, max=60, value=3),
                    ], md=12, className="mb-2"),
                ]),
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="close-vendor-modal", outline=True, color="secondary"),
                dbc.Button("Add Vendor", id="save-vendor",
                           style={"background": "var(--primary)", "border": "none", "color": "#0F172A", "fontWeight": "600"}),
            ]),
        ], id="vendor-modal", is_open=False),
        
        dbc.Toast(id="vendor-toast", header="", is_open=False, dismissable=True, duration=3000,
                  style={"position": "fixed", "top": "80px", "right": "20px", "zIndex": 9999, "minWidth": "300px"}),
        
        dcc.ConfirmDialog(id="confirm-delete-vendor", message="Are you sure you want to delete this vendor?"),
        dcc.Store(id="vendor-to-delete", data=None),
        dcc.Interval(id="vendors-refresh", interval=30000, n_intervals=0),
    ], className="page-content")
