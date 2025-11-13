# Implementation Plan: FastMCP 2.13.0 OAuth Persistence

**Branch**: `001-fastmcp-oauth-persistence` | **Date**: 2025-11-06 | **Spec**: [spec.md](spec.md)

## Summary

Upgrade FastMCP from 2.12.5 to 2.13.0 and implement persistent OAuth client storage using PostgreSQL with Fernet encryption. This solves the "Client Not Registered" issue where ChatGPT users must re-authenticate after every Cloud Run deployment.

**Technical Approach**: Use FastMCP 2.13.0's official `client_storage` parameter with PostgreSQL-backed AsyncKeyValue implementation, wrapped with FernetEncryptionWrapper for transparent encryption.

## Technical Context

**Language/Version**: Python 3.11+ (Cloud Run compatibility)
**Primary Dependencies**: FastMCP 2.13.0, py-key-value-aio 0.2.8+, cryptography 41.0.0+
**Storage**: Cloud SQL PostgreSQL with existing `oauth_clients` table
**Testing**: pytest with pytest-asyncio
**Target Platform**: Google Cloud Run (Linux containers)
**Project Type**: Single web application (MCP server)
**Performance Goals**: OAuth lookup <50ms, registration <100ms, startup <2s overhead
**Constraints**: Zero breaking changes, backward compatible, encryption key in Secret Manager
**Scale/Scope**: <100 OAuth clients, ~100KB storage, multiple deployments per day

## Constitution Check

✅ **PASS** - All gates satisfied

**I. Spec-First**: ✅ spec.md, plan.md, research.md, data-model.md, quickstart.md complete
**II. Test-First**: ✅ Tests planned for Phase 2
**III. Async-Safe**: ✅ AsyncKeyValue protocol is fully async
**IV. Security**: ✅ Fernet encryption, Secret Manager, IAM auth
**V. Operational Simplicity**: ✅ Standard libraries, minimal changes

## Project Structure

### Documentation
```
specs/001-fastmcp-oauth-persistence/
├── spec.md ✅          research.md ✅          data-model.md ✅
├── plan.md ✅          quickstart.md ✅        checklists/requirements.md ✅
```

### Source Code
```
src/
├── server.py ⚠️                   # Add client_storage parameter
├── auth/
│   ├── postgres_storage.py ⚠️    # Fix delete() return type
│   └── oauth_storage.py ➕        # New: encryption key helper

tests/
├── unit/test_postgres_kv_storage.py ➕
├── integration/test_oauth_persistence.py ➕
└── test_oauth_config_tdd.py ⚠️

pyproject.toml ⚠️                  # FastMCP 2.13.0, py-key-value-aio
```

## Design Complete (Phase 0 & 1)

✅ **research.md**: AsyncKeyValue protocol, FastMCP 2.13.0 changes, encryption approach
✅ **data-model.md**: OAuth client entity, database schema, data flows
✅ **quickstart.md**: 8-step implementation guide (30-45 minutes)

## Next Steps

Run `/speckit.tasks` to generate dependency-ordered implementation tasks.

## Success Criteria

- SC-001: 7-day continuous auth without re-authentication
- SC-002: 100% OAuth client survival across restarts
- SC-003: Zero "Client Not Registered" errors
- SC-004: Encrypted secrets in database
- SC-005: <2s startup time increase
- SC-006: <10s auth flow completion
