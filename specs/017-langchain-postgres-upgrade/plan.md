# Implementation Plan: LangChain 1.0 with langchain-postgres

**Feature**: 016-langchain-postgres-upgrade
**Estimated Effort**: 8 days
**Risk Level**: Medium-High (data migration, production database changes)

## Phase Breakdown

### Phase 0: Development Setup (1 day)
**Goal**: Update dependencies and verify compatibility
**Deliverables**:
- Updated `pyproject.toml` with LangChain 1.0+ dependencies
- Successful `uv sync` with no conflicts
- Import verification in Python REPL

**Risks**: Dependency conflicts between packages
**Mitigation**: Test in isolated virtual environment first

---

### Phase 1: Cloud SQL Engine Factory (1 day)
**Goal**: Create SQLAlchemy engine with Cloud SQL IAM authentication
**Deliverables**:
- `src/storage/cloud_sql_engine.py` implementation
- Unit tests with mocked connector
- Verified connection string format (postgresql+psycopg://)

**Dependencies**: Phase 0 complete
**Risks**: IAM authentication configuration errors
**Mitigation**: Extensive debug logging, test against dev Cloud SQL

---

### Phase 2: Vector Store Adapter (1.5 days)
**Goal**: Wrap langchain-postgres in async interface
**Deliverables**:
- `src/storage/postgres_vector_store.py` implementation
- Async wrappers using asyncio.to_thread()
- Unit tests with mocked PGVector

**Dependencies**: Phase 1 complete
**Risks**: Async/sync boundary issues, thread pool exhaustion
**Mitigation**: Thorough async testing, proper thread pool configuration

---

### Phase 3: Backend Selection (0.5 days)
**Goal**: Implement feature flag for gradual rollout
**Deliverables**:
- Updated `src/storage/vector_store.py` with backend factory
- Updated `src/config.py` with VECTOR_BACKEND config
- Startup validation for backend selection

**Dependencies**: Phase 2 complete
**Risks**: Configuration errors causing wrong backend selection
**Mitigation**: Fail-fast validation, clear logging

---

### Phase 4: Integration Testing (1 day)
**Goal**: Verify end-to-end functionality with real Cloud SQL
**Deliverables**:
- `tests/integration/storage/test_postgres_integration.py`
- E2E tests for all MCP tools
- Comparison tests (legacy vs postgres backends)

**Dependencies**: Phase 3 complete
**Risks**: Dev Cloud SQL availability, IAM permission issues
**Mitigation**: Document Cloud SQL setup requirements, have fallback test data

---

### Phase 5: Migration Script (1 day)
**Goal**: Create production-ready migration tooling
**Deliverables**:
- `scripts/migrate_to_langchain_postgres.py` with --dry-run and --execute modes
- Batch processing with progress reporting
- Post-migration validation
- Migration procedure documentation

**Dependencies**: Phase 4 complete
**Risks**: Data loss, partial migration failures
**Mitigation**: Dry-run mode, transaction rollback, comprehensive validation

---

### Phase 6: Staging Deployment (1 day)
**Goal**: Validate in staging environment with real data
**Deliverables**:
- Staging deployment with VECTOR_BACKEND=legacy
- Successful staging migration
- Performance baseline measurements
- Staging E2E test results

**Dependencies**: Phase 5 complete
**Risks**: Staging migration failures, performance regressions
**Mitigation**: Database backups, rollback procedures, performance monitoring

---

### Phase 7: Production Rollout (1 day + monitoring)
**Goal**: Deploy to production with gradual rollout
**Deliverables**:
- Production Cloud SQL snapshot backup
- Successful production migration
- Gradual instance rollout (10% → 100%)
- Monitoring dashboards

**Dependencies**: Phase 6 complete, stakeholder approval
**Risks**: Production outage, data corruption, performance issues
**Mitigation**: Feature flag rollback, database snapshots, gradual rollout strategy

---

### Phase 8: Cleanup (1+ weeks later)
**Goal**: Remove legacy code after stable production operation
**Deliverables**:
- Removed VECTOR_BACKEND feature flag
- Removed langchain-google-cloud-sql-pg dependency
- Archived old hansard_speeches table
- Updated documentation

**Dependencies**: 1 week of stable production operation
**Risks**: Undiscovered edge cases requiring rollback
**Mitigation**: Extended monitoring period, keep backups

## Critical Path

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8
   1d       1d       1.5d      0.5d       1d        1d        1d        1d       later
```

**Total Implementation Time**: 8 days (excluding Phase 8 cleanup)
**Critical Path Items**: All phases are on critical path (sequential dependencies)

**Note**: Timeline accounts for sequential critical path execution. Tasks marked with [P] in tasks.md can be executed in parallel to reduce wall-clock time. Actual calendar time may be 5-6 days with effective parallelization (e.g., unit tests T006, T008, T010 can run concurrently after their dependencies complete).

## Resource Requirements

- **Developer**: Full-time for 8 days (implementation + testing)
- **DBA/Admin**: Part-time for Phases 5-7 (migration operations, ~4 hours)
- **DevOps**: Part-time for Phase 7 (monitoring setup, ~2 hours)
- **QA**: Part-time for Phases 4, 6 (testing, ~4 hours)

## Go/No-Go Checkpoints

**After Phase 4 (Integration Testing)**:
- ✓ All integration tests pass on dev environment
- ✓ Search results match between legacy and postgres backends
- ✓ IAM authentication works in dev
- ✗ Block: Any failing integration tests, IAM auth failures

**After Phase 6 (Staging Deployment)**:
- ✓ Staging migration completes successfully
- ✓ Performance within 10% of baseline
- ✓ Rollback procedure verified
- ✗ Block: Migration failures, >10% performance regression, rollback doesn't work

**Before Phase 7 (Production Rollout)**:
- ✓ Stakeholder approval obtained
- ✓ Maintenance window scheduled
- ✓ On-call engineer available
- ✓ Rollback procedures documented and tested
- ✗ Block: Any checkbox unchecked

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Migration script data loss | Low | Critical | Dry-run validation, transaction rollback, database snapshots |
| Performance regression >10% | Medium | High | Baseline measurements, gradual rollout, rollback flag |
| IAM authentication failures in prod | Low | High | Test in staging first, verify service account permissions |
| Dependency conflicts during install | Medium | Medium | Test in isolated environment, lock dependency versions |
| Async/sync threading issues | Medium | Medium | Comprehensive async testing, proper thread pool config |
| Partial migration failure | Medium | High | Checkpoint/resume capability, transaction management |
| Undetected edge cases in production | Low | Medium | Extended staging testing, gradual rollout, monitoring |

## Success Metrics

- **Technical**: Zero functional regressions, 100% data migration, P95 latency within 10%
- **Operational**: Zero rollbacks, <0.1% error rate, 7 days stable production
- **Business**: No user complaints, maintained SLA, no security incidents

## Rollback Procedures

**Immediate Rollback** (< 5 minutes):
1. Set `VECTOR_BACKEND=legacy` in Cloud Run environment variables
2. Redeploy all instances (rolling restart)
3. Verify legacy backend operational
4. Incident report and root cause analysis

**Full Rollback** (if migration compromised):
1. Immediate rollback (above)
2. Restore Cloud SQL from snapshot backup (if needed)
3. Revert code changes (git revert)
4. Remove new database tables (if created)
5. Extended testing before retry

## Communication Plan

**Stakeholders to Notify**:
- Product Owner (all phases)
- DevOps team (Phases 6-7)
- On-call engineers (Phase 7)
- End users (if maintenance window required)

**Communication Points**:
- Phase 6 start: "Staging deployment beginning"
- Phase 6 complete: "Staging successful, requesting production approval"
- Phase 7 start: "Production migration starting" (if maintenance window)
- Phase 7 complete: "Production migration successful, monitoring ongoing"
- Phase 8 start: "Legacy cleanup beginning"
