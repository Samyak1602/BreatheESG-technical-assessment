# Data Sources & Ingestion Boundaries

This document defines the scope of physical reality handled by the ingestion platform. Each raw data source is mapped to its boundaries, structures, and emissions scope categorization.

---

## Source 1: SAP (Fuel & Procurement Exports)

* **Medium**: Flat file exports (typically CSV or TSV) dumped from ERP tables.
* **Scope**: Scope 1 (Direct Emissions from stationary and mobile combustion) and Scope 3 (Purchased goods and services).
* **Boundaries & Subset of Reality**:
  - Fuel purchasing: Tracks purchases of bulk diesel and natural gas for facility generators and company-owned vehicles.
  - Stationary combustion: Restricts reality to volume-based fuel quantities (e.g. Gallons of Diesel, Therms of Natural Gas) and cost metrics.
  - **Sample Schema Boundary**:
    - `invoice_id` (Unique ERP invoice reference)
    - `fuel_type` (e.g., "DIESEL", "NATURAL_GAS")
    - `quantity` (Decimal value representing volume purchased)
    - `unit` (e.g., "GAL", "THERM")
    - `cost` (Currency amount in USD)
    - `facility_code` (Maps to facility entity)
    - `transaction_date` (ERP booking date)

---

## Source 2: Utility (Electricity Portal CSV Exports)

* **Medium**: Monthly billing CSV exports downloaded from local utility portals (e.g. PG&E, Duke Energy).
* **Scope**: Scope 2 (Indirect Emissions from purchased electricity, steam, heating, or cooling).
* **Boundaries & Subset of Reality**:
  - Restricts reality to metered utility consumption at the facility meter level.
  - Focuses strictly on Active Energy Consumption (kWh) and reactive power metrics (kVARh) if needed, ignoring detailed smart meter sub-hourly interval spikes (which are out-of-scope for compliance carbon accounting).
  - **Sample Schema Boundary**:
    - `account_number` (Utility account reference)
    - `meter_number` (Physical facility meter identifier)
    - `billing_start_date` (Date energy consumption cycle started)
    - `billing_end_date` (Date energy consumption cycle ended)
    - `usage_kwh` (Total active electrical energy consumed)
    - `peak_demand_kw` (Maximum power drawn during the cycle)
    - `total_charges` (Billing cost in USD)

---

## Source 3: Navan (Corporate Travel API Integration)

* **Medium**: Asynchronous REST API JSON response payloads from the Navan (formerly TripActions) platform.
* **Scope**: Scope 3 (Business Travel - Category 6).
* **Boundaries & Subset of Reality**:
  - Captures corporate-booked flights, hotel stays, rail travel, and car rentals.
  - Restricts flight reality to origin/destination airport codes (for geodesic distance-based radiative forcing calculations) and cabin class (Economy, Business, First).
  - Restricts hotel reality to room-nights and regional location.
  - **Sample Schema Boundary**:
    - `booking_id` (Navan platform booking reference)
    - `traveler_email` (Identifier of traveler)
    - `travel_type` (e.g., "FLIGHT", "HOTEL", "RAIL", "CAR")
    - `flight_segments` (Array of objects detailing departure/arrival airports, e.g. `["SFO", "JFK"]`, cabin class, and distance)
    - `hotel_nights` (Number of nights stayed)
    - `hotel_country` (Country code of the property)
    - `booking_date` (Date transaction took place)
    - `carbon_kg_est` (Navan-calculated estimated carbon footprint for secondary validation)
