# =============================================================================
# scenario_model.py
# Unit Economics Intelligence Platform — Scenario & Sensitivity Engine
# =============================================================================
# ScenarioEngine class models the margin impact of strategic levers:
#   1. Price increases       — what if we raise prices by X%?
#   2. Cost reduction        — what if we cut support/delivery costs by X%?
#   3. Churn reduction       — what if we retain X% more customers?
#   4. Channel reallocation  — what if we shift spend away from Paid Search?
#   5. Loss order removal    — what if we stop fulfilling loss-making orders?
#
# Outputs:
#   scenarios_output.csv     — all named scenarios vs baseline
#   sensitivity_table.csv    — grid of price × cost levers
#   channel_reallocation.csv — margin impact of shifting marketing spend
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
    PRICE_INCREASE_SCENARIOS,
    COST_REDUCTION_SCENARIOS,
    CHURN_REDUCTION_SCENARIOS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "scenario_model.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)


# =============================================================================
# SCENARIO ENGINE CLASS
# =============================================================================

class ScenarioEngine:
    """
    Models the contribution margin impact of strategic business levers.

    Usage:
        engine = ScenarioEngine()
        engine.run_all()
        engine.save_outputs()
    """

    def __init__(self):
        log.info("=" * 60)
        log.info("SCENARIO ENGINE — INITIALISING")
        log.info("=" * 60)

        conn = sqlite3.connect(DB_PATH)
        self.df = pd.read_sql("""
            SELECT
                order_id, customer_id, service_type,
                acquisition_channel, region,
                order_month, order_year,
                net_revenue, total_cost,
                variable_cost, delivery_cost, support_cost,
                contribution_margin, is_profitable,
                is_refunded, order_value
            FROM unit_economics
        """, conn)
        conn.close()

        self.baseline_margin  = self.df["contribution_margin"].sum()
        self.baseline_revenue = self.df["net_revenue"].sum()
        self.total_orders     = len(self.df)
        self.results          = []

        log.info(f"  Orders loaded     : {self.total_orders:,}")
        log.info(f"  Baseline revenue  : ₹{self.baseline_revenue:,.0f}")
        log.info(f"  Baseline margin   : ₹{self.baseline_margin:,.0f}")
        log.info(f"  Baseline margin % : {self.baseline_margin/self.baseline_revenue*100:.2f}%")

    # ── HELPER ────────────────────────────────────────────────────────────────

    def _record(self, scenario: str, category: str, lever: str,
                lever_value: float, new_margin: float):
        """Store a single scenario result."""
        delta        = new_margin - self.baseline_margin
        delta_pct    = (delta / abs(self.baseline_margin) * 100) if self.baseline_margin != 0 else 0
        margin_pct   = (new_margin / self.baseline_revenue * 100) if self.baseline_revenue != 0 else 0

        self.results.append({
            "scenario":             scenario,
            "category":             category,
            "lever":                lever,
            "lever_value":          lever_value,
            "baseline_margin":      round(self.baseline_margin, 2),
            "new_margin":           round(new_margin, 2),
            "margin_delta":         round(delta, 2),
            "margin_delta_pct":     round(delta_pct, 2),
            "new_margin_pct":       round(margin_pct, 2),
        })

    # ── SCENARIO 1: PRICE INCREASE ────────────────────────────────────────────

    def run_price_scenarios(self):
        """Model impact of uniform price increases across all orders."""
        log.info("\nRunning price increase scenarios …")

        for pct in PRICE_INCREASE_SCENARIOS:
            temp = self.df.copy()
            # Price increase flows directly to margin (cost unchanged)
            temp["new_margin"] = temp["contribution_margin"] + (temp["net_revenue"] * pct)
            new_total = temp["new_margin"].sum()

            self._record(
                scenario    = f"Price increase {int(pct*100)}%",
                category    = "Pricing",
                lever       = "price_increase_pct",
                lever_value = pct,
                new_margin  = new_total,
            )
            log.info(f"  +{int(pct*100)}% price  →  margin ₹{new_total:,.0f}  "
                     f"(Δ ₹{new_total - self.baseline_margin:+,.0f})")

    # ── SCENARIO 2: SUPPORT COST REDUCTION ───────────────────────────────────

    def run_support_cost_scenarios(self):
        """Model impact of reducing support costs by X%."""
        log.info("\nRunning support cost reduction scenarios …")

        for pct in COST_REDUCTION_SCENARIOS:
            temp = self.df.copy()
            saving = temp["support_cost"] * pct
            temp["new_margin"] = temp["contribution_margin"] + saving
            new_total = temp["new_margin"].sum()

            self._record(
                scenario    = f"Support cost -{int(pct*100)}%",
                category    = "Cost Reduction",
                lever       = "support_cost_reduction_pct",
                lever_value = pct,
                new_margin  = new_total,
            )
            log.info(f"  -{int(pct*100)}% support  →  margin ₹{new_total:,.0f}  "
                     f"(Δ ₹{new_total - self.baseline_margin:+,.0f})")

    # ── SCENARIO 3: DELIVERY COST REDUCTION ──────────────────────────────────

    def run_delivery_cost_scenarios(self):
        """Model impact of reducing delivery costs by X% (route optimisation)."""
        log.info("\nRunning delivery cost reduction scenarios …")

        for pct in COST_REDUCTION_SCENARIOS:
            temp = self.df.copy()
            saving = temp["delivery_cost"] * pct
            temp["new_margin"] = temp["contribution_margin"] + saving
            new_total = temp["new_margin"].sum()

            self._record(
                scenario    = f"Delivery cost -{int(pct*100)}%",
                category    = "Cost Reduction",
                lever       = "delivery_cost_reduction_pct",
                lever_value = pct,
                new_margin  = new_total,
            )
            log.info(f"  -{int(pct*100)}% delivery →  margin ₹{new_total:,.0f}  "
                     f"(Δ ₹{new_total - self.baseline_margin:+,.0f})")

    # ── SCENARIO 4: REMOVE LOSS-MAKING ORDERS ────────────────────────────────

    def run_loss_removal_scenarios(self):
        """
        Model impact of stopping loss-making orders.
        Three variants: remove all losses, remove only deep losses (< -50), 
        remove only Standard service losses.
        """
        log.info("\nRunning loss order removal scenarios …")

        # Variant A — remove all loss-making orders
        profitable_only = self.df[self.df["contribution_margin"] >= 0]
        new_total = profitable_only["contribution_margin"].sum()
        removed   = self.total_orders - len(profitable_only)
        self._record(
            scenario    = f"Remove all loss orders ({removed:,} orders)",
            category    = "Order Strategy",
            lever       = "remove_loss_orders",
            lever_value = 1.0,
            new_margin  = new_total,
        )
        log.info(f"  Remove all losses →  margin ₹{new_total:,.0f}  "
                 f"({removed:,} orders removed, {removed/self.total_orders:.1%} of volume)")

        # Variant B — remove only deep losses (margin < -50)
        less_aggressive = self.df[self.df["contribution_margin"] >= -50]
        new_total_b = less_aggressive["contribution_margin"].sum()
        removed_b   = self.total_orders - len(less_aggressive)
        self._record(
            scenario    = f"Remove deep loss orders only (<-50 margin, {removed_b:,} orders)",
            category    = "Order Strategy",
            lever       = "remove_deep_loss_orders",
            lever_value = -50,
            new_margin  = new_total_b,
        )
        log.info(f"  Remove deep losses → margin ₹{new_total_b:,.0f}  "
                 f"({removed_b:,} orders removed)")

        # Variant C — remove loss-making Standard service orders only
        standard_fix = self.df[
            ~((self.df["service_type"] == "Standard") &
              (self.df["contribution_margin"] < 0))
        ]
        new_total_c = standard_fix["contribution_margin"].sum()
        removed_c   = self.total_orders - len(standard_fix)
        self._record(
            scenario    = f"Remove loss-making Standard orders ({removed_c:,} orders)",
            category    = "Order Strategy",
            lever       = "remove_standard_losses",
            lever_value = 1.0,
            new_margin  = new_total_c,
        )
        log.info(f"  Fix Standard losses → margin ₹{new_total_c:,.0f}  "
                 f"({removed_c:,} orders removed)")

    # ── SCENARIO 5: CHANNEL REALLOCATION ─────────────────────────────────────

    def run_channel_reallocation(self):
        """
        Model impact of reallocating 30% of Paid Search budget to Organic/Referral.
        Assumes Organic/Referral customers have higher avg margin per order.
        """
        log.info("\nRunning channel reallocation scenario …")

        channel_margin = (
            self.df.groupby("acquisition_channel")["contribution_margin"]
            .mean()
            .to_dict()
        )
        channel_orders = (
            self.df.groupby("acquisition_channel")["order_id"]
            .count()
            .to_dict()
        )

        log.info("  Avg margin per order by channel:")
        for ch, m in sorted(channel_margin.items()):
            log.info(f"    {ch:<15} ₹{m:>7.2f}  ({channel_orders.get(ch,0):,} orders)")

        # Reallocate 30% of Paid Search orders to Organic margin profile
        paid_search_orders = channel_orders.get("Paid Search", 0)
        reallocated        = int(paid_search_orders * 0.30)

        organic_margin     = channel_margin.get("Organic", 0)
        paid_margin        = channel_margin.get("Paid Search", 0)

        margin_gain = reallocated * (organic_margin - paid_margin)
        new_total   = self.baseline_margin + margin_gain

        self._record(
            scenario    = f"Reallocate 30% Paid Search → Organic ({reallocated:,} orders)",
            category    = "Channel Strategy",
            lever       = "channel_reallocation_pct",
            lever_value = 0.30,
            new_margin  = new_total,
        )
        log.info(f"  Reallocation gain → Δ ₹{margin_gain:+,.0f}  "
                 f"new margin ₹{new_total:,.0f}")

    # ── SCENARIO 6: COMBINED LEVERS ───────────────────────────────────────────

    def run_combined_scenario(self):
        """
        Best-case combined scenario:
        5% price increase + 15% support cost reduction + remove deep losses
        """
        log.info("\nRunning combined scenario …")

        temp = self.df.copy()

        # Apply price increase
        temp["new_margin"] = temp["contribution_margin"] + (temp["net_revenue"] * 0.05)

        # Apply support cost reduction
        temp["new_margin"] = temp["new_margin"] + (temp["support_cost"] * 0.15)

        # Remove deep losses
        temp = temp[temp["new_margin"] >= -50]

        new_total = temp["new_margin"].sum()
        self._record(
            scenario    = "Combined: +5% price, -15% support, remove deep losses",
            category    = "Combined",
            lever       = "combined",
            lever_value = 1.0,
            new_margin  = new_total,
        )
        log.info(f"  Combined scenario → margin ₹{new_total:,.0f}  "
                 f"(Δ ₹{new_total - self.baseline_margin:+,.0f})")

    # ── SENSITIVITY TABLE ─────────────────────────────────────────────────────

    def build_sensitivity_table(self) -> pd.DataFrame:
        """
        Build a price × support cost sensitivity grid.
        Rows = price increase %, Cols = support cost reduction %.
        Values = resulting total contribution margin.
        """
        log.info("\nBuilding sensitivity table (price × support cost) …")

        price_levels   = [0.0, 0.02, 0.05, 0.08, 0.10]
        support_levels = [0.0, 0.10, 0.15, 0.20, 0.25]

        rows = []
        for p in price_levels:
            row = {"price_increase_pct": f"{int(p*100)}%"}
            for s in support_levels:
                temp = self.df.copy()
                temp["new_margin"] = (
                    temp["contribution_margin"]
                    + (temp["net_revenue"]  * p)
                    + (temp["support_cost"] * s)
                )
                row[f"support_cut_{int(s*100)}pct"] = round(temp["new_margin"].sum(), 0)
            rows.append(row)

        sensitivity = pd.DataFrame(rows)
        log.info(f"  Sensitivity table: {sensitivity.shape[0]} rows × {sensitivity.shape[1]} cols")
        return sensitivity

    # ── CHANNEL REALLOCATION TABLE ────────────────────────────────────────────

    def build_channel_reallocation_table(self) -> pd.DataFrame:
        """
        Model margin impact of shifting X% of Paid Search spend to each other channel.
        """
        log.info("\nBuilding channel reallocation table …")

        channel_margin = (
            self.df.groupby("acquisition_channel")["contribution_margin"]
            .mean()
            .to_dict()
        )
        paid_orders = len(self.df[self.df["acquisition_channel"] == "Paid Search"])
        paid_margin = channel_margin.get("Paid Search", 0)

        rows = []
        for realloc_pct in [0.10, 0.20, 0.30, 0.40, 0.50]:
            reallocated = int(paid_orders * realloc_pct)
            for target_channel in ["Organic", "Referral", "Social"]:
                target_margin = channel_margin.get(target_channel, 0)
                gain          = reallocated * (target_margin - paid_margin)
                rows.append({
                    "reallocation_pct":   f"{int(realloc_pct*100)}%",
                    "from_channel":       "Paid Search",
                    "to_channel":         target_channel,
                    "orders_reallocated": reallocated,
                    "margin_gain":        round(gain, 2),
                    "new_total_margin":   round(self.baseline_margin + gain, 2),
                })

        realloc_df = pd.DataFrame(rows)
        log.info(f"  Channel reallocation table: {len(realloc_df)} rows")
        return realloc_df

    # ── RUN ALL ───────────────────────────────────────────────────────────────

    def run_all(self):
        """Execute all scenario categories."""
        self.run_price_scenarios()
        self.run_support_cost_scenarios()
        self.run_delivery_cost_scenarios()
        self.run_loss_removal_scenarios()
        self.run_channel_reallocation()
        self.run_combined_scenario()
        log.info(f"\n  Total scenarios modelled: {len(self.results)}")

    # ── SAVE ──────────────────────────────────────────────────────────────────

    def save_outputs(self):
        log.info("\nSaving outputs …")

        # Main scenarios table
        scenarios_df = pd.DataFrame(self.results).sort_values(
            "margin_delta", ascending=False
        ).reset_index(drop=True)
        scenarios_df["rank"] = scenarios_df.index + 1

        path = OUTPUTS_DIR / "scenarios_output.csv"
        scenarios_df.to_csv(path, index=False)
        log.info(f"  ✅  scenarios_output.csv          {len(scenarios_df)} scenarios")

        # Sensitivity table
        sensitivity = self.build_sensitivity_table()
        path = OUTPUTS_DIR / "sensitivity_table.csv"
        sensitivity.to_csv(path, index=False)
        log.info(f"  ✅  sensitivity_table.csv         {len(sensitivity)} rows")

        # Channel reallocation table
        realloc = self.build_channel_reallocation_table()
        path = OUTPUTS_DIR / "channel_reallocation.csv"
        realloc.to_csv(path, index=False)
        log.info(f"  ✅  channel_reallocation.csv      {len(realloc)} rows")

        # Summary log
        log.info("\n" + "=" * 60)
        log.info("TOP 5 SCENARIOS BY MARGIN IMPACT")
        log.info("=" * 60)
        for _, r in scenarios_df.head(5).iterrows():
            log.info(f"  #{r['rank']}  {r['scenario']}")
            log.info(f"      New margin: ₹{r['new_margin']:>12,.0f}  "
                     f"Δ ₹{r['margin_delta']:>+12,.0f}  "
                     f"({r['margin_delta_pct']:>+.1f}%)")

        log.info("\n" + "=" * 60)
        log.info("SCENARIO ENGINE COMPLETE")
        log.info(f"  Outputs saved to: {OUTPUTS_DIR}")
        log.info("=" * 60)

        return scenarios_df


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    engine = ScenarioEngine()
    engine.run_all()
    engine.save_outputs()