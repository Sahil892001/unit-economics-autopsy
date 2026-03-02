# =============================================================================
# cohort_analysis.py
# Unit Economics Intelligence Platform — Cohort Retention & LTV Analysis
# =============================================================================
# Outputs:
#   cohort_retention_matrix.csv  — % of Month-0 customers still ordering in Mo N
#   cohort_revenue_matrix.csv    — cumulative revenue per cohort by month number
#   cohort_margin_matrix.csv     — cumulative margin per cohort by month number
#   cohort_summary.csv           — one row per cohort: size, M1 retention, LTV
#   cohort_ltv_curve.csv         — avg cumulative LTV by months-since-signup
# =============================================================================

import sys
import sqlite3
import logging
from pathlib import Path

import pandas as pd
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import DB_PATH, OUTPUTS_DIR, LOGS_DIR, GOOD_MONTH1_RETENTION, POOR_MONTH3_RETENTION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "cohort_analysis.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

# =============================================================================
# CONNECT & LOAD
# =============================================================================
log.info("=" * 60)
log.info("COHORT ANALYSIS")
log.info("=" * 60)

conn = sqlite3.connect(DB_PATH)

# Pull the full unit_economics table — already has cohort + months_since_signup
log.info("Loading unit_economics from DB …")
ue = pd.read_sql("""
    SELECT
        order_id,
        customer_id,
        cohort,
        order_month,
        months_since_signup,
        net_revenue,
        contribution_margin,
        is_profitable
    FROM unit_economics
""", conn)

customers = pd.read_sql("""
    SELECT customer_id, cohort, signup_month, acquisition_channel, region
    FROM customers
""", conn)

conn.close()

log.info(f"  unit_economics  : {len(ue):,} rows")
log.info(f"  customers       : {len(customers):,} rows")

# =============================================================================
# 1. COHORT SIZE (customers per signup cohort)
# =============================================================================
log.info("\nBuilding cohort sizes …")
cohort_sizes = (
    customers
    .groupby("cohort")["customer_id"]
    .nunique()
    .reset_index()
    .rename(columns={"customer_id": "cohort_size"})
)
log.info(f"  {len(cohort_sizes)} cohorts found")

# =============================================================================
# 2. ACTIVE CUSTOMERS PER COHORT × MONTH NUMBER
# =============================================================================
log.info("Building retention matrix …")

# Count distinct customers who placed at least one order in each cohort-month pair
cohort_activity = (
    ue
    .groupby(["cohort", "months_since_signup"])["customer_id"]
    .nunique()
    .reset_index()
    .rename(columns={"customer_id": "active_customers"})
)

# Merge cohort sizes
cohort_activity = cohort_activity.merge(cohort_sizes, on="cohort", how="left")

# Retention rate = active_customers / cohort_size
cohort_activity["retention_rate"] = (
    cohort_activity["active_customers"] / cohort_activity["cohort_size"]
).round(4)

# Pivot to matrix: rows = cohort, cols = month number
retention_matrix = cohort_activity.pivot(
    index="cohort",
    columns="months_since_signup",
    values="retention_rate"
).sort_index()

# Rename columns for readability
retention_matrix.columns = [f"M{int(c)}" for c in retention_matrix.columns]
retention_matrix.index.name = "cohort"

log.info(f"  Retention matrix: {retention_matrix.shape[0]} cohorts × {retention_matrix.shape[1]} months")

# =============================================================================
# 3. COHORT REVENUE & MARGIN MATRICES
# =============================================================================
log.info("Building revenue & margin matrices …")

# Cumulative revenue per cohort × month
cohort_financials = (
    ue
    .groupby(["cohort", "months_since_signup"])
    .agg(
        revenue = ("net_revenue",           "sum"),
        margin  = ("contribution_margin",   "sum"),
        orders  = ("order_id",              "count"),
    )
    .reset_index()
)

# Per-customer (normalise by cohort size for fair comparison)
cohort_financials = cohort_financials.merge(cohort_sizes, on="cohort", how="left")
cohort_financials["revenue_per_customer"] = (
    cohort_financials["revenue"] / cohort_financials["cohort_size"]
).round(2)
cohort_financials["margin_per_customer"] = (
    cohort_financials["margin"] / cohort_financials["cohort_size"]
).round(2)

# Cumulative versions (sort within cohort by month, then cumsum)
cohort_financials = cohort_financials.sort_values(["cohort", "months_since_signup"])
cohort_financials["cum_revenue_per_customer"] = (
    cohort_financials.groupby("cohort")["revenue_per_customer"].cumsum().round(2)
)
cohort_financials["cum_margin_per_customer"] = (
    cohort_financials.groupby("cohort")["margin_per_customer"].cumsum().round(2)
)

# Revenue matrix pivot
revenue_matrix = cohort_financials.pivot(
    index="cohort",
    columns="months_since_signup",
    values="cum_revenue_per_customer"
).sort_index()
revenue_matrix.columns = [f"M{int(c)}" for c in revenue_matrix.columns]
revenue_matrix.index.name = "cohort"

# Margin matrix pivot
margin_matrix = cohort_financials.pivot(
    index="cohort",
    columns="months_since_signup",
    values="cum_margin_per_customer"
).sort_index()
margin_matrix.columns = [f"M{int(c)}" for c in margin_matrix.columns]
margin_matrix.index.name = "cohort"

# =============================================================================
# 4. COHORT SUMMARY TABLE (one row per cohort)
# =============================================================================
log.info("Building cohort summary …")

# M1 retention = % of cohort still ordering in month 1
m1_retention = (
    cohort_activity[cohort_activity["months_since_signup"] == 1]
    [["cohort", "retention_rate"]]
    .rename(columns={"retention_rate": "m1_retention"})
)
m3_retention = (
    cohort_activity[cohort_activity["months_since_signup"] == 3]
    [["cohort", "retention_rate"]]
    .rename(columns={"retention_rate": "m3_retention"})
)
m6_retention = (
    cohort_activity[cohort_activity["months_since_signup"] == 6]
    [["cohort", "retention_rate"]]
    .rename(columns={"retention_rate": "m6_retention"})
)

# Lifetime margin per cohort
cohort_ltv = (
    ue.groupby("cohort")
    .agg(
        total_orders    = ("order_id",            "count"),
        total_revenue   = ("net_revenue",          "sum"),
        total_margin    = ("contribution_margin",  "sum"),
    )
    .reset_index()
)
cohort_ltv = cohort_ltv.merge(cohort_sizes, on="cohort", how="left")
cohort_ltv["avg_ltv"]          = (cohort_ltv["total_margin"]  / cohort_ltv["cohort_size"]).round(2)
cohort_ltv["avg_revenue"]      = (cohort_ltv["total_revenue"] / cohort_ltv["cohort_size"]).round(2)
cohort_ltv["orders_per_customer"] = (cohort_ltv["total_orders"] / cohort_ltv["cohort_size"]).round(2)

cohort_summary = (
    cohort_ltv
    .merge(m1_retention, on="cohort", how="left")
    .merge(m3_retention, on="cohort", how="left")
    .merge(m6_retention, on="cohort", how="left")
    .sort_values("cohort")
    .reset_index(drop=True)
)

# Health flags
cohort_summary["m1_health"] = cohort_summary["m1_retention"].apply(
    lambda x: "Good" if pd.notna(x) and x >= GOOD_MONTH1_RETENTION else
              ("Poor" if pd.notna(x) and x < POOR_MONTH3_RETENTION else "Fair")
)

log.info(f"  Cohort summary: {len(cohort_summary)} cohorts")
log.info(f"  Avg M1 retention: {cohort_summary['m1_retention'].mean():.1%}")
log.info(f"  Avg LTV per customer: ₹{cohort_summary['avg_ltv'].mean():.2f}")

# =============================================================================
# 5. LTV CURVE — avg cumulative LTV by months-since-signup (across all cohorts)
# =============================================================================
log.info("Building LTV curve …")

ltv_curve = (
    cohort_financials
    .groupby("months_since_signup")
    .agg(
        avg_cum_revenue = ("cum_revenue_per_customer", "mean"),
        avg_cum_margin  = ("cum_margin_per_customer",  "mean"),
        cohorts_in_month = ("cohort",                  "nunique"),
    )
    .reset_index()
    .rename(columns={"months_since_signup": "month_number"})
    .sort_values("month_number")
    .reset_index(drop=True)
)
ltv_curve["avg_cum_revenue"] = ltv_curve["avg_cum_revenue"].round(2)
ltv_curve["avg_cum_margin"]  = ltv_curve["avg_cum_margin"].round(2)

log.info(f"  LTV curve: {len(ltv_curve)} data points (months 0–{ltv_curve['month_number'].max()})")

# =============================================================================
# 6. SAVE ALL OUTPUTS
# =============================================================================
log.info("\nSaving outputs …")

outputs = {
    "cohort_retention_matrix.csv": retention_matrix.reset_index(),
    "cohort_revenue_matrix.csv":   revenue_matrix.reset_index(),
    "cohort_margin_matrix.csv":    margin_matrix.reset_index(),
    "cohort_summary.csv":          cohort_summary,
    "cohort_ltv_curve.csv":        ltv_curve,
    "cohort_financials.csv":       cohort_financials,
}

for filename, df in outputs.items():
    path = OUTPUTS_DIR / filename
    df.to_csv(path, index=False)
    log.info(f"  ✅  {filename:<40} {len(df):>6,} rows")

# =============================================================================
# SUMMARY INSIGHTS
# =============================================================================
log.info("\n" + "=" * 60)
log.info("KEY FINDINGS")
log.info("=" * 60)

# Best and worst cohorts by M1 retention
best  = cohort_summary.nlargest(3,  "m1_retention")[["cohort", "m1_retention", "avg_ltv"]]
worst = cohort_summary.nsmallest(3, "m1_retention")[["cohort", "m1_retention", "avg_ltv"]]

log.info("  Top 3 cohorts by M1 retention:")
for _, r in best.iterrows():
    log.info(f"    {r['cohort']}  M1={r['m1_retention']:.1%}  LTV=₹{r['avg_ltv']:.2f}")

log.info("  Bottom 3 cohorts by M1 retention:")
for _, r in worst.iterrows():
    log.info(f"    {r['cohort']}  M1={r['m1_retention']:.1%}  LTV=₹{r['avg_ltv']:.2f}")

log.info("\n" + "=" * 60) 
log.info("COHORT ANALYSIS COMPLETE")
log.info(f"  Outputs saved to: {OUTPUTS_DIR}")
log.info("=" * 60) 