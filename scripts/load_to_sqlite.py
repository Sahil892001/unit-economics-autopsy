import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = "data/unit_economics.db"
RAW_DATA_PATH = Path("data/raw")

conn = sqlite3.connect(DB_PATH)

for csv_file in RAW_DATA_PATH.glob("*.csv"):
    df = pd.read_csv(csv_file)
    table_name = csv_file.stem
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    print(f"Loaded table: {table_name}")

conn.close()
print("All raw tables loaded into SQLite.")