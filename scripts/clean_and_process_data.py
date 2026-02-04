import pandas as pd
from pathlib import Path

RAW_PATH = Path("data/raw")
PROCESSED_PATH = Path("data/processed")
PROCESSED_PATH.mkdir(exist_ok=True)

# -------------------------
# LOAD RAW DATA
# -------------------------
customers = pd.read_csv(RAW_PATH / "customers.csv", parse_dates=["signup_date"])
orders = pd.read_csv(RAW_PATH / "orders.csv", parse_dates=["order_date"])
costs = pd.read_csv(RAW_PATH / "costs.csv")
marketing = pd.read_csv(RAW_PATH / "marketing_spend.csv", parse_dates=["date"])
support = pd.read_csv(RAW_PATH / "support_tickets.csv", parse_dates=["created_at"])

# -------------------------
# CUSTOMERS (clean)
# -------------------------
customers_clean = customers.copy()
customers_clean["signup_month"] = customers_clean["signup_date"].dt.to_period("M").astype(str)

# -------------------------
# ORDERS (clean + derived)
# -------------------------
orders_clean = orders.copy()
orders_clean["order_month"] = orders_clean["order_date"].dt.to_period("M").astype(str)
orders_clean["is_refunded"] = orders_clean["refund_flag"].astype(bool)

# -------------------------
# COSTS (clean)
# -------------------------
costs_clean = costs.copy()
costs_clean["total_cost"] = (
    costs_clean["variable_cost"]
    + costs_clean["delivery_cost"]
    + costs_clean["support_cost"]
)

# -------------------------
# UNIT ECONOMICS (order-level)
# -------------------------
unit_economics = (
    orders_clean
    .merge(costs_clean, on="order_id", how="left")
)

unit_economics["net_revenue"] = unit_economics["order_value"] * (~unit_economics["is_refunded"])
unit_economics["contribution_margin"] = (
    unit_economics["net_revenue"] - unit_economics["total_cost"]
)

# -------------------------
# SAVE PROCESSED FILES
# -------------------------
customers_clean.to_csv(PROCESSED_PATH / "customers_clean.csv", index=False)
orders_clean.to_csv(PROCESSED_PATH / "orders_clean.csv", index=False)
costs_clean.to_csv(PROCESSED_PATH / "costs_clean.csv", index=False)
unit_economics.to_csv(PROCESSED_PATH / "unit_economics.csv", index=False)
marketing.to_csv(PROCESSED_PATH / "marketing_spend_clean.csv", index=False)
support.to_csv(PROCESSED_PATH / "support_tickets_clean.csv", index=False)

print("Processed datasets created successfully.")
