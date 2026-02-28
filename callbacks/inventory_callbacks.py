"""Inventory page callbacks — Owner view matching seller inventory design with edit actions."""
import pandas as pd
from dash import Input, Output, State, html, ctx, ALL, no_update, dcc
from dash.exceptions import PreventUpdate
import flask
from server import app
from services.inventory_service import (
    get_inventory_df,
    get_inventory_df_with_category,
    get_at_risk_products,
    adjust_stock,
    MATERIAL_CATEGORIES,
)
from utils import fmt_inr
from constants import ROLE_OWNER

_STATUS_COLOR = {"OK": "#10B981", "Low": "#F59E0B", "Critical": "#EF4444"}
_STATUS_BG = {
    "OK":       "rgba(16,185,129,0.12)",
    "Low":      "rgba(245,158,11,0.12)",
    "Critical": "rgba(239,68,68,0.12)",
}


# ── Helper: At-Risk panel (reused from seller design) ────────────────────────

def _build_atrisk_panel(atrisk_df) -> html.Div:
    if atrisk_df.empty:
        return html.Div([
            html.I(className="bi bi-check-circle-fill me-2",
                   style={"color": "#10B981", "fontSize": "18px"}),
            html.Span("All menu items have sufficient stock.",
                      style={"color": "#10B981", "fontWeight": "500"}),
        ], style={"display": "flex", "alignItems": "center"})

    worst = (
        atrisk_df.groupby("product_name")["material_status"]
        .apply(lambda s: "Critical" if "Critical" in s.values else "Low")
        .reset_index()
        .rename(columns={"material_status": "worst_status"})
    )
    cats = atrisk_df[["product_name", "product_category"]].drop_duplicates()
    worst = worst.merge(cats, on="product_name").sort_values(["worst_status", "product_name"])

    chips = []
    for _, row in worst.iterrows():
        color = _STATUS_COLOR[row["worst_status"]]
        bg    = _STATUS_BG[row["worst_status"]]
        affected = atrisk_df[
            atrisk_df["product_name"] == row["product_name"]
        ]["material_name"].tolist()
        tooltip_text = f"{row['worst_status']}: {', '.join(affected)}"
        chips.append(html.Span([
            html.I(className="bi bi-cup-hot me-1", style={"fontSize": "10px"}),
            row["product_name"],
        ], title=tooltip_text, style={
            "display": "inline-flex", "alignItems": "center",
            "background": bg, "color": color,
            "border": f"1px solid {color}33",
            "padding": "4px 10px", "borderRadius": "20px",
            "fontSize": "12px", "fontWeight": "500",
            "margin": "3px", "cursor": "default",
        }))

    return html.Div([
        html.Div(chips, style={"display": "flex", "flexWrap": "wrap", "gap": "2px"}),
        html.Div(
            f"{len(worst)} item(s) affected — hover a chip to see which material is low.",
            style={"fontSize": "11px", "color": "var(--text-muted)", "marginTop": "10px"},
        ),
    ])


# ── Helper: Categorised inventory with Adjust button per row ─────────────────

def _build_categorized_inventory(df) -> html.Div:
    sections = []
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

        header = html.Div([
            html.Div("Material",  style={"flex": "2.2", "fontWeight": "600"}),
            html.Div("UOM",       style={"flex": "0.7"}),
            html.Div("Current",   style={"flex": "1.1", "textAlign": "right"}),
            html.Div("Safety",    style={"flex": "1.1", "textAlign": "right"}),
            html.Div("Days Left", style={"flex": "1",   "textAlign": "right"}),
            html.Div("Cost/Unit", style={"flex": "1",   "textAlign": "right"}),
            html.Div("Status",    style={"flex": "1.1", "textAlign": "center"}),
            html.Div("",          style={"flex": "2"}),   # progress bar
            html.Div("",          style={"flex": "1",   "textAlign": "right"}),  # adjust btn
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
            cost_str = fmt_inr(row["cost_per_unit"]) if row.get("cost_per_unit", 0) > 0 else "—"

            mat_rows.append(html.Div([
                html.Div(row["name"], style={
                    "flex": "2.2", "fontWeight": "500",
                    "color": "var(--text-primary)", "fontSize": "13px",
                }),
                html.Div(row["unit"], style={
                    "flex": "0.7", "color": "var(--text-muted)", "fontSize": "12px",
                }),
                html.Div(f"{row['current_stock']:.0f}", style={
                    "flex": "1.1", "textAlign": "right",
                    "fontFamily": "Space Mono", "fontSize": "13px",
                    "color": sc if row["status"] != "OK" else "var(--text-primary)",
                }),
                html.Div(f"{row['safety_stock']:.0f}", style={
                    "flex": "1.1", "textAlign": "right",
                    "fontFamily": "Space Mono", "fontSize": "12px",
                    "color": "var(--text-muted)",
                }),
                html.Div(
                    f"{row['days_remaining']:.0f}d"
                    if row["days_remaining"] < 999 else "∞",
                    style={
                        "flex": "1", "textAlign": "right",
                        "fontFamily": "Space Mono", "fontSize": "12px",
                        "color": sc if row["status"] != "OK" else "var(--text-muted)",
                    },
                ),
                html.Div(cost_str, style={
                    "flex": "1", "textAlign": "right",
                    "fontSize": "12px", "color": "var(--text-secondary)",
                }),
                html.Div(
                    html.Span(row["status"], style={
                        "background": sbg, "color": sc,
                        "padding": "3px 8px", "borderRadius": "20px",
                        "fontSize": "10px", "fontWeight": "600",
                    }),
                    style={"flex": "1.1", "display": "flex", "justifyContent": "center"},
                ),
                # Mini progress bar
                html.Div(
                    html.Div(style={
                        "width": f"{pct:.0f}%", "height": "6px",
                        "background": sc, "borderRadius": "3px",
                    }),
                    style={
                        "flex": "2", "background": "var(--bg-main)",
                        "borderRadius": "3px", "height": "6px",
                        "alignSelf": "center",
                    },
                ),
                # Adjust button
                html.Div(
                    html.Button(
                        [html.I(className="bi bi-pencil-square me-1"), "Adjust"],
                        id={"type": "owner-quick-adjust-btn", "index": int(row["id"])},
                        n_clicks=0,
                        className="owner-prod-action-btn",
                        style={"width": "auto", "padding": "3px 10px",
                               "fontSize": "11px", "fontWeight": "600",
                               "color": "var(--primary)",
                               "border": "1px solid rgba(45,212,191,0.3)"},
                    ),
                    style={"flex": "1", "display": "flex",
                           "justifyContent": "flex-end", "alignItems": "center"},
                ),
            ], style={
                "display": "flex", "padding": "10px 20px",
                "borderBottom": "1px solid var(--border-light)",
                "gap": "8px", "alignItems": "center",
            }))

        sections.append(
            html.Div([
                html.Div([
                    html.I(className=f"bi {cat_icon} me-2",
                           style={"color": cat_color, "fontSize": "15px"}),
                    html.Span(cat_name, className="card-title-custom"),
                    badge or "",
                    html.Span(f"{len(cat_df)} items",
                              style={"marginLeft": "auto", "fontSize": "11px",
                                     "color": "var(--text-muted)"}),
                ], className="card-header-custom",
                   style={"borderLeft": f"3px solid {cat_color}", "paddingLeft": "16px"}),
                html.Div(mat_rows),
            ], className="dash-card mb-3")
        )

    return html.Div(sections)


# ── Callback registration ─────────────────────────────────────────────────────

def register_callbacks():

    # ── Main inventory render (KPIs + at-risk + categorised) ─────────────────
    @app.callback(
        [Output("owner-inv-kpi-total",          "children"),
         Output("owner-inv-kpi-attention",      "children"),
         Output("owner-inv-kpi-atrisk",         "children"),
         Output("owner-inv-kpi-value",          "children"),
         Output("owner-atrisk-products",        "children"),
         Output("owner-inventory-categorized",  "children"),
         Output("adjust-material-dropdown",     "options")],
        Input("inventory-refresh", "n_intervals"),
    )
    def update_owner_inventory(_):
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate

        df        = get_inventory_df_with_category()
        atrisk_df = get_at_risk_products()

        total        = len(df)
        low_count    = len(df[df["status"].isin(["Low", "Critical"])])
        atrisk_count = int(atrisk_df["product_name"].nunique()) if not atrisk_df.empty else 0
        stock_value  = (df["current_stock"] * df.get("cost_per_unit", pd.Series([0]*len(df), index=df.index))).sum()

        low_color    = "#F59E0B" if low_count    else "#10B981"
        atrisk_color = "#EF4444" if atrisk_count else "#10B981"

        kpi_total     = html.Span(str(total),        style={"color": "#60A5FA"})
        kpi_attention = html.Span(str(low_count),    style={"color": low_color})
        kpi_atrisk    = html.Span(str(atrisk_count), style={"color": atrisk_color})
        kpi_value     = html.Span(fmt_inr(stock_value), style={
            "color": "#2DD4BF", "fontSize": "22px",
        })

        mat_options = [{"label": row["name"], "value": row["id"]}
                       for _, row in df.iterrows()]

        return (
            kpi_total,
            kpi_attention,
            kpi_atrisk,
            kpi_value,
            _build_atrisk_panel(atrisk_df),
            _build_categorized_inventory(df),
            mat_options,
        )

    # ── Quick Adjust button → open modal pre-populated ───────────────────────
    @app.callback(
        [Output("adjust-modal",           "is_open"),
         Output("adjust-material-dropdown", "value"),
         Output("owner-adjust-material-name", "children")],
        [Input({"type": "owner-quick-adjust-btn", "index": ALL}, "n_clicks"),
         Input("close-adjust-modal",  "n_clicks"),
         Input("apply-adjustment",    "n_clicks")],
        State("adjust-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_adjust_modal(quick_clicks, close_c, apply_c, is_open):
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        triggered = ctx.triggered_id
        if triggered in ("close-adjust-modal", "apply-adjustment"):
            return False, no_update, no_update
        if isinstance(triggered, dict) and triggered.get("type") == "owner-quick-adjust-btn":
            mid = triggered["index"]
            from database.db import get_connection
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute("SELECT name, unit FROM materials WHERE id=?", (mid,))
            row = cur.fetchone()
            conn.close()
            name_str = f"{row['name']} ({row['unit']})" if row else f"Material #{mid}"
            return True, mid, name_str
        raise PreventUpdate

    # ── Apply adjustment ──────────────────────────────────────────────────────
    @app.callback(
        [Output("inventory-toast", "children"),
         Output("inventory-toast", "header"),
         Output("inventory-toast", "is_open"),
         Output("inventory-toast", "icon")],
        Input("apply-adjustment", "n_clicks"),
        [State("adjust-material-dropdown", "value"),
         State("adjust-amount",            "value"),
         State("adjust-reason",            "value")],
        prevent_initial_call=True,
    )
    def apply_stock_adjustment(n, material_id, amount, reason):
        if not n or material_id is None or amount is None:
            return "Please select a material and enter an amount.", "Warning", True, "warning"
        result = adjust_stock(int(material_id), float(amount), reason or "Manual")
        return (
            result["message"],
            "Stock Adjusted" if result["success"] else "Error",
            True,
            "success" if result["success"] else "danger",
        )

    # ── Export CSV ────────────────────────────────────────────────────────────
    @app.callback(
        Output("download-inventory", "data"),
        Input("export-inventory-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def export_inventory(n):
        if not n:
            return no_update
        df = get_inventory_df()
        return dcc.send_data_frame(df.to_csv, "kafe_inventory.csv", index=False)
