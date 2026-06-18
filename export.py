import pandas as pd
from sqlalchemy import create_engine
import os

# Connexion PostgreSQL (same convention as etl_pipeline.py / populate_reconciled.py)
DW_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:nynisa@localhost:5432/flight_dw_project"
)
engine = create_engine(DW_URL)

# Requête
query = """
SELECT
    f.flight_id,
    a.airline_name,
    ap_orig.airport_name AS origin_airport,
    ap_dest.airport_name AS destination_airport,
    f.departure_delay,
    f.arrival_delay,
    f.distance,
    f.air_time
FROM fact_flights f
LEFT JOIN dim_airlines a 
    ON f.airline_id = a.airline_id
LEFT JOIN dim_airports ap_orig 
    ON f.airport_dep_id = ap_orig.airport_id
LEFT JOIN dim_airports ap_dest 
    ON f.airport_arr_id = ap_dest.airport_id
LIMIT 100000
"""

# Export CSV
df = pd.read_sql(query, engine)
print(f"Lignes exportées : {len(df)}")
print(f"Colonnes : {list(df.columns)}")

df.to_csv("flight_analysis_sample.csv", index=False)
print("Export terminé !")