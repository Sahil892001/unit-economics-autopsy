-- =============================================================================
-- 02_unit_economics.sql
-- Unit Economics Intelligence Platform
-- =============================================================================
-- PURPOSE:
--   Core profitability diagnostics at the order level.
--   Answers the central business question: "Where are we making and
--   losing money, and why is growth not translating to profit?"
--
--   Contribution Margin = Net Revenue − (Variable + Delivery + Support Cost)
--   This excludes fixed costs intentionally — we are measuring unit-level
--   economics, not total P&L.
--
-- RUN AGAINST: unit_economics.db (SQLite)
-- DEPENDS ON:  01_data_validation.sql passing cleanly
-- =============================================================================


-- -----------------------------------------------------------------------------
-- QUERY 1: Business-level P&L summary
-- WHY: The headline number. Despite ₹1.5Cr+ revenue, are we profitable?
--      Avg margin per order tells us whether the unit economics are
--      structurally broken or just temporarily squeezed.
-- -----------------------------------------------------------------------------
SELECT
    COUNT(*)                                            AS total_orders,
    ROUND(SUM(net_revenue), 2)                         AS total_revenue,
    ROUND(SUM(total_cost), 2)                          AS total_cost,
    ROUND(SUM(contribution_margin), 2)                 AS total_margin,
    ROUND(AVG(contribution_margin), 2)                 AS avg_margin_per_order,
    ROUND(SUM(contribution_margin)
          / NULLIF(SUM(net_revenue), 0) * 100, 2)     AS margin_pct
FROM unit_economics;


-- -----------------------------------------------------------------------------
-- QUERY 2: Margin distribution — not just averages
-- WHY: Averages hide the truth. A business with avg margin of ₹5/order could
--      have 30% of orders at +₹50 and 44% at -₹30. The distribution reveals
--      the structural problem that averages obscure.
--      KEY INSIGHT: 44% of orders are loss-making.
-- -----------------------------------------------------------------------------
SELECT
    margin_bucket,
    COUNT(*)                                            AS order_count,
    ROUND(COUNT(*) * 1.0 / SUM(COUNT(*)) OVER(), 3)   AS share_of_orders,
    ROUND(SUM(contribution_margin), 2)                 AS total_margin,
    ROUND(AVG(contribution_margin), 2)                 AS avg_margin
FROM unit_economics
GROUP BY margin_bucket
ORDER BY
    CASE margin_bucket
        WHEN 'Loss-making'     THEN 1
        WHEN 'Low Margin'      THEN 2
        WHEN 'Healthy Margin'  THEN 3
        WHEN 'High Margin'     THEN 4
    END;


-- -----------------------------------------------------------------------------
-- QUERY 3: Loss rate — the key diagnostic metric
-- WHY: Industry benchmark for on-demand services is <15% loss rate.
--      If we are above this, pricing or cost structure is broken.
--      We track this monthly to detect if the problem is worsening.
-- -----------------------------------------------------------------------------
SELECT
    ROUND(AVG(CASE WHEN contribution_margin < 0 THEN 1.0 ELSE 0 END), 4) AS overall_loss_rate,
    ROUND(AVG(CASE WHEN contribution_margin < -50 THEN 1.0 ELSE 0 END), 4) AS deep_loss_rate,
    COUNT(CASE WHEN contribution_margin < 0 THEN 1 END)                   AS loss_making_orders,
    ROUND(SUM(CASE WHEN contribution_margin < 0
              THEN contribution_margin ELSE 0 END), 2)                    AS total_loss_value
FROM unit_economics;


-- -----------------------------------------------------------------------------
-- QUERY 4: Unit economics by service type
-- WHY: Not all services are equal. Standard may subsidise Express, or
--      Express may be the only profitable line. This tells leadership
--      which products to grow, reprice, or discontinue.
--      KEY INSIGHT: Standard service is loss-making at -17.7% margin.
-- -----------------------------------------------------------------------------
SELECT
    service_type,
    COUNT(*)                                            AS orders,
    ROUND(AVG(order_value), 2)                         AS avg_order_value,
    ROUND(AVG(variable_cost), 2)                       AS avg_variable_cost,
    ROUND(AVG(delivery_cost), 2)                       AS avg_delivery_cost,
    ROUND(AVG(support_cost), 2)                        AS avg_support_cost,
    ROUND(AVG(total_cost), 2)                          AS avg_total_cost,
    ROUND(AVG(contribution_margin), 2)                 AS avg_margin,
    ROUND(SUM(contribution_margin), 2)                 AS total_margin,
    ROUND(SUM(contribution_margin)
          / NULLIF(SUM(net_revenue), 0) * 100, 2)     AS margin_pct
FROM unit_economics
GROUP BY service_type
ORDER BY margin_pct ASC;


-- -----------------------------------------------------------------------------
-- QUERY 5: Unit economics by region
-- WHY: Regional performance tells us whether the problem is operational
--      (one region's delivery costs are too high) or systemic (all regions
--      are structurally unprofitable).
--      KEY INSIGHT: East region underperforms every other region.
-- -----------------------------------------------------------------------------
SELECT
    region,
    COUNT(*)                                            AS orders,
    ROUND(AVG(contribution_margin), 2)                 AS avg_margin,
    ROUND(SUM(contribution_margin), 2)                 AS total_margin,
    ROUND(SUM(contribution_margin)
          / NULLIF(SUM(net_revenue), 0) * 100, 2)     AS margin_pct,
    ROUND(AVG(support_cost), 2)                        AS avg_support_cost,
    ROUND(AVG(delivery_cost), 2)                       AS avg_delivery_cost
FROM unit_economics
GROUP BY region
ORDER BY margin_pct ASC;


-- -----------------------------------------------------------------------------
-- QUERY 6: Cost structure breakdown — where does the money go?
-- WHY: To fix margins you need to know which cost bucket is the problem.
--      Variable cost is hard to change (tied to service delivery).
--      Delivery cost can be reduced via route optimisation.
--      Support cost is the highest-leverage intervention point.
-- -----------------------------------------------------------------------------
SELECT
    service_type,
    ROUND(AVG(variable_cost / NULLIF(order_value, 0) * 100), 2)   AS variable_cost_pct,
    ROUND(AVG(delivery_cost / NULLIF(order_value, 0) * 100), 2)   AS delivery_cost_pct,
    ROUND(AVG(support_cost  / NULLIF(order_value, 0) * 100), 2)   AS support_cost_pct,
    ROUND(AVG(total_cost    / NULLIF(order_value, 0) * 100), 2)   AS total_cost_pct
FROM unit_economics
GROUP BY service_type
ORDER BY total_cost_pct DESC;


-- -----------------------------------------------------------------------------
-- QUERY 7: Power user vs regular customer economics
-- WHY: Power users (top 5% by order volume) drive disproportionate revenue.
--      But if they also drive disproportionate support costs, they may
--      be margin-negative despite high revenue. Crucial for pricing strategy.
-- -----------------------------------------------------------------------------
SELECT
    is_power_user,
    COUNT(DISTINCT customer_id)                         AS customers,
    COUNT(*)                                            AS orders,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT customer_id), 1) AS orders_per_customer,
    ROUND(AVG(order_value), 2)                         AS avg_order_value,
    ROUND(AVG(contribution_margin), 2)                 AS avg_margin,
    ROUND(SUM(contribution_margin), 2)                 AS total_margin,
    ROUND(AVG(support_cost), 2)                        AS avg_support_cost
FROM unit_economics
GROUP BY is_power_user;