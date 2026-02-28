"""Owner Menu Management callbacks — category drill-down with full CRUD editing."""
import time
from dash import Input, Output, State, html, ctx, ALL, no_update
from dash.exceptions import PreventUpdate
import flask
from server import app
from services.menu_service import (
    get_full_menu, get_product_recipe, get_categories,
    get_all_materials_for_recipe, add_product, update_product_price,
    toggle_product_active, save_recipe,
)
from constants import ROLE_OWNER

# ── Category display metadata (owner- prefix IDs; no conflict with seller) ───
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


def _ts() -> int:
    return int(time.time() * 1000)


def _fmt_qty(qty: float) -> str:
    return f"{qty:g}"


def _breadcrumb(crumbs: list) -> html.Div:
    items = []
    for i, (label, action) in enumerate(crumbs):
        is_last = i == len(crumbs) - 1
        if action and not is_last:
            items.append(html.Button(
                label,
                id={"type": "owner-menu-nav", "action": action},
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


# ── View renderers ────────────────────────────────────────────────────────────

def _render_owner_categories(menu_df) -> html.Div:
    cats = (
        menu_df.groupby("category")
        .size().reset_index(name="count")
        .sort_values("category")
    )
    tiles = []
    for _, row in cats.iterrows():
        cat  = row["category"]
        cnt  = int(row["count"])
        meta = _CAT_META.get(cat, _DEFAULT_META)
        col  = meta["color"]
        tiles.append(html.Button([
            html.I(className=f"bi {meta['icon']}", style={
                "fontSize": "30px", "color": col,
                "display": "block", "marginBottom": "10px",
            }),
            html.Div(cat, style={
                "fontSize": "13px", "fontWeight": "600",
                "color": "var(--text-primary)", "marginBottom": "4px",
                "lineHeight": "1.3",
            }),
            html.Div(f"{cnt} item{'s' if cnt != 1 else ''}",
                     style={"fontSize": "11px", "color": "var(--text-muted)"}),
        ],
        id={"type": "owner-cat-tile", "index": cat},
        n_clicks=0,
        style={
            "background": "var(--bg-card)",
            "border": f"1px solid {col}44",
            "borderRadius": "12px", "padding": "20px 14px",
            "width": "100%", "cursor": "pointer",
            "textAlign": "center", "transition": "border-color 0.2s",
        }))

    return html.Div([
        html.Div("Click a category to browse and edit items.", style={
            "fontSize": "13px", "color": "var(--text-muted)", "marginBottom": "16px",
        }),
        html.Div(tiles, style={
            "display": "grid",
            "gridTemplateColumns": "repeat(auto-fill, minmax(155px, 1fr))",
            "gap": "12px",
        }),
    ])


def _render_owner_products(menu_df, category: str) -> html.Div:
    df   = menu_df[menu_df["category"] == category].sort_values("name")
    meta = _CAT_META.get(category, _DEFAULT_META)
    col  = meta["color"]

    product_rows = []
    for _, row in df.iterrows():
        pid         = int(row["id"])
        is_active   = bool(row.get("is_active", 1))
        s_color     = "#10B981" if is_active else "#94A3B8"
        s_bg        = "rgba(16,185,129,0.12)" if is_active else "rgba(148,163,184,0.12)"
        s_label     = "Active" if is_active else "Inactive"
        tog_icon    = "bi-toggle-on" if is_active else "bi-toggle-off"

        product_rows.append(html.Button([
            html.Div([
                html.Div(row["name"], style={
                    "fontSize": "14px", "fontWeight": "500",
                    "color": "var(--text-primary)",
                }),
                html.Div([
                    html.Span(f"₹{row['price']:.0f}", style={
                        "fontFamily": "Space Mono", "fontSize": "13px",
                        "color": "var(--primary)", "fontWeight": "600",
                        "marginRight": "10px",
                    }),
                    html.Span(s_label, style={
                        "background": s_bg, "color": s_color,
                        "padding": "2px 8px", "borderRadius": "10px",
                        "fontSize": "10px", "fontWeight": "600",
                    }),
                ], style={"marginTop": "3px"}),
            ], style={"flex": "1", "textAlign": "left"}),
            html.Div([
                html.Button(
                    html.I(className=f"bi {tog_icon}"),
                    id={"type": "owner-toggle-active-btn", "index": pid},
                    n_clicks=0, className="owner-prod-action-btn",
                    title="Toggle active/inactive",
                ),
                html.I(className="bi bi-chevron-right",
                       style={"color": "var(--text-muted)", "fontSize": "12px",
                              "marginLeft": "8px"}),
            ], style={"display": "flex", "alignItems": "center",
                      "flexShrink": "0", "gap": "4px"}),
        ],
        id={"type": "owner-prod-row", "index": pid},
        n_clicks=0,
        style={
            "display": "flex", "alignItems": "center", "width": "100%",
            "background": "none", "border": "none",
            "borderBottom": "1px solid var(--border-light)",
            "padding": "12px 20px", "cursor": "pointer", "gap": "12px",
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
            html.Div(product_rows if product_rows else html.Div(
                "No items in this category.",
                style={"padding": "32px", "textAlign": "center",
                       "color": "var(--text-muted)"},
            )),
        ], className="dash-card"),
    ])


def _render_owner_recipe(menu_df, product_id: int) -> html.Div:
    rows = menu_df[menu_df["id"] == product_id]
    if rows.empty:
        return html.Div("Product not found.",
                        style={"padding": "32px", "color": "var(--text-muted)"})
    row       = rows.iloc[0]
    category  = row["category"]
    meta      = _CAT_META.get(category, _DEFAULT_META)
    col       = meta["color"]
    recipe_df = get_product_recipe(product_id)

    if recipe_df.empty:
        ingr_body = html.Div(
            "No recipe defined yet — click Edit Recipe to add ingredients.",
            style={"padding": "32px", "textAlign": "center",
                   "color": "var(--text-muted)"},
        )
    else:
        header = html.Div([
            html.Div("#",          style={"width": "32px", "flexShrink": "0", "fontWeight": "600"}),
            html.Div("Ingredient", style={"flex": "3", "fontWeight": "600"}),
            html.Div("Quantity",   style={"flex": "1.5", "textAlign": "right", "fontWeight": "600"}),
            html.Div("Unit",       style={"flex": "1", "fontWeight": "600"}),
        ], style={
            "display": "flex", "padding": "10px 20px",
            "fontSize": "11px", "fontWeight": "600", "letterSpacing": "0.5px",
            "textTransform": "uppercase", "color": "var(--text-muted)",
            "borderBottom": "1px solid var(--border-light)", "gap": "12px",
        })
        tbl = [header]
        for i, (_, ing) in enumerate(recipe_df.iterrows(), 1):
            tbl.append(html.Div([
                html.Div(str(i), style={"width": "32px", "flexShrink": "0",
                                        "color": "var(--text-muted)", "fontSize": "12px"}),
                html.Div(ing["material_name"], style={"flex": "3", "fontWeight": "500",
                                                      "color": "var(--text-primary)", "fontSize": "13px"}),
                html.Div(_fmt_qty(ing["quantity_required"]), style={
                    "flex": "1.5", "textAlign": "right",
                    "fontFamily": "Space Mono", "fontSize": "13px",
                    "color": col, "fontWeight": "600",
                }),
                html.Div(ing["unit"], style={"flex": "1", "color": "var(--text-muted)", "fontSize": "12px"}),
            ], style={
                "display": "flex", "padding": "12px 20px",
                "borderBottom": "1px solid var(--border-light)",
                "gap": "12px", "alignItems": "center",
            }))
        ingr_body = html.Div(tbl)

    desc      = str(row.get("description") or "")
    is_active = bool(row.get("is_active", 1))

    return html.Div([
        _breadcrumb([("Menu", "home"), (category, "back"), (row["name"], None)]),

        # Product hero
        html.Div([
            html.Div([
                html.Div(html.I(className=f"bi {meta['icon']}",
                                style={"fontSize": "32px", "color": col}),
                         style={"background": f"{col}1A", "borderRadius": "12px",
                                "padding": "14px", "display": "flex",
                                "alignItems": "center", "justifyContent": "center",
                                "marginRight": "20px", "minWidth": "64px"}),
                html.Div([
                    html.Div(row["name"], style={"fontSize": "20px", "fontWeight": "700",
                                                 "color": "var(--text-primary)", "marginBottom": "6px"}),
                    html.Div([
                        html.Span(category, style={"background": f"{col}22", "color": col,
                                                   "padding": "3px 10px", "borderRadius": "20px",
                                                   "fontSize": "11px", "fontWeight": "600", "marginRight": "8px"}),
                        html.Span(f"₹{row['price']:.0f}", style={"fontFamily": "Space Mono",
                                                                   "fontSize": "16px", "color": "var(--primary)",
                                                                   "fontWeight": "700", "marginRight": "8px"}),
                        html.Span("Active" if is_active else "Inactive", style={
                            "background": "rgba(16,185,129,0.12)" if is_active else "rgba(148,163,184,0.12)",
                            "color": "#10B981" if is_active else "#94A3B8",
                            "padding": "3px 8px", "borderRadius": "10px",
                            "fontSize": "10px", "fontWeight": "600",
                        }),
                        html.Button(
                            [html.I(className="bi bi-pencil-square me-1"), "Edit Price"],
                            id={"type": "owner-edit-price-btn", "index": product_id},
                            n_clicks=0,
                            style={"background": "rgba(45,212,191,0.1)",
                                   "border": "1px solid rgba(45,212,191,0.3)",
                                   "color": "var(--primary)", "borderRadius": "6px",
                                   "padding": "3px 10px", "fontSize": "11px",
                                   "fontWeight": "600", "cursor": "pointer",
                                   "marginLeft": "10px"},
                        ),
                    ]),
                    html.Div(desc, style={"fontSize": "12px", "color": "var(--text-muted)",
                                         "marginTop": "6px"}) if desc else "",
                ]),
            ], style={"display": "flex", "alignItems": "flex-start",
                      "padding": "20px 20px 16px"}),
        ], className="dash-card mb-3"),

        # Recipe card with Edit button in header
        html.Div([
            html.Div([
                html.I(className="bi bi-journal-text me-2",
                       style={"color": "var(--primary)"}),
                html.Span("Recipe / Ingredients", className="card-title-custom"),
                html.Span(
                    f"{len(recipe_df)} ingredient{'s' if len(recipe_df) != 1 else ''} · per serving",
                    style={"fontSize": "11px", "color": "var(--text-muted)", "marginRight": "auto"},
                ),
                html.Button([html.I(className="bi bi-pencil me-1"), "Edit Recipe"],
                            id="owner-open-recipe-modal", n_clicks=0,
                            style={"background": "rgba(45,212,191,0.1)",
                                   "border": "1px solid rgba(45,212,191,0.3)",
                                   "color": "var(--primary)", "borderRadius": "6px",
                                   "padding": "4px 12px", "fontSize": "12px",
                                   "fontWeight": "600", "cursor": "pointer"}),
            ], className="card-header-custom"),
            ingr_body,
        ], className="dash-card"),
    ])


# ── Callback registration ─────────────────────────────────────────────────────

def register_callbacks():

    # GROUP 1 — State router
    @app.callback(
        Output("owner-menu-state", "data"),
        [Input({"type": "owner-cat-tile",  "index": ALL}, "n_clicks"),
         Input({"type": "owner-prod-row",  "index": ALL}, "n_clicks"),
         Input({"type": "owner-menu-nav",  "action": ALL}, "n_clicks")],
        State("owner-menu-state", "data"),
        prevent_initial_call=True,
    )
    def update_owner_menu_state(cat_clicks, prod_clicks, nav_clicks, state):
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        triggered = ctx.triggered_id
        if not triggered or not isinstance(triggered, dict):
            raise PreventUpdate
        state = state or {"view": "categories", "category": None,
                          "product_id": None, "refresh_token": 0}
        t = triggered.get("type")
        if t == "owner-cat-tile":
            return {**state, "view": "products", "category": triggered["index"]}
        if t == "owner-prod-row":
            return {**state, "view": "recipe", "product_id": triggered["index"]}
        if t == "owner-menu-nav":
            action = triggered.get("action")
            if action == "home":
                return {**state, "view": "categories", "category": None, "product_id": None}
            if action == "back":
                return {**state, "view": "products", "product_id": None}
        raise PreventUpdate

    # GROUP 2 — Content renderer
    @app.callback(
        Output("owner-menu-content", "children"),
        Input("owner-menu-state", "data"),
    )
    def render_owner_menu_view(state):
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        state    = state or {"view": "categories", "category": None,
                             "product_id": None, "refresh_token": 0}
        view     = state.get("view", "categories")
        category = state.get("category")
        pid      = state.get("product_id")
        menu_df  = get_full_menu()
        if view == "products" and category:
            return _render_owner_products(menu_df, category)
        if view == "recipe" and pid is not None:
            return _render_owner_recipe(menu_df, int(pid))
        return _render_owner_categories(menu_df)

    # GROUP 3a-1 — Add Product modal open/close (resets form on open/close)
    @app.callback(
        [Output("owner-add-product-modal",    "is_open"),
         Output("owner-new-product-category", "options"),
         Output("owner-new-product-category", "value"),
         Output("owner-new-product-name",     "value"),
         Output("owner-new-product-price",    "value"),
         Output("owner-new-product-desc",     "value"),
         Output("owner-new-category-input",   "value"),
         Output("owner-new-category-row",     "style")],
        [Input("owner-open-add-product-modal",  "n_clicks"),
         Input("owner-close-add-product-modal", "n_clicks"),
         Input("owner-save-new-product",        "n_clicks")],
        prevent_initial_call=True,
    )
    def toggle_add_product_modal(open_n, close_n, save_n):
        triggered_id = ctx.triggered_id
        # Close modal — reset entire form
        if triggered_id in ("owner-close-add-product-modal", "owner-save-new-product"):
            return False, no_update, None, None, None, None, None, {"display": "none"}
        # Open modal — populate fresh category options and clear form
        cats = get_categories()
        opts = [{"label": c, "value": c} for c in cats]
        opts.append({"label": "✦ New category…", "value": "__new__"})
        return True, opts, None, None, None, None, None, {"display": "none"}

    # GROUP 3a-2 — Show/hide new-category text field when dropdown changes
    @app.callback(
        Output("owner-new-category-row", "style", allow_duplicate=True),
        Input("owner-new-product-category", "value"),
        prevent_initial_call=True,
    )
    def toggle_new_category_row(cat_val):
        return {"display": "block"} if cat_val == "__new__" else {"display": "none"}

    # GROUP 3b — Save new product
    @app.callback(
        [Output("owner-menu-toast", "children"),
         Output("owner-menu-toast", "header"),
         Output("owner-menu-toast", "is_open"),
         Output("owner-menu-toast", "icon"),
         Output("owner-menu-state", "data", allow_duplicate=True)],
        Input("owner-save-new-product", "n_clicks"),
        [State("owner-new-product-name",     "value"),
         State("owner-new-product-category", "value"),
         State("owner-new-category-input",   "value"),
         State("owner-new-product-price",    "value"),
         State("owner-new-product-desc",     "value"),
         State("owner-menu-state",           "data")],
        prevent_initial_call=True,
    )
    def save_owner_new_product(n, name, category, new_cat, price, desc, state):
        if not n:
            raise PreventUpdate
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        final_cat = (new_cat or "").strip() if category == "__new__" else (category or "").strip()
        if not name or not name.strip():
            return ("Product name is required.", "Validation Error", True, "warning", no_update)
        if not category:
            return ("Please select a category.", "Validation Error", True, "warning", no_update)
        if category == "__new__" and not final_cat:
            return ("Please type a name for the new category.", "Validation Error", True, "warning", no_update)
        if not price:
            return ("Price is required.", "Validation Error", True, "warning", no_update)
        result = add_product(name.strip(), final_cat, float(price), desc or "")
        if result["success"]:
            return (result["message"], "Product Added", True, "success",
                    {**(state or {}), "refresh_token": _ts()})
        return (result["message"], "Error", True, "danger", no_update)

    # GROUP 4a — Edit Price modal open/close
    @app.callback(
        [Output("owner-edit-price-modal",        "is_open"),
         Output("owner-edit-price-product-id",   "data"),
         Output("owner-edit-price-product-name", "children"),
         Output("owner-edit-price-input",        "value")],
        [Input({"type": "owner-edit-price-btn",  "index": ALL}, "n_clicks"),
         Input("owner-close-edit-price-modal",   "n_clicks"),
         Input("owner-save-edit-price",          "n_clicks")],
        [State({"type": "owner-edit-price-btn",  "index": ALL}, "id"),
         State("owner-edit-price-modal",         "is_open")],
        prevent_initial_call=True,
    )
    def toggle_edit_price_modal(btn_clicks, close_n, save_n, btn_ids, is_open):
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        triggered = ctx.triggered_id
        if triggered in ("owner-close-edit-price-modal", "owner-save-edit-price"):
            return False, no_update, no_update, no_update
        if isinstance(triggered, dict) and triggered.get("type") == "owner-edit-price-btn":
            pid     = triggered["index"]
            menu_df = get_full_menu()
            row     = menu_df[menu_df["id"] == pid]
            if row.empty:
                raise PreventUpdate
            row = row.iloc[0]
            return (True, pid,
                    f"{row['name']} — current price ₹{row['price']:.0f}",
                    row["price"])
        raise PreventUpdate

    # GROUP 4b — Save price
    @app.callback(
        [Output("owner-menu-toast", "children",  allow_duplicate=True),
         Output("owner-menu-toast", "header",    allow_duplicate=True),
         Output("owner-menu-toast", "is_open",   allow_duplicate=True),
         Output("owner-menu-toast", "icon",      allow_duplicate=True),
         Output("owner-menu-state", "data",      allow_duplicate=True)],
        Input("owner-save-edit-price", "n_clicks"),
        [State("owner-edit-price-product-id", "data"),
         State("owner-edit-price-input",      "value"),
         State("owner-menu-state",            "data")],
        prevent_initial_call=True,
    )
    def save_owner_price(n, product_id, price, state):
        if not n:
            raise PreventUpdate
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        if product_id is None or price is None:
            return ("Select a product and enter a price.", "Validation Error",
                    True, "warning", no_update)
        result = update_product_price(int(product_id), float(price))
        if result["success"]:
            return (result["message"], "Price Updated", True, "success",
                    {**(state or {}), "refresh_token": _ts()})
        return (result["message"], "Error", True, "danger", no_update)

    # GROUP 5 — Toggle active/inactive
    @app.callback(
        [Output("owner-menu-toast", "children",  allow_duplicate=True),
         Output("owner-menu-toast", "header",    allow_duplicate=True),
         Output("owner-menu-toast", "is_open",   allow_duplicate=True),
         Output("owner-menu-toast", "icon",      allow_duplicate=True),
         Output("owner-menu-state", "data",      allow_duplicate=True)],
        Input({"type": "owner-toggle-active-btn", "index": ALL}, "n_clicks"),
        [State({"type": "owner-toggle-active-btn", "index": ALL}, "id"),
         State("owner-menu-state", "data")],
        prevent_initial_call=True,
    )
    def toggle_owner_product_active(btn_clicks, btn_ids, state):
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        triggered = ctx.triggered_id
        if not isinstance(triggered, dict):
            raise PreventUpdate
        pid = triggered.get("index")
        if pid is None:
            raise PreventUpdate
        from database.db import get_connection
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT is_active, name FROM products WHERE id=?", (pid,))
        row  = cur.fetchone()
        conn.close()
        if not row:
            raise PreventUpdate
        new_status = 0 if row["is_active"] else 1
        result     = toggle_product_active(int(pid), new_status)
        action     = "activated" if new_status else "deactivated"
        if result["success"]:
            return (f"{row['name']} {action}.", f"Product {action.capitalize()}",
                    True, "success", {**(state or {}), "refresh_token": _ts()})
        return (result["message"], "Error", True, "danger", no_update)

    # GROUP 6a — Recipe modal open/close + populate
    @app.callback(
        [Output("owner-recipe-modal",           "is_open"),
         Output("owner-recipe-product-id",      "data"),
         Output("owner-recipe-current-display", "children"),
         Output("owner-recipe-material-select", "options"),
         Output("owner-recipe-working-store",   "data")],
        [Input("owner-open-recipe-modal",  "n_clicks"),
         Input("owner-close-recipe-modal", "n_clicks"),
         Input("owner-save-recipe-btn",    "n_clicks")],
        [State("owner-recipe-modal",  "is_open"),
         State("owner-menu-state",    "data")],
        prevent_initial_call=True,
    )
    def toggle_recipe_modal(open_n, close_n, save_n, is_open, menu_state):
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        triggered_id = ctx.triggered_id
        if triggered_id in ("owner-close-recipe-modal", "owner-save-recipe-btn"):
            return False, no_update, no_update, no_update, no_update

        pid = (menu_state or {}).get("product_id")
        if pid is None:
            raise PreventUpdate
        pid = int(pid)

        recipe_df   = get_product_recipe(pid)
        mat_df      = get_all_materials_for_recipe()
        mat_options = [{"label": f"{r['name']} ({r['unit']})", "value": r["id"]}
                       for _, r in mat_df.iterrows()]

        if recipe_df.empty:
            current_display = html.Div("No ingredients yet.",
                                       style={"color": "var(--text-muted)", "fontSize": "13px"})
            working_data = []
        else:
            rows_html = [html.Div([
                html.Span(r["material_name"], style={"flex": "1", "fontSize": "13px",
                                                     "color": "var(--text-primary)"}),
                html.Span(f"{_fmt_qty(r['quantity_required'])} {r['unit']}",
                          style={"fontFamily": "Space Mono", "fontSize": "12px",
                                 "color": "var(--primary)", "marginLeft": "12px"}),
            ], style={"display": "flex", "padding": "6px 0",
                      "borderBottom": "1px solid var(--border-light)"})
                for _, r in recipe_df.iterrows()]
            current_display = html.Div(rows_html)
            working_data = [
                {"material_id": int(r["material_id"]),
                 "quantity": float(r["quantity_required"]),
                 "name": r["material_name"], "unit": r["unit"]}
                for _, r in recipe_df.iterrows()
            ]

        return True, pid, current_display, mat_options, working_data

    # GROUP 6b — Add ingredient to working list
    @app.callback(
        [Output("owner-recipe-working-store",   "data", allow_duplicate=True),
         Output("owner-recipe-working-display", "children")],
        Input("owner-recipe-add-ingredient-btn", "n_clicks"),
        [State("owner-recipe-material-select", "value"),
         State("owner-recipe-qty-input",       "value"),
         State("owner-recipe-working-store",   "data"),
         State("owner-recipe-material-select", "options")],
        prevent_initial_call=True,
    )
    def owner_add_ingredient(n, material_id, qty, working, mat_options):
        if not n or material_id is None or not qty:
            raise PreventUpdate
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate

        mat_label = next(
            (o["label"] for o in (mat_options or []) if o["value"] == material_id),
            str(material_id),
        )
        mat_name, mat_unit = mat_label, ""
        if "(" in mat_label and mat_label.endswith(")"):
            parts    = mat_label.rsplit("(", 1)
            mat_name = parts[0].strip()
            mat_unit = parts[1].rstrip(")")

        working = [w for w in (working or []) if w["material_id"] != material_id]
        working.append({"material_id": int(material_id), "quantity": float(qty),
                        "name": mat_name, "unit": mat_unit})

        rows_html = [html.Div([
            html.Span(item["name"], style={"flex": "1", "fontSize": "13px",
                                           "color": "var(--text-primary)"}),
            html.Span(f"{_fmt_qty(item['quantity'])} {item['unit']}",
                      style={"fontFamily": "Space Mono", "fontSize": "12px",
                             "color": "var(--primary)", "marginLeft": "12px"}),
        ], style={"display": "flex", "padding": "6px 0",
                  "borderBottom": "1px solid var(--border-light)"})
            for item in sorted(working, key=lambda x: x["name"])]

        display = html.Div([
            html.Div("Pending changes", style={
                "fontSize": "11px", "color": "var(--text-muted)",
                "fontWeight": "600", "marginBottom": "6px",
                "textTransform": "uppercase",
            }),
            html.Div(rows_html),
        ]) if rows_html else html.Div()
        return working, display

    # GROUP 6c — Save recipe
    @app.callback(
        [Output("owner-recipe-save-feedback", "children"),
         Output("owner-menu-toast", "children",  allow_duplicate=True),
         Output("owner-menu-toast", "header",    allow_duplicate=True),
         Output("owner-menu-toast", "is_open",   allow_duplicate=True),
         Output("owner-menu-toast", "icon",      allow_duplicate=True),
         Output("owner-menu-state", "data",      allow_duplicate=True)],
        Input("owner-save-recipe-btn", "n_clicks"),
        [State("owner-recipe-product-id",    "data"),
         State("owner-recipe-working-store", "data"),
         State("owner-menu-state",           "data")],
        prevent_initial_call=True,
    )
    def owner_save_recipe(n, product_id, working, state):
        if not n:
            raise PreventUpdate
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        if not product_id or not working:
            msg = html.Div("No ingredients to save.", style={"color": "var(--danger)"})
            return msg, no_update, no_update, no_update, no_update, no_update
        ingredients = [{"material_id": w["material_id"], "quantity": w["quantity"]}
                       for w in working]
        result = save_recipe(int(product_id), ingredients)
        if result["success"]:
            return (
                html.Div(result["message"], style={"color": "var(--success)"}),
                result["message"], "Recipe Saved", True, "success",
                {**(state or {}), "refresh_token": _ts()},
            )
        return (
            html.Div(result["message"], style={"color": "var(--danger)"}),
            result["message"], "Error", True, "danger", no_update,
        )
