-- ============================================================
-- Reconciled Database Schema — 2015 U.S. Flight Data
-- University of Calabria — Data Analytics Project
-- Database: flight_reconciled
-- Corresponds to Section 2.2 (E/R Schema) of the report
-- ============================================================

DROP TABLE IF EXISTS flight;
DROP TABLE IF EXISTS airport;
DROP TABLE IF EXISTS airline;

-- ============================================================
-- AIRLINE
-- Source: airlines.csv (14 rows, columns: IATA_CODE, AIRLINE)
-- ============================================================
CREATE TABLE airline (
    iata_code    VARCHAR(5) PRIMARY KEY,
    airline_name VARCHAR(100) NOT NULL
);

-- ============================================================
-- AIRPORT
-- Source: airports.csv (322 rows, columns: IATA_CODE, AIRPORT, CITY,
--         STATE, COUNTRY, LATITUDE, LONGITUDE)
-- Note: 3 rows have NULL latitude/longitude (data quality note)
-- ============================================================
CREATE TABLE airport (
    iata_code    VARCHAR(5) PRIMARY KEY,
    airport_name VARCHAR(150) NOT NULL,
    city         VARCHAR(100),
    state        VARCHAR(50),
    country      VARCHAR(50),
    latitude     FLOAT,
    longitude    FLOAT
);

-- ============================================================
-- FLIGHT
-- Source: flights.csv (5,819,079 rows, 31 columns)
-- Column order matches the raw CSV exactly (lowercased).
-- No PK on purpose: the raw data has no natural unique key,
-- and FLIGHT_NUMBER is not unique across dates (see report 2.4.1).
-- A surrogate flight_id is added during ETL to the DW, not here.
-- ============================================================
CREATE TABLE flight (
    year                 INTEGER NOT NULL,
    month                INTEGER NOT NULL,
    day                  INTEGER NOT NULL,
    day_of_week          INTEGER NOT NULL,
    airline_code         VARCHAR(5) NOT NULL,
    flight_number        INTEGER,
    tail_number          VARCHAR(10),
    origin_airport       VARCHAR(5) NOT NULL,
    destination_airport  VARCHAR(5) NOT NULL,
    scheduled_departure  INTEGER,
    departure_time       FLOAT,
    departure_delay      FLOAT,
    taxi_out             FLOAT,
    wheels_off           FLOAT,
    scheduled_time       FLOAT,
    elapsed_time         FLOAT,
    air_time             FLOAT,
    distance             FLOAT,
    wheels_on            FLOAT,
    taxi_in              FLOAT,
    scheduled_arrival    INTEGER,
    arrival_time         FLOAT,
    arrival_delay        FLOAT,
    diverted             INTEGER NOT NULL DEFAULT 0,
    cancelled            INTEGER NOT NULL DEFAULT 0,
    cancellation_reason  VARCHAR(1),
    air_system_delay     FLOAT,
    security_delay       FLOAT,
    airline_delay        FLOAT,
    late_aircraft_delay  FLOAT,
    weather_delay        FLOAT
);

-- Foreign keys are NOT enforced at this stage on purpose:
-- the reconciled DB is a raw, faithful copy of the source CSVs
-- (Phase 2, step 1 of the checklist). FK validation and cleaning
-- (IATA code mismatches, etc.) happen during the ETL step that
-- populates the data warehouse (see star_schema.sql).

-- Indexes to speed up the ETL's chunked reads / lookups
CREATE INDEX idx_flight_airline ON flight(airline_code);
CREATE INDEX idx_flight_origin  ON flight(origin_airport);
CREATE INDEX idx_flight_dest    ON flight(destination_airport);
CREATE INDEX idx_flight_date    ON flight(year, month, day);
