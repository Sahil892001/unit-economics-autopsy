# =============================================================================
# config.py — Central Configuration: Unit Economics Intelligence Platform
# =============================================================================
# Single source of truth for ALL scripts, SQL runners, and the Streamlit app.
# Import pattern:
#   from config import RAW_DIR, NUM_CUSTOMERS, ...   (explicit)
#   OR
#   import config as cfg                              (namespaced)
# =============================================================================

from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# PROJECT ROOT  (resolves correctly regardless of working directory)
# ─────────────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent

# ─────────────────────────────────────────────────────────────────────────────
# DIRECTORY PATHS
# ─────────────────────────────────────────────────────────────────────────────
RAW_DIR       = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
OUTPUTS_DIR   = ROOT_DIR / "data" / "outputs"
LOGS_DIR      = ROOT_DIR / "logs"
SQL_DIR       = ROOT_DIR / "sql"
DB_PATH       = ROOT_DIR / "data" / "unit_economics.db"

# Auto-create all directories on import (safe, idempotent)
for _d in [RAW_DIR, PROCESSED_DIR, OUTPUTS_DIR, LOGS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# DATA GENERATION — SCALE
# ─────────────────────────────────────────────────────────────────────────────
RANDOM_SEED    = 42
NUM_CUSTOMERS  = 20_000
NUM_ORDERS     = 200_000
START_DATE     = "2024-01-01"
END_DATE       = "2025-12-31"

# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS SEGMENTS
# ─────────────────────────────────────────────────────────────────────────────
REGIONS       = ["North", "South", "East", "West"]
CHANNELS      = ["Paid Search", "Organic", "Referral", "Social"]
SERVICE_TYPES = ["Standard", "Premium", "Express"]

# Acquisition channel mix — must sum to 1.0
CHANNEL_MIX   = [0.45, 0.30, 0.15, 0.10]   # Paid Search dominates

# Base service mix (non-peak months) — must sum to 1.0
SERVICE_MIX   = [0.55, 0.25, 0.20]          # Standard / Premium / Express

# Peak months (Nov, Dec, Jan) — service mix shifts toward Express
PEAK_MONTHS         = [11, 12, 1]
PEAK_SERVICE_MIX    = [0.40, 0.30, 0.30]    # Express surges in peak

# ─────────────────────────────────────────────────────────────────────────────
# PRICING & COSTS
# ─────────────────────────────────────────────────────────────────────────────
# Base order value per service type (INR)
BASE_PRICES = {
    "Standard": 50,
    "Premium":  90,
    "Express":  140,
}

# Variable cost as % of order value per service type
VARIABLE_COST_RATIO = {
    "Standard": 0.45,
    "Premium":  0.50,
    "Express":  0.60,
}

# Delivery cost range (INR) — before inflation
DELIVERY_COST_MIN = 6
DELIVERY_COST_MAX = 18

# Delivery cost inflation: ~30% rise over the 2-year period
# Formula used: cost * (1 + days_elapsed / DELIVERY_INFLATION_DAYS)
DELIVERY_INFLATION_DAYS = 600

# Support cost: lognormal(mean=2.0, sigma=1.0)
SUPPORT_COST_LOGNORMAL_MEAN  = 2.0
SUPPORT_COST_LOGNORMAL_SIGMA = 1.0
SUPPORT_COST_DEC_MULTIPLIER  = 1.35   # December support spike
SUPPORT_OUTLIER_MULTIPLIER   = 8.0    # Extreme outlier magnitude

# ─────────────────────────────────────────────────────────────────────────────
# REFUND RATES (by service type; Organic channel gets 30% discount)
# ─────────────────────────────────────────────────────────────────────────────
REFUND_RATE = {
    "Express":  0.09,
    "Premium":  0.06,
    "Standard": 0.04,
}
ORGANIC_REFUND_DISCOUNT = 0.70   # Organic customers refund 30% less

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOMER BEHAVIOUR
# ─────────────────────────────────────────────────────────────────────────────
# Power users: top % who place 6x more orders
POWER_USER_PCT          = 0.05
POWER_USER_ORDER_WEIGHT = 6.0

# Churn: exponential distribution (scale = avg active months before churn)
CHURN_EXPONENTIAL_SCALE = 8       # avg 8 months before churn
CHURN_MIN_MONTHS        = 1
CHURN_MAX_MONTHS        = 24

# Per-channel churn multiplier (higher = stays longer)
CHANNEL_CHURN_MULTIPLIER = {
    "Paid Search": 0.80,   # churns fastest — low acquisition quality
    "Organic":     1.10,
    "Referral":    1.25,   # most loyal
    "Social":      0.95,
}

# ─────────────────────────────────────────────────────────────────────────────
# SUPPORT TICKETS
# ─────────────────────────────────────────────────────────────────────────────
SUPPORT_TICKET_PCT  = 0.35   # 35% of orders generate a support ticket
OUTLIER_PCT         = 0.02   # 2% of support costs are extreme outliers

TICKET_CATEGORIES = ["Delivery Issue", "Billing", "Service Quality", "Cancellation", "Other"]
TICKET_CATEGORY_MIX = [0.35, 0.20, 0.25, 0.12, 0.08]   # must sum to 1.0

# ─────────────────────────────────────────────────────────────────────────────
# MARKETING SPEND
# ─────────────────────────────────────────────────────────────────────────────
# Base daily spend per channel (INR)
BASE_MARKETING_SPEND = {
    "Paid Search": 2200,
    "Organic":      450,
    "Referral":     350,
    "Social":       650,
}

# Paid Search inflation over time (cost per click rising)
PAID_SEARCH_INFLATION_DAYS = 500   # ~50% more expensive by end of period

# Organic: slow steady growth
ORGANIC_GROWTH_DAYS = 1200

# Social: random campaign burst probability and multiplier range
SOCIAL_BURST_PROBABILITY = 0.05
SOCIAL_BURST_MULTIPLIER  = (2.5, 4.0)   # (min, max) random uniform

# ─────────────────────────────────────────────────────────────────────────────
# SEASONALITY INDICES
# ─────────────────────────────────────────────────────────────────────────────
# Monthly order volume multiplier (1.0 = baseline)
MONTHLY_SEASONALITY = {
    1: 1.20,   # January — post-holiday tail
    2: 0.90,
    3: 0.95,
    4: 1.00,
    5: 1.05,
    6: 0.88,   # June dip
    7: 0.85,   # July slowest
    8: 0.92,
    9: 1.00,
    10: 1.08,
    11: 1.18,
    12: 1.35,  # December peak
}

# Weekday order volume multiplier (0=Mon … 6=Sun)
WEEKDAY_ACTIVITY = {
    0: 1.10,   # Monday
    1: 1.15,   # Tuesday — busiest
    2: 1.12,
    3: 1.10,
    4: 1.05,
    5: 0.85,   # Saturday quieter
    6: 0.70,   # Sunday quietest
}

# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS THRESHOLDS & BENCHMARKS
# ─────────────────────────────────────────────────────────────────────────────
# LTV / CAC
HEALTHY_LTV_CAC_RATIO  = 3.0    # Industry benchmark: LTV ≥ 3x CAC
WARNING_LTV_CAC_RATIO  = 1.5    # Below this = acquisition is destroying value

# Contribution margin buckets (used in SQL and dashboard — single definition)
MARGIN_BUCKETS = {
    "Loss-making":     (None,  0),
    "Low Margin":      (0,    20),
    "Healthy Margin":  (20,   50),
    "High Margin":     (50, None),
}

# Profitability flags
MIN_HEALTHY_MARGIN      = 0.0    # Below = loss-making order
HIGH_SUPPORT_THRESHOLD  = 50.0   # Support cost above this = high-cost customer
HIGH_VALUE_ORDER        = 150.0  # Order value above this = high-value order

# Cohort retention
GOOD_MONTH1_RETENTION   = 0.60   # ≥60% Month-1 retention is healthy
POOR_MONTH3_RETENTION   = 0.30   # <30% by Month-3 is a warning signal

# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO MODEL PARAMETERS
# ─────────────────────────────────────────────────────────────────────────────
PRICE_INCREASE_SCENARIOS  = [0.02, 0.05, 0.08, 0.10]
COST_REDUCTION_SCENARIOS  = [0.10, 0.15, 0.20, 0.25]
CHURN_REDUCTION_SCENARIOS = [0.05, 0.10, 0.15]

# ─────────────────────────────────────────────────────────────────────────────
# DATA QUALITY THRESHOLDS  (used in clean_and_process_data.py)
# ─────────────────────────────────────────────────────────────────────────────
MAX_NULL_PCT          = 0.02    # >2% nulls in any column raises a warning
MAX_ORDER_VALUE       = 2000    # Orders above this are flagged as anomalies
MAX_SUPPORT_COST      = 2500    # Support costs above this are flagged
MIN_ORDER_VALUE       = 5       # Orders below this are invalid

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD / STREAMLIT CONFIG
# ─────────────────────────────────────────────────────────────────────────────
APP_TITLE       = "Unit Economics Intelligence Platform"
APP_ICON        = "📊"
APP_SUBTITLE    = "Profitability diagnostics & scenario modeling | 2024–2025"
CURRENCY_SYMBOL = "₹"

# Chart dimensions
CHART_HEIGHT    = 420
CHART_HEIGHT_SM = 320
CHART_TEMPLATE  = "plotly_white"

# Brand palette
BRAND_COLOR   = "#1B4F72"   # Deep navy — primary
ACCENT_COLOR  = "#2E86C1"   # Mid blue — charts
DANGER_COLOR  = "#C0392B"   # Red — loss / warning
SUCCESS_COLOR = "#1E8449"   # Green — profit / healthy
WARNING_COLOR = "#D4AC0D"   # Amber — caution
NEUTRAL_COLOR = "#717D7E"   # Grey — secondary text

# Color scale for heatmaps (cohort retention)
RETENTION_COLORSCALE = [
    [0.0,  "#C0392B"],   # 0%   → red
    [0.3,  "#E67E22"],   # 30%  → orange
    [0.6,  "#F1C40F"],   # 60%  → yellow
    [1.0,  "#1E8449"],   # 100% → green
]