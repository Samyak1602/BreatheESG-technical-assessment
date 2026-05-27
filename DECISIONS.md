# Architectural Decisions Log

This document records the foundational architectural decisions for the BreatheESG platform.

## DB-01: Persistent Storage Layer
* **Decision**: Use **PostgreSQL** as the single source of truth for persistent storage.
* **Rationale**: 
  - Over SQLite: ESG data ingestion involves concurrent updates, audit logs, and complex validation queries. PostgreSQL provides robust ACID compliance, transactional integrity, and scales to handle massive data tables.
  - Over Document DBs (e.g. MongoDB): ESG reporting schemas must be strictly structured, highly normalized, and audited. Relational integrity is vital for tracking audit trails and mapping normalized metrics to standards.
* **Configuration**: Database parameters are injected via standard environment variables (`DATABASE_URL` or individual host/port/creds).

## FE-01: Frontend Scaffolding
* **Decision**: Use **Vite** for React frontend bootstrapping and development tooling.
* **Rationale**: 
  - Over Create React App (CRA): CRA is deprecated and slow. Vite provides near-instant hot module replacement (HMR), extremely fast build times using Esbuild, and clean project configuration without ejecting.
  - Over Next.js: While Next.js is powerful, the platform's core dashboard focuses on heavy client-side interactive state (grid rendering, live flagging, bulk editing) where client-side SPA architecture is extremely clean and performs excellently without server-side rendering complexity.

## PIPE-01: Normalizer Pipeline Ingestion Rules & Heuristics

To handle messy incoming data streams asynchronously and defensively, the normalizer resolves specific ambiguities through standard architectural rules.

### 1. Handling Missing & Non-Standard Units
* **Heuristic**: Unit parsing is case-insensitive.
* **Fallback Strategy**:
  - **SAP**: If the unit is missing, we raise a parse error, setting `RawRow` status to `FAILED`. If a unit is present but unrecognized (not `GAL`, `THERM`, `L`, `LITER`), we process the quantity as-is, but flag the normalized row with a `UNSUPPORTED_UNIT` warning `DataIssue`. Liter conversion (`L` or `LITER`) to gallons (`GAL`) is handled automatically for diesel fuel (`qty * 0.264172`).
  - **Utility**: We default to `KWH` if the unit is omitted. If the unit is `MWH`, we convert it to `KWH` (`qty * 1000`). Other units trigger an `UNSUPPORTED_UNIT` warning.
  - **Navan Travel**: Flights and Rail default to `KM` (converting from miles to km if miles are specified). Hotels strictly enforce `NIGHTS` as the raw unit.

### 2. Dropped & Ignored Fields from Raw Payloads
* **Dropped Cost/Financial Fields**: Financial costs (e.g. `kosten` in SAP, `charges` in Utility) are preserved in the immutable `RawRow` JSONB payload for reconciliation but completely ignored by the emission calculation engine. ESG compliance standards strictly prohibit calculating emissions based on highly volatile currency pricing.
* **Ignored Metadata**: Secondary transit descriptions (e.g., airline carrier, class subclasses, travelers' names) are kept in raw JSON storage but skipped for carbon metrics calculations.

### 3. Static Emission Factor (EF) Mapping & Heuristics
We leveraged standardized EPA and DEFRA benchmarks for calculations:
* **Diesel**: `10.18` kgCO2e per Gallon (Scope 1).
* **Natural Gas**: `5.3` kgCO2e per Therm (Scope 1).
* **Electricity**: `0.385` kgCO2e per kWh (Scope 2 - Location-based standard grid average).
* **Flights**: Dynamic categorization based on travel length (geodesic proxy):
  - **Short-haul (< 500 km)**: `0.25` kgCO2e/km (capturing high-burn take-off profiles).
  - **Long-haul (>= 500 km)**: `0.15` kgCO2e/km (capturing cruise-level efficiencies).
* **Hotel Stays**: `15.0` kgCO2e per Room-Night (Scope 3).
* **Rail Travel**: `0.04` kgCO2e per km (Scope 3).
* **General Unmapped Goods/Services**: Defaults to a fallback of `1.2` kgCO2e per Unit (Scope 3) and automatically flags a warning.

