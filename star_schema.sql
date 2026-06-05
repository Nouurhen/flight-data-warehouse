-- ============================================================
-- Star Schema — 2015 U.S. Flight Data Warehouse
-- University of Calabria — Data Analytics Project
-- ============================================================

-- Drop tables if they exist (order matters for FK constraints)
DROP TABLE IF EXISTS fact_flights;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_airports;
DROP TABLE IF EXISTS dim_airlines;

-- ============================================================
-- DIM_DATE
-- ============================================================
CREATE TABLE dim_date (
    date_id      SERIAL       PRIMARY KEY,
    year         INTEGER      NOT NULL,
    quarter      INTEGER      NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month        INTEGER      NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name   VARCHAR(10)  NOT NULL,
    week         INTEGER      NOT NULL,
    day          INTEGER      NOT NULL CHECK (day BETWEEN 1 AND 31),
    day_of_week  INTEGER      NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    day_name     VARCHAR(10)  NOT NULL,
    is_weekend   BOOLEAN      NOT NULL
);

-- ============================================================
-- DIM_AIRLINES
-- ============================================================
CREATE TABLE dim_airlines (
    airline_id    SERIAL      PRIMARY KEY,
    iata_code     VARCHAR(5)  NOT NULL UNIQUE,
    airline_name  VARCHAR(100) NOT NULL
);

-- ============================================================
-- DIM_AIRPORTS
-- Plays two roles: departure airport and arrival airport
-- ============================================================
CREATE TABLE dim_airports (
    airport_id    SERIAL       PRIMARY KEY,
    iata_code     VARCHAR(5)   NOT NULL UNIQUE,
    airport_name  VARCHAR(150) NOT NULL,
    city          VARCHAR(100),
    state         VARCHAR(50),
    country       VARCHAR(50),
    latitude      FLOAT,
    longitude     FLOAT
);

-- ============================================================
-- FACT_FLIGHTS (central fact table)
-- ============================================================
CREATE TABLE fact_flights (
    flight_id        SERIAL   PRIMARY KEY,

    -- Foreign keys to dimension tables
    date_id          INTEGER  NOT NULL REFERENCES dim_date(date_id),
    airport_dep_id   INTEGER  NOT NULL REFERENCES dim_airports(airport_id),
    airport_arr_id   INTEGER  NOT NULL REFERENCES dim_airports(airport_id),
    airline_id       INTEGER  NOT NULL REFERENCES dim_airlines(airline_id),

    -- Additive measures
    departure_delay  FLOAT,   -- minutes (negative = early departure)
    arrival_delay    FLOAT,   -- minutes (negative = early arrival)
    distance         FLOAT,   -- great-circle distance in miles
    air_time         FLOAT,   -- wheels-off to wheels-on in minutes
    weather_delay    FLOAT,   -- delay attributable to weather (min)
    airline_delay    FLOAT,   -- delay attributable to airline (min)

    -- Semi-additive measure
    cancelled        INTEGER  NOT NULL DEFAULT 0 CHECK (cancelled IN (0, 1)),

    -- Count measure
    nb_vols          INTEGER  NOT NULL DEFAULT 1
);

-- ============================================================
-- Indexes for common OLAP query patterns
-- ============================================================
CREATE INDEX idx_fact_date       ON fact_flights(date_id);
CREATE INDEX idx_fact_dep        ON fact_flights(airport_dep_id);
CREATE INDEX idx_fact_arr        ON fact_flights(airport_arr_id);
CREATE INDEX idx_fact_airline    ON fact_flights(airline_id);
CREATE INDEX idx_fact_cancelled  ON fact_flights(cancelled);
