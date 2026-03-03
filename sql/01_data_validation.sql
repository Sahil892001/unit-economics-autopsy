-- =============================================================================
-- 01_data_validation.sql
-- Unit Economics Intelligence Platform
-- =============================================================================
-- PURPOSE:
--   Establish trust in the dataset before any analysis.
--   These checks mirror what a data engineer would run in a production
--   pipeline. Catching issues here prevents silent errors downstream.
--
-- RUN AGAINST: unit_economics.db (SQLite)
-- RUN ORDER:   Always first — before any analytical queries
-- =============================================================================


-- -----------------------------------------------------------------------------
-- CHECK 1: Row counts
-- WHY: Baseline sanity check. If counts are far from expected, data generation
--      or loading failed. Expected: ~20K customers, ~200K orders.
-- -----------------------------------------------------------------------------
SELECT 'customers'       AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL
SELECT 'orders',                         COUNT(*)             FROM orders
UNION ALL
SELECT 'costs',                          COUNT(*)             FROM costs
UNION ALL
SELECT 'marketing_spend',                COUNT(*)             FROM marketing_spend
UNION ALL
SELECT 'support_tickets',                COUNT(*)             FROM support_tickets
UNION ALL
SELECT 'unit_economics',                 COUNT(*)             FROM unit_economics;


-- -----------------------------------------------------------------------------
-- CHECK 2: Foreign key integrity — orders → customers
-- WHY: Orphaned orders (no matching customer) would silently corrupt any
--      customer-level aggregation like LTV or cohort analysis.
--      Expected result: 0 orphan_orders
-- -----------------------------------------------------------------------------
SELECT COUNT(*) AS orphan_orders
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;


-- -----------------------------------------------------------------------------
-- CHECK 3: Foreign key integrity — costs → orders
-- WHY: Orders missing cost records would show inflated margins.
--      Every order must have exactly one cost record.
--      Expected result: 0 orders_missing_costs
-- -----------------------------------------------------------------------------
SELECT COUNT(*) AS orders_missing_costs
FROM orders o
LEFT JOIN costs c ON o.order_id = c.order_id
WHERE c.order_id IS NULL;


-- -----------------------------------------------------------------------------
-- CHECK 4: Revenue sanity — no zero or negative order values
-- WHY: Zero-revenue orders skew avg order value and margin %.
--      Negative revenue would indicate a data entry error.
--      Expected result: 0 invalid_revenue_orders
-- -----------------------------------------------------------------------------
SELECT COUNT(*) AS invalid_revenue_orders
FROM orders
WHERE order_value <= 0;


-- -----------------------------------------------------------------------------
-- CHECK 5: Refund rate check
-- WHY: Refund rate should sit between 4–9% based on our data model.
--      If it spikes above 15% or drops to 0, something is wrong with
--      the refund_flag column (all 0s, all 1s, or corrupted values).
--      Expected result: ~0.05 (5%)
-- -----------------------------------------------------------------------------
SELECT
    ROUND(AVG(refund_flag), 4)                              AS overall_refund_rate,
    ROUND(AVG(CASE WHEN service_type = 'Express'  THEN CAST(refund_flag AS FLOAT) END), 4) AS express_refund_rate,
    ROUND(AVG(CASE WHEN service_type = 'Premium'  THEN CAST(refund_flag AS FLOAT) END), 4) AS premium_refund_rate,
    ROUND(AVG(CASE WHEN service_type = 'Standard' THEN CAST(refund_flag AS FLOAT) END), 4) AS standard_refund_rate
FROM orders;


-- -----------------------------------------------------------------------------
-- CHECK 6: Support cost outlier scan
-- WHY: Support costs follow a lognormal distribution with intentional outliers
--      at 8x the base. Outliers above ₹500 were capped during processing.
--      Any remaining values above ₹500 indicate the capping step was skipped.
--      Expected result: 0 extreme_support_costs (after processing)
-- -----------------------------------------------------------------------------
SELECT
    COUNT(*)                                    AS extreme_support_costs,
    ROUND(MAX(support_cost), 2)                 AS max_support_cost,
    ROUND(AVG(support_cost), 2)                 AS avg_support_cost,
    ROUND(SUM(CASE WHEN support_cost > 100
              THEN 1.0 ELSE 0 END) / COUNT(*), 4) AS pct_above_100
FROM costs;


-- -----------------------------------------------------------------------------
-- CHECK 7: Date range validation
-- WHY: All orders must fall within Jan 2024 – Dec 2025.
--      Any dates outside this range indicate a data generation or
--      timezone conversion error.
--      Expected result: min=2024-01-01, max=2025-12-31
-- -----------------------------------------------------------------------------
SELECT
    MIN(order_date) AS earliest_order,
    MAX(order_date) AS latest_order,
    COUNT(DISTINCT strftime('%Y-%m', order_date)) AS distinct_months
FROM orders;


-- -----------------------------------------------------------------------------
-- CHECK 8: Acquisition channel distribution
-- WHY: Channel mix should reflect our defined weights (Paid Search 45%,
--      Organic 30%, Referral 15%, Social 10%). Large deviations suggest
--      the generation weights were accidentally changed.
-- -----------------------------------------------------------------------------
SELECT
    acquisition_channel,
    COUNT(*)                                        AS customers,
    ROUND(COUNT(*) * 1.0 / SUM(COUNT(*)) OVER(), 3) AS share
FROM customers
GROUP BY acquisition_channel
ORDER BY customers DESC;


-- -----------------------------------------------------------------------------
-- CHECK 9: Unit economics completeness
-- WHY: Every order in unit_economics should have non-null revenue and margin.
--      Null contribution_margin would silently exclude orders from totals.
-- -----------------------------------------------------------------------------
SELECT
    COUNT(*)                                                         AS total_orders,
    SUM(CASE WHEN net_revenue        IS NULL THEN 1 ELSE 0 END)     AS null_revenue,
    SUM(CASE WHEN contribution_margin IS NULL THEN 1 ELSE 0 END)    AS null_margin,
    SUM(CASE WHEN total_cost          IS NULL THEN 1 ELSE 0 END)    AS null_cost
FROM unit_economics;