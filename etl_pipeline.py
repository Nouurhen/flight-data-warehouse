import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine("postgresql://postgres:nynisa@localhost:5432/flight_dw_project")
print("Connected to PostgreSQL")

CHUNKSIZE = 100000

print("Running Data Quality Assessment...")
total_rows = 0
missing_counts = None
for chunk in pd.read_sql("SELECT * FROM flights", engine, chunksize=CHUNKSIZE):
    total_rows += len(chunk)
    if missing_counts is None:
        missing_counts = chunk.isnull().sum()
    else:
        missing_counts += chunk.isnull().sum()
print("Total records: " + str(total_rows))
missing_pct = (missing_counts / total_rows * 100).round(2)
report = pd.DataFrame({"Missing Count": missing_counts, "Missing Percent": missing_pct})
print(report[report["Missing Count"] > 0].to_string())

print("Loading DIM_DATE...")
dim_date = pd.read_sql("SELECT DISTINCT year, month, day, day_of_week FROM flights ORDER BY year, month, day", engine)
with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE dim_date CASCADE"))
dim_date.to_sql("dim_date", engine, if_exists="append", index=False)
print("DIM_DATE loaded: " + str(len(dim_date)) + " rows")

print("Loading DIM_AIRLINES...")
dim_airlines = pd.read_sql("SELECT airline_code, airline_name FROM airlines", engine)
with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE dim_airlines CASCADE"))
dim_airlines.to_sql("dim_airlines", engine, if_exists="append", index=False)
print("DIM_AIRLINES loaded: " + str(len(dim_airlines)) + " rows")

print("Loading DIM_AIRPORTS...")
dim_airports = pd.read_sql("SELECT airport_code, airport_name, city, state, country, latitude, longitude FROM airports", engine)
with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE dim_airports CASCADE"))
dim_airports.to_sql("dim_airports", engine, if_exists="append", index=False)
print("DIM_AIRPORTS loaded: " + str(len(dim_airports)) + " rows")

print("Loading FACT_FLIGHTS...")
airlines_valid = set(dim_airlines["airline_code"].tolist())
airports_valid = set(dim_airports["airport_code"].tolist())
with engine.begin() as conn:
    conn.execute(text("TRUNCATE TABLE fact_flights CASCADE"))
total_loaded = 0
total_dupes = 0
total_invalid = 0
for chunk in pd.read_sql("SELECT * FROM flights", engine, chunksize=CHUNKSIZE):
    before = len(chunk)
    chunk = chunk.drop_duplicates(subset=["year", "month", "day", "airline_code", "flight_number", "origin_airport", "destination_airport"])
    total_dupes += before - len(chunk)
    before = len(chunk)
    chunk = chunk[chunk["airline_code"].isin(airlines_valid) & chunk["origin_airport"].isin(airports_valid) & chunk["destination_airport"].isin(airports_valid)]
    total_invalid += before - len(chunk)
    mask = chunk["cancelled"] == 0
    for col in ["departure_delay", "arrival_delay", "air_time", "elapsed_time"]:
        chunk.loc[mask, col] = chunk.loc[mask, col].fillna(0)
    fact_chunk = chunk[["flight_id", "airline_code", "origin_airport", "destination_airport", "year", "month", "day", "departure_delay", "arrival_delay", "distance", "air_time", "elapsed_time", "cancelled", "diverted"]].copy()
    fact_chunk = fact_chunk.rename(columns={"year": "flight_year", "month": "flight_month", "day": "flight_day"})
    fact_chunk.to_sql("fact_flights", engine, if_exists="append", index=False, chunksize=5000)
    total_loaded += len(fact_chunk)
    print("Loaded " + str(total_loaded) + " rows...", end="\r")

print("")
print("FACT_FLIGHTS loaded: " + str(total_loaded) + " rows")

validation = pd.read_sql("""
SELECT 'fact_flights' AS table_name, COUNT(*) AS row_count FROM fact_flights
UNION ALL SELECT 'dim_date', COUNT(*) FROM dim_date
UNION ALL SELECT 'dim_airlines', COUNT(*) FROM dim_airlines
UNION ALL SELECT 'dim_airports', COUNT(*) FROM dim_airports
""", engine)
print(validation.to_string(index=False))

print("ETL Pipeline completed!")
print("Duplicates removed: " + str(total_dupes))
print("Invalid codes removed: " + str(total_invalid))
print("Final records in DW: " + str(total_loaded))