-- =====================================
-- CAC vs LTV ANALYSIS
-- =====================================

-- 1. Customers acquired by channel (first-touch)
WITH customers_by_channel AS (
    SELECT
        acquisition_channel,
        COUNT(DISTINCT customer_id) AS customers_acquired
    FROM customers
    GROUP BY acquisition_channel
),

-- 2. Total marketing spend by channel
spend_by_channel AS (
    SELECT
        channel AS acquisition_channel,
        ROUND(SUM(spend), 2) AS total_spend
    FROM marketing_spend
    GROUP BY channel
),

-- 3. CAC by channel
cac_by_channel AS (
    SELECT
        c.acquisition_channel,
        c.customers_acquired,
        s.total_spend,
        ROUND(s.total_spend * 1.0 / c.customers_acquired, 2) AS cac
    FROM customers_by_channel c
    JOIN spend_by_channel s
      ON c.acquisition_channel = s.acquisition_channel
),

-- 4. Lifetime margin by customer
customer_lifetime AS (
    SELECT
        o.customer_id,
        SUM(u.contribution_margin) AS lifetime_margin
    FROM unit_economics u
    JOIN orders o
      ON u.order_id = o.order_id
    GROUP BY o.customer_id
),

-- 5. LTV by acquisition channel
ltv_by_channel AS (
    SELECT
        c.acquisition_channel,
        ROUND(AVG(cl.lifetime_margin), 2) AS avg_ltv,
        ROUND(SUM(cl.lifetime_margin), 2) AS total_ltv
    FROM customer_lifetime cl
    JOIN customers c
      ON cl.customer_id = c.customer_id
    GROUP BY c.acquisition_channel
)

-- 6. CAC vs LTV comparison
SELECT
    cac.acquisition_channel,
    cac.customers_acquired,
    cac.cac,
    ltv.avg_ltv,
    ROUND(ltv.avg_ltv * 1.0 / cac.cac, 2) AS ltv_to_cac_ratio
FROM cac_by_channel cac
JOIN ltv_by_channel ltv
  ON cac.acquisition_channel = ltv.acquisition_channel
ORDER BY ltv_to_cac_ratio DESC;