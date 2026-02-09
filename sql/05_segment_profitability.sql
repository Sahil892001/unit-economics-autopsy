-- =====================================
-- SEGMENT PROFITABILITY ANALYSIS
-- =====================================

-- 1. Profitability by region
SELECT
    c.region,
    COUNT(*) AS orders,
    ROUND(AVG(u.contribution_margin), 2) AS avg_margin,
    ROUND(SUM(u.contribution_margin), 2) AS total_margin
FROM unit_economics u
JOIN orders o
  ON u.order_id = o.order_id
JOIN customers c
  ON o.customer_id = c.customer_id
GROUP BY c.region
ORDER BY total_margin ASC;

-- 2. Profitability by service type
SELECT
    u.service_type,
    COUNT(*) AS orders,
    ROUND(AVG(u.contribution_margin), 2) AS avg_margin,
    ROUND(SUM(u.contribution_margin), 2) AS total_margin
FROM unit_economics u
GROUP BY u.service_type
ORDER BY total_margin ASC;

-- 3. Profitability by acquisition channel
SELECT
    c.acquisition_channel,
    COUNT(*) AS orders,
    ROUND(AVG(u.contribution_margin), 2) AS avg_margin,
    ROUND(SUM(u.contribution_margin), 2) AS total_margin
FROM unit_economics u
JOIN orders o
  ON u.order_id = o.order_id
JOIN customers c
  ON o.customer_id = c.customer_id
GROUP BY c.acquisition_channel
ORDER BY total_margin ASC;

-- 4. Support-heavy customers (top 10% by support cost)
WITH support_by_customer AS (
    SELECT
        o.customer_id,
        SUM(u.support_cost) AS total_support_cost
    FROM unit_economics u
    JOIN orders o
      ON u.order_id = o.order_id
    GROUP BY o.customer_id
),
support_threshold AS (
    SELECT
        PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY total_support_cost) AS threshold
    FROM support_by_customer
)
SELECT
    COUNT(DISTINCT sbc.customer_id) AS customers,
    ROUND(AVG(u.contribution_margin), 2) AS avg_margin
FROM support_by_customer sbc
JOIN support_threshold st
  ON sbc.total_support_cost >= st.threshold
JOIN orders o
  ON sbc.customer_id = o.customer_id
JOIN unit_economics u
  ON o.order_id = u.order_id;
