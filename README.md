# ✈ Flight Data Warehouse — 2015 U.S. Flight Delays

**Data Analytics Project** | University of Calabria  
**Author:** Nourhene Dahmen | **Matriculation:** 283388  
**Professor:** Prof. Giorgio Terracina | **Exam Date:** 24 June 2026

---

## 📌 Project Overview

This repository contains the complete ETL pipeline for a Data Warehouse project analyzing **5,819,079 domestic U.S. flights** from 2015, sourced from the [U.S. Department of Transportation dataset on Kaggle](https://www.kaggle.com/datasets/usdot/flight-delays).

The project covers the full Data Warehouse lifecycle:
- **Phase 1 – Design:** E/R modeling, DFM conceptual design, Star Schema logical design
- **Phase 2 – Data Management:** Database population, data quality assessment, ETL pipeline
- **Phase 3 – Visualization:** Interactive OLAP dashboards in Tableau Public

---

## 🗄️ Data Warehouse Architecture

### Star Schema

```
                    DIM_TEMPS
               (Hour→Day→Month→Quarter→Year)
                         |
DIM_AIRPORT_DEP ── FACT_FLIGHTS ── DIM_AIRPORT_ARR
(Airport→City→State)    |          (Airport→City→State)
                    DIM_AIRLINE
                  (IATA Code→Name)
```

### Fact Table: `FACT_FLIGHTS`

| Measure | Type | Description |
|---|---|---|
| `departure_delay` | Float | Minutes between scheduled and actual departure |
| `arrival_delay` | Float | Minutes between scheduled and actual arrival |
| `distance` | Float | Flight distance in miles |
| `air_time` | Float | Wheels-off to wheels-on duration (min) |
| `cancelled` | Integer | Binary flag: 1 = cancelled, 0 = operated |
| `nb_vols` | Integer | Count measure (always = 1 per flight) |
| `weather_delay` | Float | Delay attributable to weather (min) |
| `airline_delay` | Float | Delay attributable to the airline (min) |

---

## 📁 Repository Structure

```
flight-data-warehouse/
│
└── etl_pipeline.py        # Complete ETL pipeline (data quality + loading)
```

### `etl_pipeline.py`

The ETL script performs the following steps:

1. **Data Quality Assessment** — full scan of 5,819,079 records to identify missing values and anomalies
2. **Load `DIM_DATE`** — 365 distinct dates extracted from the reconciled database
3. **Load `DIM_AIRLINES` and `DIM_AIRPORTS`** — 14 airlines and 322 airports
4. **Load `FACT_FLIGHTS`** — 5,332,914 records loaded in chunks of 100,000 rows, with deduplication and IATA code validation

---

## ⚙️ Setup & Requirements

### Prerequisites

```bash
pip install pandas sqlalchemy psycopg2-binary
```

### Database

The pipeline connects to a **PostgreSQL** database. Update the connection string in `etl_pipeline.py`:

```python
engine = create_engine("postgresql://postgres:PASSWORD@localhost:5432/flight_dw_project")
```

### Data Source

Download the three CSV files from Kaggle and place them in the project root:

| File | Rows | Description |
|---|---|---|
| `flights.csv` | 5,819,079 | One row per flight, 31 columns |
| `airlines.csv` | 14 | Airline IATA codes and names |
| `airports.csv` | 322 | Airport details with GPS coordinates |

---

## 🧹 Data Quality

| Issue | Resolution |
|---|---|
| Null delays for cancelled flights | Expected — NULL preserved |
| Negative delay values | Kept as-is (negative = early departure) |
| Null `CANCELLATION_REASON` | Expected for non-cancelled flights |
| Null `TAIL_NUMBER` (0.25%) | Column excluded from Data Warehouse |
| Invalid IATA codes | 486,165 records excluded |
| Duplicate records | 0 duplicates found |

---

## 📊 ETL Results

| Table | Row Count |
|---|---|
| `FACT_FLIGHTS` | 5,332,914 |
| `DIM_DATE` | 365 |
| `DIM_AIRLINES` | 14 |
| `DIM_AIRPORTS` | 322 |
| Records excluded (invalid IATA) | 486,165 |

---

## 📈 Tableau Dashboards

Interactive OLAP dashboards published on **Tableau Public**:

- **Dashboard 01 — Flight Overview:** KPIs, top airlines by volume, monthly trends, airport map
- **Dashboard 02 — Delay Analysis:** Delay by day of week, avg arrival delay by airline, distance vs. delay scatter
- **Dashboard 03 — Cancellation Analysis:** Cancellation rate by airline, monthly cancellation trend

**OLAP operations supported:** Roll-up · Drill-down · Slice · Dice

---

## 💡 Key Findings

- **Spirit Airlines** has the highest avg departure delay (15.94 min) — 32× worse than Hawaiian Airlines (0.49 min)
- **February 2015** cancellation rate (4.78%) was nearly 3× the annual average due to Winter Storm Juno
- **Monday** is the worst day to fly (10.87 min avg delay); **Saturday** is the best (7.83 min)
- **Distance does NOT cause delays** — systemic factors (weather, ATC, hub congestion) are the real drivers
- **Size ≠ Punctuality** — Delta (2nd largest carrier) achieves one of the best delay scores (7.37 min)

---

## 📄 License

This project was developed for academic purposes at the University of Calabria, Department of Mathematics and Computer Science.
