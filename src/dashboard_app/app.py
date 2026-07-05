import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

# ── DATABASE_URL: load .env if present, else rely on session env var ─────────
try:
    from dotenv import load_dotenv
    _here = Path(__file__).resolve()
    for _parent in [_here.parent, _here.parent.parent, _here.parent.parent.parent]:
        _env_file = _parent / ".env"
        if _env_file.exists():
            load_dotenv(_env_file, override=False)  # never clobber $env:DATABASE_URL
            break
except ImportError:
    pass  # python-dotenv not installed — session env var is enough

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ── optional live imports (graceful fallback to hardcoded findings) ──────────
try:
    from src.simulations.compare import compare_scenarios, get_best_scenario
    _SIM_LIVE = True
except ImportError:
    _SIM_LIVE = False

try:
    from src.dashboard_app.components.drivers import get_driver_insights
    _DRIVERS_LIVE = True
except ImportError:
    _DRIVERS_LIVE = False

try:
    from src.data_loaders import (
    load_monthly_trend,
    load_discount_cannibalization,
    load_channel_ltv_cac,
    load_logistics_by_region_discount,
    load_return_rate_trap,
    load_prioritization_helper,
)
    _DATA_LIVE = True
except ImportError:
    _DATA_LIVE = False


# ═══════════════════════════════════════════════════════════════════════════════
# THEME & CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Profitability Diagnostics — Apex Global",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    /* ── Base ── */
    [data-testid="stAppViewContainer"] {
        background-color: #0f1117;
        color: #e8e8e8;
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { background-color: #0f1117; }

    /* ── Typography ── */
    h1 { font-size: 2rem !important; font-weight: 700 !important;
          letter-spacing: -0.03em; color: #ffffff !important; }
    h2 { font-size: 1.15rem !important; font-weight: 600 !important;
          color: #ffffff !important; letter-spacing: 0.01em; }
    h3 { font-size: 0.85rem !important; font-weight: 500 !important;
          color: #8a8f9e !important; text-transform: uppercase;
          letter-spacing: 0.12em; }

    /* ── Divider ── */
    hr { border: none; border-top: 1px solid #1e2130; margin: 1.5rem 0; }

    /* ── Metric cards ── */
    [data-testid="metric-container"] {
        background: #151822;
        border: 1px solid #1e2130;
        border-radius: 6px;
        padding: 1rem 1.2rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: #ffffff !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.72rem !important;
        color: #8a8f9e !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    [data-testid="stMetricDelta"] > div {
        font-size: 0.78rem !important;
    }

    /* ── Finding callout ── */
    .finding {
        border-left: 3px solid #e05c2a;
        background: #16111a;
        padding: 0.75rem 1rem;
        border-radius: 0 6px 6px 0;
        margin: 0.75rem 0 1.25rem 0;
        font-size: 0.88rem;
        line-height: 1.6;
        color: #c8cad4;
    }
    .finding strong { color: #ffffff; }

    /* ── Section label ── */
    .section-label {
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        color: #e05c2a;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }

    /* ── Tab strip ── */
    [data-testid="stTabs"] button {
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.06em;
        color: #8a8f9e !important;
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
        color: #ffffff !important;
        border-bottom-color: #e05c2a !important;
    }

    /* ── Dataframe ── */
    [data-testid="stDataFrame"] { border: 1px solid #1e2130; border-radius: 6px; }

    /* ── Info / warning boxes ── */
    [data-testid="stInfo"], [data-testid="stWarning"] {
        background: #151822 !important;
        border: 1px solid #1e2130 !important;
        border-radius: 6px !important;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HARDCODED FINDINGS  (from confirmed SQL outputs in analysis_results.md)
# All numbers are real — sourced from the project's own diagnostic queries.
# ═══════════════════════════════════════════════════════════════════════════════

MONTHLY_TREND = pd.DataFrame({
    "period": ["Jan 2024", "Feb 2024", "Mar 2024",
                "Jan 2025", "Mar 2025", "Apr 2025", "May 2025", "Jun 2025"],
    "net_revenue_k": [375, 408, 438, 720, 755, 786, 798, 811],
    "net_margin_pct": [27.1, 26.8, 27.0, 24.5, 23.9, 23.4, 23.1, 22.6],
})

DISCOUNT_BANDS = pd.DataFrame({
    "band": ["No Discount", "Low (5–10%)", "Mid (10–20%)", "High (22–40%)"],
    "orders": [4793, 4536, 4518, 4339],
    "net_revenue_k": [3140, 2730, 2520, 1980],
    "net_margin_pct": [35.78, 30.23, 23.22, 1.93],
})

CHANNEL_LTV_CAC = pd.DataFrame({
    "channel": ["Organic", "Email", "Referral", "Paid Social"],
    "avg_cac": [8.19, 18.03, 23.91, 63.48],
    "avg_ltv": [824.50, 938.46, 1027.49, 125.89],
    "ltv_cac_ratio": [100.68, 52.06, 42.97, 1.98],
    "repeat_rate_pct": [76.0, 78.0, 76.4, 52.0],
    "customers": [1221, 778, 648, 1353],
})

SHIPPING_REGIONS = pd.DataFrame({
    "region": ["Metro", "Suburban", "Rural", "Remote"],
    "orders": [7457, 5621, 3345, 1763],
    "charged_k": [34.5, 29.5, 19.3, 11.4],
    "actual_cost_k": [127.9, 107.6, 85.6, 76.0],
    "deficit_k": [-93.3, -78.1, -66.3, -64.6],
    "net_margin_pct": [25.28, 25.64, 23.92, 21.76],
})

RETURN_RATES = pd.DataFrame({
    "subcategory": [
        "Luxury Apparel", "Footwear", "Everyday Apparel",
        "Premium Electronics", "Budget Electronics",
        "Home", "Sports",
    ],
    "return_rate_pct": [33.4, 27.8, 26.8, 20.1, 18.9, 12.0, 10.5],
    "net_revenue_k": [629, 785, 769, 1720, 1310, 860, 740],
})

LOSS_SEGMENTS = pd.DataFrame({
    "rank": [1, 2, 3, 4, 5],
    "segment": ["Retail", "Retail", "Retail", "Corporate", "Corporate"],
    "channel": ["Paid Social"] * 5,
    "region": ["Metro", "Rural", "Suburban", "Metro", "Suburban"],
    "discount": ["High"] * 5,
    "orders": [406, 197, 246, 128, 80],
    "profit": [-14311, -9875, -8626, -5941, -3371],
})

SCENARIOS = pd.DataFrame({
    "rank": [1, 2, 3],
    "name": [
        "Aggressive (8% cap + 50% shift)",
        "Balanced (9% cap + 35% shift)",
        "Conservative (15% cap + 50% shift)",
    ],
    "discount_cap_pct": [8, 9, 15],
    "paid_social_shift_pct": [50, 35, 50],
    "delta_profit": [884_000, 817_000, 499_000],
    "delta_margin_pts": [5.91, 5.49, 3.46],
    "score": [0.94, 0.87, 0.71],
})

DRIVERS = pd.DataFrame({
    "driver": [
        "Discount %",
        "Paid Social channel",
        "Shipping cost imbalance",
        "Return rate",
        "Support cost intensity",
        "Email channel",
        "Organic channel",
        "Low-return subcategory",
    ],
    "direction": ["negative", "negative", "negative", "negative", "negative",
                  "positive", "positive", "positive"],
    "abs_impact": [0.38, 0.27, 0.16, 0.11, 0.05, 0.12, 0.18, 0.09],
})


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

DARK_BG   = "#0f1117"
CARD_BG   = "#151822"
BORDER    = "#1e2130"
ACCENT    = "#e05c2a"
TEXT_MAIN = "#e8e8e8"
TEXT_DIM  = "#8a8f9e"
RED       = "#e05c2a"
GREEN     = "#3ecf8e"
GREY_LINE = "#2a2f3e"


def _base_layout(title="", height=320):
    return dict(
        title=dict(text=title, font=dict(size=12, color=TEXT_DIM), x=0, xanchor="left"),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=TEXT_MAIN, size=11),
        margin=dict(l=8, r=8, t=36, b=8),
        xaxis=dict(showgrid=False, zeroline=False, color=TEXT_DIM,
                   tickfont=dict(size=10, color=TEXT_DIM)),
        yaxis=dict(showgrid=True, gridcolor=GREY_LINE, zeroline=False,
                   color=TEXT_DIM, tickfont=dict(size=10, color=TEXT_DIM)),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10, color=TEXT_DIM),
                    orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(bgcolor=CARD_BG, font_size=11, bordercolor=BORDER),
    )


def callout(text: str):
    st.markdown(f'<div class="finding">{text}</div>', unsafe_allow_html=True)


def section(label: str):
    st.markdown(f'<p class="section-label">{label}</p>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("### Profitability Diagnostics")
st.title("Where Is Apex Global Leaking Value?")
st.markdown(
    "<span style='color:#8a8f9e; font-size:0.88rem'>"
    "18-month investigation · Synthetic e-commerce dataset · "
    "SQL → Python → Simulation"
    "</span>",
    unsafe_allow_html=True,
)
st.markdown("<hr>", unsafe_allow_html=True)

# Status badge
if _DATA_LIVE:
    st.success("Live database connection active", icon="🟢")
else:
    st.info(
        "Running on hardcoded findings from confirmed SQL outputs. "
        "Set DATABASE_URL to connect live.",
        icon="📋",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════

tab1, tab2, tab3 = st.tabs([
    "① Business Problem",
    "② Investigation",
    "③ Decision Lab",
])


# ───────────────────────────────────────────────────────────────────────────────
# TAB 1 — THE PROBLEM
# Revenue ↑ while margins ↓ — establish the central contradiction
# ───────────────────────────────────────────────────────────────────────────────

with tab1:

    st.markdown("## Revenue is growing. Profit is not keeping up.")
    callout(
        "Over 18 months, Apex Global roughly doubled net revenue — "
        "from ~$375K/month to ~$811K/month. But net margin fell from "
        "<strong>27.1% → 22.6%</strong>, a 4.5-point structural decline. "
        "The business is scaling volume faster than it is scaling profitability."
    )

    # ── Headline KPIs ──
    section("Period comparison — Jan 2024 vs Jun 2025")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue (Jun 2025)", "$811K / mo", "+99% vs Jan 2024")
    c2.metric("Net Margin (Jun 2025)", "22.6%", "-4.5 pts", delta_color="inverse")
    c3.metric("Gross Margin (Jun 2025)", "29.8%", "-4.0 pts", delta_color="inverse")
    c4.metric("Worst Month Ever", "Jun 2025", "22.59% net margin", delta_color="off")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Dual-axis trend chart ──
    df = MONTHLY_TREND if not _DATA_LIVE else load_monthly_trend()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["order_month"], y=df["net_revenue"],
        name="Net Revenue ($K)",
        marker_color=GREY_LINE,
        opacity=0.7,
        yaxis="y",
    ))

    fig.add_trace(go.Scatter(
        x=df["order_month"], y=df["net_margin_pct"],
        name="Net Margin %",
        mode="lines+markers",
        line=dict(color=ACCENT, width=2.5),
        marker=dict(size=6, color=ACCENT),
        yaxis="y2",
    ))

    layout = _base_layout("Monthly net revenue vs net margin %", height=340)
    layout["yaxis"] = dict(
        title="Revenue ($K)", showgrid=True, gridcolor=GREY_LINE,
        zeroline=False, color=TEXT_DIM, tickfont=dict(size=10, color=TEXT_DIM),
    )
    layout["yaxis2"] = dict(
        title="Net Margin %", overlaying="y", side="right",
        showgrid=False, zeroline=False, color=ACCENT,
        tickfont=dict(size=10, color=ACCENT),
        range=[18, 32],
    )
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)

    callout(
        "The bars confirm revenue growth is real. The orange line tells the actual story: "
        "every quarter, the margin is lower. This isn't a bad month — it's a structural trend."
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Three reinforcing mechanisms ──
    st.markdown("## Three mechanisms are driving this")

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("**① Discount erosion**")
        st.markdown(
            "<span style='color:#8a8f9e; font-size:0.85rem'>"
            "High-discount orders make up a growing share of volume — "
            "but net margin at the high band is just 1.93%. "
            "The company is buying revenue with margin."
            "</span>",
            unsafe_allow_html=True,
        )

    with col_b:
        st.markdown("**② Marketing misallocation**")
        st.markdown(
            "<span style='color:#8a8f9e; font-size:0.85rem'>"
            "Paid Social is the largest acquisition channel (34% of customers) "
            "with an LTV:CAC of 1.98×. Organic returns 100×. "
            "Spend is flowing to the wrong channel."
            "</span>",
            unsafe_allow_html=True,
        )

    with col_c:
        st.markdown("**③ Structural cost leakage**")
        st.markdown(
            "<span style='color:#8a8f9e; font-size:0.85rem'>"
            "Every region runs a shipping deficit — $302K total. "
            "High-return categories (33%+ in apparel) add hidden downstream costs "
            "that gross margin doesn't capture."
            "</span>",
            unsafe_allow_html=True,
        )


# ───────────────────────────────────────────────────────────────────────────────
# TAB 2 — INVESTIGATION
# Stakeholder diagnostics → driver validation
# ───────────────────────────────────────────────────────────────────────────────

with tab2:

    # ─── LEAK 1: Discount bands ───────────────────────────────────────────────

    st.markdown('''
<div style="border-left:3px solid #3b82f6; padding:0.3rem 0.8rem; margin-bottom:1rem">
<span style="color:#3b82f6; font-size:0.68rem; text-transform:uppercase; letter-spacing:0.15em; font-weight:600">Finance diagnostics</span><br>
<span style="color:#8a8f9e; font-size:0.8rem">Margin erosion · Discount cannibalization · Pricing integrity</span>
</div>''', unsafe_allow_html=True)
    section("Finance — Pricing integrity")
    st.markdown("## Discount cannibalization")
    callout(
        "High-discount orders (22–40% off) contribute just <strong>1.93% net margin</strong> "
        "— nearly zero. These 4,339 orders generated $892K in discount giveaways "
        "against just $38K in profit. Their share of total volume is growing month over month."
    )

    df_d = DISCOUNT_BANDS if not _DATA_LIVE else load_discount_cannibalization()

    col1, col2 = st.columns([3, 2])

    with col1:
        colors = [GREEN if m > 20 else ACCENT if m > 5 else RED
                  for m in df_d["net_margin_pct"]]
        fig = go.Figure(go.Bar(
            x=df_d["discount_band"], y=df_d["net_margin_pct"],
            marker_color=colors,
            text=[f"{v:.1f}%" for v in df_d["net_margin_pct"]],
            textposition="outside",
            textfont=dict(size=11, color=TEXT_MAIN),
        ))
        layout = _base_layout("Net margin % by discount band", height=300)
        layout["yaxis"]["title"] = "Net margin %"
        layout["yaxis"]["range"] = [0, 42]
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.dataframe(
            df_d[["discount_band", "orders", "net_revenue", "net_margin_pct"]]
            .rename(columns={
                "discount_band": "Discount Band",
                "orders": "Orders",
                "net_revenue": "Revenue ($)",
                "net_margin_pct": "Net Margin %",
            }),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    # ─── LEAK 2: Channel LTV/CAC ──────────────────────────────────────────────

    st.markdown('''
<div style="border-left:3px solid #8b5cf6; padding:0.3rem 0.8rem; margin-bottom:1rem">
<span style="color:#8b5cf6; font-size:0.68rem; text-transform:uppercase; letter-spacing:0.15em; font-weight:600">Marketing diagnostics</span><br>
<span style="color:#8a8f9e; font-size:0.8rem">LTV:CAC · Channel efficiency · Acquisition cost quality</span>
</div>''', unsafe_allow_html=True)
    section("Marketing — Acquisition efficiency")
    st.markdown("## Channel LTV vs CAC")
    callout(
        "Paid Social is the <strong>single largest acquisition channel</strong> (1,353 customers, 34% of base) "
        "yet returns an LTV:CAC of just <strong>1.98×</strong>. "
        "Organic returns <strong>100.68×</strong>. Every dollar shifted away from Paid Social "
        "produces dramatically more lifetime value at lower cost."
    )

    df_c = CHANNEL_LTV_CAC if not _DATA_LIVE else load_channel_ltv_cac()

    col1, col2 = st.columns([3, 2])

    with col1:
        fig = go.Figure()
        bar_colors = [RED if ch == "Paid Social" else GREEN for ch in df_c["acquisition_channel"]]
        fig.add_trace(go.Bar(
            name="Avg LTV ($)",
            x=df_c["acquisition_channel"], y=df_c["avg_customer_ltv"],
            marker_color=bar_colors, opacity=0.85,
        ))
        fig.add_trace(go.Bar(
            name="Avg CAC ($)",
            x=df_c["acquisition_channel"], y=df_c["avg_customer_cac"],
            marker_color=BORDER,
        ))
        layout = _base_layout("LTV vs CAC by acquisition channel", height=300)
        layout["barmode"] = "group"
        layout["yaxis"]["title"] = "$ per customer"
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.dataframe(
            df_c[["acquisition_channel", "customers", "avg_customer_cac", "avg_customer_ltv", "ltv_to_cac_ratio", "repeat_customer_rate_pct"]]
            .rename(columns={
                "acquisition_channel": "Acquisition Channel",
                "customers": "Customers",
                "avg_customer_cac": "Average Customer Acquisition Cost ($)",
                "avg_customer_ltv": "Average Customer Lifetime Value ($)",
                "ltv_to_cac_ratio": "LTV:CAC",
                "repeat_customer_rate_pct": "Repeat Customer Rate (%)",
            }),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    # ─── LEAK 3: Shipping deficit ─────────────────────────────────────────────

    st.markdown('''
<div style="border-left:3px solid #10b981; padding:0.3rem 0.8rem; margin-bottom:1rem">
<span style="color:#10b981; font-size:0.68rem; text-transform:uppercase; letter-spacing:0.15em; font-weight:600">Operations diagnostics</span><br>
<span style="color:#8a8f9e; font-size:0.8rem">Shipping subsidies · Return economics · Fulfillment costs</span>
</div>''', unsafe_allow_html=True)
    section("Operations — Fulfillment economics")
    st.markdown("## Shipping deficit by region")
    callout(
        "Apex charges customers a flat shipping fee that covers a fraction of actual carrier cost. "
        "The result: a <strong>$302K total shipping subsidy</strong> buried below gross margin. "
        "Remote region orders cost ~$43 to ship but customers pay ~$6.40. "
        "High-discount orders compound this — they often ship free."
    )

    df_s = SHIPPING_REGIONS if not _DATA_LIVE else load_logistics_by_region_discount()

    st.write("Shape:", df_s.shape)
    st.write("Columns:", df_s.columns.tolist())
    st.write(df_s.head())
    
    fig.add_trace(go.Bar(
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Charged to customer ($K)",
        x=df_s["state_region"], y=df_s["avg_shipping_fee_charged"],
        marker_color=GREEN, opacity=0.8,
    ))
        name="Actual shipping cost ($K)",
        x=df_s["state_region"], y=df_s["avg_actual_shipping_cost"],
        marker_color=RED, opacity=0.75,
    ))
    layout = _base_layout("Shipping charged vs actual cost by region ($K)", height=300)
    layout["barmode"] = "group"
    layout["yaxis"]["title"] = "$K"
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)
    for col, row in zip([col1, col2, col3, col4], df_s.itertuples()):
        col.metric(row.state_region, f"-${abs(row.avg_shipping_profit):.1f}K deficit",
                   f"{row.net_margin_pct:.1f}% net margin")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ─── LEAK 4: Returns ─────────────────────────────────────────────────────

    section("Operations — Return economics")
    st.markdown("## Return-rate trap")
    callout(
        "Luxury Apparel returns 1 in 3 units. Gross revenue in these categories "
        "overstates true economic contribution because refunds, return handling, and "
        "support costs are absorbed downstream — not visible in the headline P&L. "
        "Budget Electronics is the riskiest combination: <strong>thin margins + 19% return rate</strong>."
    )

    df_r = RETURN_RATES if not _DATA_LIVE else load_return_rate_trap()

    fig = go.Figure()
    dot_colors = [RED if r > 25 else ACCENT if r > 15 else GREEN
                  for r in df_r["unit_return_rate_pct"]]

    fig.add_trace(go.Scatter(
        x=df_r["net_revenue"], y=df_r["unit_return_rate_pct"],
        mode="markers+text",
        marker=dict(size=14, color=dot_colors, opacity=0.85,
                    line=dict(width=1, color="#0f1117")),
        text=df_r["subcategory"],
        textposition="top center",
        textfont=dict(size=9, color=TEXT_DIM),
    ))

    fig.add_hline(y=20, line_dash="dot", line_color=ACCENT, opacity=0.4,
                  annotation_text="20% return threshold",
                  annotation_font_color=ACCENT, annotation_font_size=10)

    layout = _base_layout("Return rate % vs net revenue ($) by subcategory", height=340)
    layout["xaxis"]["title"] = "Net Revenue ($)"
    layout["yaxis"]["title"] = "Return Rate %"
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ─── Prioritization: worst segments ───────────────────────────────────────

    section("Cross-functional — Segment prioritization")
    st.markdown("## Where value is actively destroyed")
    callout(
        "Every single loss-making segment combination shares the same two factors: "
        "<strong>Paid Social × High Discount</strong>. This is not a coincidence — "
        "it's the structural intersection of the two largest leaks."
    )

    df_l = LOSS_SEGMENTS if not _DATA_LIVE else load_prioritization_helper()

    st.dataframe(
        df_l.rename(columns={
            "rank": "#",
            "segment": "Segment",
            "acquisition_channel": "Channel",
            "state_region": "Region",
            "discount_band": "Discount Band",
            "orders": "Orders",
            "net_operating_profit": "Net Profit ($)",
        }),
        use_container_width=True,
        hide_index=True,
    )

    # ─── ML driver chart ──────────────────────────────────────────────────────

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('''
<div style="border-left:3px solid #f59e0b; padding:0.3rem 0.8rem; margin-bottom:1rem">
<span style="color:#f59e0b; font-size:0.68rem; text-transform:uppercase; letter-spacing:0.15em; font-weight:600">Driver analysis</span><br>
<span style="color:#8a8f9e; font-size:0.8rem">Regression · Feature importance · Statistical confirmation of descriptive findings</span>
</div>''', unsafe_allow_html=True)
    section("Analytics — Driver validation")
    st.markdown("## Feature importance confirms the story")
    callout(
        "Random forest feature importance ranks the same variables the SQL diagnostics surfaced. "
        "ML here is a <strong>validation layer</strong>, not a new hypothesis — "
        "it tells us the signals hold after controlling for interaction effects."
    )

    if _DRIVERS_LIVE:
        _live_dr = get_driver_insights()
        # fall back to hardcoded if live data is missing expected columns
        df_dr = _live_dr if {"driver", "direction", "abs_impact"}.issubset(_live_dr.columns) else DRIVERS
    else:
        df_dr = DRIVERS

    df_neg = df_dr[df_dr["direction"] == "negative"].sort_values("abs_impact", ascending=True)
    df_pos = df_dr[df_dr["direction"] == "positive"].sort_values("abs_impact", ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Profit drag",
        x=[-v for v in df_neg["abs_impact"]],
        y=df_neg["driver"],
        orientation="h",
        marker_color=RED, opacity=0.8,
    ))
    fig.add_trace(go.Bar(
        name="Profit lift",
        x=df_pos["abs_impact"],
        y=df_pos["driver"],
        orientation="h",
        marker_color=GREEN, opacity=0.8,
    ))

    layout = _base_layout("Relative feature importance — profit drivers (directional)", height=320)
    layout["barmode"] = "relative"
    layout["xaxis"]["title"] = "← drag  |  lift →"
    layout["xaxis"]["zeroline"] = True
    layout["xaxis"]["zerolinecolor"] = GREY_LINE
    layout["yaxis"]["title"] = ""
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)


# ───────────────────────────────────────────────────────────────────────────────
# TAB 3 — DECISION LAB
# ───────────────────────────────────────────────────────────────────────────────

with tab3:

    st.markdown("## From findings to intervention")
    callout(
        "Two levers were tested: a <strong>discount cap</strong> (repricing all orders above the cap to the cap rate) "
        "and <strong>Paid Social budget reallocation</strong> (shifting a % of Paid Social spend "
        "to Organic, Email, and Referral in proportion to their current LTV:CAC ratios). "
        "These are directional simulations — they reprice historical orders, not demand forecasts."
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Interactive controls ──
    section("Configure a scenario")

    _can_run = False
    try:
        from src.simulations.simulate import run_scenario, ScenarioConfig
        _can_run = True
    except ImportError:
        pass

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        discount_cap = st.slider(
            "Discount cap (%)",
            min_value=5, max_value=30, value=15, step=1,
            help="All orders above this discount % are repriced to the cap.",
        )
    with col_s2:
        paid_social_shift = st.slider(
            "Paid Social budget shift (%)",
            min_value=0, max_value=75, value=50, step=5,
            help="% of current Paid Social spend reallocated to higher-LTV channels.",
        )

    # ── Run custom scenario against live engine ───────────────────────────────
    if _can_run:
        if st.button("▶ Run this scenario", type="primary"):
            _custom_name = f"custom_{discount_cap}cap_{paid_social_shift}shift"
            _custom_cfg  = ScenarioConfig(
                discount_cap=discount_cap / 100,
                marketing_shift_pct=paid_social_shift / 100,
            )
            with st.spinner("Running against live data..."):
                try:
                    _result = run_scenario(_custom_cfg, _custom_name)
                    _dp = _result.delta["profit"]
                    _dr = _result.delta["revenue"]
                    _bp = _result.baseline["profit"]
                    _br = _result.baseline["revenue"]
                    _sp = _result.simulated["profit"]
                    _sr = _result.simulated["revenue"]
                    _dm = ((_sp / _sr) - (_bp / _br)) * 100 if _sr and _br else 0
                    st.cache_data.clear()
                    # show live result metrics immediately
                    section("Actual result — live simulation")
                    r1, r2, r3 = st.columns(3)
                    r1.metric("Profit Recovery", f"${_dp:,.0f}")
                    r2.metric("Margin Lift", f"+{_dm:.2f} pts")
                    r3.metric("Primary Lever",
                              "Discount cap" if discount_cap < 20 else "Channel shift")
                    callout(
                        f"A <strong>{discount_cap}% discount cap</strong> + "
                        f"<strong>{paid_social_shift}% Paid Social reallocation</strong> "
                        f"recovers <strong>${_dp:,.0f}</strong> in profit and lifts net margin "
                        f"by <strong>{_dm:.2f} pts</strong>. "
                        "No revenue increase required — purely a unit economics correction."
                    )
                except Exception as _e:
                    st.error(f"Simulation failed: {_e}")
    else:
        st.caption("Simulation engine unavailable — connect database to run live scenarios.")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── All scenarios results ──
    section("All tested scenarios")
    st.markdown("## Scenario comparison")

    # Preset run button — runs the three canonical scenarios
    if _can_run:
        if st.button("▶ Run all preset scenarios", help="Runs conservative, balanced, and aggressive scenarios"):
            _presets = [
                ("conservative_15cap_50shift", ScenarioConfig(discount_cap=0.15, marketing_shift_pct=0.50)),
                ("balanced_9cap_35shift",      ScenarioConfig(discount_cap=0.09, marketing_shift_pct=0.35)),
                ("aggressive_8cap_50shift",    ScenarioConfig(discount_cap=0.08, marketing_shift_pct=0.50)),
            ]
            with st.spinner("Running 3 preset scenarios..."):
                _errors = []
                for _sname, _cfg in _presets:
                    try:
                        run_scenario(_cfg, _sname)
                    except Exception as _e:
                        _errors.append(f"{_sname}: {_e}")
            if _errors:
                st.error("Some scenarios failed:\n" + "\n".join(_errors))
            else:
                st.success("All 3 preset scenarios saved.")
                st.cache_data.clear()
                st.rerun()

    df_sc = SCENARIOS
    if _SIM_LIVE:
        live = compare_scenarios()
        if not live.empty:
            # filter out zero-delta runs (blank/baseline-only saves)
            live = live[live["delta_profit"].abs() > 1.0]
        if not live.empty:
            if {"name", "delta_profit"}.issubset(live.columns):
                df_sc = live

    # Determine which optional columns are present
    _profit_col  = "delta_profit"  if "delta_profit"       in df_sc.columns else df_sc.columns[2]
    _name_col    = "name"          if "name"               in df_sc.columns else df_sc.columns[1]

    fig = go.Figure(go.Bar(
        x=df_sc[_name_col],
        y=df_sc[_profit_col],
        marker_color=[ACCENT] + [GREY_LINE] * (len(df_sc) - 1),
        text=[f"+${v:,.0f}" for v in df_sc[_profit_col]],
        textposition="outside",
        textfont=dict(size=11, color=TEXT_MAIN),
    ))
    layout = _base_layout("Profit recovery by scenario ($)", height=300)
    layout["yaxis"]["title"] = "Additional profit ($)"
    layout["yaxis"]["range"] = [0, int(df_sc[_profit_col].max() * 1.25)]
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)

    # Build display table from whatever columns exist
    _display_cols = {
        "rank":                "#",
        "name":                "Scenario",
        "discount_cap_pct":    "Discount Cap %",
        "paid_social_shift_pct": "Paid Social Shift %",
        "delta_profit":        "Profit Recovery ($)",
        "delta_margin_pts":    "Margin Lift (pts)",
        "score":               "Score",
    }
    _available = {k: v for k, v in _display_cols.items() if k in df_sc.columns}
    st.dataframe(
        df_sc[list(_available.keys())].rename(columns=_available),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Executive Recommendations ─────────────────────────────────────────────
    section("Executive Recommendations")
    st.markdown("## Prioritised interventions")

    st.markdown("""
<style>
.rec-card {
    background: #151822;
    border: 1px solid #1e2130;
    border-radius: 8px;
    padding: 1.1rem 1.2rem;
    height: 100%;
}
.rec-card .rec-priority {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #e05c2a;
    font-weight: 600;
    margin-bottom: 0.25rem;
}
.rec-card .rec-owner {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #8a8f9e;
    margin-bottom: 0.5rem;
}
.rec-card .rec-action {
    font-size: 0.92rem;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 0.6rem;
    line-height: 1.4;
}
.rec-card .rec-label {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #8a8f9e;
    margin-top: 0.6rem;
    margin-bottom: 0.2rem;
}
.rec-card .rec-evidence {
    font-size: 0.78rem;
    color: #8a8f9e;
    line-height: 1.7;
}
.rec-card .rec-evidence .tick { color: #3ecf8e; margin-right: 0.3rem; }
.rec-card .rec-impact {
    font-size: 0.82rem;
    color: #3ecf8e;
    font-weight: 600;
    margin-top: 0.3rem;
}
</style>
""", unsafe_allow_html=True)

    rp1, rp2, rp3 = st.columns(3)

    with rp1:
        st.markdown("""
<div class="rec-card">
  <div class="rec-priority">Priority 1</div>
  <div class="rec-owner">Finance</div>
  <div class="rec-action">Cap excessive discounts at 15%</div>
  <div class="rec-label">Evidence</div>
  <div class="rec-evidence">
    <span class="tick">✓</span>Largest negative profit driver (SQL)<br>
    <span class="tick">✓</span>Confirmed by regression analysis<br>
    <span class="tick">✓</span>Top feature importance signal<br>
    <span class="tick">✓</span>Simulation-validated across 3 scenarios
  </div>
  <div class="rec-label">Expected impact</div>
  <div class="rec-impact">+$499K – $884K operating profit</div>
</div>""", unsafe_allow_html=True)

    with rp2:
        st.markdown("""
<div class="rec-card">
  <div class="rec-priority">Priority 2</div>
  <div class="rec-owner">Marketing</div>
  <div class="rec-action">Reallocate Paid Social budget to high-LTV channels</div>
  <div class="rec-label">Evidence</div>
  <div class="rec-evidence">
    <span class="tick">✓</span>Paid Social LTV:CAC = 1.98× (SQL)<br>
    <span class="tick">✓</span>Organic LTV:CAC = 100.68× (SQL)<br>
    <span class="tick">✓</span>Channel confirmed as profit drag (ML)<br>
    <span class="tick">✓</span>Simulation shows structural improvement
  </div>
  <div class="rec-label">Expected impact</div>
  <div class="rec-impact">Higher customer profitability per $ spent</div>
</div>""", unsafe_allow_html=True)

    with rp3:
        st.markdown("""
<div class="rec-card">
  <div class="rec-priority">Priority 3</div>
  <div class="rec-owner">Operations</div>
  <div class="rec-action">Restructure shipping fees — minimum thresholds by region</div>
  <div class="rec-label">Evidence</div>
  <div class="rec-evidence">
    <span class="tick">✓</span>$302K total shipping subsidy (SQL)<br>
    <span class="tick">✓</span>Remote: ~$43 cost vs ~$6.40 charged<br>
    <span class="tick">✓</span>Shipping imbalance confirmed by ML<br>
    <span class="tick">✓</span>Margin drag visible across all regions
  </div>
  <div class="rec-label">Expected impact</div>
  <div class="rec-impact">Improved operating margin per order</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Evidence confidence table ─────────────────────────────────────────────
    st.markdown("<hr>", unsafe_allow_html=True)
    section("Overall expected impact")
    st.markdown("## Bottom line")

    oi1, oi2, oi3 = st.columns(3)
    oi1.metric("Estimated profit recovery", "$499K – $884K", "No revenue increase required", delta_color="off")
    oi2.metric("Net margin lift", "+3.5 – +5.9 pts", "Directional — not a demand forecast", delta_color="off")
    oi3.metric("Revenue base", "$10.4M (18-month)", "Same base, better economics", delta_color="off")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("""
<style>
.ev-table { width:100%; border-collapse:collapse; font-size:0.82rem; }
.ev-table th {
    text-align:left; color:#8a8f9e; font-weight:500;
    text-transform:uppercase; letter-spacing:0.1em; font-size:0.68rem;
    border-bottom:1px solid #1e2130; padding:0.5rem 0.75rem;
}
.ev-table td { padding:0.55rem 0.75rem; color:#c8cad4; border-bottom:1px solid #151822; }
.ev-table td.pass { color:#3ecf8e; font-weight:600; }
</style>
<table class="ev-table">
  <tr><th>Analysis layer</th><th>Method</th><th>Status</th></tr>
  <tr><td>SQL diagnostics</td><td>Grouped aggregations across discount band, channel, region</td><td class="pass">✓ Complete</td></tr>
  <tr><td>Exploratory analysis</td><td>Margin trend, segment breakdowns, shipping deficit quantification</td><td class="pass">✓ Complete</td></tr>
  <tr><td>Hypothesis validation</td><td>All 4 hypotheses confirmed against actual data outputs</td><td class="pass">✓ Complete</td></tr>
  <tr><td>Regression</td><td>Order-level profit drivers, directional effect sizes</td><td class="pass">✓ Complete</td></tr>
  <tr><td>Feature importance</td><td>Random forest — nonlinear drivers and interaction effects</td><td class="pass">✓ Complete</td></tr>
  <tr><td>Simulation</td><td>Discount cap + marketing reallocation across 3 scenarios</td><td class="pass">✓ Complete</td></tr>
</table>
""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    callout(
        "<strong>Core finding:</strong> Apex Global is not constrained by demand. "
        "It is constrained by unit economics that scale losses with volume. "
        "Discount discipline, acquisition quality, and fulfillment pricing — "
        "applied together — recover significant profit from the existing revenue base "
        "within one planning cycle."
    )
