Phase 2.9 — UI clean-up and user migration
- Remove all traces of the old dashboard (dashboard_unified) from active usage. The file has been deleted, references updated, and a short deprecation notice is included in README.
- Document user migration to Enhanced Dashboard and implement redirects to guide users to the new UI.
- Ensure there is a clear path for future deprecations and a plan to remove the old UI from the codebase.

Phase 2.10 — API contract (structure and docs)
- Introduce explicit Pydantic models for new endpoints:
  - /servers/{server_id}/export (AllServersExportResponse)
  - /servers/metrics/history (HistoryAllResponse)
  - /servers/{server_id}/uptime-timeline (UptimeTimelineResponse)
- Update docs/API.md with examples and response contracts for new endpoints.

Phase 3–4 (overview)
- Phase 3: Add tests for new endpoints, integrate tests into CI, and update architecture/docs.
- Phase 4: Push toward full asynchronous paths, consider PostgreSQL for scale, TLS/secrets management, and enhanced monitoring.
