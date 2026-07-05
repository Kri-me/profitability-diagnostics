from __future__ import annotations

from pathlib import Path
import pandas as pd


# =========================================================
# PATH CONFIG
# =========================================================

from src.core.paths import DRIVERS_PATH


# =========================================================
# LOAD DRIVER DATA
# =========================================================

def load_driver_data() -> pd.DataFrame:
    """
    Loads driver importance output from EDA / ML stage.
    Expected columns (flexible but preferred):
        - feature / driver
        - importance OR coefficient OR score
    """

    if not DRIVERS_PATH.exists():
        return pd.DataFrame()

    df = pd.read_csv(DRIVERS_PATH)

    # normalize column names
    df.columns = [c.lower().strip() for c in df.columns]

    return df


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_drivers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts different model outputs into a unified schema:
    driver | impact_score
    """

    if df.empty:
        return df

    # detect likely feature column
    feature_col = None
    for c in df.columns:
        if c in ["feature", "driver", "variable", "name"]:
            feature_col = c
            break

    # detect importance column with preference ranking
    preferred_score_cols = [
        "combined_score",
        "importance",
        "abs_coef",
        "rf_importance",
        "ridge_importance",
        "coefficient",
        "score",
        "coef",
        "impact"
    ]
    score_col = None
    for pref in preferred_score_cols:
        if pref in df.columns:
            score_col = pref
            break

    if not feature_col or not score_col:
        return pd.DataFrame()

    out = pd.DataFrame({
        "driver": df[feature_col],
        "impact_score": df[score_col]
    })

    # absolute impact (for ranking stability)
    out["abs_impact"] = out["impact_score"].abs()

    return out


# =========================================================
# CORE ANALYTICS
# =========================================================

def get_top_drivers(n: int = 10) -> pd.DataFrame:
    """
    Returns top drivers sorted by absolute impact.
    """

    raw = load_driver_data()

    if raw.empty:
        return pd.DataFrame()

    df = normalize_drivers(raw)

    if df.empty:
        return df

    df = df.sort_values("abs_impact", ascending=False).head(n)

    return df.reset_index(drop=True)


# =========================================================
# DRIVER INSIGHT LOGIC
# =========================================================

def categorize_drivers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds simple interpretability layer.
    """

    if df.empty:
        return df

    def label(x):
        x = str(x).lower()

        if "discount" in x:
            return "Pricing / Discounting"
        if "cac" in x or "marketing" in x:
            return "Marketing Efficiency"
        if "ship" in x or "logistic" in x:
            return "Logistics"
        if "return" in x:
            return "Returns"
        if "region" in x or "state" in x:
            return "Geography"
        if "product" in x or "category" in x:
            return "Product Mix"
        return "Other"

    df["category"] = df["driver"].apply(label)

    return df


# =========================================================
# PUBLIC API FOR DASHBOARD
# =========================================================

def get_driver_insights(n: int = 10) -> pd.DataFrame:
    """
    Main dashboard entrypoint.
    """

    df = get_top_drivers(n)

    if df.empty:
        return df

    df = categorize_drivers(df)

    return df