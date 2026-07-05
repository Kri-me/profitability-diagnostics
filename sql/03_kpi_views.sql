-- KPI views for profitability diagnostics.
-- These views create one shared definition of revenue, cost, and profit.

CREATE OR REPLACE VIEW vw_order_item_financials AS
SELECT
    oi.order_item_id,
    oi.order_id,
    oi.product_id,
    p.product_name,
    p.category,
    p.subcategory,
    oi.quantity,
    p.standard_retail_price,
    oi.unit_price_sold,
    p.unit_cost,
    oi.is_returned,
    oi.quantity * p.standard_retail_price AS gross_revenue,
    oi.quantity * (p.standard_retail_price - oi.unit_price_sold) AS discount_amount,
    oi.quantity * oi.unit_price_sold AS net_revenue,
    oi.quantity * p.unit_cost AS cogs,
    oi.quantity * (oi.unit_price_sold - p.unit_cost) AS gross_profit
FROM order_items oi
JOIN products p
    ON oi.product_id = p.product_id;

CREATE OR REPLACE VIEW vw_order_profit AS
WITH item_rollup AS (
    SELECT
        order_id,
        count(*) AS line_item_count,
        sum(quantity) AS units_sold,
        sum(CASE WHEN is_returned THEN quantity ELSE 0 END) AS units_returned,
        sum(gross_revenue) AS gross_revenue,
        sum(discount_amount) AS discount_amount,
        sum(net_revenue) AS net_revenue,
        sum(cogs) AS cogs,
        sum(gross_profit) AS gross_profit
    FROM vw_order_item_financials
    GROUP BY order_id
),
monthly_order_counts AS (
    SELECT
        date_trunc('month', order_date)::date AS order_month,
        acquisition_channel,
        count(*) AS order_count
    FROM orders
    GROUP BY
        date_trunc('month', order_date)::date,
        acquisition_channel
),
marketing_allocation AS (
    SELECT
        moc.order_month,
        moc.acquisition_channel,
        ms.spend_amount / NULLIF(moc.order_count, 0) AS marketing_cost_per_order
    FROM monthly_order_counts moc
    LEFT JOIN marketing_spend ms
        ON moc.order_month = ms.month
        AND moc.acquisition_channel = ms.channel
)
SELECT
    o.order_id,
    o.customer_id,
    c.segment,
    c.state_region,
    o.order_date,
    date_trunc('month', o.order_date)::date AS order_month,
    o.acquisition_channel,
    o.promo_code,
    o.discount_pct,
    o.discount_band,
    o.shipping_fee_charged,
    f.shipping_carrier,
    f.actual_shipping_cost,
    o.shipping_fee_charged - f.actual_shipping_cost AS shipping_profit,
    f.delivery_days,
    f.return_handling_cost,
    f.support_tickets,
    f.support_tickets * 4.50 AS support_cost,
    COALESCE(ma.marketing_cost_per_order, 0) AS marketing_cost_per_order,
    ir.line_item_count,
    ir.units_sold,
    ir.units_returned,
    ir.units_returned::numeric / NULLIF(ir.units_sold, 0) AS unit_return_rate,
    ir.gross_revenue,
    ir.discount_amount,
    ir.net_revenue,
    ir.cogs,
    ir.gross_profit,
    ir.gross_profit / NULLIF(ir.net_revenue, 0) AS gross_margin_pct,
    (
        f.actual_shipping_cost
        + f.return_handling_cost
        + (f.support_tickets * 4.50)
    ) AS fulfillment_and_support_cost,
    (
        ir.gross_profit
        + o.shipping_fee_charged
        - f.actual_shipping_cost
        - f.return_handling_cost
        - (f.support_tickets * 4.50)
        - COALESCE(ma.marketing_cost_per_order, 0)
    ) AS net_operating_profit,
    (
        ir.gross_profit
        + o.shipping_fee_charged
        - f.actual_shipping_cost
        - f.return_handling_cost
        - (f.support_tickets * 4.50)
        - COALESCE(ma.marketing_cost_per_order, 0)
    ) / NULLIF(ir.net_revenue, 0) AS net_margin_pct
FROM orders o
JOIN customers c
    ON o.customer_id = c.customer_id
JOIN item_rollup ir
    ON o.order_id = ir.order_id
JOIN fulfillment f
    ON o.order_id = f.order_id
LEFT JOIN marketing_allocation ma
    ON date_trunc('month', o.order_date)::date = ma.order_month
    AND o.acquisition_channel = ma.acquisition_channel;

CREATE OR REPLACE VIEW vw_monthly_profit_trend AS
SELECT
    order_month,
    count(*) AS orders,
    sum(gross_revenue) AS gross_revenue,
    sum(discount_amount) AS discount_amount,
    sum(net_revenue) AS net_revenue,
    sum(cogs) AS cogs,
    sum(gross_profit) AS gross_profit,
    sum(actual_shipping_cost) AS actual_shipping_cost,
    sum(shipping_fee_charged) AS shipping_fee_charged,
    sum(return_handling_cost) AS return_handling_cost,
    sum(support_cost) AS support_cost,
    sum(marketing_cost_per_order) AS allocated_marketing_cost,
    sum(net_operating_profit) AS net_operating_profit,
    sum(gross_profit) / NULLIF(sum(net_revenue), 0) AS gross_margin_pct,
    sum(net_operating_profit) / NULLIF(sum(net_revenue), 0) AS net_margin_pct
FROM vw_order_profit
GROUP BY order_month;

CREATE OR REPLACE VIEW vw_customer_ltv AS
SELECT
    c.customer_id,
    c.segment,
    c.acquisition_channel,
    c.state_region,
    c.signup_date,
    c.acquisition_cost,
    count(op.order_id) AS order_count,
    min(op.order_date) AS first_order_date,
    max(op.order_date) AS last_order_date,
    COALESCE(sum(op.net_revenue), 0) AS lifetime_net_revenue,
    COALESCE(sum(op.net_operating_profit), 0) AS customer_ltv,
    COALESCE(sum(op.net_operating_profit), 0) - c.acquisition_cost AS ltv_after_customer_cac,
    CASE WHEN count(op.order_id) > 1 THEN true ELSE false END AS is_repeat_customer
FROM customers c
LEFT JOIN vw_order_profit op
    ON c.customer_id = op.customer_id
GROUP BY
    c.customer_id,
    c.segment,
    c.acquisition_channel,
    c.state_region,
    c.signup_date,
    c.acquisition_cost;

CREATE OR REPLACE VIEW vw_channel_ltv_cac AS
SELECT
    acquisition_channel,
    count(*) AS customers,
    sum(order_count) AS orders,
    avg(order_count) AS avg_orders_per_customer,
    avg(CASE WHEN is_repeat_customer THEN 1.0 ELSE 0.0 END) AS repeat_customer_rate,
    avg(acquisition_cost) AS avg_customer_cac,
    avg(customer_ltv) AS avg_customer_ltv,
    avg(ltv_after_customer_cac) AS avg_ltv_after_customer_cac,
    sum(lifetime_net_revenue) AS net_revenue,
    sum(customer_ltv) AS total_customer_ltv,
    sum(acquisition_cost) AS total_customer_cac,
    sum(customer_ltv) / NULLIF(sum(acquisition_cost), 0) AS ltv_to_cac_ratio
FROM vw_customer_ltv
GROUP BY acquisition_channel;

-- Export views consumed by scripts/run_pipeline.py OUTPUTS.

CREATE OR REPLACE VIEW monthly_trend_view AS
SELECT
    order_month,
    orders,
    round(net_revenue, 2) AS net_revenue,
    round(net_operating_profit, 2) AS net_operating_profit,
    round(gross_margin_pct * 100, 2) AS gross_margin_pct,
    round(net_margin_pct * 100, 2) AS net_margin_pct
FROM vw_monthly_profit_trend;

CREATE OR REPLACE VIEW discount_cannibalization_view AS
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
GROUP BY discount_band;

CREATE OR REPLACE VIEW logistics_subsidization_view AS
SELECT
    state_region,
    count(*) AS orders,
    round(sum(shipping_fee_charged), 2) AS shipping_fee_charged,
    round(sum(actual_shipping_cost), 2) AS actual_shipping_cost,
    round(sum(shipping_profit), 2) AS shipping_profit,
    round(avg(delivery_days), 2) AS avg_delivery_days,
    round(sum(net_operating_profit) / NULLIF(sum(net_revenue), 0) * 100, 2) AS net_margin_pct
FROM vw_order_profit
GROUP BY state_region;

CREATE OR REPLACE VIEW return_rate_trap_view AS
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
GROUP BY category, subcategory;

CREATE OR REPLACE VIEW channel_ltv_cac_view AS
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
FROM vw_channel_ltv_cac;

CREATE OR REPLACE VIEW prioritization_helper_view AS
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
