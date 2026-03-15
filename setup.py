# =============================================================================
# setup.py — Unit Economics Intelligence Platform
# =============================================================================
# Generates all synthetic data and runs the full analysis pipeline.
# Run this once before launching the dashboard.
#
# Usage:
#   python setup.py
#   streamlit run dashboards/app.py
#
# Or in one command:
#   python setup.py && streamlit run dashboards/app.py
# =============================================================================

import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = [
    ("scripts/generate_synthetic_data.py", "Generating synthetic data (20K customers, 200K orders)"),
    ("scripts/clean_and_process_data.py",  "Cleaning and processing data (50 DQ checks, enrichment)"),
    ("scripts/load_processed_to_sqlite.py","Loading into SQLite (10 tables, 12 indexes)"),
    ("src/cohort_analysis.py",             "Running cohort analysis (retention matrix, LTV curves)"),
    ("src/cac_ltv_analysis.py",            "Running CAC/LTV analysis (channel economics)"),
    ("src/segment_profitability.py",       "Running segment profitability (region, service, channel)"),
    ("src/scenario_model.py",              "Running scenario engine (17 scenarios, sensitivity table)"),
]

def run():
    print("=" * 60)
    print("  UNIT ECONOMICS INTELLIGENCE PLATFORM — SETUP")
    print("=" * 60)
    print()

    start_total = time.time()

    for script, description in SCRIPTS:
        path = Path(script)
        if not path.exists():
            print(f"  ❌  {script} not found — check your project structure")
            sys.exit(1)

        print(f"  ▸  {description}")
        t = time.time()

        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
        )

        elapsed = time.time() - t

        if result.returncode != 0:
            print(f"  ❌  FAILED ({elapsed:.1f}s)")
            print(f"\n  Error output:\n{result.stderr[-500:]}")
            sys.exit(1)

        print(f"  ✅  Done ({elapsed:.1f}s)")

    total = time.time() - start_total
    print()
    print("=" * 60)
    print(f"  Setup complete in {total:.0f}s")
    print("  Launch dashboard: streamlit run dashboards/app.py")
    print("=" * 60)


if __name__ == "__main__":
    run()