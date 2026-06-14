import pandas as pd
from sqlalchemy import create_engine

# Connexion PostgreSQL
engine = create_engine(
    'postgresql://postgres:TON_MOT_DE_PASSE@localhost/flight_dw_project'
)

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
    ON f.airline_code = a.airline_code
LEFT JOIN dim_airports ap_orig 
    ON f.origin_airport = ap_orig.airport_code
LEFT JOIN dim_airports ap_dest 
    ON f.destination_airport = ap_dest.airport_code
LIMIT 100000
"""

# Export CSV
df = pd.read_sql(query, engine)
print(f"Lignes exportées : {len(df)}")
print(f"Colonnes : {list(df.columns)}")

df.to_csv(
    r'C:\Users\Nourhene Dahmen\OneDrive - Università della Calabria\flight_dw_project\flight_analysis_sample.csv',
    index=False
)
print("Export terminé !")