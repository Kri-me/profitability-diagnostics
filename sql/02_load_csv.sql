-- Load generated CSVs into PostgreSQL.
-- Run from the project root after running sql/01_schema.sql.
--
-- Example:
--   psql -d profitability_diagnostics -f sql/01_schema.sql
--   psql -d profitability_diagnostics -f sql/02_load_csv.sql



SELECT 'customers' AS table_name, count(*) AS row_count FROM customers
UNION ALL
SELECT 'products', count(*) FROM products
UNION ALL
SELECT 'orders', count(*) FROM orders
UNION ALL
SELECT 'order_items', count(*) FROM order_items
UNION ALL
SELECT 'fulfillment', count(*) FROM fulfillment
UNION ALL
SELECT 'marketing_spend', count(*) FROM marketing_spend
ORDER BY table_name;
