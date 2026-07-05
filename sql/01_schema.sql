-- Project 1: Profitability Diagnostics
-- PostgreSQL schema for Apex Global synthetic transaction data.

------------------------------------------------------------
-- 1. DROP VIEWS (MOST DEPENDENT FIRST)
------------------------------------------------------------

DROP VIEW IF EXISTS prioritization_helper_view;
DROP VIEW IF EXISTS channel_ltv_cac_view;
DROP VIEW IF EXISTS return_rate_trap_view;
DROP VIEW IF EXISTS logistics_subsidization_view;
DROP VIEW IF EXISTS discount_cannibalization_view;

DROP VIEW IF EXISTS discount_by_segment_view;
DROP VIEW IF EXISTS logistics_by_region_discount_view;

DROP VIEW IF EXISTS monthly_trend_view;
DROP VIEW IF EXISTS vw_channel_ltv_cac;
DROP VIEW IF EXISTS vw_customer_ltv;
DROP VIEW IF EXISTS vw_monthly_profit_trend;

DROP VIEW IF EXISTS vw_order_profit;
DROP VIEW IF EXISTS vw_order_item_financials;

------------------------------------------------------------
-- 2. DROP TABLES (AFTER VIEWS)
------------------------------------------------------------

DROP TABLE IF EXISTS marketing_spend;
DROP TABLE IF EXISTS fulfillment;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

------------------------------------------------------------
-- 3. CREATE TABLES
------------------------------------------------------------

CREATE TABLE customers (
    customer_id integer PRIMARY KEY,
    segment varchar(30) NOT NULL,
    acquisition_channel varchar(30) NOT NULL,
    acquisition_cost numeric(10, 2) NOT NULL CHECK (acquisition_cost >= 0),
    state_region varchar(30) NOT NULL,
    signup_date date NOT NULL,
    satisfaction_score numeric(3, 1) CHECK (
        satisfaction_score >= 1
        AND satisfaction_score <= 10
    )
);

CREATE TABLE products (
    product_id integer PRIMARY KEY,
    product_name varchar(120) NOT NULL,
    category varchar(40) NOT NULL,
    subcategory varchar(60) NOT NULL,
    unit_cost numeric(10, 2) NOT NULL CHECK (unit_cost >= 0),
    standard_retail_price numeric(10, 2) NOT NULL CHECK (standard_retail_price >= 0),
    return_rate_pct numeric(8, 4) NOT NULL CHECK (
        return_rate_pct >= 0
        AND return_rate_pct <= 1
    ),
    weight_lbs numeric(8, 2) NOT NULL CHECK (weight_lbs >= 0)
);

CREATE TABLE orders (
    order_id integer PRIMARY KEY,
    customer_id integer NOT NULL REFERENCES customers(customer_id),
    order_date date NOT NULL,
    acquisition_channel varchar(30) NOT NULL,
    promo_code varchar(40),
    discount_pct numeric(8, 4) NOT NULL CHECK (
        discount_pct >= 0
        AND discount_pct <= 1
    ),
    discount_band varchar(30) NOT NULL,
    shipping_fee_charged numeric(10, 2) NOT NULL CHECK (shipping_fee_charged >= 0)
);

CREATE TABLE order_items (
    order_item_id integer PRIMARY KEY,
    order_id integer NOT NULL REFERENCES orders(order_id),
    product_id integer NOT NULL REFERENCES products(product_id),
    quantity integer NOT NULL CHECK (quantity > 0),
    unit_price_sold numeric(10, 2) NOT NULL CHECK (unit_price_sold >= 0),
    is_returned boolean NOT NULL
);

CREATE TABLE fulfillment (
    order_id integer PRIMARY KEY REFERENCES orders(order_id),
    shipping_carrier varchar(30) NOT NULL,
    actual_shipping_cost numeric(10, 2) NOT NULL CHECK (actual_shipping_cost >= 0),
    delivery_days integer NOT NULL CHECK (delivery_days > 0),
    return_handling_cost numeric(10, 2) NOT NULL CHECK (return_handling_cost >= 0),
    support_tickets integer NOT NULL CHECK (support_tickets >= 0)
);

CREATE TABLE marketing_spend (
    month date NOT NULL,
    channel varchar(30) NOT NULL,
    spend_amount numeric(12, 2) NOT NULL CHECK (spend_amount >= 0),
    new_customers_acquired integer NOT NULL CHECK (new_customers_acquired >= 0),
    PRIMARY KEY (month, channel)
);

------------------------------------------------------------
-- 4. INDEXES
------------------------------------------------------------

CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_orders_discount_band ON orders(discount_band);
CREATE INDEX idx_orders_acquisition_channel ON orders(acquisition_channel);

CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);

CREATE INDEX idx_products_category ON products(category, subcategory);
CREATE INDEX idx_customers_region ON customers(state_region);

CREATE INDEX idx_marketing_spend_channel_month ON marketing_spend(channel, month);