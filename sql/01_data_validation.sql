-- =====================================
-- DATA VALIDATION CHECKS
-- =====================================

-- 1. Row counts by table
SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'costs', COUNT(*) FROM costs
UNION ALL
SELECT 'marketing_spend', COUNT(*) FROM marketing_spend
UNION ALL
SELECT 'support_tickets', COUNT(*) FROM support_tickets;

-- 2. Foreign key integrity: orders → customers
SELECT COUNT(*) AS orphan_orders
FROM orders o
LEFT JOIN customers c
  ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

-- 3. Revenue sanity check
SELECT
    COUNT(*) AS invalid_revenue_orders
FROM orders
WHERE order_value <= 0;

-- 4. Refund rate check
SELECT
    ROUND(AVG(refund_flag), 4) AS refund_rate
FROM orders;

-- 5. Cost anomaly scan (support costs)
SELECT
    COUNT(*) AS extreme_support_costs
FROM costs
WHERE support_cost > 500;

-- 6. Orders without cost records
SELECT COUNT(*) AS orders_missing_costs
FROM orders o
LEFT JOIN costs c
  ON o.order_id = c.order_id
WHERE c.order_id IS NULL;