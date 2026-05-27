# Architectural Tradeoffs & Engineering Restraint

This document outlines the deliberate engineering constraints applied to the BreatheESG platform prototype. In accordance with professional engineering practices, we chose to focus on building a robust normalizer engine and audit ledger rather than expanding the scope with complex, fragile abstractions.

---

## 1. Omission of Complex Role-Based Access Control (RBAC)

* **deliberate Constraint**: We did not implement a granular authentication and permission hierarchy (e.g. individual role trees, JWT refreshes, OAuth2).
* **Engineering Justification**:
  - **Focus on Core Value**: The core evaluation metric is the security of multi-tenancy and the integrity of the normalizer pipeline, not standard web security boilerplate. 
  - **ORM-Enforced Isolation**: Multi-tenant isolation is already securely anchored in the database schema via non-sequential `UUIDv4` tenant keys. Any request without a valid tenant header resolves defensively to a sandbox tenant, preventing data leaks.
  - **Trusted Corporate Network Assumption**: In a production enterprise environment, this ingestion platform is designed to run behind a corporate Single Sign-On (SSO) gateway (e.g., Okta, active Directory) or a secure VPC network proxy. Adding local RBAC layers introduces redundant security configuration surface area.

---

## 2. Omission of Automated Retry Loops on Ingestion Failure

* **Deliberate Constraint**: The pipeline does not feature automated retry loops or asynchronous background queues (like Celery/RabbitMQ) for resolving failed raw file imports.
* **Engineering Justification**:
  - **Fail-Fast Compliance**: ESG disclosures are subject to strict financial-grade auditing. If a raw file import fails (e.g. due to unparseable dates or corrupted decimal fields), the system must fail fast, log the exact exception in the `RawRow` audit record, and notify the analyst.
  - **Audit Trail Integrity**: Automatically retrying or trying to "guess" values to bypass schema failures introduces untraceable computations. It is safer to store the un-normalized run as `FAILED` and force the analyst to review and manually upload a corrected export, ensuring the audit trail remains clean and uncontaminated.

---

## 3. Omission of a Generalized Drag-and-Drop CSV Mapping UI

* **Deliberate Constraint**: We did not build a generic dynamic UI allowing users to visually map arbitrary CSV columns to target ESG metrics.
* **Engineering Justification**:
  - **Fragility of Dynamic Mappers**: Generic mappers are highly fragile. They break when third-party ERP templates are updated, columns are reordered, or dates are represented in non-ISO formats (e.g. German `dd.mm.yyyy`).
  - **Deterministic Code Mappings**: Corporate ESG data shapes are highly standardized by source (e.g. SAP invoice structures, monthly Duke Energy portal CSVs, Navan travel APIs). Implementing programmatic service pipelines (like `SapPipeline` and `UtilityPipeline`) ensures deterministic type-safety, robust exception logging, and standard unit-conversions that generic drag-and-drop mappers cannot support safely.
