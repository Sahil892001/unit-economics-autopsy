import pandas as pd

DATA_PATH = "data/processed/unit_economics.csv"

df = pd.read_csv(DATA_PATH)

# -------------------------
# BASELINE
# -------------------------
baseline_margin = df["contribution_margin"].sum()

results = []

# -------------------------
# Scenario 1: Price increase (5%)
# -------------------------
price_increase = df.copy()
price_increase["new_margin"] = (
    price_increase["contribution_margin"] +
    (price_increase["net_revenue"] * 0.05)
)
results.append({
    "scenario": "5% price increase",
    "total_margin": round(price_increase["new_margin"].sum(), 2)
})

# -------------------------
# Scenario 2: Remove loss-making orders
# -------------------------
remove_losses = df[df["contribution_margin"] >= 0]
results.append({
    "scenario": "Remove loss-making orders",
    "total_margin": round(remove_losses["contribution_margin"].sum(), 2)
})

# -------------------------
# Scenario 3: Reduce support costs (20%)
# -------------------------
support_reduction = df.copy()
support_reduction["new_margin"] = (
    support_reduction["contribution_margin"] +
    (support_reduction["support_cost"] * 0.20)
)
results.append({
    "scenario": "20% support cost reduction",
    "total_margin": round(support_reduction["new_margin"].sum(), 2)
})

# -------------------------
# Compile results
# -------------------------
scenario_df = pd.DataFrame(results)
scenario_df["margin_change_vs_baseline"] = (
    scenario_df["total_margin"] - baseline_margin
)

print("Baseline margin:", round(baseline_margin, 2))
print(scenario_df)