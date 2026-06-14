"""
Reconciled Database Population
University of Calabria - Data Analytics Project
Corresponds to Section 3.2 (Reconciled Database Population) of the report.

Run order:
  1. createdb flight_reconciled
  2. psql -d flight_reconciled -f reconciled_schema.sql
  3. python populate_reconciled.py
"""

import pandas as pd
from sqlalchemy import create_engine, text
import os

# ------------------------------------------------------------
# Connection
# ------------------------------------------------------------
DATABASE_URL = os.environ.get(
    "RECONCILED_DATABASE_URL",
    "postgresql://postgres:nynisa@localhost:5432/flight_reconciled"
)
engine = create_engine(DATABASE_URL)

CHUNKSIZE = 100000

# ------------------------------------------------------------
# Step 1 -- Load AIRLINE dimension (airlines.csv: IATA_CODE, AIRLINE)
# ------------------------------------------------------------
print("Loading AIRLINE...")
airlines = pd.read_csv("airlines.csv")
airlines = airlines.rename(columns={"IATA_CODE": "iata_code", "AIRLINE": "airline_name"})

with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE airline CASCADE"))
airlines.to_sql("airline", engine, if_exists="append", index=False)
print(f"AIRLINE loaded: {len(airlines)} rows")

# ------------------------------------------------------------
# Step 2 -- Load AIRPORT dimension
# (airports.csv: IATA_CODE, AIRPORT, CITY, STATE, COUNTRY, LATITUDE, LONGITUDE)
# ------------------------------------------------------------
print("Loading AIRPORT...")
airports = pd.read_csv("airports.csv")
airports = airports.rename(columns={
    "IATA_CODE": "iata_code",
    "AIRPORT": "airport_name",
    "CITY": "city",
    "STATE": "state",
    "COUNTRY": "country",
    "LATITUDE": "latitude",
    "LONGITUDE": "longitude",
})

with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE airport CASCADE"))
airports.to_sql("airport", engine, if_exists="append", index=False)
print(f"AIRPORT loaded: {len(airports)} rows "
      f"({airports['latitude'].isnull().sum()} rows with missing GPS coordinates)")

# ------------------------------------------------------------
# Step 3 -- Load FLIGHT fact table (flights.csv, 31 columns, chunked)
# ------------------------------------------------------------
print("Loading FLIGHT (chunked, this may take a while)...")

# Mapping from raw Kaggle column names (UPPERCASE) to reconciled DB columns (lowercase)
FLIGHT_COLUMNS = {
    "YEAR": "year",
    "MONTH": "month",
    "DAY": "day",
    "DAY_OF_WEEK": "day_of_week",
    "AIRLINE": "airline_code",
    "FLIGHT_NUMBER": "flight_number",
    "TAIL_NUMBER": "tail_number",
    "ORIGIN_AIRPORT": "origin_airport",
    "DESTINATION_AIRPORT": "destination_airport",
    "SCHEDULED_DEPARTURE": "scheduled_departure",
    "DEPARTURE_TIME": "departure_time",
    "DEPARTURE_DELAY": "departure_delay",
    "TAXI_OUT": "taxi_out",
    "WHEELS_OFF": "wheels_off",
    "SCHEDULED_TIME": "scheduled_time",
    "ELAPSED_TIME": "elapsed_time",
    "AIR_TIME": "air_time",
    "DISTANCE": "distance",
    "WHEELS_ON": "wheels_on",
    "TAXI_IN": "taxi_in",
    "SCHEDULED_ARRIVAL": "scheduled_arrival",
    "ARRIVAL_TIME": "arrival_time",
    "ARRIVAL_DELAY": "arrival_delay",
    "DIVERTED": "diverted",
    "CANCELLED": "cancelled",
    "CANCELLATION_REASON": "cancellation_reason",
    "AIR_SYSTEM_DELAY": "air_system_delay",
    "SECURITY_DELAY": "security_delay",
    "AIRLINE_DELAY": "airline_delay",
    "LATE_AIRCRAFT_DELAY": "late_aircraft_delay",
    "WEATHER_DELAY": "weather_delay",
}

with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE flight CASCADE"))

total_rows = 0
for i, chunk in enumerate(pd.read_csv("flights.csv", chunksize=CHUNKSIZE, low_memory=False)):
    chunk = chunk.rename(columns=FLIGHT_COLUMNS)
    chunk = chunk[list(FLIGHT_COLUMNS.values())]  # enforce column order

    # diverted / cancelled can be read as float (NaN) on some chunks; normalize
    chunk["diverted"] = chunk["diverted"].fillna(0).astype(int)
    chunk["cancelled"] = chunk["cancelled"].fillna(0).astype(int)

    chunk.to_sql("flight", engine, if_exists="append", index=False, chunksize=10000)
    total_rows += len(chunk)
    print(f"  ... {total_rows} rows loaded", end="\r")

print("")
print(f"FLIGHT loaded: {total_rows} rows")

# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------
print("\nValidation:")
validation = pd.read_sql("""
    SELECT 'airline' AS table_name, COUNT(*) AS row_count FROM airline
    UNION ALL SELECT 'airport', COUNT(*) FROM airport
    UNION ALL SELECT 'flight', COUNT(*) FROM flight
""", engine)
print(validation.to_string(index=False))

print("\nReconciled database populated successfully.")
