# Unit Economics Autopsy

## Business Context
A fast-growing on-demand services platform is experiencing strong revenue and user growth, yet profitability has been declining over recent months. Leadership suspects that growth may be masking structural cost issues, inefficient customer acquisition, or loss-making customer segments.

This project simulates the role of a data analyst tasked with diagnosing the underlying drivers of declining unit economics and providing data-backed recommendations to restore sustainable profitability.

## Problem Statement
Despite increasing order volume and gross revenue, the company’s contribution margin has deteriorated. The key challenge is to identify where value is being created versus destroyed across customers, services, regions, and acquisition channels.

## Key Business Questions
- Where are we losing money at the unit level?
- Which customer segments are profitable vs loss-making?
- Are certain acquisition channels driving low-quality growth?
- How does customer lifetime value evolve across cohorts?
- What operational or pricing levers could improve profitability?

## Data Overview
The analysis is based on synthetic but realistic datasets representing:
- Customer profiles and acquisition channels
- Orders and revenue
- Variable, delivery, and support costs
- Marketing spend
- Customer support interactions

The dataset structure mirrors what would typically be available in a real on-demand services business.

## Deliverables
- Cleaned and validated analytical datasets
- SQL-based unit economics and cohort analysis
- CAC and LTV evaluation by acquisition channel
- Segment-level profitability diagnostics
- Scenario modeling for strategic decision-making
- Interactive dashboard for stakeholder consumption
- Executive summary with actionable recommendations


# Data Model & Assumptions

This project uses synthetic but realistic datasets designed to mimic data commonly available in an on-demand services business. The data is intentionally imperfect to reflect real-world analytical challenges.

---

## Tables Overview

### 1. customers
Represents unique customers who have placed at least one order.

**Columns**
- customer_id: Unique customer identifier
- signup_date: Date the customer first registered
- acquisition_channel: Marketing channel through which the customer was acquired
- region: Customer’s primary operating region

**Assumptions**
- Each customer is associated with a single acquisition channel
- Region is fixed for the customer lifecycle

---

### 2. orders
Represents individual service orders placed by customers.

**Columns**
- order_id: Unique order identifier
- customer_id: Identifier linking to customers table
- service_type: Category of service requested
- order_date: Date the order was completed
- order_value: Revenue generated from the order
- refund_flag: Indicates whether the order was refunded

**Assumptions**
- Orders are completed on the same day they are recorded
- Refunds negate revenue but may still incur costs

---

### 3. costs
Represents operational costs associated with fulfilling orders.

**Columns**
- order_id: Identifier linking to orders table
- variable_cost: Cost directly related to service fulfillment
- delivery_cost: Logistics or dispatch-related cost
- support_cost: Customer support cost attributed to the order

**Assumptions**
- All costs are recorded at the order level
- Some orders may be unprofitable due to high support or delivery costs

---

### 4. marketing_spend
Tracks marketing investments by acquisition channel over time.

**Columns**
- channel: Marketing acquisition channel
- date: Date of spend
- spend: Total spend for the channel on that date

**Assumptions**
- Marketing spend is aggregated daily
- Attribution is based on first-touch acquisition

---

### 5. support_tickets
Represents customer support interactions related to orders.

**Columns**
- ticket_id: Unique support ticket identifier
- order_id: Identifier linking to orders table
- created_at: Timestamp of ticket creation
- resolution_cost: Cost incurred to resolve the ticket

**Assumptions**
- An order may have multiple support tickets
- Support costs can exceed order revenue in edge cases

---

## Key Relationships
- customers (1) → orders (many)
- orders (1) → costs (1)
- orders (1) → support_tickets (many)
- marketing_spend is linked to customers via acquisition_channel

---

## Known Limitations
- No explicit attribution window for marketing spend
- No customer churn flag (derived analytically)
- No fixed cost allocation (focus is contribution margin)

These limitations are intentional and will be addressed through analytical assumptions.

---

## Data Validation & Trust Checks

The following validation checks were performed before downstream analysis:

- Row counts across all tables aligned with expected data volumes
- No orphaned foreign key relationships detected between orders and customers
- No negative or zero order revenue observed
- Refund rate falls within a realistic operational range (~5–7%)
- Presence of extreme support cost outliers is intentional and reflects real-world heavy-tail behavior
- All orders have corresponding cost records

Based on these checks, the dataset is considered suitable for unit economics and cohort-level analysis.

---

## Processed Data
Processed datasets standardize types, add derived time fields, and compute order-level unit economics. Raw data remains unchanged to preserve lineage.
