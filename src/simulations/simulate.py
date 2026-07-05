from __future__ import annotations

import os
import sys
from pathlib import Path

# =========================================================
# PATHS & ENVIRONMENT CONFIG (Moved to top)
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import argparse
import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, UTC

import numpy as np
import pandas as pd

# Now Python safely knows where 'src' lives
from src.data_loaders import (
    load_customer_ltv_raw,
    load_marketing_spend_raw,
    load_order_profit_raw,
)
from src.core.paths import RESULTS_DIR
RNG = np.random.default_rng(42)

# =========================================================
# SCENARIO STRUCTURE
# =========================================================

@dataclass
class ScenarioConfig:
    discount_cap: float | None = None
    reclassify_band: str | None = None
    reclassify_target: str | None = None

    # NEW (upgraded levers)
    marketing_shift_pct: float = 0.0
    shipping_cost_reduction_pct: float = 0.0


@dataclass
class ScenarioResult:
    scenario_id: str
    name: str
    timestamp: str
    config: dict
    baseline: dict
    simulated: dict
    delta: dict


# =========================================================
# HASHING
# =========================================================

def _hash_config(config: dict) -> str:
    raw = json.dumps(config, sort_keys=True).encode("utf-8")
    return hashlib.md5(raw).hexdigest()[:10]


# =========================================================
# PROFIT ENGINE
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
# DISCOUNT CAP
# =========================================================

def apply_discount_cap(df: pd.DataFrame, cap: float) -> pd.DataFrame:
    df = df.copy()
    df["discount_pct"] = df["discount_pct"].clip(upper=cap)
    return recompute_profit(df)


# =========================================================
# BAND SHIFT
# =========================================================

def apply_band_reclassification(df: pd.DataFrame, source_band: str, target_band: str) -> pd.DataFrame:
    df = df.copy()

    mask = df["discount_band"] == source_band
    target_pool = df.loc[df["discount_band"] == target_band, "discount_pct"]

    if target_pool.empty:
        return df

    sampled = RNG.choice(target_pool.to_numpy(), size=mask.sum(), replace=True)
    df.loc[mask, "discount_pct"] = sampled

    return recompute_profit(df)


# =========================================================
# MARKETING SHIFT (NEW LAYER)
# =========================================================

def apply_marketing_shift(df: pd.DataFrame, pct: float) -> pd.DataFrame:
    """
    Proxy model:
    - reduce marketing cost per order for efficiency gain
    """
    df = df.copy()
    df["marketing_cost_per_order"] *= (1 - pct)
    return recompute_profit(df)


# =========================================================
# SHIPPING OPTIMIZATION (NEW LAYER)
# =========================================================

def apply_shipping_optimization(df: pd.DataFrame, pct: float) -> pd.DataFrame:
    """
    Reduces fulfillment inefficiency (remote region subsidy proxy)
    """
    df = df.copy()
    df["actual_shipping_cost"] *= (1 - pct)
    return recompute_profit(df)


# =========================================================
# BASELINE LOADER
# =========================================================

def load_base():
    df = load_order_profit_raw()

    return {
        "df": df,
        "revenue": float(df["net_revenue"].sum()),
        "profit": float(df["net_operating_profit"].sum()),
    }


# =========================================================
# SCENARIO ENGINE
# =========================================================

def run_scenario(config: ScenarioConfig, name: str) -> ScenarioResult:
    base = load_base()
    df = base["df"].copy()

    # baseline snapshot
    baseline_metrics = {
        "revenue": base["revenue"],
        "profit": base["profit"],
    }

    # apply levers
    if config.discount_cap is not None:
        df = apply_discount_cap(df, config.discount_cap)

    if config.reclassify_band and config.reclassify_target:
        df = apply_band_reclassification(df, config.reclassify_band, config.reclassify_target)

    if config.marketing_shift_pct > 0:
        df = apply_marketing_shift(df, config.marketing_shift_pct)

    if config.shipping_cost_reduction_pct > 0:
        df = apply_shipping_optimization(df, config.shipping_cost_reduction_pct)

    simulated_metrics = {
        "revenue": float(df["net_revenue"].sum()),
        "profit": float(df["net_operating_profit"].sum()),
    }

    delta = {
        "revenue": simulated_metrics["revenue"] - baseline_metrics["revenue"],
        "profit": simulated_metrics["profit"] - baseline_metrics["profit"],
    }

    scenario_dict = asdict(config)
    scenario_id = _hash_config(scenario_dict)

    result = ScenarioResult(
        scenario_id=scenario_id,
        name=name,
        timestamp=datetime.now(UTC).isoformat(),
        config=scenario_dict,
        baseline=baseline_metrics,
        simulated=simulated_metrics,
        delta=delta,
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    out_path = RESULTS_DIR / f"{name}_{scenario_id}.json"

    with open(out_path, "w") as f:
        json.dump(asdict(result), f, indent=2)

    print(f"Scenario saved → {out_path}")

    return result


# =========================================================
# CLI
# =========================================================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--discount-cap", type=float)
    parser.add_argument("--reclassify-band", type=str)
    parser.add_argument("--reclassify-target", type=str)

    parser.add_argument("--marketing-shift", type=float, default=0.0)
    parser.add_argument("--shipping-opt", type=float, default=0.0)

    parser.add_argument("--name", type=str, default="scenario")

    args = parser.parse_args()

    config = ScenarioConfig(
        discount_cap=args.discount_cap,
        reclassify_band=args.reclassify_band,
        reclassify_target=args.reclassify_target,
        marketing_shift_pct=args.marketing_shift,
        shipping_cost_reduction_pct=args.shipping_opt,
    )

    run_scenario(config, args.name)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Simulation failed:", e, file=sys.stderr)
        sys.exit(1)