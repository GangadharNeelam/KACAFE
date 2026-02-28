"""Procurement and vendor management callbacks — partial delivery support."""
import json
import flask
from dash import Input, Output, State, html, no_update, ALL, callback_context
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from server import app
from services.procurement_service import (
    get_vendors_df, get_purchase_orders_df, create_purchase_order,
    update_po_delivery, cancel_po, add_vendor, delete_vendor,
    get_vendor_materials, PO_STATUSES,
)
from utils import fmt_inr
from constants import ROLE_OWNER

STATUS_COLORS = {
    "Initiated":           "#94A3B8",
    "Partially Delivered": "#F59E0B",
    "Delivered":           "#10B981",
    "Cancelled":           "#EF4444",
    "Draft":               "#94A3B8",
    "Ordered":             "#3B82F6",
    "In Transit":          "#F59E0B",
}


def register_callbacks():

    # ── PO Table ──────────────────────────────────────────────────────────
    @app.callback(
        [Output("po-table-container", "children"),
         Output("po-count-badge", "children")],
        [Input("po-status-filter", "value"),
         Input("procurement-refresh", "n_intervals")],
    )
    def update_po_table(status_filter, _):
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        df = get_purchase_orders_df()
        total = len(df)

        if status_filter != "All":
            df = df[df["status"] == status_filter]

        if df.empty:
            return (
                html.Div("No purchase orders found.",
                         style={"padding": "32px", "textAlign": "center",
                                "color": "var(--text-muted)"}),
                html.Span(f"{total} total",
                          style={"fontSize": "12px", "color": "var(--text-muted)"}),
            )

        header = html.Div([
            html.Div("PO #",       style={"flex": "1.2", "fontWeight": "600"}),
            html.Div("Vendor",     style={"flex": "2"}),
            html.Div("Material",   style={"flex": "1.8"}),
            html.Div("Ordered",    style={"flex": "0.8", "textAlign": "right"}),
            html.Div("Received",   style={"flex": "0.8", "textAlign": "right"}),
            html.Div("Remaining",  style={"flex": "0.8", "textAlign": "right"}),
            html.Div("Status",     style={"flex": "1.3", "textAlign": "center"}),
            html.Div("Actions",    style={"flex": "1.8", "textAlign": "center"}),
        ], style={"display": "flex", "padding": "12px 20px",
                  "fontSize": "11px", "fontWeight": "600", "letterSpacing": "0.5px",
                  "textTransform": "uppercase", "color": "var(--text-muted)",
                  "borderBottom": "1px solid var(--border-light)", "gap": "8px"})

        rows = [header]
        for _, row in df.iterrows():
            sc = STATUS_COLORS.get(row["status"], "#94A3B8")
            qty_ordered   = float(row.get("qty_ordered", 0) or 0)
            qty_delivered = float(row.get("qty_delivered", 0) or 0)
            remaining     = float(row.get("remaining_qty", 0) or 0)

            # Build vendor cell with call link
            vendor_name = row["vendor_name"]
            vendor_cell = html.Div([
                html.Div(vendor_name,
                         style={"fontSize": "12px", "fontWeight": "600",
                                "color": "var(--text-primary)"}),
            ])
            try:
                vdf = get_vendors_df()
                vmatch = vdf[vdf["name"] == vendor_name]
                if not vmatch.empty:
                    phone = vmatch.iloc[0]["phone"] or ""
                    if phone:
                        clean = phone.replace(" ", "").replace("-", "")
                        vendor_cell = html.Div([
                            html.Div(vendor_name,
                                     style={"fontSize": "12px", "fontWeight": "600",
                                            "color": "var(--text-primary)"}),
                            html.A(
                                [html.I(className="bi bi-telephone-fill me-1"), phone],
                                href=f"tel:{clean}",
                                style={"fontSize": "10px", "color": "var(--primary)",
                                       "textDecoration": "none",
                                       "display": "inline-flex",
                                       "alignItems": "center"},
                            ),
                        ])
            except Exception:
                pass

            can_receive = row["status"] not in ("Delivered", "Cancelled")
            can_cancel  = row["status"] not in ("Delivered", "Cancelled")

            rows.append(html.Div([
                html.Div(row["po_number"],
                         style={"flex": "1.2", "fontFamily": "Space Mono",
                                "fontSize": "11px", "color": "var(--primary)"}),
                html.Div(vendor_cell, style={"flex": "2"}),
                html.Div(row["material_name"],
                         style={"flex": "1.8", "fontSize": "12px",
                                "color": "var(--text-secondary)"}),
                html.Div(f"{qty_ordered:.0f}",
                         style={"flex": "0.8", "textAlign": "right",
                                "fontFamily": "Space Mono", "fontSize": "12px"}),
                html.Div(f"{qty_delivered:.0f}",
                         style={"flex": "0.8", "textAlign": "right",
                                "fontFamily": "Space Mono", "fontSize": "12px",
                                "color": "var(--success)"}),
                html.Div(f"{remaining:.0f}",
                         style={"flex": "0.8", "textAlign": "right",
                                "fontFamily": "Space Mono", "fontSize": "12px",
                                "color": "var(--warning)" if remaining > 0
                                         else "var(--text-muted)"}),
                html.Div(
                    html.Span(row["status"],
                              style={"background": f"{sc}22", "color": sc,
                                     "border": f"1px solid {sc}44",
                                     "padding": "3px 8px", "borderRadius": "20px",
                                     "fontSize": "10px", "fontWeight": "600",
                                     "whiteSpace": "nowrap"}),
                    style={"flex": "1.3", "display": "flex",
                           "justifyContent": "center", "alignItems": "center"},
                ),
                html.Div([
                    dbc.Button(
                        [html.I(className="bi bi-box-arrow-in-down me-1"), "Receive"],
                        id={"type": "receive-delivery-btn", "index": row["id"]},
                        size="sm",
                        disabled=not can_receive,
                        style={"background": "var(--success)" if can_receive
                                             else "transparent",
                               "border": "none" if can_receive
                                          else "1px solid var(--border-light)",
                               "color": "#fff" if can_receive else "var(--text-muted)",
                               "fontSize": "11px"},
                        n_clicks=0,
                    ),
                    dbc.Button(
                        html.I(className="bi bi-x-circle"),
                        id={"type": "cancel-po-btn", "index": row["id"]},
                        size="sm",
                        disabled=not can_cancel,
                        color="danger",
                        outline=True,
                        style={"fontSize": "11px"},
                        n_clicks=0,
                    ),
                ], style={"flex": "1.8", "display": "flex", "gap": "4px",
                          "justifyContent": "center", "alignItems": "center"}),
            ], style={"display": "flex", "padding": "10px 20px",
                      "borderBottom": "1px solid var(--border-light)",
                      "gap": "8px", "alignItems": "center"}))

        return html.Div(rows), html.Span(
            f"{total} total",
            style={"fontSize": "12px", "color": "var(--text-muted)"}
        )

    # ── Delivery Modal open ───────────────────────────────────────────────
    @app.callback(
        [Output("delivery-modal", "is_open"),
         Output("delivery-po-id", "data"),
         Output("delivery-po-info", "children")],
        [Input({"type": "receive-delivery-btn", "index": ALL}, "n_clicks"),
         Input("close-delivery-modal", "n_clicks"),
         Input("save-delivery", "n_clicks")],
        [State({"type": "receive-delivery-btn", "index": ALL}, "id"),
         State("delivery-modal", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_delivery_modal(btn_clicks, close_n, save_n, btn_ids, is_open):
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        triggered = ctx.triggered[0]["prop_id"]
        if "close-delivery-modal" in triggered or "save-delivery" in triggered:
            return False, no_update, no_update
        try:
            btn_data = json.loads(triggered.split(".")[0])
            po_id = btn_data["index"]
        except Exception:
            raise PreventUpdate

        from database.db import get_connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM purchase_orders WHERE id=?", (po_id,))
        po = cur.fetchone()
        conn.close()
        if not po:
            raise PreventUpdate

        qty_remaining = float(po["remaining_qty"] or po.get("qty_ordered", 0) or 0)
        info = html.Div([
            html.Div(f"PO: {po['po_number']}  —  {po['material_name']}",
                     style={"fontWeight": "600", "marginBottom": "4px"}),
            html.Div(
                f"Ordered: {po.get('qty_ordered', 0) or 0:.0f}  ·  "
                f"Received so far: {po.get('qty_delivered', 0) or 0:.0f}  ·  "
                f"Still expected: {qty_remaining:.0f}",
                style={"color": "var(--text-muted)", "fontSize": "12px"}
            ),
        ])
        return True, po_id, info

    # ── Save Delivery ─────────────────────────────────────────────────────
    @app.callback(
        [Output("po-toast", "children"),
         Output("po-toast", "header"),
         Output("po-toast", "is_open"),
         Output("po-toast", "icon"),
         Output("procurement-refresh", "n_intervals")],
        Input("save-delivery", "n_clicks"),
        [State("delivery-po-id", "data"),
         State("delivery-qty-input", "value"),
         State("procurement-refresh", "n_intervals")],
        prevent_initial_call=True,
    )
    def save_delivery(n, po_id, qty_received, n_intervals):
        if not n or not po_id or not qty_received:
            return "Fill all fields", "Validation Error", True, "warning", n_intervals
        result = update_po_delivery(int(po_id), float(qty_received))
        return (
            result["message"],
            "Delivery Recorded" if result["success"] else "Error",
            True,
            "success" if result["success"] else "danger",
            (n_intervals or 0) + 1,
        )

    # ── Cancel PO ─────────────────────────────────────────────────────────
    @app.callback(
        [Output("po-toast", "children", allow_duplicate=True),
         Output("po-toast", "header", allow_duplicate=True),
         Output("po-toast", "is_open", allow_duplicate=True),
         Output("po-toast", "icon", allow_duplicate=True),
         Output("procurement-refresh", "n_intervals", allow_duplicate=True)],
        Input({"type": "cancel-po-btn", "index": ALL}, "n_clicks"),
        [State({"type": "cancel-po-btn", "index": ALL}, "id"),
         State("procurement-refresh", "n_intervals")],
        prevent_initial_call=True,
    )
    def handle_cancel_po(n_clicks_list, btn_ids, n_intervals):
        ctx = callback_context
        if not ctx.triggered or not any(n for n in (n_clicks_list or []) if n):
            raise PreventUpdate
        triggered = ctx.triggered[0]["prop_id"]
        try:
            btn_data = json.loads(triggered.split(".")[0])
            po_id = btn_data["index"]
        except Exception:
            raise PreventUpdate
        result = cancel_po(int(po_id))
        return (
            result["message"],
            "PO Cancelled" if result["success"] else "Error",
            True,
            "success" if result["success"] else "danger",
            (n_intervals or 0) + 1,
        )

    # ── Create PO Modal ───────────────────────────────────────────────────
    @app.callback(
        Output("po-modal", "is_open"),
        [Input("open-po-modal", "n_clicks"),
         Input("close-po-modal", "n_clicks"),
         Input("save-po", "n_clicks")],
        State("po-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_po_modal(open_c, close_c, save_c, is_open):
        return not is_open

    @app.callback(
        Output("po-vendor", "options"),
        Input("po-modal", "is_open"),
    )
    def populate_vendor_options(is_open):
        if not is_open:
            return []
        df = get_vendors_df()
        return [
            {"label": f"{r['name']}  📞 {r['phone'] or '—'}", "value": r["id"]}
            for _, r in df.iterrows()
        ]

    @app.callback(
        Output("po-material", "options"),
        Input("po-vendor", "value"),
    )
    def populate_material_options(vendor_id):
        if not vendor_id:
            return []
        vm = get_vendor_materials(vendor_id)
        return [
            {"label": f"{r['material_name']} ({r['unit']}) — {fmt_inr(r['price_per_unit'])}/unit",
             "value": r["material_id"]}
            for _, r in vm.iterrows()
        ]

    @app.callback(
        [Output("po-toast", "children", allow_duplicate=True),
         Output("po-toast", "header", allow_duplicate=True),
         Output("po-toast", "is_open", allow_duplicate=True),
         Output("po-toast", "icon", allow_duplicate=True)],
        Input("save-po", "n_clicks"),
        [State("po-vendor", "value"), State("po-material", "value"),
         State("po-quantity", "value"), State("po-unit-cost", "value"),
         State("po-delivery-date", "value"), State("po-notes", "value")],
        prevent_initial_call=True,
    )
    def save_po(n, vendor_id, material_id, quantity, unit_cost, delivery_date, notes):
        if not n:
            return no_update, no_update, False, no_update
        if not all([vendor_id, material_id, quantity]):
            return "Fill all required fields", "Validation Error", True, "warning"
        result = create_purchase_order(
            vendor_id, material_id, float(quantity),
            delivery_date,
            float(unit_cost) if unit_cost else 0.0,
            notes or "",
        )
        return (
            result["message"],
            "PO Created" if result["success"] else "Error",
            True,
            "success" if result["success"] else "danger",
        )

    # ── Vendors ───────────────────────────────────────────────────────────
    @app.callback(
        [Output("vendors-table-container", "children"),
         Output("vendor-stats", "children")],
        [Input("vendors-refresh", "n_intervals"),
         Input("save-vendor", "n_clicks")],
    )
    def update_vendors(_, __):
        df = get_vendors_df()
        if df.empty:
            table = html.Div("No vendors found.",
                             style={"padding": "32px", "textAlign": "center",
                                    "color": "var(--text-muted)"})
        else:
            header = html.Div([
                html.Div("Name",      style={"flex": "2",   "fontWeight": "600"}),
                html.Div("Phone",     style={"flex": "1.5"}),
                html.Div("Email",     style={"flex": "2"}),
                html.Div("Lead Time", style={"flex": "1",   "textAlign": "center"}),
                html.Div("Actions",   style={"flex": "1",   "textAlign": "center"}),
            ], style={"display": "flex", "padding": "12px 20px",
                      "fontSize": "11px", "fontWeight": "600", "letterSpacing": "0.5px",
                      "textTransform": "uppercase", "color": "var(--text-muted)",
                      "borderBottom": "1px solid var(--border-light)", "gap": "8px"})

            rows = [header]
            for _, row in df.iterrows():
                phone = row["phone"] or "—"
                clean = phone.replace(" ", "").replace("-", "") if phone != "—" else ""
                phone_el = html.A(
                    [html.I(className="bi bi-telephone me-1"), phone],
                    href=f"tel:{clean}", target="_blank",
                    style={"fontSize": "12px", "color": "var(--primary)",
                           "textDecoration": "none"},
                ) if phone != "—" else html.Span("—", style={"color":"var(--text-muted)"})

                rows.append(html.Div([
                    html.Div(row["name"],
                             style={"flex": "2", "fontWeight": "600",
                                    "fontSize": "13px", "color": "var(--text-primary)"}),
                    html.Div(phone_el, style={"flex": "1.5"}),
                    html.Div(row["email"] or "—",
                             style={"flex": "2", "fontSize": "12px",
                                    "color": "var(--text-muted)"}),
                    html.Div(f"{row['lead_time_days']}d",
                             style={"flex": "1", "textAlign": "center",
                                    "fontFamily": "Space Mono", "fontSize": "13px"}),
                    html.Div([
                        dbc.Button(
                            html.I(className="bi bi-trash"),
                            id={"type": "delete-vendor-btn", "index": row["id"]},
                            size="sm", color="danger", outline=True,
                            style={"fontSize": "11px"}, n_clicks=0,
                        ),
                    ], style={"flex": "1", "display": "flex",
                              "justifyContent": "center"}),
                ], style={"display": "flex", "padding": "12px 20px",
                          "borderBottom": "1px solid var(--border-light)",
                          "gap": "8px", "alignItems": "center"}))
            table = html.Div(rows)

        vm_df = get_vendor_materials()
        stats = html.Div([
            html.Div([
                html.Div("Total Vendors", className="kpi-label"),
                html.Div(str(len(df)), className="kpi-value", style={"fontSize": "22px"}),
            ], style={"marginBottom": "16px"}),
            html.Div([
                html.Div("Avg Lead Time", className="kpi-label"),
                html.Div(
                    f"{df['lead_time_days'].mean():.1f} days" if not df.empty else "—",
                    style={"fontFamily": "Space Mono", "fontSize": "18px",
                           "color": "var(--primary)"},
                ),
            ], style={"marginBottom": "16px"}),
            html.Div([
                html.Div("Material Links", className="kpi-label"),
                html.Div(str(len(vm_df)),
                         style={"fontFamily": "Space Mono", "fontSize": "18px",
                                "color": "var(--accent)"}),
            ]),
        ])
        return table, stats

    @app.callback(
        Output("vendor-modal", "is_open"),
        [Input("open-vendor-modal", "n_clicks"),
         Input("close-vendor-modal", "n_clicks"),
         Input("save-vendor", "n_clicks")],
        State("vendor-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_vendor_modal(open_c, close_c, save_c, is_open):
        return not is_open

    @app.callback(
        [Output("vendor-toast", "children"),
         Output("vendor-toast", "header"),
         Output("vendor-toast", "is_open"),
         Output("vendor-toast", "icon")],
        Input("save-vendor", "n_clicks"),
        [State("vendor-name", "value"), State("vendor-phone", "value"),
         State("vendor-email", "value"), State("vendor-lead-time", "value")],
        prevent_initial_call=True,
    )
    def save_vendor(n, name, phone, email, lead_time):
        if not n:
            return no_update, no_update, False, no_update
        if not name:
            return "Vendor name is required", "Validation Error", True, "warning"
        result = add_vendor(name, phone, email, int(lead_time or 3))
        return (
            result["message"],
            "Vendor Added" if result["success"] else "Error",
            True,
            "success" if result["success"] else "danger",
        )
