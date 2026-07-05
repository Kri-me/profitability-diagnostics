"""Starter analysis script for Project 1 after SQL tables/views are loaded."""

from __future__ import annotations

import os

import pandas as pd
from sqlalchemy import create_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:password@localhost:5432/profitability_diagnostics",
)


def load_query(sql: str) -> pd.DataFrame:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        return pd.read_sql(sql, connection)


def main() -> None:
    monthly = load_query(
        """
        SELECT order_month, net_revenue, net_operating_profit, net_margin_pct
        FROM vw_monthly_profit_trend
        ORDER BY order_month;
        """
    )
    discount = load_query(
        """
        SELECT
            discount_band,
            count(*) AS orders,
            sum(net_revenue) AS net_revenue,
            sum(net_operating_profit) AS net_operating_profit,
            sum(net_operating_profit) / NULLIF(sum(net_revenue), 0) AS net_margin_pct
        FROM vw_order_profit
        GROUP BY discount_band
        ORDER BY net_margin_pct;
        """
    )
    channel = load_query(
        """
        SELECT *
        FROM vw_channel_ltv_cac
        ORDER BY avg_ltv_after_customer_cac;
        """
    )

    print("\nMonthly trend")
    print(monthly.to_string(index=False))
    print("\nDiscount diagnostic")
    print(discount.to_string(index=False))
    print("\nChannel LTV/CAC")
    print(channel.to_string(index=False))


if __name__ == "__main__":
    main()
