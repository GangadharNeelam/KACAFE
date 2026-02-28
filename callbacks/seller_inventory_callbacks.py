"""Seller Inventory monitoring — single comprehensive callback."""
from dash import Input, Output, html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import flask
from server import app
from services.inventory_service import (
    get_inventory_df_with_category,
    get_at_risk_products,
    MATERIAL_CATEGORIES,
)
from constants import ROLE_OWNER, ROLE_STAFF

# ── Shared status config ──────────────────────────────────────────────────────
_STATUS_COLOR  = {"OK": "#10B981", "Low": "#F59E0B", "Critical": "#EF4444"}
_STATUS_BG     = {
    "OK":       "rgba(16,185,129,0.12)",
    "Low":      "rgba(245,158,11,0.12)",
    "Critical": "rgba(239,68,68,0.12)",
}


# ── Helper: KPI value span ────────────────────────────────────────────────────
def _kpi_value(n: int, color: str) -> html.Span:
    return html.Span(str(n), style={"color": color})


# ── Helper: At-Risk Products panel body ──────────────────────────────────────
def _build_atrisk_panel(atrisk_df) -> html.Div:
    if atrisk_df.empty:
        return html.Div([
            html.I(className="bi bi-check-circle-fill me-2",
                   style={"color": "#10B981", "fontSize": "18px"}),
            html.Span("All menu items have sufficient stock.",
                      style={"color": "#10B981", "fontWeight": "500"}),
        ], style={"display": "flex", "alignItems": "center"})

    # For each product, pick its worst material_status
    worst = (
        atrisk_df.groupby("product_name")["material_status"]
        .apply(lambda s: "Critical" if "Critical" in s.values else "Low")
        .reset_index()
        .rename(columns={"material_status": "worst_status"})
    )
    # Merge to get product_category
    cats = atrisk_df[["product_name", "product_category"]].drop_duplicates()
    worst = worst.merge(cats, on="product_name")
    worst = worst.sort_values(["worst_status", "product_name"])

    chips = []
    for _, row in worst.iterrows():
        color = _STATUS_COLOR[row["worst_status"]]
        bg    = _STATUS_BG[row["worst_status"]]
        # Tooltip-like: show affected material names
        affected = atrisk_df[atrisk_df["product_name"] == row["product_name"]]["material_name"].tolist()
        tooltip_text = f"{row['worst_status']}: {', '.join(affected)}"
        chips.append(
            html.Span([
                html.I(className="bi bi-cup-hot me-1",
                       style={"fontSize": "10px"}),
                row["product_name"],
            ], title=tooltip_text, style={
                "display": "inline-flex", "alignItems": "center",
                "background": bg, "color": color,
                "border": f"1px solid {color}33",
                "padding": "4px 10px", "borderRadius": "20px",
                "fontSize": "12px", "fontWeight": "500",
                "margin": "3px", "cursor": "default",
            })
        )

    return html.Div([
        html.Div(chips, style={"display": "flex", "flexWrap": "wrap", "gap": "2px"}),
        html.Div(
            f"{len(worst)} item(s) affected — hover a chip to see which material is low.",
            style={"fontSize": "11px", "color": "var(--text-muted)",
                   "marginTop": "10px"},
        ),
    ])


# ── Helper: Categorised inventory section ────────────────────────────────────
def _build_categorized_inventory(df) -> html.Div:
    sections = []

    # Build ordered list: defined categories first, then "Other" if needed
    ordered_cats = list(MATERIAL_CATEGORIES.keys())
    if "Other" in df["category"].values:
        ordered_cats.append("Other")

    for cat_name in ordered_cats:
        cat_df = df[df["category"] == cat_name].copy()
        if cat_df.empty:
            continue

        cfg = MATERIAL_CATEGORIES.get(cat_name, {
            "icon": "bi-box", "color": "#94A3B8", "materials": [],
        })
        cat_color = cfg["color"]
        cat_icon  = cfg["icon"]

        # Sort: Critical first, then Low, then OK
        order_map = {"Critical": 0, "Low": 1, "OK": 2}
        cat_df["_ord"] = cat_df["status"].map(order_map)
        cat_df = cat_df.sort_values(["_ord", "name"])

        low_in_cat = len(cat_df[cat_df["status"].isin(["Low", "Critical"])])
        badge = None
        if low_in_cat:
            badge = html.Span(
                f"{low_in_cat} alert{'s' if low_in_cat > 1 else ''}",
                style={
                    "background": "rgba(239,68,68,0.15)",
                    "color": "#EF4444", "fontSize": "10px", "fontWeight": "600",
                    "padding": "2px 8px", "borderRadius": "10px", "marginLeft": "8px",
                }
            )

        # Table header
        header = html.Div([
            html.Div("Material",      style={"flex": "2.5", "fontWeight": "600"}),
            html.Div("UOM",           style={"flex": "0.7"}),
            html.Div("Current",       style={"flex": "1.2", "textAlign": "right"}),
            html.Div("Safety",        style={"flex": "1.2", "textAlign": "right"}),
            html.Div("Days Left",     style={"flex": "1",   "textAlign": "right"}),
            html.Div("Status",        style={"flex": "1.2", "textAlign": "center"}),
            html.Div("",              style={"flex": "3"}),   # progress bar column
        ], style={
            "display": "flex", "padding": "8px 20px",
            "fontSize": "10px", "fontWeight": "600", "letterSpacing": "0.5px",
            "textTransform": "uppercase", "color": "var(--text-muted)",
            "borderBottom": "1px solid var(--border-light)", "gap": "8px",
        })

        mat_rows = [header]
        for _, row in cat_df.iterrows():
            sc  = _STATUS_COLOR.get(row["status"], "#10B981")
            sbg = _STATUS_BG.get(row["status"], "rgba(16,185,129,0.12)")
            pct = min(100, (row["current_stock"] / max(row["safety_stock"], 1)) * 100)

            mat_rows.append(html.Div([
                html.Div(row["name"], style={
                    "flex": "2.5", "fontWeight": "500",
                    "color": "var(--text-primary)", "fontSize": "13px",
                }),
                html.Div(row["unit"], style={
                    "flex": "0.7", "color": "var(--text-muted)", "fontSize": "12px",
                }),
                html.Div(f"{row['current_stock']:.0f}", style={
                    "flex": "1.2", "textAlign": "right",
                    "fontFamily": "Space Mono", "fontSize": "13px",
                    "color": "var(--text-primary)",
                }),
                html.Div(f"{row['safety_stock']:.0f}", style={
                    "flex": "1.2", "textAlign": "right",
                    "fontFamily": "Space Mono", "fontSize": "12px",
                    "color": "var(--text-muted)",
                }),
                html.Div(f"{row['days_remaining']:.0f}d", style={
                    "flex": "1", "textAlign": "right",
                    "fontFamily": "Space Mono", "fontSize": "12px",
                    "color": sc if row["status"] != "OK" else "var(--text-muted)",
                }),
                html.Div(
                    html.Span(row["status"], style={
                        "background": sbg, "color": sc,
                        "padding": "3px 8px", "borderRadius": "20px",
                        "fontSize": "10px", "fontWeight": "600",
                    }),
                    style={"flex": "1.2", "display": "flex", "justifyContent": "center"},
                ),
                # Mini progress bar
                html.Div(
                    html.Div(style={
                        "width": f"{pct:.0f}%", "height": "6px",
                        "background": sc, "borderRadius": "3px",
                        "transition": "width 0.5s",
                    }),
                    style={
                        "flex": "3", "background": "var(--bg-main)",
                        "borderRadius": "3px", "height": "6px",
                        "alignSelf": "center",
                    },
                ),
            ], style={
                "display": "flex", "padding": "10px 20px",
                "borderBottom": "1px solid var(--border-light)",
                "gap": "8px", "alignItems": "center",
            }))

        sections.append(
            html.Div([
                # Category header
                html.Div([
                    html.I(className=f"bi {cat_icon} me-2",
                           style={"color": cat_color, "fontSize": "15px"}),
                    html.Span(cat_name, className="card-title-custom"),
                    badge or "",
                    html.Span(f"{len(cat_df)} items",
                              style={"marginLeft": "auto", "fontSize": "11px",
                                     "color": "var(--text-muted)"}),
                ], className="card-header-custom",
                   style={"borderLeft": f"3px solid {cat_color}",
                          "paddingLeft": "16px"}),
                html.Div(mat_rows),
            ], className="dash-card mb-3")
        )

    return html.Div(sections)


# ── Single comprehensive callback ─────────────────────────────────────────────
def register_callbacks():

    @app.callback(
        [Output("inv-kpi-total",               "children"),
         Output("inv-kpi-low",                 "children"),
         Output("inv-kpi-atrisk",              "children"),
         Output("seller-atrisk-products",      "children"),
         Output("seller-inventory-categorized","children")],
        Input("seller-inv-refresh", "n_intervals"),
    )
    def update_seller_inventory_full(_):
        if flask.session.get("role") not in (ROLE_STAFF, ROLE_OWNER):
            raise PreventUpdate

        df       = get_inventory_df_with_category()
        atrisk_df = get_at_risk_products()

        total        = len(df)
        low_count    = len(df[df["status"].isin(["Low", "Critical"])])
        atrisk_count = int(atrisk_df["product_name"].nunique()) if not atrisk_df.empty else 0

        low_color    = "#F59E0B" if low_count    else "#10B981"
        atrisk_color = "#EF4444" if atrisk_count else "#10B981"

        return (
            _kpi_value(total,        "#60A5FA"),
            _kpi_value(low_count,    low_color),
            _kpi_value(atrisk_count, atrisk_color),
            _build_atrisk_panel(atrisk_df),
            _build_categorized_inventory(df),
        )
