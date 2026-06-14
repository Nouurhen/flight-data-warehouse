# ✈️ Data Warehouse & Visualization – 2015 U.S. Flight Analysis

> **University of Calabria** – Department of Mathematics and Computer Science
> Project Report of Data Analytics – Prof. Giorgio Terracina

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Data Source](#data-source)
- [Reconciled Database](#reconciled-database)
- [Data Warehouse — Star Schema](#data-warehouse--star-schema)
- [ETL Process](#etl-process)
- [Data Quality Assessment](#data-quality-assessment)
- [Results](#results)
- [KPIs](#kpis)
- [Tableau Dashboards](#tableau-dashboards)
- [Project Structure](#project-structure)
- [Setup & Requirements](#setup--requirements)

---

## 🎯 Overview

This project implements a complete Data Warehouse pipeline applied to the
2015 U.S. Flight Delays and Cancellations dataset, published by the U.S.
Department of Transportation (DOT).

The dataset covers:

- 🛫 **5,819,079** individual flight records
- ✈️ **14** major U.S. airlines
- 🏢 **322** airports across the United States
- 📅 Full year **2015**

The project follows the standard DW development lifecycle:

| Phase | Description |
| ----- | ----------- |
| **Phase 1 – Design** | E/R modeling (reconciled DB), DFM conceptual design, Star Schema logical design |
| **Phase 2 – Data Management** | Reconciled DB population, data quality assessment, ETL pipeline |
| **Phase 3 – Visualization** | Interactive OLAP dashboards in Tableau Public |

---

## 🏗️ Architecture

```
CSV Files (Kaggle)
       │
       ▼
Reconciled Database (PostgreSQL: flight_reconciled)
  ├── flight      (5,819,079 rows, 31 columns — raw copy of flights.csv)
  ├── airline     (14 rows)
  └── airport     (322 rows)
       │
       ▼ ETL Pipeline (Python: etl_pipeline.py)
       │  - data quality assessment
       │  - dim_date enrichment (quarter, week, day_name, is_weekend)
       │  - dedup + IATA code validation
       │  - lookup to surrogate keys (date_id, airport_*_id, airline_id)
       │
       ▼
Data Warehouse (PostgreSQL: flight_dw_project — Star Schema)
  ├── fact_flights   (5,332,914 rows)
  ├── dim_date       (365 rows)
  ├── dim_airlines   (14 rows)
  └── dim_airports   (322 rows)
       │
       ▼
Tableau Public (3 Interactive Dashboards)
```

---

## 📊 Data Source

Dataset: [2015 Flight Delays and Cancellations](https://www.kaggle.com/datasets/usdot/flight-delays)
Source: U.S. Department of Transportation (DOT)

| File | Description | Rows | Columns |
| ---- | ----------- | ---- | ------- |
| `flights.csv` | One row per flight | 5,819,079 | 31 |
| `airlines.csv` | Airline IATA codes and names | 14 | 2 |
| `airports.csv` | Airport details with GPS coordinates | 322 | 7 |

`flights.csv` is not included in this repository due to its size (~590 MB).
Download it from Kaggle and place it in the project root before running
`populate_reconciled.py`.

---

## 🗄️ Reconciled Database

Built first, as a faithful 1:1 copy of the source CSVs (no FK enforcement,
no cleaning) — see `reconciled_schema.sql`.

| Table | Columns | Rows |
| ----- | ------- | ---- |
| `flight` | 31 (all raw `flights.csv` columns, lowercased) | 5,819,079 |
| `airline` | `iata_code`, `airline_name` | 14 |
| `airport` | `iata_code`, `airport_name`, `city`, `state`, `country`, `latitude`, `longitude` | 322 |

Population: `populate_reconciled.py` (chunked load, 100k rows/chunk).

> **Data quality note**: 3 rows in `airport` have missing latitude/longitude.

---

## ⭐ Data Warehouse — Star Schema

The Data Warehouse follows a **Star Schema** design with one central fact
table and three dimension tables, where `dim_airports` is a **role-playing
dimension** (referenced twice by the fact, as departure and arrival airport).

### `dim_date`
Hierarchy: `day → week → month → quarter → year`

| Column | Type |
| ------ | ---- |
| date_id (PK) | SERIAL |
| year, quarter, month, week, day, day_of_week | INTEGER |
| month_name, day_name | VARCHAR |
| is_weekend | BOOLEAN |

### `dim_airlines`
Hierarchy: `IATA code → airline name`

| Column | Type |
| ------ | ---- |
| airline_id (PK) | SERIAL |
| iata_code | VARCHAR(5), UNIQUE |
| airline_name | VARCHAR(100) |

### `dim_airports` (role-playing: departure / arrival)
Hierarchy: `airport → city → state → country`

| Column | Type |
| ------ | ---- |
| airport_id (PK) | SERIAL |
| iata_code | VARCHAR(5), UNIQUE |
| airport_name, city, state, country | VARCHAR |
| latitude, longitude | FLOAT |

### `fact_flights`

| Column | Type | Additivity |
| ------ | ---- | ---------- |
| flight_id (PK) | SERIAL | — |
| date_id, airport_dep_id, airport_arr_id, airline_id (FK) | INTEGER | — |
| departure_delay, arrival_delay | FLOAT | Additive |
| distance, air_time | FLOAT | Additive |
| weather_delay, airline_delay | FLOAT | Additive |
| cancelled | INTEGER (0/1) | Semi-additive |
| nb_vols | INTEGER (always 1) | Additive (count measure) |

**Design choice (Star vs Snowflake):** the star schema was preferred because
dimensions are small (14 airlines, 322 airports, 365 dates); denormalization
simplifies OLAP queries and improves Tableau Public compatibility.

**Pruned attributes** (present in the raw data but excluded from the DW,
see report Section 2.4.1): `tail_number`, `flight_number`,
`scheduled_departure`/`scheduled_arrival`, `wheels_off`/`wheels_on`,
`taxi_out`/`taxi_in`, `diverted`, and three of the five delay-breakdown
columns (`air_system_delay`, `security_delay`, `late_aircraft_delay` — only
`weather_delay` and `airline_delay` are retained as the two most analytically
relevant delay causes).

**Grafted attributes** (added during ETL, see report Section 2.4.2):
`is_weekend`, `quarter`, `nb_vols`.

---

## ⚙️ ETL Process

The ETL pipeline (`etl_pipeline.py`) reads from `flight_reconciled` and
writes to `flight_dw_project`.

### Pipeline Steps

```
Step 0 -- Data Quality Assessment
          Full scan of 5,819,079 records (chunked)
          Identify missing values per column

Step 1 -- Load DIM_DATE
          Extract 365 distinct dates from the reconciled `flight` table
          Compute quarter, month_name, week, day_name, is_weekend

Step 2 -- Load DIM_AIRLINES
          14 airline records from the reconciled `airline` table

Step 3 -- Load DIM_AIRPORTS
          322 airport records from the reconciled `airport` table

Step 4 -- Load FACT_FLIGHTS
          Process `flight` in chunks of 100,000 rows
          Remove duplicates on each chunk
          Validate IATA codes (airline / origin / destination)
          Fill nulls for non-cancelled flights
          Lookup surrogate keys (date_id, airline_id, airport_dep_id,
          airport_arr_id) and set nb_vols = 1
          Insert into fact_flights
```

### Key Implementation Choices

| Decision | Rationale |
| -------- | --------- |
| Two-database design (reconciled → DW) | Separates raw integration from dimensional modeling, as required by the project methodology |
| Chunked reading (100K rows) | Handles 5.8M records within memory constraints |
| IATA validation | Ensures referential integrity in the DW |
| NULL preservation for cancellations | Cancelled flights legitimately have no delay values |
| Deduplication on composite key | Prevents double-counting of flight records |
| Lookup dictionaries for surrogate keys | Avoids per-row SQL joins during the chunked load |

---

## 🔍 Data Quality Assessment

Full assessment performed on **5,819,079 records**.

### Missing Values Analysis

| Column | Missing Count | Missing % | Resolution |
| ------ | -------------- | --------- | ---------- |
| `tail_number` | 14,721 | 0.25% | Column excluded from DW |
| `departure_time` | 86,153 | 1.48% | Not used in DW |
| `departure_delay` | 86,153 | 1.48% | NULL→0 for non-cancelled, kept for cancelled |
| `taxi_out` | 89,047 | 1.53% | Pruned from DW |
| `wheels_off` | 89,047 | 1.53% | Pruned from DW |
| `elapsed_time` | 105,071 | 1.81% | Not used in DW |
| `air_time` | 105,071 | 1.81% | NULL→0 for non-cancelled, kept for cancelled |
| `arrival_delay` | 105,071 | 1.81% | NULL→0 for non-cancelled, kept for cancelled |
| `cancellation_reason` | 5,729,195 | 98.46% | Expected – only 1.54% cancelled |
| `weather_delay` | 4,755,640 | 81.72% | NULL→0 for non-cancelled, kept for cancelled |
| `airline_delay` | 4,755,640 | 81.72% | NULL→0 for non-cancelled, kept for cancelled |
| `air_system_delay`, `security_delay`, `late_aircraft_delay` | 4,755,640 | 81.72% | Pruned from DW (see Star Schema section) |

### Issues & Resolutions

| Issue | Resolution |
| ----- | ---------- |
| Null delays for cancelled flights | NULL kept – expected behavior |
| Negative delay values | Kept as-is (negative = early departure) |
| Null `TAIL_NUMBER` (0.25%) | Column excluded from DW |
| Null delay components (81.72%) | NULL→0 for on-time flights |
| Duplicate records | 0 duplicates found |
| IATA code mismatch | 486,165 records (8.35%) excluded |
| Missing GPS coordinates in `airports.csv` | 3 records (0.93%) — kept, lat/long NULL |

---

## 📈 Results

### ETL Execution Results

| Table | Row Count |
| ----- | --------- |
| `fact_flights` | **5,332,914** |
| `dim_date` | 365 |
| `dim_airlines` | 14 |
| `dim_airports` | 322 |
| Duplicates removed | 0 |
| Invalid codes excluded | 486,165 |

### Key Findings

- 🥇 **Southwest Airlines** operated the highest number of flights (1,261,855)
- ⏰ **Spirit Air Lines** had the highest average departure delay (15.94 min)
- 🌡️ **February** had the highest cancellation rate (4.78%) – winter weather
- 📅 **Monday** had the highest average delay (10.87 min)
- ✅ **Alaska Airlines** had the best average departure delay (1.79 min)
- 🗺️ Long-haul flights show no meaningful correlation between distance and delay

---

## 📊 KPIs

| KPI | Value |
| --- | ----- |
| Total Flights | 5,819,079 |
| Average Departure Delay | 9.37 min |
| Cancellation Rate | 1.54% |
| Number of Airlines | 14 |
| Number of Airports | 322 |
| Most Flights (Airline) | Southwest (1,261,855) |
| Worst Delay (Airline) | Spirit Air Lines (15.94 min avg) |
| Best Month (Cancellations) | September (0.45%) |
| Worst Month (Cancellations) | February (4.78%) |

---

## 📉 Tableau Dashboards

🔗 **View all dashboards:**
👉 [Tableau Public Profile – Nourhene Dahmen](https://public.tableau.com/app/profile/nourhene.dahmen/vizzes)

### Dashboard 1 – Flight Analysis Overview
KPI cards, top airlines by volume, average departure delay by airline,
flights per month, airport map, cancellation rate by airline.

### Dashboard 2 – Delay Analysis
Delay by day of week, average arrival delay by airline, distance vs arrival
delay scatter plot.

### Dashboard 3 – Cancellation Analysis
Cancellation rate by airline, cancellation by month.

**OLAP operations supported:**

- 🔼 **Roll-up:** Day → Week → Month → Quarter → Year
- 🔽 **Drill-down:** Year → Quarter → Month → Day
- 🔪 **Slice:** Filter by airline or airport
- 🎲 **Dice:** Cross-filter airline × month

---

## 🛠️ Technologies

| Technology | Purpose |
| ---------- | ------- |
| **PostgreSQL** | Reconciled database + Data Warehouse |
| **Python (Pandas + SQLAlchemy)** | ETL pipeline, data quality |
| **Tableau Public** | Interactive OLAP dashboards |

---

## 📁 Project Structure

```
flight-data-warehouse/
│
├── reconciled_schema.sql   # Reconciled DB DDL (flight, airline, airport)
├── populate_reconciled.py  # Loads CSVs into the reconciled DB
├── star_schema.sql         # Data Warehouse DDL (Star Schema)
├── etl_pipeline.py          # Reconciled DB -> Data Warehouse ETL
├── export.py                # Sample export query (DW -> CSV)
├── .env.example              # Database connection template
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup & Requirements

### Prerequisites

```bash
pip install pandas sqlalchemy psycopg2-binary
```

### Database setup

```bash
# 1. Create both databases
createdb flight_reconciled
createdb flight_dw_project

# 2. Create schemas
psql -d flight_reconciled -f reconciled_schema.sql
psql -d flight_dw_project  -f star_schema.sql

# 3. Configure credentials
cp .env.example .env
# edit .env with your PostgreSQL password, then load it:
#   Windows (cmd):  for /f "delims=" %i in (.env) do set %i
#   Linux/Mac:      export $(cat .env | xargs)
```

### Run the pipeline

```bash
# Place flights.csv, airlines.csv, airports.csv in the project root
python populate_reconciled.py   # ~15-30 min for 5.8M rows
python etl_pipeline.py          # ~20-40 min
```

Expected final output:

```
fact_flights    5332914
dim_date             365
dim_airlines          14
dim_airports         322
ETL Pipeline completed!
Duplicates removed: 0
Invalid codes excluded: 486165
```

---

## 📜 License

This project was developed for academic purposes at the University of Calabria.
Dataset: [Kaggle – 2015 Flight Delays](https://www.kaggle.com/datasets/usdot/flight-delays) (Public Domain)
