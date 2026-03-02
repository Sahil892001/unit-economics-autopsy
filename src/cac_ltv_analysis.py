# =============================================================================
# cac_ltv_analysis.py
# Unit Economics Intelligence Platform — CAC vs LTV Analysis
# =============================================================================
# Outputs:
#   cac_ltv_by_channel.csv       — CAC, LTV, LTV/CAC ratio per channel
#   cac_trend_monthly.csv        — rolling CAC per channel over time
#   ltv_distribution.csv         — LTV distribution per customer (for box plots)
#   payback_period.csv           — months to recover CAC per channel
#   channel_efficiency_score.csv — composite efficiency ranking
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
    HEALTHY_LTV_CAC_RATIO, WARNING_LTV_CAC_RATIO,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "cac_ltv_analysis.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

# =============================================================================
# LOAD
# =============================================================================
log.info("=" * 60)
log.info("CAC vs LTV ANALYSIS")
log.info("=" * 60)

conn = sqlite3.connect(DB_PATH)

ue = pd.read_sql("""
    SELECT
        order_id, customer_id, acquisition_channel,
        order_month, cohort, months_since_signup,
        net_revenue, contribution_margin, is_profitable
    FROM unit_economics
""", conn)

customers = pd.read_sql("""
    SELECT customer_id, acquisition_channel, signup_month, active_months, is_churned
    FROM customers
""", conn)

marketing = pd.read_sql("""
    SELECT date, channel, spend
    FROM marketing_spend
""", conn, parse_dates=["date"])

conn.close()
log.info(f"  unit_economics  : {len(ue):,} rows")
log.info(f"  customers       : {len(customers):,} rows")
log.info(f"  marketing_spend : {len(marketing):,} rows")

# =============================================================================
# 1. CAC BY CHANNEL
# =============================================================================
log.info("\nComputing CAC by channel …")

customers_by_channel = (
    customers
    .groupby("acquisition_channel")["customer_id"]
    .nunique()
    .reset_index()
    .rename(columns={"customer_id": "customers_acquired"})
)

spend_by_channel = (
    marketing
    .groupby("channel")["spend"]
    .sum()
    .reset_index()
    .rename(columns={"channel": "acquisition_channel", "spend": "total_spend"})
)

cac_df = customers_by_channel.merge(spend_by_channel, on="acquisition_channel", how="left")
cac_df["cac"] = (cac_df["total_spend"] / cac_df["customers_acquired"]).round(2)

log.info("  CAC by channel:")
for _, r in cac_df.iterrows():
    log.info(f"    {r['acquisition_channel']:<15} ₹{r['cac']:>8.2f}  ({r['customers_acquired']:,} customers)")

# =============================================================================
# 2. LTV BY CHANNEL
# =============================================================================
log.info("\nComputing LTV by channel …")

# Lifetime margin per customer
customer_ltv = (
    ue
    .groupby("customer_id")
    .agg(
        lifetime_margin  = ("contribution_margin", "sum"),
        lifetime_revenue = ("net_revenue",          "sum"),
        total_orders     = ("order_id",             "count"),
    )
    .reset_index()
)

# Attach channel
customer_ltv = customer_ltv.merge(
    customers[["customer_id", "acquisition_channel", "active_months", "is_churned"]],
    on="customer_id", how="left"
)

ltv_by_channel = (
    customer_ltv
    .groupby("acquisition_channel")
    .agg(
        avg_ltv              = ("lifetime_margin",  "mean"),
        median_ltv           = ("lifetime_margin",  "median"),
        total_ltv            = ("lifetime_margin",  "sum"),
        avg_lifetime_revenue = ("lifetime_revenue", "mean"),
        avg_orders           = ("total_orders",     "mean"),
        avg_active_months    = ("active_months",    "mean"),
    )
    .reset_index()
    .round(2)
)

log.info("  LTV by channel:")
for _, r in ltv_by_channel.iterrows():
    log.info(f"    {r['acquisition_channel']:<15}  avg LTV=₹{r['avg_ltv']:>8.2f}  avg orders={r['avg_orders']:.1f}")

# =============================================================================
# 3. CAC vs LTV MASTER TABLE
# =============================================================================
log.info("\nBuilding CAC vs LTV comparison …")

cac_ltv = cac_df.merge(ltv_by_channel, on="acquisition_channel", how="left")
cac_ltv["ltv_to_cac_ratio"] = (cac_ltv["avg_ltv"] / cac_ltv["cac"]).round(2)
cac_ltv["ltv_cac_health"]   = cac_ltv["ltv_to_cac_ratio"].apply(
    lambda x: "Healthy"  if x >= HEALTHY_LTV_CAC_RATIO  else
              ("Warning"  if x >= WARNING_LTV_CAC_RATIO   else "Critical")
)

# Margin after CAC recovery
cac_ltv["net_value_after_cac"] = (cac_ltv["avg_ltv"] - cac_ltv["cac"]).round(2)

cac_ltv = cac_ltv.sort_values("ltv_to_cac_ratio", ascending=False).reset_index(drop=True)

log.info("  CAC/LTV Summary:")
for _, r in cac_ltv.iterrows():
    log.info(f"    {r['acquisition_channel']:<15}  CAC=₹{r['cac']:>7.2f}  "
             f"LTV=₹{r['avg_ltv']:>7.2f}  Ratio={r['ltv_to_cac_ratio']:>5.2f}x  [{r['ltv_cac_health']}]")

# =============================================================================
# 4. ROLLING CAC TREND (monthly)
# =============================================================================
log.info("\nBuilding monthly CAC trend …")

marketing["month"] = marketing["date"].dt.to_period("M").astype(str)
monthly_spend = (
    marketing
    .groupby(["month", "channel"])["spend"]
    .sum()
    .reset_index()
    .rename(columns={"channel": "acquisition_channel"})
)

# Monthly new customer acquisitions (signup month as proxy)
customers["signup_month_str"] = customers["signup_month"].astype(str)
monthly_acq = (
    customers
    .groupby(["signup_month_str", "acquisition_channel"])["customer_id"]
    .nunique()
    .reset_index()
    .rename(columns={"signup_month_str": "month", "customer_id": "new_customers"})
)

cac_trend = monthly_spend.merge(monthly_acq, on=["month", "acquisition_channel"], how="left")
cac_trend["new_customers"] = cac_trend["new_customers"].fillna(0)
cac_trend["monthly_cac"]   = np.where(
    cac_trend["new_customers"] > 0,
    (cac_trend["spend"] / cac_trend["new_customers"]).round(2),
    np.nan
)
cac_trend = cac_trend.sort_values(["acquisition_channel", "month"]).reset_index(drop=True)
log.info(f"  CAC trend: {len(cac_trend)} rows across {cac_trend['month'].nunique()} months")

# =============================================================================
# 5. LTV DISTRIBUTION (per customer, for box plots)
# =============================================================================
log.info("\nBuilding LTV distribution …")

ltv_dist = customer_ltv[[
    "customer_id", "acquisition_channel",
    "lifetime_margin", "lifetime_revenue",
    "total_orders", "active_months", "is_churned"
]].copy()
ltv_dist["ltv_bucket"] = pd.cut(
    ltv_dist["lifetime_margin"],
    bins=[-np.inf, -50, 0, 50, 150, np.inf],
    labels=["Deep Loss (<-50)", "Loss (-50–0)", "Low (0–50)", "Healthy (50–150)", "High (>150)"]
)
log.info(f"  LTV distribution: {len(ltv_dist):,} customers")

# =============================================================================
# 6. PAYBACK PERIOD — months to recover CAC from cumulative margin
# =============================================================================
log.info("\nComputing payback periods …")

# Average monthly margin per customer per channel
monthly_margin_per_customer = (
    ue
    .groupby(["acquisition_channel", "months_since_signup"])["contribution_margin"]
    .mean()
    .reset_index()
    .rename(columns={"contribution_margin": "avg_margin_in_month"})
    .sort_values(["acquisition_channel", "months_since_signup"])
)

monthly_margin_per_customer["cum_margin"] = (
    monthly_margin_per_customer
    .groupby("acquisition_channel")["avg_margin_in_month"]
    .cumsum()
    .round(2)
)

payback_rows = []
for channel in monthly_margin_per_customer["acquisition_channel"].unique():
    cac_val = cac_df.loc[cac_df["acquisition_channel"] == channel, "cac"].values
    if len(cac_val) == 0:
        continue
    cac_val = cac_val[0]

    channel_df = monthly_margin_per_customer[
        monthly_margin_per_customer["acquisition_channel"] == channel
    ].reset_index(drop=True)

    payback_month = None
    for _, row in channel_df.iterrows():
        if row["cum_margin"] >= cac_val:
            payback_month = int(row["months_since_signup"])
            break

    payback_rows.append({
        "acquisition_channel": channel,
        "cac":                 round(cac_val, 2),
        "payback_month":       payback_month if payback_month is not None else ">24",
        "recovered":           payback_month is not None,
    })

payback_df = pd.DataFrame(payback_rows).sort_values("acquisition_channel").reset_index(drop=True)

log.info("  Payback periods:")
for _, r in payback_df.iterrows():
    log.info(f"    {r['acquisition_channel']:<15}  CAC=₹{r['cac']:.2f}  "
             f"Payback={r['payback_month']} months  Recovered={r['recovered']}")

# =============================================================================
# 7. CHANNEL EFFICIENCY SCORE (composite rank)
# =============================================================================
log.info("\nBuilding channel efficiency scores …")

eff = cac_ltv[["acquisition_channel", "cac", "avg_ltv", "ltv_to_cac_ratio",
               "avg_active_months", "ltv_cac_health"]].copy()

# Normalise each metric 0–1 (higher = better)
for col, ascending in [("cac", True), ("avg_ltv", False),
                        ("ltv_to_cac_ratio", False), ("avg_active_months", False)]:
    mn, mx = eff[col].min(), eff[col].max()
    if mx > mn:
        norm = (eff[col] - mn) / (mx - mn)
        eff[f"{col}_score"] = (1 - norm) if ascending else norm   # lower CAC = better
    else:
        eff[f"{col}_score"] = 1.0

# Weighted composite (CAC 20%, LTV 30%, Ratio 30%, Tenure 20%)
eff["efficiency_score"] = (
    eff["cac_score"]              * 0.20 +
    eff["avg_ltv_score"]          * 0.30 +
    eff["ltv_to_cac_ratio_score"] * 0.30 +
    eff["avg_active_months_score"]* 0.20
).round(4)

eff = eff.sort_values("efficiency_score", ascending=False).reset_index(drop=True)
eff["rank"] = eff.index + 1

log.info("  Channel efficiency ranking:")
for _, r in eff.iterrows():
    log.info(f"    #{r['rank']} {r['acquisition_channel']:<15}  score={r['efficiency_score']:.3f}")

# =============================================================================
# 8. SAVE
# =============================================================================
log.info("\nSaving outputs …")

outputs = {
    "cac_ltv_by_channel.csv":        cac_ltv,
    "cac_trend_monthly.csv":         cac_trend,
    "ltv_distribution.csv":          ltv_dist,
    "payback_period.csv":            payback_df,
    "channel_efficiency_score.csv":  eff,
}

for filename, df in outputs.items():
    path = OUTPUTS_DIR / filename
    df.to_csv(path, index=False)
    log.info(f"  ✅  {filename:<45} {len(df):>6,} rows")

log.info("\n" + "=" * 60)
log.info("CAC vs LTV ANALYSIS COMPLETE")
log.info(f"  Outputs saved to: {OUTPUTS_DIR}")
log.info("=" * 60)