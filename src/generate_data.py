"""Generate synthetic data for the Apex Global profitability diagnostic.

The dataset intentionally contains competing profit leaks:
1. high discounts that lift revenue while compressing margin
2. Paid Social customers with high CAC and weak repeat behavior

Run from the project root:
    python src/generate_data.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RNG = np.random.default_rng(42)


@dataclass(frozen=True)
class GeneratorConfig:
    n_customers: int = 4_000
    n_products: int = 120
    start_date: str = "2024-01-01"
    periods: int = 18
    output_dir: Path = DATA_DIR


REGIONS = ["Metro", "Suburban", "Rural", "Remote"]
SEGMENTS = ["Retail", "Corporate", "Wholesale"]
CHANNELS = ["Organic", "Paid Social", "Email", "Referral"]
PRODUCT_CATEGORIES = {
    "Electronics": ["Budget Electronics", "Premium Electronics", "Accessories"],
    "Apparel": ["Everyday Apparel", "Luxury Apparel", "Footwear"],
    "Home": ["Kitchen", "Decor", "Furniture"],
    "Sports": ["Fitness", "Outdoor", "Team Sports"],
}


def clip(values: np.ndarray, low: float, high: float) -> np.ndarray:
    return np.clip(values, low, high)


def month_starts(config: GeneratorConfig) -> pd.DatetimeIndex:
    return pd.date_range(config.start_date, periods=config.periods, freq="MS")


def generate_customers(config: GeneratorConfig) -> pd.DataFrame:
    months = month_starts(config)
    channels = RNG.choice(
        CHANNELS,
        size=config.n_customers,
        p=[0.30, 0.34, 0.20, 0.16],
    )
    segments = RNG.choice(SEGMENTS, size=config.n_customers, p=[0.68, 0.22, 0.10])
    regions = RNG.choice(REGIONS, size=config.n_customers, p=[0.42, 0.30, 0.18, 0.10])
    signup_months = RNG.choice(months, size=config.n_customers)

    channel_cac = {
        "Organic": (8, 4),
        "Paid Social": (62, 18),
        "Email": (18, 8),
        "Referral": (24, 10),
    }
    acquisition_cost = np.array(
        [
            max(0, RNG.normal(channel_cac[channel][0], channel_cac[channel][1]))
            for channel in channels
        ]
    )

    satisfaction_base = {
        "Organic": 7.6,
        "Paid Social": 6.1,
        "Email": 7.2,
        "Referral": 7.8,
    }
    satisfaction_score = np.array(
        [RNG.normal(satisfaction_base[channel], 1.2) for channel in channels]
    )

    return pd.DataFrame(
        {
            "customer_id": np.arange(1, config.n_customers + 1),
            "segment": segments,
            "acquisition_channel": channels,
            "acquisition_cost": acquisition_cost.round(2),
            "state_region": regions,
            "signup_date": pd.to_datetime(signup_months)
            + pd.to_timedelta(RNG.integers(0, 28, config.n_customers), unit="D"),
            "satisfaction_score": clip(satisfaction_score, 1, 10).round(1),
        }
    )


def generate_products(config: GeneratorConfig) -> pd.DataFrame:
    rows = []
    product_id = 1

    for category, subcategories in PRODUCT_CATEGORIES.items():
        for subcategory in subcategories:
            for _ in range(config.n_products // 12):
                if category == "Electronics":
                    retail_price = RNG.uniform(65, 650)
                    margin = RNG.uniform(0.24, 0.42)
                    return_rate = RNG.uniform(0.10, 0.24)
                    weight = RNG.uniform(0.5, 8.0)
                elif category == "Apparel":
                    retail_price = RNG.uniform(25, 220)
                    margin = RNG.uniform(0.45, 0.65)
                    return_rate = RNG.uniform(0.18, 0.36)
                    weight = RNG.uniform(0.2, 2.0)
                elif category == "Home":
                    retail_price = RNG.uniform(35, 420)
                    margin = RNG.uniform(0.32, 0.55)
                    return_rate = RNG.uniform(0.06, 0.16)
                    weight = RNG.uniform(1.0, 18.0)
                else:
                    retail_price = RNG.uniform(20, 300)
                    margin = RNG.uniform(0.35, 0.58)
                    return_rate = RNG.uniform(0.05, 0.15)
                    weight = RNG.uniform(0.4, 6.0)

                if "Luxury Apparel" in subcategory:
                    return_rate = RNG.uniform(0.30, 0.38)
                if "Budget Electronics" in subcategory:
                    margin = RNG.uniform(0.18, 0.30)

                unit_cost = retail_price * (1 - margin)
                rows.append(
                    {
                        "product_id": product_id,
                        "product_name": f"{subcategory} SKU {product_id:03d}",
                        "category": category,
                        "subcategory": subcategory,
                        "unit_cost": round(unit_cost, 2),
                        "standard_retail_price": round(retail_price, 2),
                        "return_rate_pct": round(return_rate, 4),
                        "weight_lbs": round(weight, 2),
                    }
                )
                product_id += 1

    return pd.DataFrame(rows)


def monthly_order_targets(months: pd.DatetimeIndex) -> dict[pd.Timestamp, int]:
    targets = {}
    for idx, month in enumerate(months):
        trend = 620 + idx * 44
        seasonality = 85 * np.sin((idx / 12) * 2 * np.pi)
        noise = RNG.normal(0, 25)
        targets[month] = int(max(350, trend + seasonality + noise))
    return targets


def customer_repeat_weights(customers: pd.DataFrame, order_month: pd.Timestamp) -> np.ndarray:
    eligible = customers["signup_date"] <= order_month + pd.offsets.MonthEnd(0)
    months_since_signup = (
        (order_month.year - customers["signup_date"].dt.year) * 12
        + (order_month.month - customers["signup_date"].dt.month)
    ).clip(lower=0)

    channel_weight = customers["acquisition_channel"].map(
        {
            "Organic": 1.15,
            "Paid Social": 0.52,
            "Email": 1.30,
            "Referral": 1.45,
        }
    )
    segment_weight = customers["segment"].map(
        {"Retail": 1.00, "Corporate": 1.25, "Wholesale": 1.10}
    )
    recency_weight = 1 + np.sqrt(months_since_signup) / 5
    weights = eligible.astype(float) * channel_weight * segment_weight * recency_weight
    weights = weights.to_numpy()
    return weights / weights.sum()


def generate_orders(config: GeneratorConfig, customers: pd.DataFrame) -> pd.DataFrame:
    months = month_starts(config)
    order_targets = monthly_order_targets(months)
    customer_lookup = customers.set_index("customer_id")
    rows = []
    order_id = 1

    discount_probs_early = [0.40, 0.28, 0.22, 0.10]
    discount_probs_late = [0.22, 0.24, 0.26, 0.28]

    for month_index, month in enumerate(months):
        probs = np.linspace(discount_probs_early, discount_probs_late, config.periods)[
            month_index
        ]
        customer_probs = customer_repeat_weights(customers, month)
        selected_customers = RNG.choice(
            customers["customer_id"],
            size=order_targets[month],
            p=customer_probs,
            replace=True,
        )

        for customer_id in selected_customers:
            customer = customer_lookup.loc[customer_id]
            order_date = month + pd.to_timedelta(int(RNG.integers(0, 28)), unit="D")
            discount_band = RNG.choice(
                ["No Discount", "Low", "Mid", "High"],
                p=probs / probs.sum(),
            )
            if customer["acquisition_channel"] == "Paid Social":
                discount_band = RNG.choice(
                    ["No Discount", "Low", "Mid", "High"],
                    p=[0.12, 0.20, 0.28, 0.40],
                )
            if discount_band == "No Discount":
                discount_pct = 0.0
                promo_code = None
            elif discount_band == "Low":
                discount_pct = float(RNG.uniform(0.05, 0.10))
                promo_code = "WELCOME10"
            elif discount_band == "Mid":
                discount_pct = float(RNG.uniform(0.10, 0.20))
                promo_code = "SAVE15"
            else:
                discount_pct = float(RNG.uniform(0.22, 0.40))
                promo_code = "FLASH30"

            shipping_fee = {
                "Metro": 7.99,
                "Suburban": 8.99,
                "Rural": 9.99,
                "Remote": 10.99,
            }[customer["state_region"]]
            if discount_band == "High" or RNG.random() < 0.24:
                shipping_fee = 0.0

            rows.append(
                {
                    "order_id": order_id,
                    "customer_id": int(customer_id),
                    "order_date": order_date,
                    "acquisition_channel": customer["acquisition_channel"],
                    "promo_code": promo_code,
                    "discount_pct": round(discount_pct, 4),
                    "discount_band": discount_band,
                    "shipping_fee_charged": round(shipping_fee, 2),
                }
            )
            order_id += 1

    return pd.DataFrame(rows)


def generate_order_items(
    orders: pd.DataFrame, products: pd.DataFrame, customers: pd.DataFrame
) -> pd.DataFrame:
    rows = []
    order_item_id = 1
    category_weights = np.array([0.28, 0.34, 0.22, 0.16])
    categories = np.array(list(PRODUCT_CATEGORIES.keys()))
    customer_lookup = customers.set_index("customer_id")
    products_by_category = {
        category: frame.reset_index(drop=True)
        for category, frame in products.groupby("category")
    }

    for order in orders.itertuples(index=False):
        n_items = int(RNG.choice([1, 2, 3, 4], p=[0.55, 0.28, 0.12, 0.05]))
        customer = customer_lookup.loc[order.customer_id]
        adjusted_weights = category_weights.copy()
        if order.acquisition_channel == "Paid Social":
            adjusted_weights += np.array([0.06, 0.08, -0.06, -0.08])
        if customer["segment"] == "Wholesale":
            adjusted_weights += np.array([0.03, -0.08, 0.08, -0.03])
        adjusted_weights = adjusted_weights / adjusted_weights.sum()

        for _ in range(n_items):
            category = RNG.choice(categories, p=adjusted_weights)
            candidates = products_by_category[category]
            product = candidates.iloc[int(RNG.integers(0, len(candidates)))]
            quantity = int(RNG.choice([1, 2, 3, 4, 5], p=[0.62, 0.22, 0.09, 0.05, 0.02]))
            if customer["segment"] == "Wholesale":
                quantity += int(RNG.choice([0, 1, 2, 3], p=[0.40, 0.30, 0.20, 0.10]))

            return_probability = product["return_rate_pct"]
            if customer["satisfaction_score"] < 6:
                return_probability += 0.05
            if order.discount_band == "High":
                return_probability += 0.03
            is_returned = bool(RNG.random() < min(return_probability, 0.55))
            unit_price_sold = product["standard_retail_price"] * (1 - order.discount_pct)

            rows.append(
                {
                    "order_item_id": order_item_id,
                    "order_id": order.order_id,
                    "product_id": int(product["product_id"]),
                    "quantity": quantity,
                    "unit_price_sold": round(unit_price_sold, 2),
                    "is_returned": is_returned,
                }
            )
            order_item_id += 1

    return pd.DataFrame(rows)


def generate_fulfillment(
    orders: pd.DataFrame,
    order_items: pd.DataFrame,
    products: pd.DataFrame,
    customers: pd.DataFrame,
) -> pd.DataFrame:
    item_products = order_items.merge(products[["product_id", "weight_lbs"]], on="product_id")
    order_weight = (
        item_products.assign(total_weight=lambda df: df["quantity"] * df["weight_lbs"])
        .groupby("order_id", as_index=False)["total_weight"]
        .sum()
    )
    returned_items = (
        order_items.groupby("order_id", as_index=False)["is_returned"]
        .sum()
        .rename(columns={"is_returned": "returned_item_count"})
    )
    base = (
        orders[["order_id", "customer_id"]]
        .merge(order_weight, on="order_id", how="left")
        .merge(returned_items, on="order_id", how="left")
        .merge(customers[["customer_id", "state_region"]], on="customer_id", how="left")
    )
    base["returned_item_count"] = base["returned_item_count"].fillna(0)

    carrier_choices = np.array(["DHL", "FedEx", "UPS", "Standard"])
    rows = []
    for row in base.itertuples(index=False):
        region_multiplier = {
            "Metro": 1.00,
            "Suburban": 1.15,
            "Rural": 1.55,
            "Remote": 2.65,
        }[row.state_region]
        carrier = RNG.choice(carrier_choices, p=[0.12, 0.26, 0.24, 0.38])
        carrier_multiplier = {
            "DHL": 1.35,
            "FedEx": 1.20,
            "UPS": 1.12,
            "Standard": 0.92,
        }[carrier]
        actual_shipping_cost = (
            5.50 + row.total_weight * 0.82
        ) * region_multiplier * carrier_multiplier
        delivery_days = int(
            round(
                RNG.normal(
                    {"Metro": 2.0, "Suburban": 3.0, "Rural": 4.6, "Remote": 6.5}[
                        row.state_region
                    ],
                    0.9,
                )
            )
        )
        delivery_days = max(1, delivery_days)
        return_handling_cost = row.returned_item_count * RNG.uniform(6.0, 14.0)
        support_tickets = int(RNG.poisson(0.18))
        if delivery_days > 5:
            support_tickets += int(RNG.random() < 0.35)
        if row.returned_item_count > 0:
            support_tickets += int(RNG.random() < 0.45)

        rows.append(
            {
                "order_id": row.order_id,
                "shipping_carrier": carrier,
                "actual_shipping_cost": round(actual_shipping_cost, 2),
                "delivery_days": delivery_days,
                "return_handling_cost": round(return_handling_cost, 2),
                "support_tickets": support_tickets,
            }
        )

    return pd.DataFrame(rows)


def generate_marketing_spend(
    config: GeneratorConfig, customers: pd.DataFrame
) -> pd.DataFrame:
    months = month_starts(config)
    customers = customers.assign(month=customers["signup_date"].dt.to_period("M").dt.to_timestamp())
    acquired = (
        customers.groupby(["month", "acquisition_channel"], as_index=False)
        .size()
        .rename(columns={"acquisition_channel": "channel", "size": "new_customers_acquired"})
    )

    rows = []
    for month_index, month in enumerate(months):
        for channel in CHANNELS:
            customer_count = acquired.loc[
                (acquired["month"] == month) & (acquired["channel"] == channel),
                "new_customers_acquired",
            ]
            new_customers = int(customer_count.iloc[0]) if not customer_count.empty else 0
            if channel == "Paid Social":
                spend_per_customer = RNG.normal(68 + month_index * 1.8, 7)
                base_spend = 2_500 + month_index * 280
            elif channel == "Email":
                spend_per_customer = RNG.normal(20, 4)
                base_spend = 900 + month_index * 40
            elif channel == "Referral":
                spend_per_customer = RNG.normal(28, 5)
                base_spend = 700 + month_index * 35
            else:
                spend_per_customer = RNG.normal(10, 3)
                base_spend = 1_100 + month_index * 55

            spend = max(0, base_spend + new_customers * spend_per_customer)
            rows.append(
                {
                    "month": month,
                    "channel": channel,
                    "spend_amount": round(spend, 2),
                    "new_customers_acquired": new_customers,
                }
            )

    return pd.DataFrame(rows)


def write_tables(tables: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(output_dir / f"{name}.csv", index=False)


def calculate_order_profit(
    orders: pd.DataFrame,
    order_items: pd.DataFrame,
    products: pd.DataFrame,
    fulfillment: pd.DataFrame,
    marketing_spend: pd.DataFrame,
) -> pd.DataFrame:
    item_profit = order_items.merge(products, on="product_id")
    item_profit = item_profit.assign(
        gross_revenue=lambda df: df["quantity"] * df["standard_retail_price"],
        net_revenue=lambda df: df["quantity"] * df["unit_price_sold"],
        cogs=lambda df: df["quantity"] * df["unit_cost"],
    )
    order_profit = (
        item_profit.groupby("order_id", as_index=False)
        .agg(
            gross_revenue=("gross_revenue", "sum"),
            net_revenue=("net_revenue", "sum"),
            cogs=("cogs", "sum"),
            returned_items=("is_returned", "sum"),
        )
        .merge(orders, on="order_id")
        .merge(fulfillment, on="order_id")
    )

    channel_month_spend = marketing_spend.assign(
        order_month=marketing_spend["month"].dt.to_period("M").dt.to_timestamp()
    )
    order_counts = orders.assign(
        order_month=orders["order_date"].dt.to_period("M").dt.to_timestamp()
    ).groupby(["order_month", "acquisition_channel"], as_index=False).size()
    marketing_allocation = order_counts.merge(
        channel_month_spend,
        left_on=["order_month", "acquisition_channel"],
        right_on=["order_month", "channel"],
        how="left",
    )
    marketing_allocation["marketing_cost_per_order"] = (
        marketing_allocation["spend_amount"] / marketing_allocation["size"]
    )

    order_profit = order_profit.assign(
        order_month=order_profit["order_date"].dt.to_period("M").dt.to_timestamp()
    ).merge(
        marketing_allocation[
            ["order_month", "acquisition_channel", "marketing_cost_per_order"]
        ],
        on=["order_month", "acquisition_channel"],
        how="left",
    )
    order_profit["support_cost"] = order_profit["support_tickets"] * 4.50
    order_profit["gross_profit"] = order_profit["net_revenue"] - order_profit["cogs"]
    order_profit["net_operating_profit"] = (
        order_profit["gross_profit"]
        + order_profit["shipping_fee_charged"]
        - order_profit["actual_shipping_cost"]
        - order_profit["return_handling_cost"]
        - order_profit["support_cost"]
        - order_profit["marketing_cost_per_order"]
    )
    order_profit["net_margin_pct"] = (
        order_profit["net_operating_profit"] / order_profit["net_revenue"]
    )
    return order_profit


def validation_summary(
    tables: dict[str, pd.DataFrame],
    order_profit: pd.DataFrame,
) -> pd.DataFrame:
    monthly = (
        order_profit.groupby("order_month", as_index=False)
        .agg(
            gross_revenue=("gross_revenue", "sum"),
            net_revenue=("net_revenue", "sum"),
            net_operating_profit=("net_operating_profit", "sum"),
        )
        .assign(net_margin_pct=lambda df: df["net_operating_profit"] / df["net_revenue"])
    )
    discount = (
        order_profit.groupby("discount_band", as_index=False)
        .agg(
            orders=("order_id", "count"),
            net_revenue=("net_revenue", "sum"),
            net_margin_pct=("net_margin_pct", "mean"),
        )
        .sort_values("net_margin_pct")
    )
    channel = (
        order_profit.groupby("acquisition_channel", as_index=False)
        .agg(
            orders=("order_id", "count"),
            net_revenue=("net_revenue", "sum"),
            net_operating_profit=("net_operating_profit", "sum"),
        )
        .assign(net_margin_pct=lambda df: df["net_operating_profit"] / df["net_revenue"])
        .sort_values("net_margin_pct")
    )

    checks = {
        "customers": len(tables["customers"]),
        "products": len(tables["products"]),
        "orders": len(tables["orders"]),
        "order_items": len(tables["order_items"]),
        "fulfillment": len(tables["fulfillment"]),
        "marketing_spend": len(tables["marketing_spend"]),
        "revenue_growth_pct": (
            monthly.tail(3)["net_revenue"].mean()
            / monthly.head(3)["net_revenue"].mean()
            - 1
        )
        * 100,
        "net_margin_first_3_months_pct": monthly.head(3)["net_margin_pct"].mean() * 100,
        "net_margin_last_3_months_pct": monthly.tail(3)["net_margin_pct"].mean() * 100,
        "worst_discount_band": discount.iloc[0]["discount_band"],
        "worst_channel": channel.iloc[0]["acquisition_channel"],
    }
    return pd.DataFrame([checks])


def generate_all(config: GeneratorConfig) -> dict[str, pd.DataFrame]:
    customers = generate_customers(config)
    products = generate_products(config)
    orders = generate_orders(config, customers)
    order_items = generate_order_items(orders, products, customers)
    fulfillment = generate_fulfillment(orders, order_items, products, customers)
    marketing_spend = generate_marketing_spend(config, customers)
    return {
        "customers": customers,
        "products": products,
        "orders": orders,
        "order_items": order_items,
        "fulfillment": fulfillment,
        "marketing_spend": marketing_spend,
    }


def main() -> None:
    config = GeneratorConfig()
    tables = generate_all(config)
    order_profit = calculate_order_profit(
        tables["orders"],
        tables["order_items"],
        tables["products"],
        tables["fulfillment"],
        tables["marketing_spend"],
    )
    summary = validation_summary(tables, order_profit)
    tables["validation_order_profit"] = order_profit
    tables["validation_summary"] = summary
    write_tables(tables, config.output_dir)

    print("Generated synthetic profitability dataset")
    print(f"Output directory: {config.output_dir}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
