# =============================================================================
# segment_profitability.py
# Unit Economics Intelligence Platform — Segment Profitability Analysis
# =============================================================================
# Outputs:
#   segment_by_region.csv          — P&L breakdown by region
#   segment_by_service.csv         — P&L breakdown by service type
#   segment_by_channel.csv         — P&L breakdown by acquisition channel
#   segment_cross_tab.csv          — service × channel profitability matrix
#   support_heavy_customers.csv    — top 10% support cost customers profile
#   power_user_analysis.csv        — power users vs regular customers comparison
# =============================================================================

import sys
import sqlite3
import logging
from pathlib import Path

import pandas as pd
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import (
    DB_PATH, OUTPUTS_DIR, LOGS_DIR,
    HIGH_SUPPORT_THRESHOLD, MIN_HEALTHY_MARGIN,
)
 
logging.basicConfig( 
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "segment_profitability.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

# =============================================================================
# LOAD
# =============================================================================
log.info("=" * 60)
log.info("SEGMENT PROFITABILITY ANALYSIS")
log.info("=" * 60)

conn = sqlite3.connect(DB_PATH)
ue = pd.read_sql("SELECT * FROM unit_economics", conn)
conn.close()

log.info(f"  unit_economics: {len(ue):,} rows × {ue.shape[1]} cols")

def segment_summary(df, group_col):
    """Compute full P&L summary for a single groupby dimension."""
    return (
        df.groupby(group_col)
        .agg(
            orders             = ("order_id",             "count"),
            customers          = ("customer_id",          "nunique"),
            total_revenue      = ("net_revenue",           "sum"),
            total_cost         = ("total_cost",            "sum"),
            variable_cost      = ("variable_cost",         "sum"),
            delivery_cost      = ("delivery_cost",         "sum"),
            support_cost       = ("support_cost",          "sum"),
            total_margin       = ("contribution_margin",   "sum"),
            avg_margin         = ("contribution_margin",   "mean"),
            median_margin      = ("contribution_margin",   "median"),
            profitable_pct     = ("is_profitable",         "mean"),
            refund_rate        = ("is_refunded",           "mean"),
            avg_order_value    = ("order_value",           "mean"),
            high_support_pct   = ("is_high_support",       "mean"),
        )
        .reset_index()
        .round(2)
    )

# =============================================================================
# 1. BY REGION
# =============================================================================
log.info("\nAnalysing by region …")
seg_region = segment_summary(ue, "region")
seg_region["margin_pct"] = (seg_region["total_margin"] / seg_region["total_revenue"] * 100).round(2)
seg_region["orders_per_customer"] = (seg_region["orders"] / seg_region["customers"]).round(2)
seg_region = seg_region.sort_values("total_margin", ascending=False).reset_index(drop=True)

for _, r in seg_region.iterrows():
    log.info(f"  {r['region']:<8}  margin=₹{r['total_margin']:>12,.0f}  "
             f"margin%={r['margin_pct']:>6.1f}%  profitable={r['profitable_pct']:.1%}")

# =============================================================================
# 2. BY SERVICE TYPE
# =============================================================================
log.info("\nAnalysing by service type …")
seg_service = segment_summary(ue, "service_type")
seg_service["margin_pct"] = (seg_service["total_margin"] / seg_service["total_revenue"] * 100).round(2)
seg_service["cost_ratio"]  = (seg_service["total_cost"]   / seg_service["total_revenue"] * 100).round(2)
seg_service["support_ratio"] = (seg_service["support_cost"] / seg_service["total_revenue"] * 100).round(2)
seg_service = seg_service.sort_values("total_margin", ascending=False).reset_index(drop=True)

for _, r in seg_service.iterrows():
    log.info(f"  {r['service_type']:<10}  margin%={r['margin_pct']:>6.1f}%  "
             f"support%={r['support_ratio']:>5.1f}%  refund%={r['refund_rate']:.1%}")

# =============================================================================
# 3. BY ACQUISITION CHANNEL
# =============================================================================
log.info("\nAnalysing by acquisition channel …")
seg_channel = segment_summary(ue, "acquisition_channel")
seg_channel["margin_pct"] = (seg_channel["total_margin"] / seg_channel["total_revenue"] * 100).round(2)
seg_channel["revenue_per_customer"] = (seg_channel["total_revenue"] / seg_channel["customers"]).round(2)
seg_channel["margin_per_customer"]  = (seg_channel["total_margin"]  / seg_channel["customers"]).round(2)
seg_channel = seg_channel.sort_values("margin_per_customer", ascending=False).reset_index(drop=True)

for _, r in seg_channel.iterrows():
    log.info(f"  {r['acquisition_channel']:<15}  margin/cust=₹{r['margin_per_customer']:>7.2f}  "
             f"margin%={r['margin_pct']:>6.1f}%")

# =============================================================================
# 4. CROSS-TAB: SERVICE TYPE × CHANNEL
# =============================================================================
log.info("\nBuilding service × channel cross-tab …")

cross = (
    ue.groupby(["service_type", "acquisition_channel"])
    .agg(
        orders       = ("order_id",           "count"),
        total_margin = ("contribution_margin", "sum"),
        margin_pct   = ("margin_pct",          "mean"),
        profitable   = ("is_profitable",       "mean"),
    )
    .reset_index()
    .round(2)
)

# Pivot for heatmap: service type × channel → avg margin %
cross_pivot = cross.pivot(
    index="service_type",
    columns="acquisition_channel",
    values="margin_pct"
).round(2)
cross_pivot.index.name = "service_type"

log.info(f"  Cross-tab matrix: {cross_pivot.shape}")

# =============================================================================
# 5. SUPPORT-HEAVY CUSTOMERS
# =============================================================================
log.info("\nAnalysing support-heavy customers …")

support_by_customer = (
    ue.groupby("customer_id")
    .agg(
        total_support_cost = ("support_cost",         "sum"),
        total_margin       = ("contribution_margin",  "sum"),
        orders             = ("order_id",             "count"),
        avg_order_value    = ("order_value",          "mean"),
        acquisition_channel= ("acquisition_channel",  "first"),
        region             = ("region",               "first"),
        is_power_user      = ("is_power_user",        "first"),
    )
    .reset_index()
    .round(2)
)

# Top 10% by support cost
p90_support = support_by_customer["total_support_cost"].quantile(0.90)
support_heavy = support_by_customer[support_by_customer["total_support_cost"] >= p90_support].copy()
support_heavy["is_profitable_customer"] = support_heavy["total_margin"] > 0
support_heavy["support_to_margin_ratio"] = (
    support_heavy["total_support_cost"] / support_heavy["total_margin"].clip(lower=1)
).round(2)

log.info(f"  Support-heavy customers (top 10%): {len(support_heavy):,}")
log.info(f"  Avg margin for support-heavy : ₹{support_heavy['total_margin'].mean():.2f}")
log.info(f"  Avg margin for regular       : ₹{support_by_customer[support_by_customer['total_support_cost'] < p90_support]['total_margin'].mean():.2f}")
log.info(f"  % profitable among support-heavy: {support_heavy['is_profitable_customer'].mean():.1%}")

# =============================================================================
# 6. POWER USER ANALYSIS
# =============================================================================
log.info("\nAnalysing power users vs regular customers …")

power_summary = (
    ue.groupby("is_power_user")
    .agg(
        customers          = ("customer_id",          "nunique"),
        orders             = ("order_id",             "count"),
        total_revenue      = ("net_revenue",           "sum"),
        total_margin       = ("contribution_margin",   "sum"),
        avg_margin         = ("contribution_margin",   "mean"),
        avg_order_value    = ("order_value",           "mean"),
        profitable_pct     = ("is_profitable",         "mean"),
        high_support_pct   = ("is_high_support",       "mean"),
    )
    .reset_index()
    .round(2)
)
power_summary["label"] = power_summary["is_power_user"].map({True: "Power User", False: "Regular"})
power_summary["orders_per_customer"]  = (power_summary["orders"]         / power_summary["customers"]).round(2)
power_summary["revenue_per_customer"] = (power_summary["total_revenue"]  / power_summary["customers"]).round(2)
power_summary["margin_per_customer"]  = (power_summary["total_margin"]   / power_summary["customers"]).round(2)
power_summary["revenue_share"]        = (power_summary["total_revenue"]  / power_summary["total_revenue"].sum() * 100).round(2)

for _, r in power_summary.iterrows():
    log.info(f"  {r['label']:<12}  {r['customers']:,} cust  "
             f"revenue share={r['revenue_share']:.1f}%  "
             f"margin/cust=₹{r['margin_per_customer']:.2f}  "
             f"orders/cust={r['orders_per_customer']:.1f}")

# =============================================================================
# 7. REGION × SERVICE TYPE HEATMAP
# =============================================================================
log.info("\nBuilding region × service type heatmap …")

region_service = (
    ue.groupby(["region", "service_type"])
    .agg(
        orders       = ("order_id",           "count"),
        total_margin = ("contribution_margin", "sum"),
        margin_pct   = ("margin_pct",          "mean"),
        profitable   = ("is_profitable",       "mean"),
    )
    .reset_index()
    .round(2)
)

# Pivot for heatmap
region_service_pivot = region_service.pivot(
    index="region",
    columns="service_type",
    values="margin_pct"
).round(2)
region_service_pivot.index.name = "region"

log.info(f"  Region × service heatmap: {region_service_pivot.shape}")

# =============================================================================
# 8. SAVE
# =============================================================================
log.info("\nSaving outputs …")

outputs = {
    "segment_by_region.csv":         seg_region,
    "segment_by_service.csv":        seg_service,
    "segment_by_channel.csv":        seg_channel,
    "segment_cross_tab.csv":         cross_pivot.reset_index(),
    "support_heavy_customers.csv":   support_heavy,
    "power_user_analysis.csv":       power_summary,
    "region_service_heatmap.csv":    region_service_pivot.reset_index(),
}

for filename, df in outputs.items():
    path = OUTPUTS_DIR / filename
    df.to_csv(path, index=False)
    log.info(f"  ✅  {filename:<45} {len(df):>6,} rows")

log.info("\n" + "=" * 60)
log.info("SEGMENT PROFITABILITY COMPLETE")
log.info(f"  Outputs saved to: {OUTPUTS_DIR}")
log.info("=" * 60)