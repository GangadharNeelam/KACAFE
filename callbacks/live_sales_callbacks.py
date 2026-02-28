"""Live Sales Monitor callbacks — Owner only."""
import plotly.graph_objects as go
import pandas as pd
from dash import Input, Output, html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import flask
from server import app
from services.sales_service import get_today_sales, get_kpis, get_staff_tile_data
from utils import fmt_inr, CATEGORY_COLORS
from constants import ROLE_OWNER

CHART_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#94A3B8", size=11),
    margin=dict(l=16, r=16, t=16, b=16),
)

PAYMENT_COLORS = {
    "Cash": "#10B981",
    "UPI": "#3B82F6",
    "Card": "#F59E0B",
}

# One accent colour per seller name (cycles through palette)
_SELLER_PALETTE = [
    "#2DD4BF", "#A78BFA", "#FB923C", "#60A5FA",
    "#34D399", "#F472B6", "#FCD34D", "#67E8F9",
]


def _seller_color(name: str) -> str:
    idx = hash(name) % len(_SELLER_PALETTE)
    return _SELLER_PALETTE[idx]


def _initials(name: str) -> str:
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if name else "??"


def _tile_stat(label: str, value: str, icon: str) -> html.Div:
    """Mini stat block used inside each staff tile."""
    return html.Div([
        html.I(className=f"bi {icon}",
               style={"fontSize": "14px", "color": "var(--text-muted)",
                      "marginBottom": "4px"}),
        html.Div(value, style={
            "fontFamily": "Space Mono", "fontSize": "15px",
            "fontWeight": "700", "color": "var(--text-primary)",
        }),
        html.Div(label, style={
            "fontSize": "10px", "color": "var(--text-muted)",
            "textTransform": "uppercase", "letterSpacing": "0.5px",
        }),
    ], style={"textAlign": "center", "flex": "1"})


def _build_tile(seller: str, data: dict) -> html.Div:
    col = _seller_color(seller)
    initials = _initials(seller)

    # Top items rows
    top_rows = []
    for name, qty in data.get("top_items", []):
        top_rows.append(html.Div([
            html.Span(name, style={
                "fontSize": "11px", "color": "var(--text-secondary)",
                "flex": "1", "overflow": "hidden",
                "textOverflow": "ellipsis", "whiteSpace": "nowrap",
            }),
            html.Span(f"×{int(qty)}", style={
                "fontFamily": "Space Mono", "fontSize": "11px",
                "color": col, "fontWeight": "600", "flexShrink": "0",
                "marginLeft": "8px",
            }),
        ], style={"display": "flex", "alignItems": "center",
                  "padding": "3px 0", "borderBottom": "1px solid var(--border-light)"}))

    return html.Div([
        # Avatar + name row
        html.Div([
            html.Div(initials, style={
                "width": "42px", "height": "42px", "borderRadius": "50%",
                "background": f"{col}22", "border": f"2px solid {col}",
                "display": "flex", "alignItems": "center", "justifyContent": "center",
                "fontSize": "14px", "fontWeight": "700", "color": col,
                "marginRight": "12px", "flexShrink": "0",
            }),
            html.Div(seller.title(), style={
                "fontSize": "14px", "fontWeight": "600",
                "color": "var(--text-primary)",
            }),
        ], style={"display": "flex", "alignItems": "center",
                  "marginBottom": "14px"}),

        # Stats row
        html.Div([
            _tile_stat("Items",    str(data["items"]),  "bi-basket2"),
            html.Div(style={"width": "1px", "background": "var(--border-light)",
                            "margin": "0 4px"}),
            _tile_stat("Txns",     str(data["txns"]),   "bi-receipt-cutoff"),
            html.Div(style={"width": "1px", "background": "var(--border-light)",
                            "margin": "0 4px"}),
            _tile_stat("Revenue",  fmt_inr(data["revenue"]), "bi-currency-rupee"),
        ], style={"display": "flex", "alignItems": "center",
                  "background": "rgba(0,0,0,0.15)", "borderRadius": "8px",
                  "padding": "10px 6px", "marginBottom": "14px"}),

        # Top items section
        html.Div([
            html.Div("TOP ITEMS", style={
                "fontSize": "10px", "fontWeight": "600", "letterSpacing": "0.6px",
                "color": "var(--text-muted)", "marginBottom": "6px",
            }),
            html.Div(top_rows if top_rows else html.Div(
                "No items yet", style={"fontSize": "11px", "color": "var(--text-muted)"}
            )),
        ]),
    ], className="seller-tile-card",
       style={"borderTop": f"3px solid {col}"})


def register_callbacks():

    # ── Live sales KPIs ───────────────────────────────────────────────────
    @app.callback(
        Output("live-sales-kpis", "children"),
        Input("live-sales-refresh", "n_intervals"),
    )
    def update_live_kpis(_):
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        kpis = get_kpis(1)
        growth = kpis["revenue_growth"]
        delta_icon = "↑" if growth >= 0 else "↓"
        delta_color = "positive" if growth >= 0 else "negative"

        cards = [
            ("Today Revenue",  fmt_inr(kpis["total_revenue"]),
             f"{delta_icon} {abs(growth):.1f}% vs yesterday",
             delta_color, "bi-currency-rupee"),
            ("Items Sold",     str(kpis["total_items"]),      None, None, "bi-basket2"),
            ("Transactions",   str(kpis["num_transactions"]),  None, None, "bi-receipt-cutoff"),
            ("Top Category",   kpis["top_category"],           None, None, "bi-bar-chart"),
        ]

        cols = []
        for label, value, delta, d_color, icon in cards:
            cols.append(dbc.Col([
                html.Div([
                    html.I(className=f"bi {icon} kpi-icon"),
                    html.Div(label, className="kpi-label"),
                    html.Div(value, className="kpi-value"),
                    html.Div([html.Span(delta, className=f"kpi-delta {d_color}")]
                             if delta else []),
                ], className="kpi-card"),
            ], md=3))
        return dbc.Row(cols, className="g-3")

    # ── Seller filter options ─────────────────────────────────────────────
    @app.callback(
        Output("live-sales-seller-filter", "options"),
        Input("live-sales-refresh", "n_intervals"),
    )
    def update_seller_options(_):
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        df = get_today_sales()
        if df.empty or "seller_name" not in df.columns:
            return []
        sellers = df["seller_name"].dropna().unique().tolist()
        return [{"label": s.title(), "value": s} for s in sorted(sellers)]

    # ── Staff activity tiles ──────────────────────────────────────────────
    @app.callback(
        Output("seller-tiles-area", "children"),
        [Input("live-sales-refresh", "n_intervals"),
         Input("live-sales-seller-filter", "value")],
    )
    def update_seller_tiles(_, seller_filter):
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate

        tile_data = get_staff_tile_data()

        if not tile_data:
            return html.Div([
                html.I(className="bi bi-person-badge",
                       style={"fontSize": "32px", "color": "var(--text-muted)",
                              "marginBottom": "12px"}),
                html.Div("No staff activity recorded today yet.",
                         style={"fontSize": "13px", "color": "var(--text-muted)"}),
            ], style={"display": "flex", "flexDirection": "column",
                      "alignItems": "center", "justifyContent": "center",
                      "padding": "48px 0"})

        # Apply seller filter
        if seller_filter:
            tile_data = {k: v for k, v in tile_data.items() if k == seller_filter}
            if not tile_data:
                return html.Div("No data for the selected seller.",
                                style={"padding": "32px", "textAlign": "center",
                                       "color": "var(--text-muted)", "fontSize": "13px"})

        tiles = [_build_tile(seller, data)
                 for seller, data in sorted(tile_data.items())]

        return html.Div(tiles, style={
            "display": "grid",
            "gridTemplateColumns": "repeat(auto-fill, minmax(240px, 1fr))",
            "gap": "16px",
        })

    # ── Payment Pie Chart ─────────────────────────────────────────────────
    @app.callback(
        Output("live-payment-pie", "figure"),
        Input("live-sales-refresh", "n_intervals"),
    )
    def update_payment_pie(_):
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        df = get_today_sales()
        fig = go.Figure()
        if not df.empty and "payment_mode" in df.columns:
            pay_rev = df.groupby("payment_mode")["total_amount"].sum().reset_index()
            colors = [PAYMENT_COLORS.get(p, "#94A3B8") for p in pay_rev["payment_mode"]]
            total = pay_rev["total_amount"].sum()
            fig.add_trace(go.Pie(
                labels=pay_rev["payment_mode"],
                values=pay_rev["total_amount"],
                hole=0.6,
                marker=dict(colors=colors),
                textinfo="label+percent",
            ))
            fig.update_layout(
                **CHART_THEME, height=200,
                showlegend=False,
                annotations=[dict(
                    text=fmt_inr(total),
                    x=0.5, y=0.5,
                    font=dict(size=12, color="#F1F5F9", family="Space Mono"),
                    showarrow=False,
                )],
            )
        else:
            fig.update_layout(**CHART_THEME, height=200)
        return fig

    # ── Seller Performance ────────────────────────────────────────────────
    @app.callback(
        Output("live-seller-perf", "children"),
        Input("live-sales-refresh", "n_intervals"),
    )
    def update_seller_perf(_):
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        df = get_today_sales()
        if df.empty or "seller_name" not in df.columns:
            return html.Div("No data yet.",
                            style={"color": "var(--text-muted)", "fontSize": "12px"})

        seller_stats = df.groupby("seller_name").agg(
            items=("quantity", "sum"),
            revenue=("total_amount", "sum"),
            txns=("id", "count"),
        ).reset_index().sort_values("revenue", ascending=False)

        rows = []
        for _, row in seller_stats.iterrows():
            col = _seller_color(row["seller_name"])
            rows.append(html.Div([
                html.Div([
                    html.Div(str(row["seller_name"]).title(),
                             style={"fontSize": "13px", "fontWeight": "600",
                                    "color": "var(--text-primary)"}),
                    html.Div(f"{int(row['items'])} items · {int(row['txns'])} txns",
                             style={"fontSize": "11px", "color": "var(--text-muted)"}),
                ], style={"flex": "1"}),
                html.Div(fmt_inr(row["revenue"]),
                         style={"fontFamily": "Space Mono", "fontSize": "14px",
                                "fontWeight": "700", "color": col}),
            ], style={"display": "flex", "justifyContent": "space-between",
                      "alignItems": "center",
                      "padding": "10px 0",
                      "borderBottom": "1px solid var(--border-light)"}))
        return html.Div(rows)
