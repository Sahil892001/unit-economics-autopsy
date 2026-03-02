# =============================================================================
# clean_and_process_data.py
# Unit Economics Intelligence Platform — Data Cleaning & Processing Pipeline
# =============================================================================
# Pipeline stages:
#   1. LOAD        — read raw CSVs with type enforcement
#   2. VALIDATE    — null checks, range checks, referential integrity
#   3. CLEAN       — fix types, strip whitespace, cap outliers (flagged not dropped)
#   4. ENRICH      — derived columns: cohort, tenure, margin buckets, flags
#   5. BUILD       — assemble unit_economics master table
#   6. AGGREGATE   — monthly summaries for dashboard performance
#   7. SAVE        — write all processed CSVs + data quality report
# =============================================================================

import sys
import logging
from pathlib import Path

import pandas as pd
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import (
    RAW_DIR, PROCESSED_DIR, LOGS_DIR,
    START_DATE, END_DATE,
    MAX_NULL_PCT, MAX_ORDER_VALUE, MIN_ORDER_VALUE, MAX_SUPPORT_COST,
    MIN_HEALTHY_MARGIN, HIGH_SUPPORT_THRESHOLD, HIGH_VALUE_ORDER,
    MARGIN_BUCKETS, CHANNELS, SERVICE_TYPES, REGIONS,
)

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "processing.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

START_TS = pd.Timestamp(START_DATE)
END_TS   = pd.Timestamp(END_DATE)

# ─────────────────────────────────────────────────────────────────────────────
# HELPER: DATA QUALITY CHECKER
# ─────────────────────────────────────────────────────────────────────────────
dq_issues = []   # collects all warnings — written to report at end

def dq_check(condition: bool, severity: str, table: str, message: str):
    """Log a data quality finding and store it for the final report."""
    status = "✅ PASS" if condition else f"{'⚠️  WARN' if severity == 'warning' else '❌ FAIL'}"
    log.info(f"  [{table}] {status}  {message}")
    if not condition:
        dq_issues.append({"severity": severity, "table": table, "issue": message})

def null_check(df: pd.DataFrame, table: str):
    """Check null rates across all columns."""
    for col in df.columns:
        null_pct = df[col].isna().mean()
        dq_check(
            null_pct <= MAX_NULL_PCT,
            "warning",
            table,
            f"Column '{col}': {null_pct:.2%} nulls (threshold {MAX_NULL_PCT:.0%})"
        )

def range_check(df: pd.DataFrame, col: str, low, high, table: str):
    """Check that values fall within [low, high]."""
    out = ((df[col] < low) | (df[col] > high)).sum()
    dq_check(out == 0, "warning", table, f"'{col}' has {out:,} values outside [{low}, {high}]")

def referential_check(child_ids, parent_ids, child_col: str, parent_table: str, child_table: str):
    """Check referential integrity between two tables."""
    orphans = (~child_ids.isin(parent_ids)).sum()
    dq_check(orphans == 0, "error", child_table,
             f"'{child_col}' has {orphans:,} IDs not found in {parent_table}")

# =============================================================================
# STAGE 1 — LOAD
# =============================================================================
log.info("=" * 60)
log.info("STAGE 1: LOADING RAW DATA")
log.info("=" * 60)

customers = pd.read_csv(RAW_DIR / "customers.csv",        parse_dates=["signup_date"])
orders    = pd.read_csv(RAW_DIR / "orders.csv",           parse_dates=["order_date"])
costs     = pd.read_csv(RAW_DIR / "costs.csv")
marketing = pd.read_csv(RAW_DIR / "marketing_spend.csv",  parse_dates=["date"])
support   = pd.read_csv(RAW_DIR / "support_tickets.csv",  parse_dates=["created_at"])

log.info(f"  customers       : {len(customers):>8,} rows")
log.info(f"  orders          : {len(orders):>8,} rows")
log.info(f"  costs           : {len(costs):>8,} rows")
log.info(f"  marketing_spend : {len(marketing):>8,} rows")
log.info(f"  support_tickets : {len(support):>8,} rows")

# =============================================================================
# STAGE 2 — VALIDATE
# =============================================================================
log.info("\n" + "=" * 60)
log.info("STAGE 2: DATA VALIDATION")
log.info("=" * 60)

# ── Null checks ───────────────────────────────────────────────────────────────
log.info("  Running null checks …")
for name, df in [("customers", customers), ("orders", orders),
                 ("costs", costs), ("marketing", marketing), ("support", support)]:
    null_check(df, name)

# ── Range checks ──────────────────────────────────────────────────────────────
log.info("  Running range checks …")
range_check(orders,   "order_value",    MIN_ORDER_VALUE, MAX_ORDER_VALUE, "orders")
range_check(costs,    "support_cost",   0,               MAX_SUPPORT_COST, "costs")
range_check(costs,    "variable_cost",  0,               MAX_ORDER_VALUE,  "costs")
range_check(costs,    "delivery_cost",  0,               200,              "costs")
range_check(marketing,"spend",          0,               100_000,          "marketing")

# ── Date range checks ─────────────────────────────────────────────────────────
log.info("  Running date range checks …")
dq_check(orders["order_date"].min() >= START_TS, "warning", "orders",
         f"Earliest order date: {orders['order_date'].min().date()}")
dq_check(orders["order_date"].max() <= END_TS,   "warning", "orders",
         f"Latest order date: {orders['order_date'].max().date()}")

# ── Referential integrity ─────────────────────────────────────────────────────
log.info("  Running referential integrity checks …")
referential_check(orders["customer_id"],  customers["customer_id"], "customer_id", "customers", "orders")
referential_check(costs["order_id"],      orders["order_id"],       "order_id",    "orders",    "costs")
referential_check(support["order_id"],    orders["order_id"],       "order_id",    "orders",    "support")

# ── Categorical value checks ──────────────────────────────────────────────────
log.info("  Running categorical checks …")
invalid_channels = (~customers["acquisition_channel"].isin(CHANNELS)).sum()
dq_check(invalid_channels == 0, "error", "customers",
         f"acquisition_channel: {invalid_channels:,} invalid values")

invalid_services = (~orders["service_type"].isin(SERVICE_TYPES)).sum()
dq_check(invalid_services == 0, "error", "orders",
         f"service_type: {invalid_services:,} invalid values")

invalid_regions = (~customers["region"].isin(REGIONS)).sum()
dq_check(invalid_regions == 0, "error", "customers",
         f"region: {invalid_regions:,} invalid values")

# ── Duplicate checks ──────────────────────────────────────────────────────────
log.info("  Running duplicate checks …")
dq_check(customers["customer_id"].duplicated().sum() == 0, "error",   "customers", "customer_id duplicates")
dq_check(orders["order_id"].duplicated().sum() == 0,       "error",   "orders",    "order_id duplicates")
dq_check(costs["order_id"].duplicated().sum() == 0,        "warning", "costs",     "order_id duplicates in costs")

log.info(f"\n  DQ Summary: {len(dq_issues)} issue(s) found")

# =============================================================================
# STAGE 3 — CLEAN
# =============================================================================
log.info("\n" + "=" * 60)
log.info("STAGE 3: CLEANING")
log.info("=" * 60)

# ── Customers ─────────────────────────────────────────────────────────────────
customers_clean = customers.copy()
customers_clean["acquisition_channel"] = customers_clean["acquisition_channel"].str.strip()
customers_clean["region"]              = customers_clean["region"].str.strip()
# Enforce boolean
customers_clean["is_churned"]    = customers_clean["is_churned"].astype(bool)
customers_clean["is_power_user"] = customers_clean["is_power_user"].astype(bool)
log.info(f"  customers_clean : {len(customers_clean):,} rows — dtypes enforced")

# ── Orders ────────────────────────────────────────────────────────────────────
orders_clean = orders.copy()
orders_clean["service_type"]  = orders_clean["service_type"].str.strip()
orders_clean["is_refunded"]   = orders_clean["refund_flag"].astype(bool)
# Flag anomalous order values (keep row, add flag column)
orders_clean["is_anomalous_value"] = (
    (orders_clean["order_value"] < MIN_ORDER_VALUE) |
    (orders_clean["order_value"] > MAX_ORDER_VALUE)
)
n_anomalous = orders_clean["is_anomalous_value"].sum()
log.info(f"  orders_clean    : {len(orders_clean):,} rows | {n_anomalous:,} anomalous values flagged")

# ── Costs ─────────────────────────────────────────────────────────────────────
costs_clean = costs.copy()
# Cap extreme support costs at 99th percentile — flag before capping
p99_support = costs_clean["support_cost"].quantile(0.99)
costs_clean["support_cost_raw"]    = costs_clean["support_cost"]
costs_clean["is_support_outlier"]  = costs_clean["support_cost"] > p99_support
costs_clean["support_cost"]        = costs_clean["support_cost"].clip(upper=p99_support)
costs_clean["total_cost"]          = (
    costs_clean["variable_cost"] +
    costs_clean["delivery_cost"] +
    costs_clean["support_cost"]
).round(2)
n_outliers = costs_clean["is_support_outlier"].sum()
log.info(f"  costs_clean     : {len(costs_clean):,} rows | {n_outliers:,} support outliers capped at ₹{p99_support:.2f}")

# ── Marketing ─────────────────────────────────────────────────────────────────
marketing_clean = marketing.copy()
marketing_clean["channel"] = marketing_clean["channel"].str.strip()
marketing_clean["spend"]   = marketing_clean["spend"].clip(lower=0)
log.info(f"  marketing_clean : {len(marketing_clean):,} rows")

# ── Support tickets ───────────────────────────────────────────────────────────
support_clean = support.copy()
support_clean["category"] = support_clean["category"].str.strip()
log.info(f"  support_clean   : {len(support_clean):,} rows")

# =============================================================================
# STAGE 4 — ENRICH  (derived columns)
# =============================================================================
log.info("\n" + "=" * 60)
log.info("STAGE 4: ENRICHMENT")
log.info("=" * 60)

# ── Customers: cohort + tenure ────────────────────────────────────────────────
customers_clean["signup_month"]       = customers_clean["signup_date"].dt.to_period("M").astype(str)
customers_clean["signup_year"]        = customers_clean["signup_date"].dt.year
customers_clean["signup_quarter"]     = customers_clean["signup_date"].dt.to_period("Q").astype(str)
customers_clean["cohort"]             = customers_clean["signup_month"]
customers_clean["tenure_days"]        = (END_TS - customers_clean["signup_date"]).dt.days.clip(lower=0)
customers_clean["tenure_months"]      = (customers_clean["tenure_days"] / 30).astype(int).clip(lower=0)
customers_clean["tenure_bucket"]      = pd.cut(
    customers_clean["tenure_months"],
    bins=[0, 3, 6, 12, 24, 999],
    labels=["0–3 mo", "3–6 mo", "6–12 mo", "12–24 mo", "24+ mo"],
    right=False,
)
log.info(f"  customers: cohort, tenure_days, tenure_months, tenure_bucket added")

# ── Orders: time dimensions ───────────────────────────────────────────────────
orders_clean["order_month"]     = orders_clean["order_date"].dt.to_period("M").astype(str)
orders_clean["order_year"]      = orders_clean["order_date"].dt.year
orders_clean["order_quarter"]   = orders_clean["order_date"].dt.to_period("Q").astype(str)
orders_clean["order_dow"]       = orders_clean["order_date"].dt.day_name()
orders_clean["is_peak_month"]   = orders_clean["order_date"].dt.month.isin([11, 12, 1])
orders_clean["is_weekend"]      = orders_clean["order_date"].dt.dayofweek >= 5
orders_clean["is_high_value"]   = orders_clean["order_value"] >= HIGH_VALUE_ORDER
log.info(f"  orders: month, quarter, dow, peak flag, weekend flag added")

# ── Costs: flags ─────────────────────────────────────────────────────────────
costs_clean["is_high_support"] = costs_clean["support_cost"] >= HIGH_SUPPORT_THRESHOLD
log.info(f"  costs: is_high_support flag added")

# =============================================================================
# STAGE 5 — BUILD UNIT ECONOMICS MASTER TABLE
# =============================================================================
log.info("\n" + "=" * 60)
log.info("STAGE 5: BUILDING UNIT ECONOMICS TABLE")
log.info("=" * 60)

unit_economics = (
    orders_clean
    .merge(costs_clean, on="order_id", how="left")
    .merge(customers_clean[["customer_id", "acquisition_channel", "region",
                             "cohort", "signup_date", "tenure_months",
                             "is_power_user", "is_churned"]], on="customer_id", how="left")
)

# Core financials
unit_economics["net_revenue"] = (
    unit_economics["order_value"] * (~unit_economics["is_refunded"])
).round(2)

unit_economics["contribution_margin"] = (
    unit_economics["net_revenue"] - unit_economics["total_cost"]
).round(2)

unit_economics["margin_pct"] = np.where(
    unit_economics["net_revenue"] > 0,
    (unit_economics["contribution_margin"] / unit_economics["net_revenue"] * 100).round(2),
    0.0
)

# Margin bucket (uses MARGIN_BUCKETS from config — single source of truth)
def assign_margin_bucket(margin):
    for bucket, (low, high) in MARGIN_BUCKETS.items():
        if low is None and margin < high:
            return bucket
        elif high is None and margin >= low:
            return bucket
        elif low is not None and high is not None and low <= margin < high:
            return bucket
    return "High Margin"

unit_economics["margin_bucket"] = unit_economics["contribution_margin"].apply(assign_margin_bucket)

# Profitability flag
unit_economics["is_profitable"] = unit_economics["contribution_margin"] > MIN_HEALTHY_MARGIN

# Months since signup (for cohort age at time of order)
unit_economics["months_since_signup"] = (
    (unit_economics["order_date"].dt.to_period("M") -
     unit_economics["signup_date"].dt.to_period("M"))
    .apply(lambda x: x.n if hasattr(x, "n") else 0)
    .clip(lower=0)
)

log.info(f"  unit_economics  : {len(unit_economics):,} rows × {unit_economics.shape[1]} columns")
log.info(f"  Profitable orders : {unit_economics['is_profitable'].mean():.1%}")
log.info(f"  Avg margin/order  : ₹{unit_economics['contribution_margin'].mean():.2f}")
log.info(f"  Total net revenue : ₹{unit_economics['net_revenue'].sum():,.0f}")
log.info(f"  Total margin      : ₹{unit_economics['contribution_margin'].sum():,.0f}")

# =============================================================================
# STAGE 6 — MONTHLY AGGREGATES  (pre-computed for dashboard speed)
# =============================================================================
log.info("\n" + "=" * 60)
log.info("STAGE 6: BUILDING MONTHLY AGGREGATES")
log.info("=" * 60)

# Monthly unit economics summary
monthly_summary = (
    unit_economics
    .groupby("order_month")
    .agg(
        orders          = ("order_id",             "count"),
        revenue         = ("net_revenue",           "sum"),
        total_cost      = ("total_cost",            "sum"),
        margin          = ("contribution_margin",   "sum"),
        avg_margin      = ("contribution_margin",   "mean"),
        profitable_pct  = ("is_profitable",         "mean"),
        refund_rate     = ("is_refunded",           "mean"),
        avg_order_value = ("order_value",           "mean"),
    )
    .reset_index()
)
monthly_summary["margin_pct"] = (monthly_summary["margin"] / monthly_summary["revenue"] * 100).round(2)
monthly_summary = monthly_summary.sort_values("order_month").reset_index(drop=True)
log.info(f"  monthly_summary : {len(monthly_summary):,} months")

# Monthly cost breakdown
monthly_costs = (
    unit_economics
    .groupby("order_month")
    .agg(
        variable_cost = ("variable_cost", "sum"),
        delivery_cost = ("delivery_cost", "sum"),
        support_cost  = ("support_cost",  "sum"),
        total_cost    = ("total_cost",    "sum"),
    )
    .reset_index()
    .sort_values("order_month")
    .reset_index(drop=True)
)
log.info(f"  monthly_costs   : {len(monthly_costs):,} months")

# Channel monthly summary (for CAC/LTV trend)
channel_monthly = (
    unit_economics
    .groupby(["order_month", "acquisition_channel"])
    .agg(
        orders  = ("order_id",           "count"),
        revenue = ("net_revenue",         "sum"),
        margin  = ("contribution_margin", "sum"),
    )
    .reset_index()
    .sort_values(["order_month", "acquisition_channel"])
    .reset_index(drop=True)
)
log.info(f"  channel_monthly : {len(channel_monthly):,} rows")

# Service type monthly summary
service_monthly = (
    unit_economics
    .groupby(["order_month", "service_type"])
    .agg(
        orders  = ("order_id",           "count"),
        revenue = ("net_revenue",         "sum"),
        margin  = ("contribution_margin", "sum"),
    )
    .reset_index()
    .sort_values(["order_month", "service_type"])
    .reset_index(drop=True)
)
log.info(f"  service_monthly : {len(service_monthly):,} rows")

# =============================================================================
# STAGE 7 — SAVE ALL PROCESSED FILES
# =============================================================================
log.info("\n" + "=" * 60)
log.info("STAGE 7: SAVING PROCESSED FILES")
log.info("=" * 60)

files_to_save = {
    "customers_clean.csv":       customers_clean,
    "orders_clean.csv":          orders_clean,
    "costs_clean.csv":           costs_clean,
    "marketing_spend_clean.csv": marketing_clean,
    "support_tickets_clean.csv": support_clean,
    "unit_economics.csv":        unit_economics,
    "monthly_summary.csv":       monthly_summary,
    "monthly_costs.csv":         monthly_costs,
    "channel_monthly.csv":       channel_monthly,
    "service_monthly.csv":       service_monthly,
}

for filename, df in files_to_save.items():
    path = PROCESSED_DIR / filename
    df.to_csv(path, index=False)
    log.info(f"  ✅  {filename:<35} {len(df):>8,} rows  {df.shape[1]:>3} cols")

# =============================================================================
# DATA QUALITY REPORT
# =============================================================================
log.info("\n" + "=" * 60)
log.info("DATA QUALITY REPORT")
log.info("=" * 60)

if not dq_issues:
    log.info("  ✅  All checks passed — no issues found")
else:
    errors   = [i for i in dq_issues if i["severity"] == "error"]
    warnings = [i for i in dq_issues if i["severity"] == "warning"]
    log.info(f"  ❌  Errors   : {len(errors)}")
    log.info(f"  ⚠️   Warnings : {len(warnings)}")
    for issue in dq_issues:
        log.info(f"     [{issue['severity'].upper()}] {issue['table']} — {issue['issue']}")

# Save DQ report as CSV for reference
dq_report = pd.DataFrame(dq_issues) if dq_issues else pd.DataFrame(
    columns=["severity", "table", "issue"]
)
dq_report.to_csv(PROCESSED_DIR / "dq_report.csv", index=False)
log.info(f"\n  DQ report saved to: {PROCESSED_DIR / 'dq_report.csv'}")

log.info("\n" + "=" * 60)
log.info("PROCESSING COMPLETE")
log.info("=" * 60)
log.info(f"  Output directory : {PROCESSED_DIR}")
log.info(f"  Files written    : {len(files_to_save)}")
log.info(f"  DQ issues        : {len(dq_issues)}")
log.info("=" * 60)

