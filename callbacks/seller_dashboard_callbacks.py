"""Seller Dashboard callbacks — non-financial metrics, period-filterable."""
import plotly.graph_objects as go
import pandas as pd
from dash import Input, Output, html
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import flask
from server import app
from services.sales_service import (
    get_today_sales, get_all_time_sales, get_seller_kpis, get_sales_df,
)
from services.inventory_service import get_inventory_df
from utils import CATEGORY_COLORS
from constants import ROLE_OWNER, ROLE_STAFF

CHART_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#94A3B8", size=11),
    margin=dict(l=16, r=16, t=16, b=16),
)

# Critical materials to watch for sellers
SELLER_WATCH_MATERIALS = [
    "Milk", "Tea Cups", "Coffee Powder", "Banana",
    "Juice Cups", "Ice", "Coffee Cups", "Milkshake Cups",
]


def _get_df(filter_type: str) -> pd.DataFrame:
    """Return the sales DataFrame for the chosen period."""
    return get_today_sales() if filter_type == "today" else get_all_time_sales()


def register_callbacks():

    # ── KPIs ─────────────────────────────────────────────────────────────────
    @app.callback(
        Output("seller-kpis", "children"),
        [Input("seller-dashboard-refresh", "n_intervals"),
         Input("seller-dash-filter", "value")],
    )
    def update_seller_kpis(_, filter_val):
        if flask.session.get("role") not in (ROLE_STAFF, ROLE_OWNER):
            raise PreventUpdate
        filter_type = filter_val or "today"
        kpis = get_seller_kpis(filter_type)
        period_label = "Today" if filter_type == "today" else "All Time"

        cards_data = [
            (f"Items Sold ({period_label})", str(kpis["total_items"]),
             "bi-basket2",  "#2DD4BF"),
            ("Top Item",    kpis["top_item"],
             "bi-trophy",   "#EC4899"),
            ("Top Category", kpis.get("top_category", "N/A"),
             "bi-tags",     "#F59E0B"),
            ("Peak Hour",   kpis["peak_hour"],
             "bi-clock",    "#3B82F6"),
        ]

        cols = []
        for label, value, icon, color in cards_data:
            cols.append(dbc.Col([
                html.Div([
                    html.I(className=f"bi {icon} kpi-icon",
                           style={"color": color, "opacity": "0.7"}),
                    html.Div(label, className="kpi-label"),
                    html.Div(value, className="kpi-value",
                             style={"fontSize": "20px", "color": color}),
                ], className="kpi-card"),
            ], md=3))

        return dbc.Row(cols, className="g-3")

    # ── Category chart ────────────────────────────────────────────────────────
    @app.callback(
        [Output("seller-category-chart", "figure"),
         Output("seller-cat-chart-title", "children")],
        [Input("seller-dashboard-refresh", "n_intervals"),
         Input("seller-dash-filter", "value")],
    )
    def update_seller_cat_chart(_, filter_val):
        if flask.session.get("role") not in (ROLE_STAFF, ROLE_OWNER):
            raise PreventUpdate
        filter_type = filter_val or "today"
        title = ("Category-wise Items Sold Today"
                 if filter_type == "today"
                 else "Category-wise Items Sold (All Time)")
        df = _get_df(filter_type)

        if df.empty:
            fig = go.Figure()
            fig.update_layout(**CHART_THEME, height=250)
            return fig, title

        cat_qty = df.groupby("category")["quantity"].sum().reset_index()
        cat_qty.columns = ["category", "qty"]
        cat_qty = cat_qty.sort_values("qty", ascending=True)
        colors = [CATEGORY_COLORS.get(c, "#8B5CF6") for c in cat_qty["category"]]

        fig = go.Figure(go.Bar(
            x=cat_qty["qty"],
            y=cat_qty["category"],
            orientation="h",
            marker=dict(color=colors),
            text=cat_qty["qty"],
            textposition="outside",
            textfont=dict(color="#94A3B8", size=11),
        ))
        fig.update_layout(
            **CHART_THEME, height=280,
            xaxis=dict(showgrid=True, gridcolor="#1E293B", zeroline=False,
                       title="Units Sold"),
            yaxis=dict(showgrid=False, zeroline=False),
        )
        return fig, title

    # ── Trend chart (hourly today / daily last-30 for all-time) ───────────────
    @app.callback(
        [Output("seller-hourly-chart", "figure"),
         Output("seller-trend-chart-title", "children")],
        [Input("seller-dashboard-refresh", "n_intervals"),
         Input("seller-dash-filter", "value")],
    )
    def update_seller_trend(_, filter_val):
        if flask.session.get("role") not in (ROLE_STAFF, ROLE_OWNER):
            raise PreventUpdate
        filter_type = filter_val or "today"
        fig = go.Figure()

        if filter_type == "today":
            title = "Hourly Activity (Today)"
            df = get_today_sales()
            if not df.empty and "created_at" in df.columns:
                df["hour"] = pd.to_datetime(df["created_at"], errors="coerce").dt.hour
                hourly = df.groupby("hour")["quantity"].sum().reindex(
                    range(8, 23), fill_value=0
                )
                labels = [f"{h:02d}:00" for h in hourly.index]
                fig.add_trace(go.Bar(
                    x=labels, y=hourly.values,
                    marker=dict(color="#2DD4BF", opacity=0.85),
                    text=hourly.values,
                    textposition="outside",
                    textfont=dict(size=9, color="#94A3B8"),
                ))
            fig.update_layout(
                **CHART_THEME, height=220,
                xaxis=dict(showgrid=False, zeroline=False),
                yaxis=dict(showgrid=True, gridcolor="#1E293B", zeroline=False,
                           title="Units Sold"),
            )
        else:
            title = "Daily Trend (Last 30 Days)"
            df = get_sales_df(30)
            if not df.empty and "sale_date" in df.columns:
                daily = (
                    df.groupby("sale_date")["quantity"].sum()
                    .reset_index()
                    .sort_values("sale_date")
                )
                fig.add_trace(go.Scatter(
                    x=daily["sale_date"], y=daily["quantity"],
                    mode="lines+markers",
                    line=dict(color="#2DD4BF", width=2),
                    marker=dict(color="#2DD4BF", size=6),
                    fill="tozeroy",
                    fillcolor="rgba(45,212,191,0.08)",
                ))
            fig.update_layout(
                **CHART_THEME, height=220,
                xaxis=dict(showgrid=False, zeroline=False, title="Date"),
                yaxis=dict(showgrid=True, gridcolor="#1E293B", zeroline=False,
                           title="Units Sold"),
            )

        return fig, title

    # ── Top items ─────────────────────────────────────────────────────────────
    @app.callback(
        [Output("seller-top-items", "children"),
         Output("seller-top-items-title", "children")],
        [Input("seller-dashboard-refresh", "n_intervals"),
         Input("seller-dash-filter", "value")],
    )
    def update_top_items(_, filter_val):
        if flask.session.get("role") not in (ROLE_STAFF, ROLE_OWNER):
            raise PreventUpdate
        filter_type = filter_val or "today"
        title = "Top Items Today" if filter_type == "today" else "Top Items (All Time)"
        df = _get_df(filter_type)

        if df.empty:
            return (
                html.Div("No sales data yet.",
                         style={"color": "var(--text-muted)", "fontSize": "12px",
                                "textAlign": "center", "padding": "20px"}),
                title,
            )

        top5 = df.groupby("product_name")["quantity"].sum().nlargest(5).reset_index()
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        rows = []
        for i, (_, row) in enumerate(top5.iterrows()):
            rows.append(html.Div([
                html.Span(medals[i],
                          style={"fontSize": "16px", "marginRight": "10px"}),
                html.Div(
                    html.Div(row["product_name"],
                             style={"fontSize": "12px", "fontWeight": "600",
                                    "color": "var(--text-primary)"}),
                    style={"flex": "1"},
                ),
                html.Div(f"{int(row['quantity'])} units",
                         style={"fontFamily": "Space Mono", "fontSize": "12px",
                                "color": "var(--primary)", "fontWeight": "700"}),
            ], style={"display": "flex", "alignItems": "center",
                      "padding": "8px 0",
                      "borderBottom": "1px solid var(--border-light)"}))
        return html.Div(rows), title

    # ── Low stock panel (always current stock — filter-independent) ───────────
    @app.callback(
        Output("seller-low-stock-panel", "children"),
        [Input("seller-dashboard-refresh", "n_intervals")],
    )
    def update_low_stock_panel(_):
        if flask.session.get("role") not in (ROLE_STAFF, ROLE_OWNER):
            raise PreventUpdate
        inv_df = get_inventory_df()
        watch_df = inv_df[inv_df["name"].isin(SELLER_WATCH_MATERIALS)]
        low = watch_df[watch_df["status"].isin(["Low", "Critical"])]

        if low.empty:
            return html.Div([
                html.I(className="bi bi-check-circle me-2",
                       style={"color": "var(--success)", "fontSize": "18px"}),
                html.Span("All critical materials are stocked.",
                          style={"color": "var(--success)", "fontSize": "13px"}),
            ], style={"display": "flex", "alignItems": "center",
                      "padding": "16px 0"})

        rows = []
        for _, row in low.iterrows():
            is_crit = row["status"] == "Critical"
            color = "var(--danger)" if is_crit else "var(--warning)"
            bg    = "rgba(239,68,68,0.08)" if is_crit else "rgba(245,158,11,0.08)"
            icon  = "bi-exclamation-octagon" if is_crit else "bi-exclamation-triangle"
            rows.append(html.Div([
                html.I(className=f"bi {icon}",
                       style={"color": color, "fontSize": "16px",
                              "marginRight": "10px", "flexShrink": "0"}),
                html.Div([
                    html.Div(row["name"],
                             style={"fontSize": "12px", "fontWeight": "600",
                                    "color": "var(--text-primary)"}),
                    html.Div(f"{row['current_stock']:.0f} {row['unit']} remaining",
                             style={"fontSize": "11px", "color": color}),
                ], style={"flex": "1"}),
                html.Span(row["status"],
                          style={"fontSize": "10px", "fontWeight": "600",
                                 "background": bg, "color": color,
                                 "padding": "2px 8px", "borderRadius": "20px",
                                 "border": f"1px solid {color}44"}),
            ], style={"display": "flex", "alignItems": "center",
                      "padding": "8px 0",
                      "borderBottom": "1px solid var(--border-light)"}))

        return html.Div([
            html.Div([
                html.I(className="bi bi-exclamation-triangle me-2",
                       style={"color": "var(--danger)"}),
                html.Span(f"{len(low)} item(s) need attention",
                          style={"fontSize": "12px", "fontWeight": "600",
                                 "color": "var(--danger)"}),
            ], style={"marginBottom": "12px"}),
            html.Div(rows),
        ])

    # ── Sales by Item chart ───────────────────────────────────────────────────
    @app.callback(
        Output("seller-items-chart", "figure"),
        [Input("seller-dashboard-refresh", "n_intervals"),
         Input("seller-dash-filter", "value"),
         Input("seller-item-cat-filter", "value")],
    )
    def update_items_chart(_, filter_val, category_filter):
        if flask.session.get("role") not in (ROLE_STAFF, ROLE_OWNER):
            raise PreventUpdate

        filter_type = filter_val or "today"
        df = _get_df(filter_type)

        if df.empty:
            fig = go.Figure()
            fig.update_layout(
                **CHART_THEME, height=200,
                annotations=[dict(
                    text="No sales data for this period.",
                    xref="paper", yref="paper", x=0.5, y=0.5,
                    showarrow=False,
                    font=dict(color="#475569", size=13),
                )],
            )
            return fig

        if category_filter:
            df = df[df["category"] == category_filter]

        item_qty = (
            df.groupby(["product_name", "category"])["quantity"]
            .sum()
            .reset_index()
        )
        item_qty.columns = ["product_name", "category", "qty"]

        # Top 25 for all-categories view; all items for single-category view
        if not category_filter:
            item_qty = item_qty.nlargest(25, "qty")

        item_qty = item_qty.sort_values("qty", ascending=True)
        colors = [CATEGORY_COLORS.get(c, "#8B5CF6") for c in item_qty["category"]]

        fig = go.Figure(go.Bar(
            x=item_qty["qty"],
            y=item_qty["product_name"],
            orientation="h",
            marker=dict(color=colors),
            text=item_qty["qty"],
            textposition="outside",
            textfont=dict(color="#94A3B8", size=10),
            customdata=item_qty["category"],
            hovertemplate=(
                "<b>%{y}</b><br>Category: %{customdata}"
                "<br>Qty: %{x}<extra></extra>"
            ),
        ))

        chart_height = max(220, len(item_qty) * 28 + 60)
        fig.update_layout(
            **CHART_THEME,
            height=chart_height,
            xaxis=dict(showgrid=True, gridcolor="#1E293B", zeroline=False,
                       title="Units Sold"),
            yaxis=dict(showgrid=False, zeroline=False,
                       tickfont=dict(size=10)),
        )
        return fig
