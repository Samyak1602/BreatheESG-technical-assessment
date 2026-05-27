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
