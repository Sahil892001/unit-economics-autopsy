import pandas as pd
import numpy as np

np.random.seed(42)

# -------------------------
# CONFIG
# -------------------------
NUM_CUSTOMERS = 5000
NUM_ORDERS = 60000
START_DATE = pd.to_datetime("2023-01-01")
END_DATE = pd.to_datetime("2024-12-31")

regions = ["North", "South", "East", "West"]
channels = ["Paid Search", "Organic", "Referral", "Social"]
service_types = ["Standard", "Premium", "Express"]

dates = pd.date_range(START_DATE, END_DATE)

# -------------------------
# CUSTOMERS
# -------------------------
customers = pd.DataFrame({
    "customer_id": range(1, NUM_CUSTOMERS + 1),
    "signup_date": np.random.choice(dates, NUM_CUSTOMERS),
    "acquisition_channel": np.random.choice(
        channels, NUM_CUSTOMERS, p=[0.45, 0.3, 0.15, 0.1]
    ),
    "region": np.random.choice(regions, NUM_CUSTOMERS)
})

# Power users (top 5%)
power_users = np.random.choice(customers["customer_id"], size=int(0.05 * NUM_CUSTOMERS), replace=False)

# -------------------------
# ORDERS
# -------------------------
orders = pd.DataFrame({
    "order_id": range(1, NUM_ORDERS + 1),
    "customer_id": np.random.choice(
        customers["customer_id"],
        NUM_ORDERS,
        p=np.where(
            customers["customer_id"].isin(power_users),
            5,
            1
        ) / np.where(
            customers["customer_id"].isin(power_users),
            5,
            1
        ).sum()
    )
})

orders["order_date"] = np.random.choice(dates, NUM_ORDERS)
orders["service_type"] = np.random.choice(
    service_types, NUM_ORDERS, p=[0.55, 0.25, 0.20]
)

base_prices = {
    "Standard": 50,
    "Premium": 90,
    "Express": 140
}

orders["order_value"] = orders["service_type"].map(base_prices)
orders["order_value"] *= np.random.lognormal(mean=0, sigma=0.25, size=NUM_ORDERS)
orders["order_value"] = orders["order_value"].clip(lower=10).round(2)

orders["refund_flag"] = np.random.choice([0, 1], NUM_ORDERS, p=[0.94, 0.06])

# -------------------------
# COSTS (with drift + outliers)
# -------------------------
costs = orders[["order_id", "order_date", "service_type"]].copy()

base_variable_cost = {
    "Standard": 0.45,
    "Premium": 0.50,
    "Express": 0.60
}

costs["variable_cost"] = (
    orders["order_value"]
    * costs["service_type"].map(base_variable_cost)
    * np.random.normal(1.0, 0.15, NUM_ORDERS)
)

# delivery cost inflation over time
costs["delivery_cost"] = np.random.uniform(6, 18, NUM_ORDERS)
costs["delivery_cost"] *= (
    1 + (costs["order_date"] - START_DATE).dt.days / 900
)

# support costs with heavy tail
costs["support_cost"] = np.random.lognormal(mean=2.0, sigma=1.0, size=NUM_ORDERS)

# extreme support outliers (2%)
outliers = np.random.choice(costs.index, size=int(0.02 * NUM_ORDERS), replace=False)
costs.loc[outliers, "support_cost"] *= 8

costs = costs.round(2)[["order_id", "variable_cost", "delivery_cost", "support_cost"]]

# -------------------------
# MARKETING SPEND (efficiency decay)
# -------------------------
marketing_spend = pd.DataFrame({
    "date": np.tile(dates, len(channels)),
    "channel": np.repeat(channels, len(dates))
})

base_spend = {
    "Paid Search": 2200,
    "Organic": 450,
    "Referral": 350,
    "Social": 650
}

marketing_spend["spend"] = marketing_spend["channel"].map(base_spend)
marketing_spend["spend"] *= np.random.normal(1.0, 0.25, len(marketing_spend))

# paid search gets worse over time
mask = marketing_spend["channel"] == "Paid Search"
marketing_spend.loc[mask, "spend"] *= (
    1 + (marketing_spend.loc[mask, "date"] - START_DATE).dt.days / 800
)

marketing_spend["spend"] = marketing_spend["spend"].clip(lower=50).round(2)

# -------------------------
# SUPPORT TICKETS
# -------------------------
num_tickets = int(NUM_ORDERS * 0.35)

support_tickets = pd.DataFrame({
    "ticket_id": range(1, num_tickets + 1),
    "order_id": np.random.choice(orders["order_id"], num_tickets),
    "resolution_cost": np.random.lognormal(mean=2.2, sigma=0.9, size=num_tickets).round(2)
})

support_tickets["created_at"] = np.random.choice(dates, num_tickets)

# -------------------------
# SAVE FILES
# -------------------------
customers.to_csv("data/raw/customers.csv", index=False)
orders.to_csv("data/raw/orders.csv", index=False)
costs.to_csv("data/raw/costs.csv", index=False)
marketing_spend.to_csv("data/raw/marketing_spend.csv", index=False)
support_tickets.to_csv("data/raw/support_tickets.csv", index=False)

print("Enhanced synthetic data generation complete.")