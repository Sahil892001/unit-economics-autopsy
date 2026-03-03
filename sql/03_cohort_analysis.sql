-- =============================================================================
-- 03_cohort_analysis.sql
-- Unit Economics Intelligence Platform
-- =============================================================================
-- PURPOSE:
--   Cohort analysis tracks groups of customers acquired in the same month
--   and measures how their behaviour evolves over time.
--
--   WHY COHORTS MATTER:
--   Aggregate metrics like "avg LTV" hide the fact that recent cohorts
--   may be far worse than older ones. A business can look healthy in
--   aggregate while newer customers are destroying value.
--
--   KEY METRIC: Month-1 retention rate
--   If a cohort doesn't come back in Month 1, they almost never will.
--   M1 retention is the single strongest predictor of long-term LTV.
--
-- RUN AGAINST: unit_economics.db (SQLite)
-- =============================================================================


-- -----------------------------------------------------------------------------
-- QUERY 1: Cohort sizes — how many customers signed up each month?
-- WHY: Cohort analysis is only meaningful if we normalise by cohort size.
--      A cohort of 1,000 customers with 300 active in M3 is very different
--      from a cohort of 100 customers with 30 active.
-- -----------------------------------------------------------------------------
SELECT
    cohort                                  AS cohort_month,
    COUNT(DISTINCT customer_id)             AS cohort_size,
    acquisition_channel,
    COUNT(DISTINCT CASE WHEN acquisition_channel = 'Paid Search'
          THEN customer_id END)             AS paid_search_customers,
    COUNT(DISTINCT CASE WHEN acquisition_channel = 'Organic'
          THEN customer_id END)             AS organic_customers
FROM customers
GROUP BY cohort
ORDER BY cohort;


-- -----------------------------------------------------------------------------
-- QUERY 2: Orders per cohort per calendar month
-- WHY: The raw data for building a retention matrix.
--      cohort_month = when the customer signed up
--      order_month  = when they actually placed this order
--      months_since_signup = how far into their lifecycle this is
-- -----------------------------------------------------------------------------
WITH cohort_orders AS (
    SELECT
        u.cohort,
        u.order_month,
        u.months_since_signup,
        u.customer_id,
        u.contribution_margin,
        u.net_revenue
    FROM unit_economics u
)
SELECT
    cohort,
    order_month,
    months_since_signup,
    COUNT(DISTINCT customer_id)             AS active_customers,
    COUNT(*)                               AS orders,
    ROUND(SUM(net_revenue), 2)             AS revenue,
    ROUND(SUM(contribution_margin), 2)     AS margin,
    ROUND(AVG(contribution_margin), 2)     AS avg_margin_per_order
FROM cohort_orders
GROUP BY cohort, order_month, months_since_signup
ORDER BY cohort, months_since_signup;


-- -----------------------------------------------------------------------------
-- QUERY 3: Retention rate by cohort × month number
-- WHY: Core of cohort analysis. What % of original cohort still orders N months later?
--      INTERPRETATION GUIDE:
--        M1 >= 60%  → Healthy   |   M3 >= 30%  → Acceptable   |   M6 >= 15%  → Retained core
-- -----------------------------------------------------------------------------
WITH cohort_sizes AS (
    SELECT cohort, COUNT(DISTINCT customer_id) AS cohort_size
    FROM customers GROUP BY cohort
),
cohort_activity AS (
    SELECT cohort, months_since_signup,
           COUNT(DISTINCT customer_id) AS active_customers
    FROM unit_economics
    GROUP BY cohort, months_since_signup
)
SELECT ca.cohort, cs.cohort_size, ca.months_since_signup,
       ca.active_customers,
       ROUND(ca.active_customers * 1.0 / cs.cohort_size, 4) AS retention_rate
FROM cohort_activity ca
JOIN cohort_sizes cs ON ca.cohort = cs.cohort
ORDER BY ca.cohort, ca.months_since_signup;


-- QUERY 4: Cumulative LTV by cohort
-- WHY: High M1 retention cohorts (recent) have NEGATIVE LTV.
--      Older cohorts with lower M1 retention generate POSITIVE LTV.
--      This reveals an acquisition quality problem, not a retention problem.
-- -----------------------------------------------------------------------------
WITH cohort_sizes AS (
    SELECT cohort, COUNT(DISTINCT customer_id) AS cohort_size
    FROM customers GROUP BY cohort
),
cohort_monthly AS (
    SELECT cohort, months_since_signup,
           SUM(contribution_margin) AS monthly_margin
    FROM unit_economics GROUP BY cohort, months_since_signup
),
cohort_cumulative AS (
    SELECT cm.cohort, cm.months_since_signup, cm.monthly_margin,
           cs.cohort_size,
           SUM(cm2.monthly_margin) AS cumulative_margin
    FROM cohort_monthly cm
    JOIN cohort_sizes cs ON cm.cohort = cs.cohort
    JOIN cohort_monthly cm2
        ON cm.cohort = cm2.cohort
        AND cm2.months_since_signup <= cm.months_since_signup
    GROUP BY cm.cohort, cm.months_since_signup
)
SELECT cohort, cohort_size, months_since_signup,
       ROUND(monthly_margin, 2)                         AS monthly_margin,
       ROUND(cumulative_margin, 2)                      AS cumulative_margin,
       ROUND(cumulative_margin / cohort_size, 2)        AS cumulative_margin_per_customer
FROM cohort_cumulative
ORDER BY cohort, months_since_signup;


-- QUERY 5: Cohort quality summary — one row per cohort
-- WHY: Executive-level view. Rank cohorts by LTV and flag underperformers.
--      This is the table that goes into board presentations.
-- -----------------------------------------------------------------------------
WITH cohort_sizes AS (
    SELECT cohort, COUNT(DISTINCT customer_id) AS cohort_size
    FROM customers
    GROUP BY cohort
),
cohort_m1 AS (
    SELECT cohort, COUNT(DISTINCT customer_id) AS m1_active
    FROM unit_economics
    WHERE months_since_signup = 1
    GROUP BY cohort
),
cohort_m3 AS (
    SELECT cohort, COUNT(DISTINCT customer_id) AS m3_active
    FROM unit_economics
    WHERE months_since_signup = 3
    GROUP BY cohort
),
cohort_lifetime AS (
    SELECT
        cohort,
        COUNT(*)                            AS total_orders,
        ROUND(SUM(net_revenue), 2)         AS total_revenue,
        ROUND(SUM(contribution_margin), 2) AS total_margin
    FROM unit_economics
    GROUP BY cohort
)
SELECT
    cs.cohort,
    cs.cohort_size,
    ROUND(m1.m1_active * 1.0 / cs.cohort_size, 3)  AS m1_retention,
    ROUND(m3.m3_active * 1.0 / cs.cohort_size, 3)  AS m3_retention,
    cl.total_orders,
    ROUND(cl.total_revenue  / cs.cohort_size, 2)    AS avg_revenue_per_customer,
    ROUND(cl.total_margin   / cs.cohort_size, 2)    AS avg_ltv,
    CASE
        WHEN cl.total_margin / cs.cohort_size >= 50  THEN 'High Value'
        WHEN cl.total_margin / cs.cohort_size >= 0   THEN 'Positive'
        WHEN cl.total_margin / cs.cohort_size >= -30 THEN 'Marginal Loss'
        ELSE                                              'High Loss'
    END                                             AS cohort_health
FROM cohort_sizes cs
LEFT JOIN cohort_m1 m1       ON cs.cohort = m1.cohort
LEFT JOIN cohort_m3 m3       ON cs.cohort = m3.cohort
LEFT JOIN cohort_lifetime cl ON cs.cohort = cl.cohort
ORDER BY cs.cohort;