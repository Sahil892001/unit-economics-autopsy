# =============================================================================
# generate_synthetic_data.py
# Unit Economics Intelligence Platform — Synthetic Data Generator
# =============================================================================
# Generates realistic business data with:
#   - Seasonality (monthly + weekday patterns)
#   - Customer churn simulation (cohort-based retention decay)
#   - Power-law order distribution (Pareto principle)
#   - Cost drift over time (delivery inflation, paid search saturation)
#   - Support cost heavy tail with extreme outliers
#   - Ticket categories for deeper support analysis
# =============================================================================

import sys, logging
from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import (
    RAW_DIR, RANDOM_SEED,
    POWER_USER_PCT, REFUND_RATE, SUPPORT_TICKET_PCT, OUTLIER_PCT,
    REGIONS, CHANNELS, SERVICE_TYPES,
    CHANNEL_MIX, SERVICE_MIX,
    BASE_PRICES, VARIABLE_COST_RATIO, BASE_MARKETING_SPEND,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(ROOT_DIR / "logs" / "data_generation.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

# ── Sizes & dates ─────────────────────────────────────────────────────────────
NUM_CUSTOMERS = 20_000
NUM_ORDERS    = 200_000
START_DATE    = "2024-01-01"
END_DATE      = "2025-12-31"

np.random.seed(RANDOM_SEED)

start_ts  = pd.Timestamp(START_DATE)
end_ts    = pd.Timestamp(END_DATE)
all_dates = pd.date_range(start_ts, end_ts)

# =============================================================================
# HELPERS
# =============================================================================

def seasonal_weight(dates):
    monthly = {1:1.20,2:0.90,3:0.95,4:1.00,5:1.05,6:0.88,
               7:0.85,8:0.92,9:1.00,10:1.08,11:1.18,12:1.35}
    return pd.Series(dates).dt.month.map(monthly).values

def weekday_weight(dates):
    day = {0:1.10,1:1.15,2:1.12,3:1.10,4:1.05,5:0.85,6:0.70}
    return pd.Series(dates).dt.dayofweek.map(day).values

# =============================================================================
# 1. CUSTOMERS
# =============================================================================
log.info("Generating customers ...")

signup_weights = np.linspace(1.0, 2.5, len(all_dates))
signup_weights /= signup_weights.sum()
signup_dates = pd.to_datetime(
    np.random.choice(all_dates, size=NUM_CUSTOMERS, p=signup_weights, replace=True)
)

customers = pd.DataFrame({
    "customer_id":         range(1, NUM_CUSTOMERS + 1),
    "signup_date":         signup_dates,
    "acquisition_channel": np.random.choice(CHANNELS, NUM_CUSTOMERS, p=CHANNEL_MIX),
    "region":              np.random.choice(REGIONS,  NUM_CUSTOMERS),
})

customers["signup_month"] = customers["signup_date"].dt.to_period("M").astype(str)
customers["cohort"]       = customers["signup_month"]

# Churn simulation — exponential decay, channel-adjusted
churn_base = np.random.exponential(scale=8, size=NUM_CUSTOMERS).clip(1, 24).astype(int)
churn_adj  = customers["acquisition_channel"].map({
    "Paid Search": 0.80, "Organic": 1.10, "Referral": 1.25, "Social": 0.95
}).values
customers["active_months"] = np.clip((churn_base * churn_adj).astype(int), 1, 24)
customers["churn_date"] = customers.apply(
    lambda r: r["signup_date"] + pd.DateOffset(months=int(r["active_months"])), axis=1
)
customers["is_churned"]    = customers["churn_date"] <= end_ts
customers["is_power_user"] = customers["customer_id"].isin(
    np.random.choice(customers["customer_id"], size=int(POWER_USER_PCT * NUM_CUSTOMERS), replace=False)
)

power_user_ids = set(customers.loc[customers["is_power_user"], "customer_id"])

log.info(f"  Customers: {len(customers):,}  |  Churned: {customers['is_churned'].mean():.1%}  |  Power users: {len(power_user_ids):,}")

# =============================================================================
# 2. ORDERS
# =============================================================================
log.info("Generating orders (this takes ~30s for 200K) ...")

order_weights = np.where(customers["customer_id"].isin(power_user_ids), 6.0, 1.0)
order_weights /= order_weights.sum()
order_customer_ids = np.random.choice(customers["customer_id"], size=NUM_ORDERS, p=order_weights, replace=True)

cust_lookup = customers.set_index("customer_id")[["signup_date", "churn_date"]].to_dict("index")

order_dates = []
for cid in order_customer_ids:
    info  = cust_lookup[cid]
    low   = max(info["signup_date"], start_ts)
    high  = min(info["churn_date"], end_ts - pd.Timedelta(days=1))
    if low >= high:
        high = min(low + pd.Timedelta(days=1), end_ts)
    window  = pd.date_range(low, high)
    w       = seasonal_weight(window) * weekday_weight(window)
    w      /= w.sum()
    order_dates.append(np.random.choice(window, p=w))

order_dates = pd.to_datetime(order_dates)

orders = pd.DataFrame({
    "order_id":    range(1, NUM_ORDERS + 1),
    "customer_id": order_customer_ids,
    "order_date":  order_dates,
})

# Service type — peaks shift in Nov/Dec/Jan
month = orders["order_date"].dt.month.values
peak  = np.isin(month, [11, 12, 1])
service_probs = np.column_stack([
    np.where(peak, 0.40, 0.55),
    np.where(peak, 0.30, 0.25),
    np.where(peak, 0.30, 0.20),
])
orders["service_type"] = [
    np.random.choice(SERVICE_TYPES, p=service_probs[i]) for i in range(NUM_ORDERS)
]

# Order value — lognormal around base price
orders["order_value"] = (
    orders["service_type"].map(BASE_PRICES).values
    * np.random.lognormal(0, 0.25, NUM_ORDERS)
).clip(10).round(2)

# Refunds — clustered by service type (Express refunds more)
cust_channel   = customers.set_index("customer_id")["acquisition_channel"]
order_channels = orders["customer_id"].map(cust_channel)
refund_prob    = np.where(orders["service_type"] == "Express", 0.09,
                 np.where(orders["service_type"] == "Premium",  0.06, 0.04))
refund_prob    = np.where(order_channels == "Organic", refund_prob * 0.7, refund_prob)
orders["refund_flag"]  = (np.random.rand(NUM_ORDERS) < refund_prob).astype(int)
orders["order_month"]  = orders["order_date"].dt.to_period("M").astype(str)
orders["order_year"]   = orders["order_date"].dt.year

log.info(f"  Orders: {len(orders):,}  |  Refund rate: {orders['refund_flag'].mean():.2%}")

# =============================================================================
# 3. COSTS
# =============================================================================
log.info("Generating costs ...")

costs = orders[["order_id", "order_date", "order_value", "service_type"]].copy()
days  = (costs["order_date"] - start_ts).dt.days.values

var_ratio            = costs["service_type"].map(VARIABLE_COST_RATIO).values
costs["variable_cost"] = (costs["order_value"].values * var_ratio * np.random.normal(1.0, 0.15, NUM_ORDERS)).clip(1).round(2)
costs["delivery_cost"] = (np.random.uniform(6, 18, NUM_ORDERS) * (1 + days / 600)).round(2)

# Support cost — heavy tail, Dec spike, 2% extreme outliers
support = np.random.lognormal(2.0, 1.0, NUM_ORDERS)
support[costs["order_date"].dt.month.values == 12] *= 1.35
outlier_idx = np.random.choice(len(costs), int(OUTLIER_PCT * NUM_ORDERS), replace=False)
support[outlier_idx] *= 8
costs["support_cost"] = support.round(2)
costs = costs[["order_id", "variable_cost", "delivery_cost", "support_cost"]]

# =============================================================================
# 4. MARKETING SPEND
# =============================================================================
log.info("Generating marketing spend ...")

mkt_rows = []
for channel in CHANNELS:
    base = BASE_MARKETING_SPEND[channel]
    day_offsets = (all_dates - start_ts).days.values
    spend = base * np.random.normal(1.0, 0.20, len(all_dates))
    if channel == "Paid Search":
        spend *= (1 + day_offsets / 500)
    elif channel == "Organic":
        spend *= (1 + day_offsets / 1200)
    elif channel == "Social":
        burst_mask = np.random.rand(len(all_dates)) < 0.05
        spend[burst_mask] *= np.random.uniform(2.5, 4.0, burst_mask.sum())
    for i, date in enumerate(all_dates):
        mkt_rows.append({"date": date, "channel": channel, "spend": max(50.0, round(spend[i], 2))})

marketing_spend = pd.DataFrame(mkt_rows)

# =============================================================================
# 5. SUPPORT TICKETS
# =============================================================================
log.info("Generating support tickets ...")

n_tickets = int(NUM_ORDERS * SUPPORT_TICKET_PCT)
support_tickets = pd.DataFrame({
    "ticket_id":       range(1, n_tickets + 1),
    "order_id":        np.random.choice(orders["order_id"], n_tickets, replace=False),
    "resolution_cost": np.random.lognormal(2.2, 0.9, n_tickets).round(2),
    "created_at":      np.random.choice(all_dates, n_tickets),
    "category":        np.random.choice(
        ["Delivery Issue", "Billing", "Service Quality", "Cancellation", "Other"],
        n_tickets, p=[0.35, 0.20, 0.25, 0.12, 0.08],
    ),
})

# =============================================================================
# 6. SAVE
# =============================================================================
log.info("Saving files ...")
customers.to_csv(     RAW_DIR / "customers.csv",        index=False)
orders.to_csv(        RAW_DIR / "orders.csv",            index=False)
costs.to_csv(         RAW_DIR / "costs.csv",             index=False)
marketing_spend.to_csv(RAW_DIR / "marketing_spend.csv", index=False)
support_tickets.to_csv(RAW_DIR / "support_tickets.csv", index=False)

log.info("=" * 55)
log.info("GENERATION COMPLETE")
log.info(f"  Customers      : {len(customers):>8,}")
log.info(f"  Orders         : {len(orders):>8,}")
log.info(f"  Marketing rows : {len(marketing_spend):>8,}")
log.info(f"  Support tickets: {len(support_tickets):>8,}")
log.info(f"  Date range     : {START_DATE}  to  {END_DATE}")
log.info(f"  Churned        : {customers['is_churned'].mean():.1%} of customers")
log.info(f"  Refund rate    : {orders['refund_flag'].mean():.2%}")
log.info(f"  Files saved to : {RAW_DIR}")
log.info("=" * 55)




