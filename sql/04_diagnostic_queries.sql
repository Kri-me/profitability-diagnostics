-- Diagnostic queries for the four profit leak hypotheses.
-- Run after sql/01_schema.sql, sql/02_load_csv.sql, and sql/03_kpi_views.sql.

-- 0. Executive trend check:
-- Is revenue growing while net margin weakens?
SELECT
    order_month,
    orders,
    round(net_revenue, 2) AS net_revenue,
    round(net_operating_profit, 2) AS net_operating_profit,
    round(gross_margin_pct * 100, 2) AS gross_margin_pct,
    round(net_margin_pct * 100, 2) AS net_margin_pct
FROM vw_monthly_profit_trend
ORDER BY order_month;

-- 1. Discount cannibalization:
-- Which discount bands produce revenue but destroy margin?
SELECT
    discount_band,
    count(*) AS orders,
    round(sum(net_revenue), 2) AS net_revenue,
    round(sum(discount_amount), 2) AS discount_amount,
    round(sum(gross_profit), 2) AS gross_profit,
    round(sum(net_operating_profit), 2) AS net_operating_profit,
    round(sum(gross_profit) / NULLIF(sum(net_revenue), 0) * 100, 2) AS gross_margin_pct,
    round(sum(net_operating_profit) / NULLIF(sum(net_revenue), 0) * 100, 2) AS net_margin_pct
FROM vw_order_profit
GROUP BY discount_band
ORDER BY net_margin_pct;

-- 1A. Discount cannibalization by segment:
-- Where would a discount cap be most useful?
SELECT
    segment,
    discount_band,
    count(*) AS orders,
    round(sum(net_revenue), 2) AS net_revenue,
    round(sum(net_operating_profit), 2) AS net_operating_profit,
    round(sum(net_operating_profit) / NULLIF(sum(net_revenue), 0) * 100, 2) AS net_margin_pct
FROM vw_order_profit
GROUP BY segment, discount_band
ORDER BY net_margin_pct;

-- 2. Logistics subsidization:
-- Which regions are being undercharged for shipping relative to carrier cost?
SELECT
    state_region,
    count(*) AS orders,
    round(sum(shipping_fee_charged), 2) AS shipping_fee_charged,
    round(sum(actual_shipping_cost), 2) AS actual_shipping_cost,
    round(sum(shipping_profit), 2) AS shipping_profit,
    round(avg(delivery_days), 2) AS avg_delivery_days,
    round(sum(net_operating_profit) / NULLIF(sum(net_revenue), 0) * 100, 2) AS net_margin_pct
FROM vw_order_profit
GROUP BY state_region
ORDER BY shipping_profit;

-- 2A. Logistics problem by region and discount band:
-- Do free/high-discount orders make remote shipping deficits worse?
SELECT
    state_region,
    discount_band,
    count(*) AS orders,
    round(avg(shipping_fee_charged), 2) AS avg_shipping_fee_charged,
    round(avg(actual_shipping_cost), 2) AS avg_actual_shipping_cost,
    round(avg(shipping_profit), 2) AS avg_shipping_profit,
    round(sum(net_operating_profit) / NULLIF(sum(net_revenue), 0) * 100, 2) AS net_margin_pct
FROM vw_order_profit
GROUP BY state_region, discount_band
ORDER BY avg_shipping_profit;

-- 3. Return-rate trap:
-- Which subcategories look attractive on sales but weak after returns and operating costs?
WITH item_allocations AS (
    SELECT
        item.*,
        op.return_handling_cost
            / NULLIF(count(*) OVER (PARTITION BY item.order_id), 0) AS allocated_return_handling_cost,
        op.net_operating_profit
            / NULLIF(count(*) OVER (PARTITION BY item.order_id), 0) AS allocated_net_operating_profit
    FROM vw_order_item_financials item
    JOIN vw_order_profit op
        ON item.order_id = op.order_id
)
SELECT
    category,
    subcategory,
    count(DISTINCT order_id) AS orders,
    sum(quantity) AS units_sold,
    sum(CASE WHEN is_returned THEN quantity ELSE 0 END) AS units_returned,
    round(
        sum(CASE WHEN is_returned THEN quantity ELSE 0 END)::numeric
        / NULLIF(sum(quantity), 0) * 100,
        2
    ) AS unit_return_rate_pct,
    round(sum(net_revenue), 2) AS net_revenue,
    round(sum(gross_profit), 2) AS gross_profit,
    round(sum(allocated_return_handling_cost), 2) AS allocated_return_handling_cost,
    round(sum(allocated_net_operating_profit), 2) AS allocated_net_operating_profit
FROM item_allocations
GROUP BY category, subcategory
ORDER BY unit_return_rate_pct DESC, allocated_net_operating_profit;

-- 4. Marketing cost outpacing customer value:
-- Which acquisition channels fail the LTV/CAC test?
SELECT
    acquisition_channel,
    customers,
    orders,
    round(avg_orders_per_customer, 2) AS avg_orders_per_customer,
    round(repeat_customer_rate * 100, 2) AS repeat_customer_rate_pct,
    round(avg_customer_cac, 2) AS avg_customer_cac,
    round(avg_customer_ltv, 2) AS avg_customer_ltv,
    round(avg_ltv_after_customer_cac, 2) AS avg_ltv_after_customer_cac,
    round(ltv_to_cac_ratio, 2) AS ltv_to_cac_ratio
FROM vw_channel_ltv_cac
ORDER BY avg_ltv_after_customer_cac;

-- 4A. Marketing channel by signup cohort:
-- Is acquisition quality getting better or worse over time?
SELECT
    date_trunc('month', signup_date)::date AS signup_month,
    acquisition_channel,
    count(*) AS customers,
    round(avg(order_count), 2) AS avg_orders_per_customer,
    round(avg(CASE WHEN is_repeat_customer THEN 1.0 ELSE 0.0 END) * 100, 2) AS repeat_customer_rate_pct,
    round(avg(acquisition_cost), 2) AS avg_customer_cac,
    round(avg(customer_ltv), 2) AS avg_customer_ltv,
    round(avg(ltv_after_customer_cac), 2) AS avg_ltv_after_customer_cac
FROM vw_customer_ltv
GROUP BY
    date_trunc('month', signup_date)::date,
    acquisition_channel
ORDER BY signup_month, acquisition_channel;

-- 5. Prioritization helper:
-- Which combinations have the largest negative profit pools?
SELECT
    segment,
    acquisition_channel,
    state_region,
    discount_band,
    count(*) AS orders,
    round(sum(net_revenue), 2) AS net_revenue,
    round(sum(net_operating_profit), 2) AS net_operating_profit,
    round(sum(net_operating_profit) / NULLIF(sum(net_revenue), 0) * 100, 2) AS net_margin_pct
FROM vw_order_profit
GROUP BY
    segment,
    acquisition_channel,
    state_region,
    discount_band
HAVING sum(net_operating_profit) < 0
ORDER BY net_operating_profit
LIMIT 20;
