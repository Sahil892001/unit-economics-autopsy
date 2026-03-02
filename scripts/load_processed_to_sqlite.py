# =============================================================================
# load_processed_to_sqlite.py
# Unit Economics Intelligence Platform — SQLite Database Loader
# =============================================================================
# Loads ALL processed CSVs into a single SQLite database.
# Run this after clean_and_process_data.py and before any analysis scripts.
#
# Tables created:
#   customers         — cleaned customer master with cohort + churn flags
#   orders            — cleaned orders with time dimensions
#   costs             — cleaned costs with outlier flags
#   marketing_spend   — cleaned marketing spend
#   support_tickets   — cleaned support tickets with categories
#   unit_economics    — master order-level P&L table (35 cols)
#   monthly_summary   — pre-aggregated monthly KPIs
#   monthly_costs     — pre-aggregated monthly cost breakdown
#   channel_monthly   — channel performance by month
#   service_monthly   — service type performance by month
# =============================================================================

import sys
import sqlite3
import logging
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import PROCESSED_DIR, DB_PATH, LOGS_DIR


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "db_load.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

# ── Map: CSV filename → SQLite table name ─────────────────────────────────────
TABLES = {
    "customers_clean.csv":       "customers",
    "orders_clean.csv":          "orders",
    "costs_clean.csv":           "costs",
    "marketing_spend_clean.csv": "marketing_spend",
    "support_tickets_clean.csv": "support_tickets",
    "unit_economics.csv":        "unit_economics",
    "monthly_summary.csv":       "monthly_summary",
    "monthly_costs.csv":         "monthly_costs",
    "channel_monthly.csv":       "channel_monthly",
    "service_monthly.csv":       "service_monthly",
}

# ── Index definitions for query performance ───────────────────────────────────
INDEXES = [
    ("idx_orders_customer",    "orders",         "customer_id"),
    ("idx_orders_month",       "orders",         "order_month"),
    ("idx_orders_service",     "orders",         "service_type"),
    ("idx_ue_customer",        "unit_economics", "customer_id"),
    ("idx_ue_channel",         "unit_economics", "acquisition_channel"),
    ("idx_ue_cohort",          "unit_economics", "cohort"),
    ("idx_ue_month",           "unit_economics", "order_month"),
    ("idx_ue_service",         "unit_economics", "service_type"),
    ("idx_ue_region",          "unit_economics", "region"),
    ("idx_mkt_channel",        "marketing_spend","channel"),
    ("idx_support_order",      "support_tickets","order_id"),
    ("idx_support_category",   "support_tickets","category"),
]

def load_all():
    log.info("=" * 60)
    log.info("LOADING PROCESSED DATA INTO SQLITE")
    log.info(f"  Database : {DB_PATH}")
    log.info("=" * 60)

    conn = sqlite3.connect(DB_PATH)

    total_rows = 0
    for csv_file, table_name in TABLES.items():
        path = PROCESSED_DIR / csv_file
        if not path.exists():
            log.warning(f"  ⚠️  File not found, skipping: {csv_file}")
            continue

        df = pd.read_csv(path)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        total_rows += len(df)
        log.info(f"  ✅  {table_name:<25} {len(df):>8,} rows  {df.shape[1]:>3} cols")

    log.info(f"\n  Building indexes for query performance …")
    for idx_name, table, col in INDEXES:
        try:
            conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({col})")
            log.info(f"  ✅  Index: {idx_name}")
        except Exception as e:
            log.warning(f"  ⚠️  Index {idx_name} skipped: {e}")

    conn.commit()

    # ── Verify: row counts from DB ────────────────────────────────────────────
    log.info("\n  Verifying row counts in DB …")
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables_in_db = [r[0] for r in cursor.fetchall()]
    for t in tables_in_db:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        log.info(f"  DB table '{t}': {count:,} rows")

    conn.close()

    log.info("\n" + "=" * 60)
    log.info("DB LOAD COMPLETE")
    log.info(f"  Tables loaded : {len(TABLES)}")
    log.info(f"  Total rows    : {total_rows:,}")
    log.info(f"  DB path       : {DB_PATH}")
    log.info("=" * 60)

if __name__ == "__main__":
    load_all()