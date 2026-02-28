"""Owner Menu Management — category drill-down with full CRUD editing."""
import dash_bootstrap_components as dbc
from dash import html, dcc


def get_layout():
    return html.Div([
        # ── Main content — driven by owner-menu-state store ───────────────────
        html.Div(id="owner-menu-content"),

        # ── State store ───────────────────────────────────────────────────────
        dcc.Store(
            id="owner-menu-state",
            data={"view": "categories", "category": None,
                  "product_id": None, "refresh_token": 0},
        ),

        # ═══ ADD PRODUCT MODAL ════════════════════════════════════════════════
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle([
                html.I(className="bi bi-plus-circle me-2",
                       style={"color": "var(--primary)"}),
                "Add New Product",
            ])),
            dbc.ModalBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Product Name *"),
                        dbc.Input(id="owner-new-product-name",
                                  placeholder="e.g. Mango Lassi",
                                  className="custom-input"),
                    ], md=12, className="mb-3"),
                    dbc.Col([
                        dbc.Label("Category *"),
                        dcc.Dropdown(
                            id="owner-new-product-category",
                            placeholder="Select or create category…",
                            clearable=False,
                            style={"fontSize": "13px"},
                        ),
                    ], md=6, className="mb-3"),
                    dbc.Col([
                        dbc.Label("Price (₹) *"),
                        dbc.Input(id="owner-new-product-price", type="number",
                                  min=1, step=1, placeholder="e.g. 120",
                                  className="custom-input"),
                    ], md=6, className="mb-3"),
                    # Revealed only when "✦ New category…" is chosen
                    dbc.Col([
                        dbc.Label("New Category Name"),
                        dbc.Input(id="owner-new-category-input",
                                  placeholder="Type new category name…",
                                  className="custom-input"),
                    ], md=12, className="mb-3",
                       id="owner-new-category-row",
                       style={"display": "none"}),
                    dbc.Col([
                        dbc.Label("Description"),
                        dbc.Input(id="owner-new-product-desc",
                                  placeholder="Short description…",
                                  className="custom-input"),
                    ], md=12, className="mb-2"),
                ]),
                html.Div(id="owner-add-product-feedback"),
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="owner-close-add-product-modal",
                           outline=True, color="secondary", className="me-2"),
                dbc.Button("Add Product", id="owner-save-new-product",
                           n_clicks=0,
                           style={"background": "var(--primary)", "border": "none",
                                  "color": "#0F172A", "fontWeight": "600"}),
            ]),
        ], id="owner-add-product-modal", is_open=False),

        # ═══ EDIT PRICE MODAL ═════════════════════════════════════════════════
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle([
                html.I(className="bi bi-pencil-square me-2",
                       style={"color": "var(--primary)"}),
                "Edit Product Price",
            ])),
            dbc.ModalBody([
                dcc.Store(id="owner-edit-price-product-id"),
                html.Div(id="owner-edit-price-product-name", style={
                    "fontSize": "14px", "fontWeight": "600",
                    "color": "var(--text-primary)", "marginBottom": "16px",
                }),
                dbc.Label("New Price (₹) *"),
                dbc.Input(id="owner-edit-price-input", type="number",
                          min=1, step=1, placeholder="Enter new price",
                          className="custom-input"),
                html.Div(id="owner-edit-price-feedback", style={"marginTop": "8px"}),
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="owner-close-edit-price-modal",
                           outline=True, color="secondary", className="me-2"),
                dbc.Button("Update Price", id="owner-save-edit-price",
                           n_clicks=0,
                           style={"background": "var(--primary)", "border": "none",
                                  "color": "#0F172A", "fontWeight": "600"}),
            ]),
        ], id="owner-edit-price-modal", is_open=False),

        # ═══ RECIPE EDITOR MODAL ══════════════════════════════════════════════
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle([
                html.I(className="bi bi-journal-text me-2",
                       style={"color": "var(--primary)"}),
                "Recipe / Ingredients",
            ])),
            dbc.ModalBody([
                dcc.Store(id="owner-recipe-product-id"),
                dcc.Store(id="owner-recipe-working-store", data=[]),

                html.Div("Current Recipe", style={
                    "fontSize": "11px", "fontWeight": "600",
                    "textTransform": "uppercase", "letterSpacing": "0.5px",
                    "color": "var(--text-muted)", "marginBottom": "8px",
                }),
                html.Div(id="owner-recipe-current-display"),
                html.Hr(style={"borderColor": "var(--border-light)", "margin": "16px 0"}),

                html.Div("Add / Update Ingredient", style={
                    "fontSize": "11px", "fontWeight": "600",
                    "textTransform": "uppercase", "letterSpacing": "0.5px",
                    "color": "var(--text-muted)", "marginBottom": "10px",
                }),
                dbc.Row([
                    dbc.Col([
                        dcc.Dropdown(id="owner-recipe-material-select",
                                     placeholder="Select ingredient…",
                                     style={"fontSize": "12px"}),
                    ], md=5),
                    dbc.Col([
                        dbc.Input(id="owner-recipe-qty-input", type="number",
                                  min=0.01, step=0.01, placeholder="Qty",
                                  className="custom-input"),
                    ], md=3),
                    dbc.Col([
                        dbc.Button("+ Add", id="owner-recipe-add-ingredient-btn",
                                   n_clicks=0, style={
                                       "background": "var(--primary)", "border": "none",
                                       "color": "#0F172A", "fontWeight": "600",
                                       "width": "100%",
                                   }),
                    ], md=4),
                ], className="g-2 mb-3"),

                html.Div(id="owner-recipe-working-display"),
                html.Div(id="owner-recipe-save-feedback", style={"marginTop": "8px"}),
            ]),
            dbc.ModalFooter([
                dbc.Button("Close", id="owner-close-recipe-modal",
                           outline=True, color="secondary", className="me-2"),
                dbc.Button("Save Recipe", id="owner-save-recipe-btn",
                           n_clicks=0,
                           style={"background": "var(--primary)", "border": "none",
                                  "color": "#0F172A", "fontWeight": "600"}),
            ]),
        ], id="owner-recipe-modal", is_open=False, size="lg"),

        # ═══ TOAST ════════════════════════════════════════════════════════════
        dbc.Toast(
            id="owner-menu-toast",
            header="",
            is_open=False,
            dismissable=True,
            duration=4000,
            style={"position": "fixed", "top": "80px", "right": "20px",
                   "zIndex": 9999, "minWidth": "300px"},
        ),

        # FAB — always in DOM so its n_clicks is always wired
        html.Button(
            html.I(className="bi bi-plus"),
            id="owner-open-add-product-modal",
            n_clicks=0,
            className="fab-add-product",
            title="Add new product",
        ),
    ], className="page-content")
