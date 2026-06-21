# ✈️ Data Warehouse & Visualization – 2015 U.S. Flight Analysis

> **University of Calabria** – Department of Mathematics and Computer Science  

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Data Source](#data-source)
- [Data Warehouse Schema](#data-warehouse-schema)
- [ETL Process](#etl-process)
- [Data Quality Assessment](#data-quality-assessment)
- [Results](#results)
- [KPIs](#kpis)
- [Tableau Dashboards](#tableau-dashboards)
- [Technologies](#technologies)
- [Project Structure](#project-structure)
- [Setup & Requirements](#setup--requirements)

---

## 🎯 Overview

This project implements a complete **Data Warehouse pipeline** applied to the
2015 U.S. Flight Delays and Cancellations dataset, published by the U.S.
Department of Transportation (DOT).

The dataset covers:

- 🛫 **5,819,079** individual flight records
- ✈️ **14** major U.S. airlines
- 🏢 **322** airports across the United States
- 📅 Full year **2015**

The project follows the standard DW development lifecycle:

| Phase | Description |
|-------|-------------|
| **Phase 1 – Design** | E/R modeling, DFM conceptual design, Star Schema logical design |
| **Phase 2 – Data Management** | Data quality assessment, cleaning, ETL pipeline |
| **Phase 3 – Visualization** | Interactive OLAP dashboards in Tableau Public |

---

## 🏗️ Architecture

```
CSV Files (Kaggle)
       │
       ▼
Reconciled Database (PostgreSQL) — populated by populate_reconciled.py
  ├── flight      (5,819,079 rows)
  ├── airline     (14 rows)
  └── airport     (322 rows)
       │
       ▼ ETL Pipeline (etl_pipeline.py)
       │
       ▼
Data Warehouse – Star Schema (PostgreSQL) — flight_dw_project
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
|------|-------------|------|---------|
| `flights.csv` | One row per flight | 5,819,079 | 31 |
| `airlines.csv` | Airline IATA codes and names | 14 | 2 |
| `airports.csv` | Airport details with GPS coordinates | 322 | 7 |

**Key attributes analyzed:**

- `DEPARTURE_DELAY` / `ARRIVAL_DELAY` – delay in minutes
- `CANCELLED` / `CANCELLATION_REASON` – cancellation flags
- `DISTANCE` – flight distance in miles
- `AIRLINE` / `ORIGIN_AIRPORT` / `DESTINATION_AIRPORT` – dimensional keys

---

## 🗄️ Data Warehouse Schema

The Data Warehouse follows a **Star Schema** design with one central fact table
and three dimension tables. `DIM_AIRPORTS` is a **role-playing dimension**:
the same table is referenced twice by `FACT_FLIGHTS` via `airport_dep_id`
(departure) and `airport_arr_id` (arrival).

### Star Schema

```
                    ┌──────────────────┐
                    │    DIM_DATE      │
                    │──────────────────│
                    │ date_id    (PK)  │
                    │ year             │
                    │ quarter          │
                    │ month            │
                    │ month_name       │
                    │ week             │
                    │ day              │
                    │ day_of_week      │
                    │ day_name         │
                    │ is_weekend       │
                    └────────┬─────────┘
                             │ date_id (FK)
                             │
┌──────────────────┐  ┌──────┴────────────────┐  ┌──────────────────┐
│   DIM_AIRPORTS   │  │     FACT_FLIGHTS       │  │   DIM_AIRPORTS   │
│──────────────────│  │────────────────────────│  │──────────────────│
│ airport_id (PK)  │◄─│ airport_dep_id   (FK)  │  │ airport_id (PK)  │
│ iata_code        │  │ airport_arr_id   (FK)  │─►│ iata_code        │
│ airport_name     │  │ airline_id       (FK)  │  │ airport_name     │
│ city             │  │ date_id          (FK)  │  │ city             │
│ state            │  │ flight_id        (PK)  │  │ state            │
│ country          │  │ departure_delay        │  │ country          │
│ latitude         │  │ arrival_delay          │  │ latitude         │
│ longitude        │  │ distance               │  │ longitude        │
└──────────────────┘  │ air_time               │  └──────────────────┘
    (departure role)  │ cancelled              │      (arrival role)
                      │ weather_delay          │
                      │ airline_delay          │  ┌──────────────────┐
                      │ nb_vols                │  │   DIM_AIRLINES   │
                      └────────────────────────┘  │──────────────────│
                                      │            │ airline_id (PK)  │
                                      └───(FK)────►│ iata_code        │
                                                   │ airline_name     │
                                                   └──────────────────┘
```

**Design choices:**

- **Star Schema over Snowflake**: dimensions are small (14 airlines, 322 airports,
  365 dates), so denormalization has negligible storage cost but significantly
  simplifies OLAP queries and Tableau Public compatibility.
- **Role-playing dimension**: `DIM_AIRPORTS` is referenced twice by `FACT_FLIGHTS`
  (departure and arrival) rather than duplicating the table, avoiding data redundancy.
- **Surrogate keys**: integer PKs (`airline_id`, `airport_id`, `date_id`) decouple
  the DW from the operational IATA codes used in the reconciled database.

### Dimensional Hierarchies

| Dimension | Hierarchy |
|-----------|-----------|
| `DIM_DATE` | Day → Week → Month → Quarter → Year |
| `DIM_AIRPORTS` | Airport → City → State → Country |
| `DIM_AIRLINES` | IATA Code → Airline Name |

> **Note on Hour level:** An Hour level was considered during the initial
> data-driven design but was not implemented in `DIM_DATE`. Its only source,
> `SCHEDULED_DEPARTURE`/`SCHEDULED_ARRIVAL`, was pruned from the DFM because
> those timestamps are superseded by the more analytically meaningful
> `DEPARTURE_DELAY` and `ARRIVAL_DELAY` measures. The implemented hierarchy
> therefore starts at the Day level.

### Measures – FACT_FLIGHTS

| Measure | Additivity | Definition |
|---------|-----------|------------|
| `departure_delay` | Additive | Minutes between scheduled and actual departure. Negative = early. |
| `arrival_delay` | Additive | Minutes between scheduled and actual arrival. |
| `distance` | Additive | Great-circle distance in miles. |
| `air_time` | Additive | Wheels-off to wheels-on duration in minutes. |
| `cancelled` | Semi-additive | Binary flag: 1 = cancelled, 0 = operated. AVG gives cancellation rate. |
| `nb_vols` | Additive | Count measure (always = 1). SUM gives total flights. |
| `weather_delay` | Additive | Minutes of delay attributable to weather. |
| `airline_delay` | Additive | Minutes of delay attributable to the airline. |

---

## ⚙️ ETL Process

The ETL pipeline is split across two scripts:

- `populate_reconciled.py` — loads the 3 CSV files into the reconciled PostgreSQL database
- `etl_pipeline.py` — runs data quality assessment and loads the star schema DW

### Pipeline Steps

```
Step 1 ── Data Quality Assessment (etl_pipeline.py)
          └── Full scan of 5,819,079 records
          └── Identify missing values per column (18 columns checked)
          └── Detect duplicates and IATA code mismatches

Step 2 ── Load DIM_DATE
          └── 365 distinct dates extracted from the reconciled flight table
          └── Enriched with quarter, month_name, week, day_name, is_weekend

Step 3 ── Load DIM_AIRLINES
          └── 14 airline records loaded from the airline reference table

Step 4 ── Load DIM_AIRPORTS
          └── 322 airport records with GPS coordinates

Step 5 ── Load FACT_FLIGHTS
          └── Process in chunks of 100,000 rows
          └── Deduplication on composite key (year, month, day, airline_code,
              flight_number, origin_airport, destination_airport)
          └── IATA code validation — exclude records with unresolvable codes
          └── fillna(0) for non-cancelled flights on delay columns
          └── Surrogate key lookup: airline_code → airline_id, etc.
          └── 5,332,914 records inserted into fact_flights
```

### Key Implementation Choices

| Decision | Rationale |
|----------|-----------|
| Chunked reading (100K rows) | Handles 5.8M records within memory constraints |
| IATA validation before load | Ensures referential integrity in the DW |
| NULL preservation for cancellations | Cancelled flights legitimately have no delay values |
| Surrogate keys via lookup dictionaries | Decouples DW from operational IATA codes |
| `flight_number` used only in dedup key | Used internally for deduplication but not stored in FACT_FLIGHTS (high-cardinality identifier with no aggregation path) |

---

## 🔍 Data Quality Assessment

Full assessment performed on **5,819,079 records**.

### Missing Values Analysis

| Column | Missing Count | Missing % | Resolution |
|--------|--------------|-----------|------------|
| `tail_number` | 14,721 | 0.25% | Column excluded from DW |
| `departure_time` | 86,153 | 1.48% | Not used in DW |
| `departure_delay` | 86,153 | 1.48% | NULL kept (cancelled flights) |
| `taxi_out` | 89,047 | 1.53% | Pruned from DW |
| `wheels_off` | 89,047 | 1.53% | Pruned from DW |
| `elapsed_time` | 105,071 | 1.81% | Not used in DW |
| `air_time` | 105,071 | 1.81% | fillna(0) for non-cancelled |
| `wheels_on` | 92,513 | 1.59% | Pruned from DW |
| `taxi_in` | 92,513 | 1.59% | Pruned from DW |
| `arrival_time` | 92,513 | 1.59% | Not used in DW |
| `arrival_delay` | 105,071 | 1.81% | NULL kept (cancelled flights) |
| `cancellation_reason` | 5,729,195 | 98.46% | Expected – only 1.54% cancelled; column pruned from DW |
| `air_system_delay` | 4,755,640 | 81.72% | Pruned from DW |
| `security_delay` | 4,755,640 | 81.72% | Pruned from DW |
| `airline_delay` | 4,755,640 | 81.72% | fillna(0) for non-cancelled |
| `late_aircraft_delay` | 4,755,640 | 81.72% | Pruned from DW |
| `weather_delay` | 4,755,640 | 81.72% | fillna(0) for non-cancelled |

### Issues & Resolutions

| Issue | Affected Columns | Resolution |
|-------|-----------------|------------|
| Null delays for cancelled flights | `arrival_delay`, `departure_delay` | NULL kept for cancelled; fillna(0) for non-cancelled |
| Negative delay values | `departure_delay`, `arrival_delay` | Kept as-is (negative = early departure/arrival) |
| Null `cancellation_reason` | `cancellation_reason` | Expected for non-cancelled flights; column pruned from DW |
| Null `tail_number` (0.25%) | `tail_number` | Column excluded from DW |
| Duplicate records | All columns | 0 duplicates found after deduplication check |
| IATA code mismatch | `airline_code`, `origin_airport`, `destination_airport` | 486,165 records (8.35%) excluded |
| Missing GPS coordinates | `latitude`, `longitude` | 3 airports affected; kept with NULL coords |

---

## 📈 Results

### ETL Execution Results

| Table | Row Count |
|-------|-----------|
| `fact_flights` | **5,332,914** |
| `dim_date` | 365 |
| `dim_airlines` | 14 |
| `dim_airports` | 322 |
| Duplicates removed | 0 |
| Invalid codes excluded | 486,165 |

> Verification: 5,819,079 − 486,165 = **5,332,914** ✓

### Key Findings

- 🥇 **Southwest Airlines** operated the most flights (1,157,339 after cleaning)
- ⏰ **Spirit Air Lines** had the highest average departure delay (~15.94 min)
- ❄️ **February** had the highest cancellation rate (4.78%) — consistent with severe winter weather patterns in the Northeast
- 📅 **Monday** had the highest average delay (10.87 min)
- ✅ **Hawaiian Airlines** had the lowest average departure delay (0.49 min)
- 📏 No meaningful correlation between flight distance and arrival delay

---

## 📊 KPIs

| KPI | Value |
|-----|-------|
| Total Flights (raw) | 5,819,079 |
| Total Flights (DW) | 5,332,914 |
| Average Departure Delay | 9.37 min |
| Cancellation Rate | 1.54% |
| Number of Airlines | 14 |
| Number of Airports | 322 |
| Worst Delay (Airline) | Spirit Air Lines (~15.94 min avg) |
| Best Delay (Airline) | Hawaiian Airlines (0.49 min avg) |
| Best Month (Cancellations) | September (0.45%) |
| Worst Month (Cancellations) | February (4.78%) |

---

## 📉 Tableau Dashboards

🔗 **View all dashboards:**  
👉 [Tableau Public Profile – Nourhene Dahmen](https://public.tableau.com/app/profile/nourhene.dahmen/vizzes)

### Dashboard 1 – Flight Analysis Overview
- KPI cards: Total Flights, Avg Delay, Cancellation Rate, Airlines
- Top Airlines by Number of Flights (bar chart)
- Average Departure Delay by Airline (bar chart)
- Flights per Month – 2015 (line chart)
- Airport Map (geographic view)

### Dashboard 2 – Delay Analysis
- Delay by Day of Week (bar chart)
- Average Arrival Delay by Airline (bar chart)
- Distance vs Arrival Delay (scatter plot)

### Dashboard 3 – Cancellation Analysis
- Cancellation Rate by Airline (bar chart)
- Cancellation by Month (bar chart – February peak visible)

**OLAP operations supported:**

| Operation | Implementation |
|-----------|---------------|
| 🔼 Roll-up | Day → Month → Quarter → Year (via DIM_DATE hierarchy) |
| 🔽 Drill-down | Year → Month → Day |
| 🔪 Slice | Filter by airline, airport, or is_weekend |
| 🎲 Dice | Cross-filter airline × month |

---

## 🛠️ Technologies

| Technology | Purpose |
|------------|---------|
| **PostgreSQL 17** | Reconciled database + Data Warehouse |
| **Python 3** | ETL pipeline, data quality assessment |
| **Pandas** | Data manipulation and cleaning |
| **SQLAlchemy** | Database connection and ORM |
| **pgAdmin 4** | Database administration and query execution |
| **Tableau Public** | Interactive OLAP dashboards |
| **GitHub** | Version control and code sharing |

---

## 📁 Project Structure

```
flight-data-warehouse/
│
├── reconciled_schema.sql    # Reconciled DB DDL (PostgreSQL)
├── star_schema.sql          # Star Schema DDL (PostgreSQL)
├── populate_reconciled.py   # Load CSV files → reconciled DB
├── etl_pipeline.py          # Data quality + ETL → Data Warehouse
├── export.py                # Export DW to CSV for Tableau Public
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation
```

---

## ⚙️ Setup & Requirements

### Prerequisites

```bash
pip install pandas sqlalchemy psycopg2-binary
```

### Step 1 — Create the schemas

```sql
-- In PostgreSQL (psql or pgAdmin):
\i reconciled_schema.sql   -- creates flight_reconciled database schema
\i star_schema.sql         -- creates flight_dw_project database schema
```

### Step 2 — Populate the reconciled database

```bash
# Place flights.csv, airlines.csv, airports.csv in the working directory
python populate_reconciled.py
```

### Step 3 — Run the ETL pipeline

```bash
python etl_pipeline.py
```

Expected output:

```
Connected to PostgreSQL
Running Data Quality Assessment...
Total records scanned: 5,819,079
Loading DIM_DATE...       → 365 rows loaded
Loading DIM_AIRLINES...   → 14 rows loaded
Loading DIM_AIRPORTS...   → 322 rows loaded
Loading FACT_FLIGHTS...   → 5,332,914 rows loaded (486,165 excluded)
ETL Pipeline completed successfully.
```

### Step 4 — Export to CSV for Tableau

```bash
python export.py
# Output: flight_analysis_sample.csv (ready for Tableau Public)
```

### Database connection

Update the connection string in each script using the `DATABASE_URL` environment variable or directly:

```python
engine = create_engine(
    "postgresql://postgres:YOUR_PASSWORD@localhost:5432/flight_dw_project"
)
```

---

## 📜 License

This project was developed for academic purposes at the University of Calabria.  
Dataset: [Kaggle – 2015 Flight Delays](https://www.kaggle.com/datasets/usdot/flight-delays) (Public Domain)
