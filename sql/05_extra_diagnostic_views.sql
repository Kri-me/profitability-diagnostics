-- Additional diagnostic views needed by the dashboard.
-- These formalize the ad-hoc breakdowns from 04_diagnostic_queries.sql
-- (queries 1A and 2A) as reusable views, following the same pattern as
-- 03_kpi_views.sql.
--
-- Run after sql/01_schema.sql, sql/02_load_csv.sql, and sql/03_kpi_views.sql.

DROP VIEW IF EXISTS logistics_by_region_discount_view;
DROP VIEW IF EXISTS discount_by_segment_view;

-- 1A. Discount cannibalization by segment:
-- Where would a discount cap be most useful?
CREATE OR REPLACE VIEW discount_by_segment_view AS
SELECT
    segment,
    discount_band,
    count(*) AS orders,
    round(sum(net_revenue), 2) AS net_revenue,
    round(sum(net_operating_profit), 2) AS net_operating_profit,
    round(sum(net_operating_profit) / NULLIF(sum(net_revenue), 0) * 100, 2) AS net_margin_pct
FROM vw_order_profit
GROUP BY segment, discount_band;

-- 2A. Logistics problem by region and discount band:
-- Do free/high-discount orders make remote shipping deficits worse?
CREATE OR REPLACE VIEW logistics_by_region_discount_view AS
SELECT
    state_region,
    discount_band,
    count(*) AS orders,
    round(avg(shipping_fee_charged), 2) AS avg_shipping_fee_charged,
    round(avg(actual_shipping_cost), 2) AS avg_actual_shipping_cost,
    round(avg(shipping_profit), 2) AS avg_shipping_profit,
    round(sum(net_operating_profit) / NULLIF(sum(net_revenue), 0) * 100, 2) AS net_margin_pct
FROM vw_order_profit
GROUP BY state_region, discount_band;
