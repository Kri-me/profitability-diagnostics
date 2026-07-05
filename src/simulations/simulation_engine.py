from __future__ import annotations
import os
import sys
from pathlib import Path
# Add project root to sys.path so Python can find the 'src' module
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple

import numpy as np
import pandas as pd

from src.data_loaders import (
    load_order_profit_raw,
    load_marketing_spend_raw,
    load_customer_ltv_raw,
)

RNG = np.random.default_rng(42)


# =========================================================
# CORE PROFIT RECOMPUTATION (single source of truth)
# =========================================================

def recompute_profit(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["net_revenue"] = df["gross_revenue"] * (1 - df["discount_pct"])
    df["gross_profit"] = df["net_revenue"] - df["cogs"]

    df["net_operating_profit"] = (
        df["gross_profit"]
        + df["shipping_fee_charged"]
        - df["actual_shipping_cost"]
        - df["return_handling_cost"]
        - df["support_cost"]
        - df["marketing_cost_per_order"]
    )

    return df


# =========================================================
# POLICY LAYER (what we are testing)
# =========================================================

@dataclass
class DiscountPolicy:
    cap: Optional[float] = None
    reclassify_source_band: Optional[str] = None
    reclassify_target_band: Optional[str] = None


@dataclass
class MarketingPolicy:
    source_channels: Optional[List[str]] = None
    target_channels: Optional[List[str]] = None
    shift_pct: float = 0.0


@dataclass
class SimulationPolicy:
    name: str
    discount: DiscountPolicy
    marketing: MarketingPolicy


# =========================================================
# DISCOUNT TRANSFORMS
# =========================================================

def apply_discount_policy(df: pd.DataFrame, policy: DiscountPolicy) -> pd.DataFrame:
    df = df.copy()

    if policy.cap is not None:
        df["discount_pct"] = df["discount_pct"].clip(upper=policy.cap)

    if policy.reclassify_source_band and policy.reclassify_target_band:
        target_pool = df.loc[
            df["discount_band"] == policy.reclassify_target_band,
            "discount_pct",
        ]

        if target_pool.empty:
            raise ValueError("Target band has no samples for reclassification.")

        mask = df["discount_band"] == policy.reclassify_source_band
        sampled = RNG.choice(target_pool.values, size=mask.sum(), replace=True)
        df.loc[mask, "discount_pct"] = sampled

    return recompute_profit(df)


# =========================================================
# MARKETING ECONOMICS MODEL (upgraded vs old version)
# =========================================================

def simulate_marketing_effect(
    monthly_spend: pd.DataFrame,
    customer_ltv: pd.DataFrame,
    policy: MarketingPolicy,
) -> Dict[str, Any]:
    """
    Improved version:
    - still uses LTV:CAC as efficiency proxy
    - but now returns structured policy-level delta estimates
    - separated from order-level simulation (clean architecture)
    """

    if not policy.source_channels or not policy.target_channels or policy.shift_pct <= 0:
        return {"enabled": False}

    cohort = (
        customer_ltv.groupby(["signup_month", "acquisition_channel"])
        .agg(
            customers=("customer_id", "count"),
            avg_cac=("acquisition_cost", "mean"),
            avg_ltv=("customer_ltv", "mean"),
        )
        .reset_index()
    )

    cohort["ltv_to_cac"] = cohort["avg_ltv"] / cohort["avg_cac"]

    spend = monthly_spend.copy()
    spend["month"] = pd.to_datetime(spend["month"]).values.astype("datetime64[M]")

    total_value_gain = 0.0
    total_shifted = 0.0

    for month in spend["month"].unique():
        m = spend[spend["month"] == month]

        if m.empty:
            continue

        m = m.set_index("channel")["spend_amount"]

        cohort_m = cohort[cohort["signup_month"] == month].set_index("acquisition_channel")

        for src in policy.source_channels:
            if src not in m:
                continue

            shifted = m[src] * policy.shift_pct
            total_shifted += shifted

            src_ratio = cohort_m.loc[src, "ltv_to_cac"] if src in cohort_m.index else 1.0

            for tgt in policy.target_channels:
                tgt_ratio = cohort_m.loc[tgt, "ltv_to_cac"] if tgt in cohort_m.index else 1.0

                efficiency_gain = shifted * (tgt_ratio - src_ratio)
                total_value_gain += efficiency_gain

    return {
        "enabled": True,
        "total_shifted_spend": total_shifted,
        "estimated_ltv_value_gain": total_value_gain,
        "efficiency_multiplier": (
            total_value_gain / total_shifted if total_shifted else 0
        ),
    }


# =========================================================
# POLICY SIMULATION ENGINE
# =========================================================

def run_policy(policy: SimulationPolicy) -> Dict[str, Any]:
    baseline = load_order_profit_raw()
    simulated = baseline.copy()

    simulated = apply_discount_policy(simulated, policy.discount)
    simulated = recompute_profit(simulated)

    marketing = load_marketing_spend_raw()
    customer_ltv = load_customer_ltv_raw()

    marketing_result = simulate_marketing_effect(
        marketing,
        customer_ltv,
        policy.marketing,
    )

    baseline_profit = baseline["net_operating_profit"].sum()
    simulated_profit = simulated["net_operating_profit"].sum()

    return {
        "policy_name": policy.name,
        "baseline_profit": baseline_profit,
        "simulated_profit": simulated_profit,
        "profit_delta": simulated_profit - baseline_profit,
        "marketing": marketing_result,
        "simulated_table": simulated,
    }


# =========================================================
# POLICY COMPARISON / RANKING
# =========================================================

def rank_policies(results: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []

    for r in results:
        rows.append(
            {
                "policy": r["policy_name"],
                "baseline_profit": r["baseline_profit"],
                "simulated_profit": r["simulated_profit"],
                "delta": r["profit_delta"],
                "marketing_efficiency": r["marketing"].get("efficiency_multiplier", 0),
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("delta", ascending=False)

    return df


# =========================================================
# DEFAULT POLICY EXAMPLE (used by dashboard)
# =========================================================

def default_policy() -> SimulationPolicy:
    return SimulationPolicy(
        name="default_policy",
        discount=DiscountPolicy(cap=0.15),
        marketing=MarketingPolicy(
            source_channels=["Paid Social"],
            target_channels=["Organic", "Email", "Referral"],
            shift_pct=0.5,
        ),
    )