"""
ETL Pipeline — Reconciled Database -> Data Warehouse (Star Schema)
University of Calabria - Data Analytics Project
Corresponds to Section 3.3 / 3.4 (Data Quality, ETL execution) of the report.

Source : flight_reconciled (flight, airline, airport)
Target : flight_dw_project (fact_flights, dim_date, dim_airlines, dim_airports)

Run order:
  1. flight_reconciled must already be populated (populate_reconciled.py)
  2. flight_dw_project must already have the star schema (star_schema.sql)
  3. python etl_pipeline.py
"""

import pandas as pd
from sqlalchemy import create_engine, text
import os

# ------------------------------------------------------------
# Connections
# ------------------------------------------------------------
RECON_URL = os.environ.get(
    "RECONCILED_DATABASE_URL",
    "postgresql://postgres:nynisa@localhost:5432/flight_reconciled"
)
DW_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:nynisa@localhost:5432/flight_dw_project"
)

recon_engine = create_engine(RECON_URL)
dw_engine = create_engine(DW_URL)

CHUNKSIZE = 100000

MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

print("Connected to PostgreSQL")

# ------------------------------------------------------------
# Step 0 -- Data Quality Assessment (full scan, chunked)
# ------------------------------------------------------------
print("Running Data Quality Assessment...")

total_rows = 0
missing_counts = None
for chunk in pd.read_sql("SELECT * FROM flight", recon_engine, chunksize=CHUNKSIZE):
    total_rows += len(chunk)
    if missing_counts is None:
        missing_counts = chunk.isnull().sum()
    else:
        missing_counts += chunk.isnull().sum()

print("Total records: " + str(total_rows))
missing_pct = (missing_counts / total_rows * 100).round(2)
report = pd.DataFrame({"Missing Count": missing_counts, "Missing Percent": missing_pct})
print(report[report["Missing Count"] > 0].to_string())

# ------------------------------------------------------------
# Step 1 -- Load DIM_DATE
# Compute: quarter, month_name, week, day_name, is_weekend
# ------------------------------------------------------------
print("Loading DIM_DATE...")

dim_date = pd.read_sql(
    "SELECT DISTINCT year, month, day, day_of_week FROM flight ORDER BY year, month, day",
    recon_engine
)

dim_date["quarter"] = ((dim_date["month"] - 1) // 3) + 1
dim_date["month_name"] = dim_date["month"].apply(lambda m: MONTH_NAMES[m - 1])
dim_date["week"] = pd.to_datetime(dim_date[["year", "month", "day"]]).dt.isocalendar().week.astype(int)
dim_date["day_name"] = dim_date["day_of_week"].apply(lambda d: DAY_NAMES[d - 1])
dim_date["is_weekend"] = dim_date["day_of_week"].isin([6, 7])

dim_date = dim_date[["year", "quarter", "month", "month_name", "week",
                      "day", "day_of_week", "day_name", "is_weekend"]]

with dw_engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE fact_flights, dim_date, dim_airlines, dim_airports RESTART IDENTITY CASCADE"))

dim_date.to_sql("dim_date", dw_engine, if_exists="append", index=False)
print("DIM_DATE loaded: " + str(len(dim_date)) + " rows")

# Reload with generated date_id for lookup
dim_date = pd.read_sql("SELECT date_id, year, month, day FROM dim_date", dw_engine)

# ------------------------------------------------------------
# Step 2 -- Load DIM_AIRLINES
# ------------------------------------------------------------
print("Loading DIM_AIRLINES...")

dim_airlines = pd.read_sql("SELECT iata_code, airline_name FROM airline", recon_engine)
dim_airlines.to_sql("dim_airlines", dw_engine, if_exists="append", index=False)
print("DIM_AIRLINES loaded: " + str(len(dim_airlines)) + " rows")

dim_airlines = pd.read_sql("SELECT airline_id, iata_code FROM dim_airlines", dw_engine)

# ------------------------------------------------------------
# Step 3 -- Load DIM_AIRPORTS
# ------------------------------------------------------------
print("Loading DIM_AIRPORTS...")

dim_airports = pd.read_sql(
    "SELECT iata_code, airport_name, city, state, country, latitude, longitude FROM airport",
    recon_engine
)
dim_airports.to_sql("dim_airports", dw_engine, if_exists="append", index=False)
print("DIM_AIRPORTS loaded: " + str(len(dim_airports)) + " rows")

dim_airports = pd.read_sql("SELECT airport_id, iata_code FROM dim_airports", dw_engine)

# ------------------------------------------------------------
# Step 4 -- Load FACT_FLIGHTS
# ------------------------------------------------------------
print("Loading FACT_FLIGHTS...")

airlines_valid = set(dim_airlines["iata_code"].tolist())
airports_valid = set(dim_airports["iata_code"].tolist())

# Lookup dictionaries: code -> surrogate key
date_map = dim_date.set_index(["year", "month", "day"])["date_id"].to_dict()
airline_map = dim_airlines.set_index("iata_code")["airline_id"].to_dict()
airport_map = dim_airports.set_index("iata_code")["airport_id"].to_dict()

total_loaded = 0
total_dupes = 0
total_invalid = 0

for chunk in pd.read_sql("SELECT * FROM flight", recon_engine, chunksize=CHUNKSIZE):
    before = len(chunk)
    chunk = chunk.drop_duplicates(
        subset=["year", "month", "day", "airline_code", "flight_number",
                "origin_airport", "destination_airport"]
    )
    total_dupes += before - len(chunk)

    before = len(chunk)
    chunk = chunk[
        chunk["airline_code"].isin(airlines_valid)
        & chunk["origin_airport"].isin(airports_valid)
        & chunk["destination_airport"].isin(airports_valid)
    ]
    total_invalid += before - len(chunk)

    # Fill nulls for non-cancelled flights (cancelled flights legitimately have NULL delays)
    mask = chunk["cancelled"] == 0
    for col in ["departure_delay", "arrival_delay", "air_time", "weather_delay", "airline_delay"]:
        chunk.loc[mask, col] = chunk.loc[mask, col].fillna(0)

    # Lookups -> surrogate keys
    chunk["date_id"] = [
        date_map.get((y, m, d))
        for y, m, d in zip(chunk["year"], chunk["month"], chunk["day"])
    ]
    chunk["airline_id"] = chunk["airline_code"].map(airline_map)
    chunk["airport_dep_id"] = chunk["origin_airport"].map(airport_map)
    chunk["airport_arr_id"] = chunk["destination_airport"].map(airport_map)
    chunk["nb_vols"] = 1

    fact_chunk = chunk[[
        "date_id", "airport_dep_id", "airport_arr_id", "airline_id",
        "departure_delay", "arrival_delay", "distance", "air_time",
        "weather_delay", "airline_delay", "cancelled", "nb_vols"
    ]].copy()

    fact_chunk.to_sql("fact_flights", dw_engine, if_exists="append", index=False, chunksize=5000)
    total_loaded += len(fact_chunk)
    print("Loaded " + str(total_loaded) + " rows...", end="\r")

print("")
print("FACT_FLIGHTS loaded: " + str(total_loaded) + " rows")

# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------
validation = pd.read_sql("""
    SELECT 'fact_flights' AS table_name, COUNT(*) AS row_count FROM fact_flights
    UNION ALL SELECT 'dim_date', COUNT(*) FROM dim_date
    UNION ALL SELECT 'dim_airlines', COUNT(*) FROM dim_airlines
    UNION ALL SELECT 'dim_airports', COUNT(*) FROM dim_airports
""", dw_engine)
print(validation.to_string(index=False))

print("ETL Pipeline completed!")
print("Duplicates removed: " + str(total_dupes))
print("Invalid codes removed: " + str(total_invalid))
print("Final records in DW: " + str(total_loaded))
