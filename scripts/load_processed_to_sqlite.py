import sqlite3
import pandas as pd

DB_PATH = "data/unit_economics.db"
FILE_PATH = "data/processed/unit_economics.csv"

conn = sqlite3.connect(DB_PATH)

df = pd.read_csv(FILE_PATH)
df.to_sql("unit_economics", conn, if_exists="replace", index=False)

conn.close()

print("unit_economics table loaded into SQLite.")