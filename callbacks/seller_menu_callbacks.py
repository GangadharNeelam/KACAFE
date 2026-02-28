"""Seller Menu Reference callbacks — category → product → recipe drill-down."""
from dash import Input, Output, State, html, ctx, ALL
from dash.exceptions import PreventUpdate
import flask
from server import app
from services.menu_service import get_full_menu, get_product_recipe
from constants import ROLE_OWNER, ROLE_STAFF

# ── Category display metadata ─────────────────────────────────────────────────
_CAT_META: dict[str, dict] = {
    "Desi Teas":        {"icon": "bi-cup-hot-fill",       "color": "#A78BFA"},
    "Desi Coffee":      {"icon": "bi-cup-fill",            "color": "#FB923C"},
    "Water Based Teas": {"icon": "bi-droplet-fill",        "color": "#67E8F9"},
    "Ice Coffee":       {"icon": "bi-snow2",               "color": "#60A5FA"},
    "Hot Coffee":       {"icon": "bi-fire",                "color": "#F97316"},
    "Cold Coffee":      {"icon": "bi-thermometer-snow",    "color": "#34D399"},
    "Mocktails":        {"icon": "bi-stars",               "color": "#F472B6"},
    "Milkshake":        {"icon": "bi-cup-straw",           "color": "#FCD34D"},
    "Natural Juices":   {"icon": "bi-tree",                "color": "#4ADE80"},
    "Fruit Juices":     {"icon": "bi-basket2-fill",        "color": "#FB7185"},
    "Fruit Bowl":       {"icon": "bi-layers-fill",         "color": "#C084FC"},
}
_DEFAULT_META = {"icon": "bi-grid", "color": "#94A3B8"}


# ── Shared helpers ────────────────────────────────────────────────────────────

def _breadcrumb(crumbs: list) -> html.Div:
    """crumbs = [(label, nav_action_or_None), ...]  last item is plain text."""
    items = []
    for i, (label, action) in enumerate(crumbs):
        is_last = i == len(crumbs) - 1
        if action and not is_last:
            items.append(html.Button(
                label,
                id={"type": "seller-menu-nav", "action": action},
                n_clicks=0,
                style={
                    "background": "none", "border": "none",
                    "color": "var(--primary)", "cursor": "pointer",
                    "fontSize": "13px", "padding": "0", "fontWeight": "500",
                },
            ))
        else:
            items.append(html.Span(label, style={
                "fontSize": "13px",
                "color": "var(--text-primary)" if is_last else "var(--primary)",
                "fontWeight": "600",
            }))
        if not is_last:
            items.append(html.Span(
                " › ", style={"color": "var(--text-muted)", "margin": "0 6px"},
            ))
    return html.Div(items, style={
        "display": "flex", "alignItems": "center",
        "padding": "4px 0", "marginBottom": "16px",
    })


def _fmt_qty(qty: float) -> str:
    """Format quantity: whole numbers as int, decimals stripped of trailing zeros."""
    return f"{qty:g}"


# ── View renderers ────────────────────────────────────────────────────────────

def _render_categories(menu_df) -> html.Div:
    cats = (
        menu_df.groupby("category")
        .size()
        .reset_index(name="count")
        .sort_values("category")
    )
    tiles = []
    for _, row in cats.iterrows():
        cat  = row["category"]
        cnt  = int(row["count"])
        meta = _CAT_META.get(cat, _DEFAULT_META)
        col  = meta["color"]
        tiles.append(
            html.Button([
                html.I(className=f"bi {meta['icon']}", style={
                    "fontSize": "30px", "color": col,
                    "display": "block", "marginBottom": "10px",
                }),
                html.Div(cat, style={
                    "fontSize": "13px", "fontWeight": "600",
                    "color": "var(--text-primary)", "marginBottom": "4px",
                    "lineHeight": "1.3",
                }),
                html.Div(
                    f"{cnt} item{'s' if cnt != 1 else ''}",
                    style={"fontSize": "11px", "color": "var(--text-muted)"},
                ),
            ],
            id={"type": "seller-cat-tile", "index": cat},
            n_clicks=0,
            style={
                "background": "var(--bg-card)",
                "border": f"1px solid {col}44",
                "borderRadius": "12px",
                "padding": "20px 14px",
                "width": "100%", "cursor": "pointer",
                "textAlign": "center",
                "transition": "border-color 0.2s",
            })
        )

    return html.Div([
        html.Div("Select a category to browse items", style={
            "fontSize": "13px", "color": "var(--text-muted)", "marginBottom": "16px",
        }),
        html.Div(tiles, style={
            "display": "grid",
            "gridTemplateColumns": "repeat(auto-fill, minmax(155px, 1fr))",
            "gap": "12px",
        }),
    ])


def _render_products(menu_df, category: str) -> html.Div:
    df = menu_df[menu_df["category"] == category].sort_values("name")
    meta = _CAT_META.get(category, _DEFAULT_META)
    col  = meta["color"]

    product_rows = []
    for _, row in df.iterrows():
        recipe_cnt = int(row.get("recipe_items", 0))
        product_rows.append(html.Button([
            html.Div([
                html.Span(row["name"], style={
                    "fontSize": "14px", "fontWeight": "500",
                    "color": "var(--text-primary)",
                }),
                html.Span(f"₹{row['price']:.0f}", style={
                    "fontFamily": "Space Mono", "fontSize": "13px",
                    "color": "var(--primary)", "fontWeight": "600",
                }),
            ], style={
                "display": "flex", "justifyContent": "space-between",
                "alignItems": "center", "width": "100%",
            }),
            html.Div([
                html.Span(
                    f"{recipe_cnt} ingredient{'s' if recipe_cnt != 1 else ''}",
                    style={"fontSize": "11px", "color": "var(--text-muted)"},
                ),
                html.I(className="bi bi-chevron-right",
                       style={"color": "var(--text-muted)", "fontSize": "11px"}),
            ], style={
                "display": "flex", "justifyContent": "space-between",
                "alignItems": "center", "width": "100%", "marginTop": "4px",
            }),
        ],
        id={"type": "seller-prod-row", "index": int(row["id"])},
        n_clicks=0,
        style={
            "display": "block", "background": "none", "border": "none",
            "borderBottom": "1px solid var(--border-light)",
            "padding": "14px 20px", "width": "100%",
            "cursor": "pointer", "textAlign": "left",
        }))

    return html.Div([
        _breadcrumb([("Menu", "home"), (category, None)]),
        html.Div([
            html.Div([
                html.I(className=f"bi {meta['icon']} me-2",
                       style={"color": col, "fontSize": "15px"}),
                html.Span(category, className="card-title-custom"),
                html.Span(f"{len(df)} items", style={
                    "marginLeft": "auto", "fontSize": "11px",
                    "color": "var(--text-muted)",
                }),
            ], className="card-header-custom",
               style={"borderLeft": f"3px solid {col}", "paddingLeft": "16px"}),
            html.Div(
                product_rows if product_rows else html.Div(
                    "No items found.",
                    style={"padding": "32px", "textAlign": "center",
                           "color": "var(--text-muted)"},
                )
            ),
        ], className="dash-card"),
    ])


def _render_recipe(menu_df, product_id: int) -> html.Div:
    rows = menu_df[menu_df["id"] == product_id]
    if rows.empty:
        return html.Div("Product not found.",
                        style={"color": "var(--text-muted)", "padding": "32px"})
    row      = rows.iloc[0]
    category = row["category"]
    meta     = _CAT_META.get(category, _DEFAULT_META)
    col      = meta["color"]

    recipe_df = get_product_recipe(product_id)

    # Build ingredient table
    if recipe_df.empty:
        ingr_body = html.Div("No recipe defined for this item.", style={
            "padding": "32px", "textAlign": "center", "color": "var(--text-muted)",
        })
    else:
        tbl_header = html.Div([
            html.Div("#", style={
                "width": "32px", "flexShrink": "0", "fontWeight": "600",
            }),
            html.Div("Ingredient", style={"flex": "3", "fontWeight": "600"}),
            html.Div("Quantity",   style={
                "flex": "1.5", "textAlign": "right", "fontWeight": "600",
            }),
            html.Div("Unit", style={"flex": "1", "fontWeight": "600"}),
        ], style={
            "display": "flex", "padding": "10px 20px",
            "fontSize": "11px", "fontWeight": "600", "letterSpacing": "0.5px",
            "textTransform": "uppercase", "color": "var(--text-muted)",
            "borderBottom": "1px solid var(--border-light)", "gap": "12px",
        })

        tbl_rows = [tbl_header]
        for i, (_, ing) in enumerate(recipe_df.iterrows(), 1):
            qty = ing["quantity_required"]
            tbl_rows.append(html.Div([
                html.Div(str(i), style={
                    "width": "32px", "flexShrink": "0",
                    "color": "var(--text-muted)", "fontSize": "12px",
                }),
                html.Div(ing["material_name"], style={
                    "flex": "3", "fontWeight": "500",
                    "color": "var(--text-primary)", "fontSize": "13px",
                }),
                html.Div(_fmt_qty(qty), style={
                    "flex": "1.5", "textAlign": "right",
                    "fontFamily": "Space Mono", "fontSize": "13px",
                    "color": col, "fontWeight": "600",
                }),
                html.Div(ing["unit"], style={
                    "flex": "1", "color": "var(--text-muted)", "fontSize": "12px",
                }),
            ], style={
                "display": "flex", "padding": "12px 20px",
                "borderBottom": "1px solid var(--border-light)",
                "gap": "12px", "alignItems": "center",
            }))

        ingr_body = html.Div(tbl_rows)

    desc = str(row.get("description") or "")

    return html.Div([
        _breadcrumb([
            ("Menu",     "home"),
            (category,   "back"),
            (row["name"], None),
        ]),

        # ── Product hero ──────────────────────────────────────────────────
        html.Div([
            html.Div([
                html.Div(
                    html.I(className=f"bi {meta['icon']}",
                           style={"fontSize": "32px", "color": col}),
                    style={
                        "background": f"{col}1A", "borderRadius": "12px",
                        "padding": "14px", "display": "flex",
                        "alignItems": "center", "justifyContent": "center",
                        "marginRight": "20px", "minWidth": "64px",
                    },
                ),
                html.Div([
                    html.Div(row["name"], style={
                        "fontSize": "20px", "fontWeight": "700",
                        "color": "var(--text-primary)", "marginBottom": "6px",
                    }),
                    html.Div([
                        html.Span(category, style={
                            "background": f"{col}22", "color": col,
                            "padding": "3px 10px", "borderRadius": "20px",
                            "fontSize": "11px", "fontWeight": "600",
                            "marginRight": "10px",
                        }),
                        html.Span(f"₹{row['price']:.0f}", style={
                            "fontFamily": "Space Mono", "fontSize": "16px",
                            "color": "var(--primary)", "fontWeight": "700",
                        }),
                    ]),
                    html.Div(desc, style={
                        "fontSize": "12px", "color": "var(--text-muted)",
                        "marginTop": "6px",
                    }) if desc else "",
                ]),
            ], style={"display": "flex", "alignItems": "flex-start",
                      "padding": "20px 20px 16px"}),
        ], className="dash-card mb-3"),

        # ── Recipe card ───────────────────────────────────────────────────
        html.Div([
            html.Div([
                html.I(className="bi bi-journal-text me-2",
                       style={"color": "var(--primary)"}),
                html.Span("Recipe / Ingredients", className="card-title-custom"),
                html.Span(
                    f"{len(recipe_df)} ingredient{'s' if len(recipe_df) != 1 else ''}"
                    " · per serving",
                    style={"marginLeft": "auto", "fontSize": "11px",
                           "color": "var(--text-muted)"},
                ),
            ], className="card-header-custom"),
            ingr_body,
        ], className="dash-card"),
    ])


# ── Callbacks ─────────────────────────────────────────────────────────────────

def register_callbacks():

    # 1) Update state on tile / product / nav-button clicks
    @app.callback(
        Output("seller-menu-state", "data"),
        [Input({"type": "seller-cat-tile",  "index": ALL}, "n_clicks"),
         Input({"type": "seller-prod-row",  "index": ALL}, "n_clicks"),
         Input({"type": "seller-menu-nav",  "action": ALL}, "n_clicks")],
        State("seller-menu-state", "data"),
        prevent_initial_call=True,
    )
    def update_menu_state(cat_clicks, prod_clicks, nav_clicks, state):
        if flask.session.get("role") not in (ROLE_STAFF, ROLE_OWNER):
            raise PreventUpdate

        triggered = ctx.triggered_id
        if not triggered or not isinstance(triggered, dict):
            raise PreventUpdate

        state = state or {"view": "categories", "category": None, "product_id": None}
        t = triggered.get("type")

        if t == "seller-cat-tile":
            return {**state, "view": "products", "category": triggered["index"]}

        if t == "seller-prod-row":
            return {**state, "view": "recipe", "product_id": triggered["index"]}

        if t == "seller-menu-nav":
            action = triggered.get("action")
            if action == "home":
                return {"view": "categories", "category": None, "product_id": None}
            if action == "back":
                # From recipe → go back to products list for same category
                return {**state, "view": "products", "product_id": None}

        raise PreventUpdate

    # 2) Render the content area from state
    @app.callback(
        Output("seller-menu-content", "children"),
        Input("seller-menu-state", "data"),
    )
    def render_menu_view(state):
        if flask.session.get("role") not in (ROLE_STAFF, ROLE_OWNER):
            raise PreventUpdate

        state    = state or {"view": "categories", "category": None, "product_id": None}
        view     = state.get("view", "categories")
        category = state.get("category")
        pid      = state.get("product_id")

        menu_df = get_full_menu()

        if view == "products" and category:
            return _render_products(menu_df, category)

        if view == "recipe" and pid is not None:
            return _render_recipe(menu_df, int(pid))

        # Default: categories grid
        return _render_categories(menu_df)
