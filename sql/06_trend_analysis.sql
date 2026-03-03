-- =============================================================================
-- 06_trend_analysis.sql
-- Unit Economics Intelligence Platform
-- =============================================================================
-- PURPOSE:
--   Time-series analysis of margin deterioration and cost inflation.
--   This is the "how did we get here?" analysis.
--
--   CORE THESIS:
--   The business was marginally profitable in early 2024. By late 2025,
--   it is structurally loss-making. This file quantifies:
--     1. The pace of margin deterioration month-by-month
--     2. Which cost component inflated fastest
--     3. Whether the problem is accelerating or stabilising
--     4. Seasonal patterns that mask the underlying trend
--
--   This type of trend analysis is what separates a snapshot diagnosis
--   from a true understanding of business dynamics.
--
-- RUN AGAINST: unit_economics.db (SQLite)
-- =============================================================================


-- -----------------------------------------------------------------------------
-- QUERY 1: Monthly P&L trend — the margin deterioration story
-- WHY: Month-by-month P&L shows the trajectory, not just the current state.
--      A business that was +12% margin in Jan 2024 and is -7% in Dec 2025
--      has a very different story than one that was always -3%.
--      KEY INSIGHT: Margin went from +13.7% (Jan 2024) to -7.5% (Dec 2025).
-- -----------------------------------------------------------------------------
SELECT
    order_month,
    COUNT(*)                                            AS orders,
    ROUND(SUM(net_revenue), 2)                         AS revenue,
    ROUND(SUM(total_cost), 2)                          AS total_cost,
    ROUND(SUM(contribution_margin), 2)                 AS margin,
    ROUND(AVG(contribution_margin), 2)                 AS avg_margin_per_order,
    ROUND(SUM(contribution_margin)
          / NULLIF(SUM(net_revenue), 0) * 100, 2)     AS margin_pct,
    ROUND(AVG(CASE WHEN contribution_margin < 0
              THEN 1.0 ELSE 0.0 END), 3)              AS loss_rate
FROM unit_economics
GROUP BY order_month
ORDER BY order_month;


-- -----------------------------------------------------------------------------
-- QUERY 2: Cost component inflation over time
-- WHY: Not all costs inflate equally. Identifying which cost line is
--      growing fastest tells leadership where to focus cost reduction.
--      Delivery cost inflation (30% over 2 years) is structural.
--      Support cost spikes in December are seasonal and addressable.
--      KEY INSIGHT: Delivery cost per order rose from ~₹14 to ~₹22 (Jan→Dec).
-- -----------------------------------------------------------------------------
SELECT
    order_month,
    ROUND(AVG(variable_cost), 2)                       AS avg_variable_cost,
    ROUND(AVG(delivery_cost), 2)                       AS avg_delivery_cost,
    ROUND(AVG(support_cost), 2)                        AS avg_support_cost,
    ROUND(AVG(total_cost), 2)                          AS avg_total_cost,
    ROUND(AVG(order_value), 2)                         AS avg_order_value,
    -- Cost ratio: what % of avg order value goes to each cost type
    ROUND(AVG(delivery_cost / NULLIF(order_value,0) * 100), 2) AS delivery_pct_of_value,
    ROUND(AVG(support_cost  / NULLIF(order_value,0) * 100), 2) AS support_pct_of_value
FROM unit_economics
GROUP BY order_month
ORDER BY order_month;


-- -----------------------------------------------------------------------------
-- QUERY 3: 3-month rolling average margin — smoothing seasonal noise
-- WHY: Monthly margin is noisy (December always spikes negative due to
--      support costs and service mix shift). A rolling average reveals
--      the underlying trend without seasonal distortion.
--      This is standard practice in financial reporting.
-- -----------------------------------------------------------------------------
WITH monthly AS (
    SELECT
        order_month,
        ROUND(SUM(contribution_margin)
              / NULLIF(SUM(net_revenue), 0) * 100, 2) AS margin_pct,
        ROUND(AVG(contribution_margin), 2)             AS avg_margin
    FROM unit_economics
    GROUP BY order_month
)
SELECT
    order_month,
    margin_pct,
    avg_margin,
    ROUND(AVG(margin_pct) OVER (
        ORDER BY order_month
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2)                                               AS rolling_3m_margin_pct,
    ROUND(AVG(avg_margin) OVER (
        ORDER BY order_month
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2)                                               AS rolling_3m_avg_margin
FROM monthly
ORDER BY order_month;


-- -----------------------------------------------------------------------------
-- QUERY 4: Year-over-year comparison (2024 vs 2025)
-- WHY: The single most important question leadership will ask:
--      "Is 2025 better or worse than 2024?"
--      Comparing same months across years removes seasonality and gives
--      a clean view of whether the business is improving or deteriorating.
-- -----------------------------------------------------------------------------
WITH monthly_yoy AS (
    SELECT
        strftime('%m', order_date)  AS month_num,
        strftime('%Y', order_date)  AS year,
        SUM(net_revenue)            AS revenue,
        SUM(contribution_margin)    AS margin,
        COUNT(*)                    AS orders
    FROM unit_economics
    GROUP BY month_num, year
)
SELECT
    CASE month_num
        WHEN '01' THEN 'January'  WHEN '02' THEN 'February'
        WHEN '03' THEN 'March'    WHEN '04' THEN 'April'
        WHEN '05' THEN 'May'      WHEN '06' THEN 'June'
        WHEN '07' THEN 'July'     WHEN '08' THEN 'August'
        WHEN '09' THEN 'September'WHEN '10' THEN 'October'
        WHEN '11' THEN 'November' WHEN '12' THEN 'December'
    END                                                 AS month_name,
    ROUND(MAX(CASE WHEN year = '2024' THEN margin END), 2) AS margin_2024,
    ROUND(MAX(CASE WHEN year = '2025' THEN margin END), 2) AS margin_2025,
    ROUND(MAX(CASE WHEN year = '2025' THEN margin END)
        - MAX(CASE WHEN year = '2024' THEN margin END), 2) AS yoy_margin_change,
    ROUND(MAX(CASE WHEN year = '2024' THEN orders END), 0) AS orders_2024,
    ROUND(MAX(CASE WHEN year = '2025' THEN orders END), 0) AS orders_2025
FROM monthly_yoy
GROUP BY month_num
ORDER BY month_num;


-- -----------------------------------------------------------------------------
-- QUERY 5: Margin by service type over time
-- WHY: The aggregate margin trend could be caused by one service type
--      getting worse, OR by a shift in mix toward less profitable services.
--      This separates those two causes.
--      If Standard was always -15% but its share grew, that's a mix problem.
--      If Standard went from -5% to -20%, that's a structural cost problem.
-- -----------------------------------------------------------------------------
SELECT
    order_month,
    service_type,
    COUNT(*)                                            AS orders,
    ROUND(SUM(contribution_margin)
          / NULLIF(SUM(net_revenue), 0) * 100, 2)     AS margin_pct,
    ROUND(AVG(delivery_cost), 2)                       AS avg_delivery_cost,
    ROUND(AVG(support_cost), 2)                        AS avg_support_cost
FROM unit_economics
GROUP BY order_month, service_type
ORDER BY order_month, service_type;


-- -----------------------------------------------------------------------------
-- QUERY 6: Loss rate trend — is the problem getting worse?
-- WHY: If loss rate is increasing month over month, the business is on a
--      worsening trajectory and needs immediate intervention.
--      If it's stable, the problem is structural but not accelerating.
-- -----------------------------------------------------------------------------
SELECT
    order_month,
    COUNT(*)                                            AS total_orders,
    SUM(CASE WHEN contribution_margin < 0 THEN 1 ELSE 0 END)   AS loss_orders,
    ROUND(AVG(CASE WHEN contribution_margin < 0
              THEN 1.0 ELSE 0.0 END) * 100, 2)        AS loss_rate_pct,
    ROUND(SUM(CASE WHEN contribution_margin < 0
              THEN contribution_margin ELSE 0 END), 2) AS total_loss_value,
    ROUND(SUM(CASE WHEN contribution_margin > 0
              THEN contribution_margin ELSE 0 END), 2) AS total_profit_value
FROM unit_economics
GROUP BY order_month
ORDER BY order_month;