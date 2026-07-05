from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

from src.core.paths import RESULTS_DIR


# =========================================================
# LOAD SCENARIOS
# =========================================================

def load_scenarios() -> List[Dict[str, Any]]:
    files = list(RESULTS_DIR.glob("*.json"))
    scenarios = []

    for f in files:
        try:
            with open(f, "r") as file:
                scenarios.append(json.load(file))
        except Exception:
            continue

    return scenarios


# =========================================================
# NORMALIZATION
# =========================================================

def normalize(s: Dict[str, Any]) -> Dict[str, float]:
    cfg = s.get("config", {})

    baseline_profit  = s["baseline"]["profit"]
    baseline_revenue = s["baseline"]["revenue"]
    sim_profit       = s["simulated"]["profit"]
    sim_revenue      = s["simulated"]["revenue"]
    delta_profit     = s["delta"]["profit"]
    delta_revenue    = s["delta"]["revenue"]

    # margin % = profit / revenue * 100
    baseline_margin = (baseline_profit / baseline_revenue * 100) if baseline_revenue else 0
    sim_margin      = (sim_profit      / sim_revenue      * 100) if sim_revenue      else 0

    return {
        "scenario_id":           s.get("scenario_id"),
        "name":                  s.get("name"),

        # config levers — unpacked from nested config dict
        "discount_cap_pct":      cfg.get("discount_cap"),          # None if not used
        "paid_social_shift_pct": cfg.get("marketing_shift_pct", 0.0) * 100,  # 0.5 → 50
        "shipping_opt_pct":      cfg.get("shipping_cost_reduction_pct", 0.0) * 100,

        # financials
        "baseline_profit":       baseline_profit,
        "sim_profit":            sim_profit,
        "delta_profit":          delta_profit,

        "baseline_revenue":      baseline_revenue,
        "sim_revenue":           sim_revenue,
        "delta_revenue":         delta_revenue,

        # derived
        "baseline_margin_pct":   round(baseline_margin, 2),
        "sim_margin_pct":        round(sim_margin, 2),
        "delta_margin_pts":      round(sim_margin - baseline_margin, 2),
    }


# =========================================================
# SCORING FUNCTION
# =========================================================

def compute_score(row: Dict[str, float]) -> float:
    profit_gain    = row["delta_profit"]
    revenue_change = row["delta_revenue"]

    efficiency        = profit_gain / (abs(revenue_change) + 1e-6)
    volatility_penalty = abs(revenue_change) * 0.000001

    score = (
        profit_gain * 1.0
        + efficiency * 0.25
        - volatility_penalty
    )

    return score


# =========================================================
# MAIN COMPARE ENGINE
# =========================================================

def compare_scenarios() -> pd.DataFrame:
    raw = load_scenarios()

    if not raw:
        return pd.DataFrame()

    rows = [normalize(s) for s in raw]
    df   = pd.DataFrame(rows)
    df["score"] = df.apply(compute_score, axis=1)
    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1

    return df


# =========================================================
# BEST SCENARIO
# =========================================================

def get_best_scenario(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {}

    best = df.iloc[0]

    return {
        "scenario_id": best["scenario_id"],
        "name":        best["name"],
        "score":       best["score"],
        "profit_gain": best["delta_profit"],   # kept for UI legacy
    }


if __name__ == "__main__":
    df = compare_scenarios()

    if df.empty:
        print("No scenarios found.")
    else:
        print("\n=== Scenario Ranking ===")
        print(df[["rank", "name", "discount_cap_pct", "paid_social_shift_pct",
                   "delta_profit", "delta_margin_pts", "score"]])
        print("\nBest scenario:")
        print(get_best_scenario(df))