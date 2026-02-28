"""Owner Dashboard callbacks — full financial analytics with INR formatting."""
import plotly.graph_objects as go
import pandas as pd
from dash import Input, Output, html
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import flask
from server import app
from services.sales_service import get_sales_df, get_kpis
from utils import fmt_inr, CATEGORY_COLORS
from constants import ROLE_OWNER

CHART_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#94A3B8", size=12),
    margin=dict(l=16, r=16, t=16, b=16),
    colorway=["#2DD4BF", "#F59E0B", "#EC4899", "#3B82F6", "#10B981", "#8B5CF6"],
)

PAYMENT_COLORS = {"Cash": "#10B981", "UPI": "#3B82F6", "Card": "#F59E0B"}


def register_callbacks():

    @app.callback(
        Output("dashboard-kpis", "children"),
        [Input("dashboard-period", "value"),
         Input("dashboard-refresh", "n_intervals")],
    )
    def update_kpis(days, _):
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        kpis = get_kpis(days)
        growth = kpis["revenue_growth"]
        delta_color = "positive" if growth >= 0 else "negative"
        delta_icon = "↑" if growth >= 0 else "↓"

        cards_data = [
            ("Total Revenue",   fmt_inr(kpis["total_revenue"]),
             f"{delta_icon} {abs(growth):.1f}% vs prev period",
             delta_color, "bi-currency-rupee"),
            ("Items Sold",      f"{kpis['total_items']:,}",   None, None, "bi-basket2"),
            ("Transactions",    f"{kpis['num_transactions']:,}", None, None, "bi-receipt-cutoff"),
            ("Top Product",     kpis["top_product"],           None, None, "bi-trophy"),
        ]

        cols = []
        for label, value, delta, d_color, icon in cards_data:
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

    @app.callback(
        [Output("revenue-trend-chart", "figure"),
         Output("category-pie-chart", "figure"),
         Output("top-products-chart", "figure"),
         Output("payment-mode-chart", "figure"),
         Output("category-perf-chart", "figure")],
        [Input("dashboard-period", "value"),
         Input("dashboard-refresh", "n_intervals")],
    )
    def update_charts(days, _):
        if flask.session.get("role") != ROLE_OWNER:
            raise PreventUpdate
        df = get_sales_df(days)

        # ── Revenue Trend ────────────────────────────────────────────────
        if not df.empty:
            daily = df.groupby("sale_date")["total_amount"].sum().reset_index()
            daily.columns = ["date", "revenue"]
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=daily["date"], y=daily["revenue"],
                mode="lines+markers",
                line=dict(color="#2DD4BF", width=2.5, shape="spline"),
                marker=dict(size=5, color="#2DD4BF"),
                fill="tozeroy",
                fillcolor="rgba(45,212,191,0.07)",
                name="Revenue",
                hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>",
            ))
        else:
            fig_trend = go.Figure()

        fig_trend.update_layout(
            **CHART_THEME, height=220,
            xaxis=dict(showgrid=False, zeroline=False, linecolor="#334155"),
            yaxis=dict(showgrid=True, gridcolor="#1E293B", zeroline=False,
                       tickprefix="₹"),
        )

        # ── Category Pie ─────────────────────────────────────────────────
        if not df.empty:
            cat_rev = df.groupby("category")["total_amount"].sum().reset_index()
            colors = [CATEGORY_COLORS.get(c, "#8B5CF6") for c in cat_rev["category"]]
            total_rev = df["total_amount"].sum()
            fig_pie = go.Figure(go.Pie(
                labels=cat_rev["category"],
                values=cat_rev["total_amount"],
                hole=0.6,
                textinfo="label+percent",
                marker=dict(colors=colors),
            ))
        else:
            total_rev = 0
            fig_pie = go.Figure()

        fig_pie.update_layout(
            **CHART_THEME, height=220, showlegend=False,
            annotations=[dict(
                text=fmt_inr(total_rev),
                x=0.5, y=0.5,
                font=dict(size=12, color="#F1F5F9", family="Space Mono"),
                showarrow=False,
            )],
        )

        # ── Top 10 Products ───────────────────────────────────────────────
        if not df.empty:
            top10 = df.groupby("product_name")["total_amount"].sum().nlargest(10).reset_index()
            fig_top = go.Figure(go.Bar(
                x=top10["total_amount"],
                y=top10["product_name"],
                orientation="h",
                marker=dict(color="#2DD4BF", opacity=0.85),
                text=[fmt_inr(v) for v in top10["total_amount"]],
                textposition="outside",
                textfont=dict(color="#94A3B8", size=10),
                hovertemplate="%{y}: ₹%{x:,.0f}<extra></extra>",
            ))
        else:
            fig_top = go.Figure()

        fig_top.update_layout(
            **CHART_THEME, height=280,
            xaxis=dict(showgrid=True, gridcolor="#1E293B", zeroline=False),
            yaxis=dict(showgrid=False, zeroline=False),
        )

        # ── Payment Mode Chart ────────────────────────────────────────────
        if not df.empty and "payment_mode" in df.columns:
            pay_data = df.groupby("payment_mode")["total_amount"].sum().reset_index()
            p_colors = [PAYMENT_COLORS.get(p, "#8B5CF6") for p in pay_data["payment_mode"]]
            fig_pay = go.Figure(go.Pie(
                labels=pay_data["payment_mode"],
                values=pay_data["total_amount"],
                hole=0.55,
                marker=dict(colors=p_colors),
                textinfo="label+percent",
            ))
        else:
            fig_pay = go.Figure()

        fig_pay.update_layout(**CHART_THEME, height=220, showlegend=False)

        # ── Category Performance ──────────────────────────────────────────
        if not df.empty:
            cat_perf = df.groupby("category").agg(
                revenue=("total_amount", "sum"),
                qty=("quantity", "sum"),
            ).reset_index().sort_values("revenue", ascending=False).head(6)
            fig_cat = go.Figure()
            fig_cat.add_trace(go.Bar(
                x=cat_perf["category"],
                y=cat_perf["revenue"],
                name="Revenue",
                marker_color="#2DD4BF",
                hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>",
            ))
            fig_cat.add_trace(go.Bar(
                x=cat_perf["category"],
                y=cat_perf["qty"],
                name="Qty",
                marker_color="#F59E0B",
                yaxis="y2",
            ))
        else:
            fig_cat = go.Figure()

        fig_cat.update_layout(
            **CHART_THEME, height=220,
            barmode="group",
            xaxis=dict(showgrid=False, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#1E293B", zeroline=False,
                       tickprefix="₹"),
            yaxis2=dict(overlaying="y", side="right", showgrid=False,
                        tickfont=dict(color="#F59E0B")),
            legend=dict(orientation="h", y=-0.25, font=dict(size=9)),
        )

        return fig_trend, fig_pie, fig_top, fig_pay, fig_cat
