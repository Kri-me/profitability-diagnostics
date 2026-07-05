"""
Data loading layer for profitability diagnostics dashboard and simulator.

Design:
- PostgreSQL is optional (prod mode)
- CSV cache is mandatory fallback (dev mode)
- Single query engine handles all logic
- Streamlit caching applied where available
"""



from __future__ import annotations

import logging

# Suppress Streamlit's internal cache warnings
logging.getLogger("streamlit.runtime.caching.cache_data_api").setLevel(logging.ERROR)
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.db import get_engine

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE_TTL_SECONDS = 600  # 10 minutes

# -----------------------------
# Streamlit caching (optional)
# -----------------------------
try:
    import streamlit as st
    _cache_decorator = st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
except ImportError:
    def _cache_decorator(func):
        return func


# -----------------------------
# Cache helpers
# -----------------------------
def _write_cache_csv(cache_key: str, df: pd.DataFrame) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(CACHE_DIR / f"{cache_key}.csv", index=False)
    except OSError:
        pass


def _read_cache_csv(cache_key: str) -> pd.DataFrame | None:
    path = CACHE_DIR / f"{cache_key}.csv"
    if path.exists():
        return pd.read_csv(path)
    return None


# -----------------------------
# Core query engine
# -----------------------------
def run_query(sql: str, cache_key: str) -> pd.DataFrame:
    """
    Single safe data access layer:
    - Uses Postgres if available
    - Falls back to cached CSV if DB fails
    - Never crashes if cache exists
    """

    engine = get_engine()

    # -------------------------
    # DEV MODE (no DB)
    # -------------------------
    if engine is None:
        cached = _read_cache_csv(cache_key)
        return cached if cached is not None else pd.DataFrame()

    # -------------------------
    # PROD MODE (DB)
    # -------------------------
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)

        _write_cache_csv(cache_key, df)
        return df

    except Exception:
        cached = _read_cache_csv(cache_key)
        return cached if cached is not None else pd.DataFrame()


# =========================================================
# PUBLIC LOADERS
# =========================================================

@_cache_decorator
def load_monthly_trend() -> pd.DataFrame:
    df = run_query(
        "SELECT * FROM monthly_trend_view ORDER BY order_month",
        "monthly_trend_view"
    )
    if not df.empty:
        df["order_month"] = pd.to_datetime(df["order_month"])
    return df


@_cache_decorator
def load_discount_cannibalization() -> pd.DataFrame:
    return run_query(
        "SELECT * FROM discount_cannibalization_view",
        "discount_cannibalization_view"
    )


@_cache_decorator
def load_discount_by_segment() -> pd.DataFrame:
    return run_query(
        "SELECT * FROM discount_by_segment_view",
        "discount_by_segment_view"
    )


@_cache_decorator
def load_logistics_subsidization() -> pd.DataFrame:
    return run_query(
        "SELECT * FROM logistics_subsidization_view",
        "logistics_subsidization_view"
    )


@_cache_decorator
def load_logistics_by_region_discount() -> pd.DataFrame:
    return run_query(
        "SELECT * FROM logistics_by_region_discount_view",
        "logistics_by_region_discount_view"
    )


@_cache_decorator
def load_return_rate_trap() -> pd.DataFrame:
    return run_query(
        "SELECT * FROM return_rate_trap_view ORDER BY unit_return_rate_pct DESC",
        "return_rate_trap_view"
    )


@_cache_decorator
def load_channel_ltv_cac() -> pd.DataFrame:
    return run_query(
        "SELECT * FROM channel_ltv_cac_view",
        "channel_ltv_cac_view"
    )


@_cache_decorator
def load_prioritization_helper() -> pd.DataFrame:
    return run_query(
        "SELECT * FROM prioritization_helper_view ORDER BY net_operating_profit",
        "prioritization_helper_view"
    )



# -----------------------------
# RAW ORDER PROFIT DATA
# -----------------------------
@_cache_decorator
def load_order_profit_raw(limit: int | None = None) -> pd.DataFrame:

    sql = """
    SELECT
        order_id,
        segment,
        state_region,
        acquisition_channel,
        order_month,
        discount_band,
        discount_pct,
        gross_revenue,
        cogs,
        net_revenue,
        gross_profit,
        shipping_fee_charged,
        actual_shipping_cost,
        return_handling_cost,
        support_cost,
        marketing_cost_per_order,
        net_operating_profit,
        unit_return_rate
    FROM vw_order_profit
    """

    if limit:
        sql += f" LIMIT {limit}"

    df = run_query(sql, "order_profit_raw")

    print("DEBUG SHAPE:", df.shape)
    print("DEBUG COLUMNS:", df.columns.tolist())

    if not df.empty and "order_month" in df.columns:
        df["order_month"] = pd.to_datetime(df["order_month"])

    return df
# -----------------------------
# CUSTOMER LTV
# -----------------------------
@_cache_decorator
def load_customer_ltv_raw() -> pd.DataFrame:
    df = run_query(
        """
        SELECT customer_id, segment, acquisition_channel, signup_date,
               acquisition_cost, order_count, customer_ltv,
               ltv_after_customer_cac, is_repeat_customer
        FROM vw_customer_ltv
        """,
        "customer_ltv_raw"
    )

    if not df.empty:
        df["signup_date"] = pd.to_datetime(df["signup_date"])
        df["signup_month"] = df["signup_date"].values.astype("datetime64[M]")

    return df


# -----------------------------
# MARKETING SPEND
# -----------------------------
@_cache_decorator
def load_marketing_spend_raw() -> pd.DataFrame:
    df = run_query(
        "SELECT month, channel, spend_amount, new_customers_acquired FROM marketing_spend",
        "marketing_spend_raw"
    )

    if not df.empty:
        df["month"] = pd.to_datetime(df["month"])

    return df


# -----------------------------
# CACHE EXPORT UTILITY
# -----------------------------
def export_cache_csvs() -> None:
    loaders = [
        load_monthly_trend,
        load_discount_cannibalization,
        load_discount_by_segment,
        load_logistics_subsidization,
        load_logistics_by_region_discount,
        load_return_rate_trap,
        load_channel_ltv_cac,
        load_prioritization_helper,
        load_order_profit_raw,
        load_customer_ltv_raw,
        load_marketing_spend_raw,
    ]

    for loader in loaders:
        name = loader.__name__.replace("load_", "")
        print(f"Refreshing cache for {name}...")
        loader()

    print(f"Done. Cached CSVs written to {CACHE_DIR}")

# -----------------------------
# CACHE BUILD UTILITY
# -----------------------------
def ensure_order_profit_cache() -> None:
    """
    Rebuild order_profit_raw.csv directly from vw_order_profit.
    Run once when DATABASE_URL is available.
    """

    sql = """
    SELECT
        order_id,
        segment,
        state_region,
        acquisition_channel,
        order_month,
        discount_band,
        discount_pct,
        gross_revenue,
        cogs,
        net_revenue,
        gross_profit,
        shipping_fee_charged,
        actual_shipping_cost,
        return_handling_cost,
        support_cost,
        marketing_cost_per_order,
        net_operating_profit,
        unit_return_rate
    FROM vw_order_profit
    """

    engine = get_engine()

    if engine is None:
        raise RuntimeError(
            "Cannot build cache: DATABASE_URL not set and no DB connection available."
        )

    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)

    if df.empty:
        raise RuntimeError(
            "vw_order_profit returned no data. Cache not written."
        )

    _write_cache_csv("order_profit_raw", df)

    print(
        f"Cache rebuilt successfully: "
        f"{CACHE_DIR / 'order_profit_raw.csv'} "
        f"({len(df):,} rows)"
    )

if __name__ == "__main__":
    export_cache_csvs()