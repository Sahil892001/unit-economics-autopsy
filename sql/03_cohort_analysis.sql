-- =====================================
-- COHORT & LTV ANALYSIS
-- =====================================

-- 1. Customer signup cohorts
WITH customer_cohorts AS (
    SELECT
        customer_id,
        strftime('%Y-%m', signup_date) AS cohort_month
    FROM customers
),

-- 2. Orders joined to cohorts
orders_with_cohorts AS (
    SELECT
        o.order_id,
        o.customer_id,
        c.cohort_month,
        strftime('%Y-%m', o.order_date) AS order_month
    FROM orders o
    JOIN customer_cohorts c
      ON o.customer_id = c.customer_id
),

-- 3. Unit economics joined
cohort_unit_economics AS (
    SELECT
        owc.cohort_month,
        owc.order_month,
        u.contribution_margin,
        u.net_revenue
    FROM orders_with_cohorts owc
    JOIN unit_economics u
      ON owc.order_id = u.order_id
)


-- 4. Cohort-level aggregation
SELECT
    cohort_month,
    order_month,
    COUNT(*) AS orders,
    ROUND(SUM(net_revenue), 2) AS revenue,
    ROUND(SUM(contribution_margin), 2) AS margin
FROM cohort_unit_economics
GROUP BY cohort_month, order_month
ORDER BY cohort_month, order_month;