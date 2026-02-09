-- =====================================
-- UNIT ECONOMICS ANALYSIS
-- =====================================

-- 1. Overall unit economics
SELECT
    COUNT(*) AS total_orders,
    ROUND(SUM(net_revenue), 2) AS total_revenue,
    ROUND(SUM(total_cost), 2) AS total_cost,
    ROUND(SUM(contribution_margin), 2) AS total_margin,
    ROUND(AVG(contribution_margin), 2) AS avg_margin_per_order
FROM unit_economics;

-- 2. Margin distribution (not averages)
SELECT
    CASE
        WHEN contribution_margin < 0 THEN 'Loss-making'
        WHEN contribution_margin BETWEEN 0 AND 20 THEN 'Low margin'
        WHEN contribution_margin BETWEEN 20 AND 50 THEN 'Healthy margin'
        ELSE 'High margin'
    END AS margin_bucket,
    COUNT(*) AS order_count
FROM unit_economics
GROUP BY margin_bucket
ORDER BY order_count DESC;

-- 3. Loss rate
SELECT
    ROUND(AVG(CASE WHEN contribution_margin < 0 THEN 1 ELSE 0 END), 4) AS loss_rate
FROM unit_economics;

-- 4. Unit economics by service type
SELECT
    service_type,
    COUNT(*) AS orders,
    ROUND(AVG(contribution_margin), 2) AS avg_margin,
    ROUND(SUM(contribution_margin), 2) AS total_margin
FROM unit_economics
GROUP BY service_type
ORDER BY total_margin ASC;

-- 5. Unit economics by region
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