-- =============================================================================
-- 05_segment_profitability.sql
-- Unit Economics Intelligence Platform
-- =============================================================================
-- PURPOSE:
--   Segment-level profitability breakdown.
--   After identifying that the business is losing money overall (Query 02),
--   this file answers: WHERE specifically is value being destroyed?
--
--   We cut the data three ways:
--     1. By region        — geographic profitability
--     2. By service type  — product profitability
--     3. By channel       — acquisition quality
--
--   Then we cross-cut to find the exact segment combinations that are
--   destroying the most value. This is the "autopsy" — finding what killed
--   the margin.
--
-- RUN AGAINST: unit_economics.db (SQLite)
-- =============================================================================


-- -----------------------------------------------------------------------------
-- QUERY 1: Profitability by region
-- WHY: If one region is consistently unprofitable, it could indicate
--      higher delivery costs, a different customer mix, or operational
--      inefficiency that leadership can address specifically.
--      KEY INSIGHT: East region has the worst margin % of all 4 regions.
-- -----------------------------------------------------------------------------
SELECT
    region,
    COUNT(*)                                            AS orders,
    COUNT(DISTINCT customer_id)                         AS customers,
    ROUND(AVG(order_value), 2)                         AS avg_order_value,
    ROUND(AVG(delivery_cost), 2)                       AS avg_delivery_cost,
    ROUND(AVG(support_cost), 2)                        AS avg_support_cost,
    ROUND(AVG(contribution_margin), 2)                 AS avg_margin,
    ROUND(SUM(contribution_margin), 2)                 AS total_margin,
    ROUND(SUM(contribution_margin)
          / NULLIF(SUM(net_revenue), 0) * 100, 2)     AS margin_pct
FROM unit_economics
GROUP BY region
ORDER BY margin_pct ASC;


-- -----------------------------------------------------------------------------
-- QUERY 2: Profitability by service type
-- WHY: Different services have fundamentally different cost structures.
--      Express has higher prices but also higher delivery + support costs.
--      Standard has volume but thin margins compressed by support costs.
--      KEY INSIGHT: Standard is -17.7% margin. It is the margin killer.
-- -----------------------------------------------------------------------------
SELECT
    service_type,
    COUNT(*)                                            AS orders,
    ROUND(SUM(net_revenue), 2)                         AS total_revenue,
    ROUND(AVG(variable_cost / NULLIF(order_value,0) * 100), 2) AS variable_cost_pct,
    ROUND(AVG(delivery_cost / NULLIF(order_value,0) * 100), 2) AS delivery_cost_pct,
    ROUND(AVG(support_cost  / NULLIF(order_value,0) * 100), 2) AS support_cost_pct,
    ROUND(AVG(contribution_margin), 2)                 AS avg_margin,
    ROUND(SUM(contribution_margin), 2)                 AS total_margin,
    ROUND(SUM(contribution_margin)
          / NULLIF(SUM(net_revenue), 0) * 100, 2)     AS margin_pct,
    ROUND(AVG(CASE WHEN contribution_margin < 0
              THEN 1.0 ELSE 0.0 END), 3)              AS loss_rate
FROM unit_economics
GROUP BY service_type
ORDER BY margin_pct ASC;


-- -----------------------------------------------------------------------------
-- QUERY 3: Profitability by acquisition channel
-- WHY: Combined with the CAC analysis in Query 04, this closes the loop.
--      A channel with high CAC AND negative margin per order is a double
--      loss — you paid to acquire a customer who costs you money every order.
--      KEY INSIGHT: Paid Search customers have the worst margin per order.
-- -----------------------------------------------------------------------------
SELECT
    acquisition_channel,
    COUNT(DISTINCT customer_id)                         AS customers,
    COUNT(*)                                            AS orders,
    ROUND(COUNT(*) * 1.0
          / COUNT(DISTINCT customer_id), 1)            AS orders_per_customer,
    ROUND(AVG(contribution_margin), 2)                 AS avg_margin_per_order,
    ROUND(SUM(contribution_margin), 2)                 AS total_margin,
    ROUND(SUM(contribution_margin)
          / COUNT(DISTINCT customer_id), 2)            AS margin_per_customer,
    ROUND(SUM(contribution_margin)
          / NULLIF(SUM(net_revenue), 0) * 100, 2)     AS margin_pct
FROM unit_economics
GROUP BY acquisition_channel
ORDER BY margin_per_customer ASC;


-- -----------------------------------------------------------------------------
-- QUERY 4: Service × Channel cross-tab
-- WHY: The intersection reveals hidden patterns. Maybe Standard service
--      is fine for Organic customers but catastrophically unprofitable
--      for Paid Search customers. This cross-tab reveals those interactions.
-- -----------------------------------------------------------------------------
SELECT
    service_type,
    acquisition_channel,
    COUNT(*)                                            AS orders,
    ROUND(AVG(contribution_margin), 2)                 AS avg_margin,
    ROUND(SUM(contribution_margin)
          / NULLIF(SUM(net_revenue), 0) * 100, 2)     AS margin_pct,
    ROUND(AVG(CASE WHEN contribution_margin < 0
              THEN 1.0 ELSE 0.0 END), 3)              AS loss_rate
FROM unit_economics
GROUP BY service_type, acquisition_channel
ORDER BY margin_pct ASC;


-- -----------------------------------------------------------------------------
-- QUERY 5: Support-heavy customers — the hidden margin destroyers
-- WHY: Top 10% by support cost average -₹77 margin vs +₹2.81 for regular customers.
--      Identifying them enables tiered support, pricing surcharges, or service limits.
-- -----------------------------------------------------------------------------
WITH customer_support AS (
    SELECT customer_id,
           SUM(support_cost)        AS total_support_cost,
           SUM(contribution_margin) AS lifetime_margin,
           COUNT(*)                 AS total_orders
    FROM unit_economics GROUP BY customer_id
),
ranked AS (
    SELECT *, NTILE(10) OVER (ORDER BY total_support_cost) AS decile
    FROM customer_support
)
SELECT
    CASE WHEN decile = 10 THEN 'Top 10% Support Cost' ELSE 'Regular' END AS customer_segment,
    COUNT(*)                                AS customers,
    ROUND(AVG(total_support_cost), 2)      AS avg_support_cost,
    ROUND(AVG(lifetime_margin), 2)         AS avg_lifetime_margin,
    ROUND(AVG(total_orders), 1)            AS avg_orders,
    ROUND(AVG(CASE WHEN lifetime_margin < 0 THEN 1.0 ELSE 0.0 END), 3) AS pct_margin_negative
FROM ranked
GROUP BY customer_segment;


-- QUERY 6: Region × Service type heatmap
-- WHY: Combines both dimensions to find the worst-performing combinations.
--      "Standard in East" might be uniquely bad. "Express in North" might
--      be the only profitable segment worth protecting and scaling.
-- -----------------------------------------------------------------------------
SELECT
    region,
    service_type,
    COUNT(*)                                            AS orders,
    ROUND(AVG(contribution_margin), 2)                 AS avg_margin,
    ROUND(SUM(contribution_margin)
          / NULLIF(SUM(net_revenue), 0) * 100, 2)     AS margin_pct,
    ROUND(AVG(CASE WHEN contribution_margin < 0
              THEN 1.0 ELSE 0.0 END), 3)              AS loss_rate
FROM unit_economics
GROUP BY region, service_type
ORDER BY margin_pct ASC;