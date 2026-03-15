# Causal Considerations

## What This Analysis Can and Cannot Claim

This project is an observational analysis of synthetic data. The findings describe strong statistical associations between variables — they do not establish causality. This distinction matters when translating findings into business decisions.

---

## What the Data Shows

The analysis identifies the following strong associations:

- Paid Search customers have higher CAC and negative LTV compared to Organic customers
- Standard service has significantly higher support cost ratios than Express or Premium
- Delivery cost per order increased steadily from 2024 to 2025
- Cohorts acquired in 2025 have higher retention but lower LTV than 2024 cohorts
- Support-heavy customers (top 10% by support cost) average -₹77.81 lifetime margin versus +₹2.81 for others

These are directional signals for decision-making, not proof of cause and effect.

---

## Why Causality Cannot Be Assumed

**Acquisition channels are not randomly assigned.** Customers who find the platform organically may have fundamentally different intent, price sensitivity, or service preferences than customers who clicked a paid ad. The LTV difference between Organic and Paid Search may reflect who those customers are, not what the channel does to them.

**Support cost intensity is bidirectional.** High support costs may cause margin losses, but customers who generate margin losses may also be more likely to raise support tickets. Reducing support costs without addressing the underlying service issues may not improve margins.

**Cohort differences may reflect external factors.** Newer cohorts may perform worse because of macro conditions, competitor activity, or seasonal effects — not purely because of changes in acquisition channel mix.

---

## How Causal Evidence Could Be Strengthened

| Method | Application |
|--------|-------------|
| A/B testing | Run pricing experiments on a random subset of Standard service orders to measure true price elasticity |
| Difference-in-differences | Compare customer behaviour before and after a specific channel policy change (e.g., Paid Search pause) |
| Holdout groups | Allocate a random subset of new customers to no-paid-acquisition and compare 6-month LTV |
| Instrumental variables | Use geography or seasonality as instruments to identify causal channel effects |
| Propensity score matching | Match Paid Search and Organic customers on observable characteristics to reduce selection bias |

---

## Practical Interpretation

The findings in this analysis should be treated as **strong hypotheses** that justify further investigation and targeted experiments — not as definitive causal conclusions that justify immediate large-scale changes without validation.

The associations are large enough in magnitude (Paid Search LTV:CAC of -0.03x vs Organic 0.07x; Standard margin of -17.7% vs Express +7.4%) that even if causal effects are partial, the directional recommendations are likely robust. A business does not need to prove full causality to conclude that Standard service pricing and Paid Search budget allocation warrant urgent review.