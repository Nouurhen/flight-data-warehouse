# ✈️ Data Warehouse & Visualization – 2015 U.S. Flight Analysis

> **University of Calabria** – Department of Mathematics and Computer Science  
> **Course:** Data Analytics | **Professor:** Giorgio Terracina  
> **Author:** Nourhene Dahmen | **Matriculation:** 283388  
> **Exam Date:** 24 June 2026

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
Reconciled Database (PostgreSQL)
  ├── flights      (5,819,079 rows)
  ├── airlines     (14 rows)
  └── airports     (322 rows)
       │
       ▼ ETL Pipeline (Python)
       │
       ▼
Data Warehouse (Star Schema – PostgreSQL)
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
and four dimension tables.

### Star Schema

```
                    ┌─────────────┐
                    │  DIM_TEMPS  │
                    │─────────────│
                    │ year        │
                    │ month       │
                    │ day         │
                    │ day_of_week │
                    └──────┬──────┘
                           │
┌──────────────┐    ┌──────┴───────────┐    ┌──────────────────┐
│ DIM_AIRPORTS │    │  FACT_FLIGHTS    │    │  DIM_AIRPORTS    │
│──────────────│    │──────────────────│    │──────────────────│
│ airport_code │◄───│ airline_code     │───►│ airport_code     │
│ airport_name │    │ origin_airport   │    │ airport_name     │
│ city         │    │ destination_airport    │ city             │
│ state        │    │ flight_year      │    │ state            │
│ country      │    │ flight_month     │    │ country          │
│ latitude     │    │ flight_day       │    │ latitude         │
│ longitude    │    │ departure_delay  │    │ longitude        │
└──────────────┘    │ arrival_delay    │    └──────────────────┘
                    │ distance         │
                    │ air_time         │    ┌──────────────────┐
                    │ elapsed_time     │    │  DIM_AIRLINES    │
                    │ cancelled        │    │──────────────────│
                    │ diverted         │◄───│ airline_code     │
                    └──────────────────┘    │ airline_name     │
                                            └──────────────────┘
```

**Design choice:** Star Schema was preferred over Snowflake Schema because:
- Dimensions are small (14 airlines, 322 airports, 365 dates)
- Denormalization simplifies OLAP queries
- Better compatibility with Tableau Public

---

## ⚙️ ETL Process

The ETL pipeline is fully implemented in Python (`etl_pipeline.py`).

### Pipeline Steps

```
Step 1 ── Data Quality Assessment
          └── Full scan of 5,819,079 records
          └── Identify missing values per column
          └── Detect duplicates and IATA mismatches

Step 2 ── Load DIM_DATE
          └── Extract 365 distinct dates from flights table
          └── Include year, month, day, day_of_week

Step 3 ── Load DIM_AIRLINES
          └── 14 airline records from reference table

Step 4 ── Load DIM_AIRPORTS
          └── 322 airport records with GPS coordinates

Step 5 ── Load FACT_FLIGHTS
          └── Process in chunks of 100,000 rows
          └── Remove duplicates on each chunk
          └── Validate IATA codes
          └── Fill nulls for non-cancelled flights
          └── Insert 5,332,914 records into DW
```

### Key Implementation Choices

| Decision | Rationale |
|----------|-----------|
| Chunked reading (100K rows) | Handles 5.8M records within memory constraints |
| IATA validation | Ensures referential integrity in the DW |
| NULL preservation for cancellations | Cancelled flights legitimately have no delay values |
| Deduplication on composite key | Prevents double-counting of flight records |

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
| `elapsed_time` | 105,071 | 1.81% | Filled with 0 for active flights |
| `air_time` | 105,071 | 1.81% | Filled with 0 for active flights |
| `arrival_delay` | 105,071 | 1.81% | NULL kept (cancelled flights) |
| `cancellation_reason` | 5,729,195 | 98.46% | Expected – only 1.54% cancelled |
| `weather_delay` | 4,755,640 | 81.72% | Expected – only for delayed flights |
| `airline_delay` | 4,755,640 | 81.72% | Expected – only for delayed flights |

### Issues & Resolutions

| Issue | Resolution |
|-------|------------|
| Null delays for cancelled flights | NULL kept – expected behavior |
| Negative delay values | Kept as-is (negative = early departure) |
| Null `TAIL_NUMBER` (0.25%) | Column excluded from DW |
| Null delay components (81.72%) | NULL preserved for on-time flights |
| Duplicate records | 0 duplicates found |
| IATA code mismatch | 486,165 records (8.35%) excluded |

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

### Key Findings

- 🥇 **Southwest Airlines** operated the highest number of flights (1,261,855)
- ⏰ **Spirit Air Lines** had the highest average departure delay (15.94 min)
- 🌡️ **February** had the highest cancellation rate (4.78%) – winter weather
- 📅 **Monday** had the highest average delay (10.87 min)
- ✅ **Hawaiian Airlines** had the lowest cancellation rate (0.49 min avg delay)
- 🗺️ Long-haul flights (>3,000 miles) showed lower average delays

---

## 📊 KPIs

| KPI | Value |
|-----|-------|
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
- KPI cards: Total Flights, Avg Delay, Cancellation Rate, Airlines
- Top Airlines by Number of Flights (bar chart)
- Average Departure Delay by Airline (bar chart)
- Flights per Month – 2015 (line chart)
- Airport Map (geographic view)
- Cancellation Rate by Airline

### Dashboard 2 – Delay Analysis
- Delay by Day of Week (bar chart)
- Average Arrival Delay by Airline (bar chart)
- Distance vs Arrival Delay (scatter plot)

### Dashboard 3 – Cancellation Analysis
- Cancellation Rate by Airline (bar chart)
- Cancellation by Month (bar chart – February peak visible)

**OLAP operations supported:**
- 🔼 **Roll-up:** Day → Month → Quarter → Year
- 🔽 **Drill-down:** Year → Month → Day
- 🔪 **Slice:** Filter by airline or airport
- 🎲 **Dice:** Cross-filter airline × month

---

## 🛠️ Technologies

| Technology | Purpose |
|------------|---------|
| **PostgreSQL** | Reconciled database + Data Warehouse |
| **Python 3.14** | ETL pipeline, data quality |
| **Pandas** | Data manipulation and cleaning |
| **SQLAlchemy** | Database connection and ORM |
| **Tableau Public** | Interactive OLAP dashboards |
| **GitHub** | Version control and code sharing |

---

## 📁 Project Structure

```
flight-data-warehouse/
│
├── etl_pipeline.py      # Main ETL pipeline (Python)
├── star_schema.sql      # Star Schema DDL (PostgreSQL)
├── requirements.txt     # Python dependencies
└── README.md            # Project documentation
```

---

## ⚙️ Setup & Requirements

### Prerequisites

```bash
pip install pandas sqlalchemy psycopg2-binary
```

### Database

The pipeline connects to a **PostgreSQL** database. Update the connection
string in `etl_pipeline.py`:

```python
engine = create_engine(
    "postgresql://postgres:PASSWORD@localhost:5432/flight_dw_project"
)
```

### Run the ETL

```bash
python etl_pipeline.py
```

Expected output:
```
Connected to PostgreSQL
Running Data Quality Assessment...
Total records: 5,819,079
Loading DIM_DATE...       → 365 rows
Loading DIM_AIRLINES...   → 14 rows
Loading DIM_AIRPORTS...   → 322 rows
Loading FACT_FLIGHTS...   → 5,332,914 rows
ETL Pipeline completed!
```

---

## 📜 License

This project was developed for academic purposes at the University of Calabria.  
Dataset: [Kaggle – 2015 Flight Delays](https://www.kaggle.com/datasets/usdot/flight-delays) (Public Domain)
