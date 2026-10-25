# Implementation status and limitations

The present runnable slice includes frontend authentication/register UI, FastAPI registration/login, imported observation storage, dashboard summary, CSV ingestion, alerts with acknowledge/resolve, audit records, and transparent demand/capacity scenario arithmetic.

Not delivered: true role authorization gates for privileged routes; robust expiring session storage; registration verification/password reset; API provider connectors; Leaflet map; migration framework; ML training/inference; PDF reports; administered configuration pages; automated test suite; production infrastructure. The UI uses a single dashboard shell with navigation labels, and the Digital Twin explicitly shows a no-data placeholder. No simulated values are passed off as observations.

The local token implementation is a development shortcut and should be replaced before deployment. SQLite schema is created on startup (no Alembic migrations yet). CSV errors are surfaced for review; production ingestion should add stronger row-level diagnostics and duplicate/idempotency handling.
