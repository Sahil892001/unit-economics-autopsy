# Cohort Analysis Notes

## Summary

24 monthly cohorts tracked from January 2024 to December 2025. The most important finding is a **divergence between retention and LTV** — recent cohorts retain better but are worth less. This indicates acquisition quality has degraded, not improved.

---

## Retention Results

Average Month-1 retention across all cohorts: **78.5%**

| Cohort | M1 Retention | M3 Retention | Avg LTV | Assessment |
|--------|-------------|-------------|---------|------------|
| 2024-01 | 68.9% | 44.6% | +₹78.95 | Best LTV despite low M1 |
| 2024-02 | 74.1% | 45.1% | +₹34.20 | Positive LTV |
| 2025-09 | 90.0% | — | Negative | High retention, negative value |
| 2025-10 | 93.6% | — | Negative | High retention, negative value |
| 2025-11 | 97.9% | — | Negative | Highest M1, worst economics |

The conventional assumption is that higher retention = better cohort. This data refutes that assumption. The 2025-11 cohort has the highest M1 retention of any cohort (97.9%) but negative LTV. The 2024-01 cohort has the lowest M1 retention but the highest LTV.

---

## The Acquisition Quality Problem

Why do newer cohorts retain better but earn less?

Newer cohorts are disproportionately acquired through Paid Search (the channel with the highest share of acquisition in 2025). Paid Search customers:
- Have lower average order values
- Order Standard service at higher rates (the -17.7% margin product)
- Generate more support tickets per order
- Churn from high-value services faster

They return frequently (high retention) but each return generates little or negative margin. High frequency × negative margin = accelerating losses.

---

## LTV Curve

Average cumulative margin per customer reaches approximately ₹6.70 by Month 1 but flattens and turns negative by Month 6 for most recent cohorts. The LTV curve never meaningfully compounds — there is no "loyal customer flywheel" generating increasing returns over time at current economics.

---

## Cohort Health Distribution

| Health Status | Cohorts | Criteria |
|--------------|---------|---------|
| High Value | 2 | Avg LTV ≥ ₹50 |
| Positive | 4 | Avg LTV ≥ ₹0 |
| Marginal Loss | 8 | Avg LTV ≥ -₹30 |
| High Loss | 10 | Avg LTV < -₹30 |

10 of 24 cohorts are classified as High Loss. All 10 are from 2025.

---

## Analytical Notes

- Cohort defined as the calendar month of customer signup
- Retention = % of cohort placing at least one order in that month number
- Months with fewer than 5 active cohort members excluded from retention calculation
- LTV calculated on observed data only — not projected beyond observation window
- Newer cohorts naturally have fewer months of data; their LTV will continue to evolve