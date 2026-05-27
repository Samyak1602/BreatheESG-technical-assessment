# ESG Data Ingestion Platform - Database Models

This document outlines the database schema design choices for the multi-tenant ESG data ingestion engine.

## Database Schema Diagram (Logical)

```mermaid
erDiagram
    Tenant ||--o{ DataSource : owns
    Tenant ||--o{ RawRow : owns
    Tenant ||--o{ NormRow : owns
    Tenant ||--o{ DataIssue : owns
    Tenant ||--o{ AuditTrail : owns

    DataSource ||--o{ RawRow : ingests
    DataSource ||--o{ NormRow : produces
    RawRow ||--o? NormRow : normalizes
    NormRow ||--o{ DataIssue : "has issues"
    NormRow ||--o{ AuditTrail : logs
```

---

## 1. Multi-Tenancy Architecture

We have adopted a **Shared Database, Shared Schema, Discriminator-Based** multi-tenancy model. 

### Implementation Details:
* Every core table (`DataSource`, `RawRow`, `NormRow`, `DataIssue`, `AuditTrail`) maintains a foreign key to the `Tenant` (Organization) model.
* Primary keys are generated using cryptographically secure, non-sequential **UUIDv4** keys (`uuid.uuid4`).

### Architectural Rationale:
1. **Security & Enforceability**: Sequential integer IDs (e.g. `1`, `2`, `3`) invite ID enumeration attacks. UUIDs guarantee that a malicious user cannot guess IDs of resources belonging to another tenant.
2. **Horizontal Scale**: Shared database and schema minimize operational overhead, allowing hundreds of tenants to be hosted on a single database cluster. Partitioning can be layered on top via PostgreSQL native declarative partitioning by `tenant_id` if single-tenant database sizes explode.
3. **Strict Query Isolation**: Row-level tenant isolation is enforced at the application/ORM level. Every single query hitting the database must filter explicitly by the active `tenant` context.

---

## 2. Audit Trail & Source-of-Truth Ledger

ESG reporting is subject to strict third-party financial-grade auditing (e.g., CSRD, SEC ESG disclosures). Data must be immutable, and every mutation must be traceable to a specific actor and calculation event.

### Implementation Details:
* **The `AuditTrail` Model**:
  - `action`: Tracks the exact event state change (`CREATE`, `UPDATE`, `APPROVE`, `FLAG`, `LOCK`).
  - `usr`: Stores a hard foreign key `PROTECT` reference to the active `django.contrib.auth.models.User` who triggered the event.
  - `old_val` and `new_val`: Leverage PostgreSQL JSONB columns to store the delta of changed fields.
* **Audit Locks**: Once a `NormRow` status is transitioned to `AUDITED`, application code locks the record. Any attempts to update or delete the row are strictly blocked at both the ORM level (overridden `save`/`delete` methods) and database triggers.

---

## 3. separation of `RawRow` and `NormRow`

Ingesting messy ESG data requires keeping an absolute raw, untampered historical record of what came from the source, completely separated from the standardized clean database state.

### Architectural Defense:

| Dimension | `RawRow` (JSONB) | `NormRow` (Relational Columns) |
| :--- | :--- | :--- |
| **Responsibility** | Raw ingestion payload, storage of messy raw schema, tracing import source errors. | Cleaned, validated, structured, scope-categorized records for carbon accounting engines. |
| **Mutability** | **100% Immutable**. Never modified once saved. | **Mutable** during analyst review (e.g., editing flag states, adjusting raw values, overriding factors). |
| **Database Type** | PostgreSQL `JSONB` for schema-less storage. | Structured PostgreSQL datatypes (`DecimalField`, `DateField`, `ForeignKey`). |

### Key Reasons for Separation:

1. **Messy, Schema-less Payloads**: Different sources (SAP flat files, Utility CSV exports, Navan API JSON) structure fuel and electricity data differently. Trying to store all varying raw formats directly in structural columns is impossible without hundreds of nullable fields. Storing the raw payload in a `JSONB` field preserves the exact data without schema limits.
2. **Defensive Reconciliation & Auditing**: If an auditor questions a carbon calculation 3 years from now, the system must prove *exactly* what the source system reported. Because `NormRow` values can be edited or transformed by conversion factors, the immutable `RawRow` remains the definitive source of truth to replay calculations.
3. **Asynchronous Pipelines**: Ingestion is asynchronous. A raw file upload creates `RawRow`s immediately (even if the file is corrupt or missing columns). The normalizer then runs in the background. If normalization fails, the `RawRow` is flagged as `FAILED` with an error message, but the system doesn't pollute the `NormRow` tables with corrupt or unparseable rows.
