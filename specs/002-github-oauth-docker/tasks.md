# Tasks: GitHub OAuth Authentication and Docker Deployment

**Input**: Design documents from `/specs/002-github-oauth-docker/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/, quickstart.md, research.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- Single project: `src/`, `tests/`, `deployment/` at repository root
- Paths assume existing FastMCP server structure from feature 001

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency management

- [X] T001 [P] Add redis-py dependency to pyproject.toml for OAuth token storage
- [X] T002 [P] Create deployment/ directory for Docker and infrastructure files
- [X] T003 [P] Create scripts/generate_secrets.py for generating JWT/encryption keys
- [X] T004 Update .env.example with OAuth and Redis configuration variables

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create deployment/.dockerignore to exclude .git, .env, specs/, docs/
- [X] T006 Create deployment/healthcheck.py with /health and /ready endpoints
- [X] T007 Create tests/integration/test_oauth_flow.py test fixture structure
- [X] T008 Create tests/integration/test_docker_container.py test fixture structure
- [X] T009 Install dependencies with uv sync to ensure redis-py is available

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Secure MCP Client Authentication (Priority: P1) 🎯 MVP

**Goal**: Enable GitHub OAuth authentication for MCP clients using FastMCP OAuth Proxy pattern

**Independent Test**:
1. Start server with OAuth enabled
2. Connect MCP client (Claude Desktop or MCP Inspector)
3. Verify unauthenticated requests are rejected
4. Complete OAuth flow and verify authenticated requests succeed

### Implementation for User Story 1

- [X] T010 [P] [US1] Update src/server.py to import GitHubProvider from fastmcp.server.auth.providers.github
- [X] T011 [P] [US1] Add OAuth configuration to FastMCP initialization in src/server.py with FASTMCP_SERVER_AUTH environment variable
- [X] T012 [US1] Configure GitHubProvider with client_id, client_secret, and base_url from environment variables in src/server.py
- [X] T013 [US1] Add conditional OAuth bypass for development (DANGEROUSLY_OMIT_AUTH) in src/server.py
- [X] T014 [US1] Update src/server.py to add authentication decorator to existing tools (search, fetch, dataset_stats)
- [X] T015 [US1] Implement scripts/generate_secrets.py to generate random JWT_SIGNING_KEY and TOKEN_ENCRYPTION_KEY
- [X] T016 [US1] Add logging for authentication events (successful/failed) in src/server.py
- [ ] T017 [US1] Test OAuth flow with MCP Inspector using quickstart.md Part 5.3 instructions
- [ ] T018 [US1] Verify unauthenticated requests return 401/403 status codes

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Production Deployment via Docker Container (Priority: P2)

**Goal**: Package application as Docker container for Google Cloud Run deployment

**Independent Test**:
1. Build Docker image locally with `docker build`
2. Run container with production environment variables
3. Verify server responds to health checks
4. Deploy to Cloud Run and verify domain accessibility

### Implementation for User Story 2

- [X] T019 [P] [US2] Create deployment/Dockerfile with multi-stage build (build + runtime stages)
- [X] T020 [P] [US2] Configure Dockerfile build stage with Python 3.13-slim and uv installation
- [X] T021 [US2] Configure Dockerfile runtime stage with non-root user (UID 1000)
- [X] T022 [US2] Add COPY commands for src/, scripts/, pyproject.toml, and uv.lock to Dockerfile
- [X] T023 [US2] Set EXPOSE 8080 and CMD ["python", "-m", "src.server"] in Dockerfile
- [X] T024 [US2] Add HEALTHCHECK instruction to Dockerfile using deployment/healthcheck.py
- [X] T025 [US2] Implement /health and /ready endpoints in src/server.py (custom routes)
- [X] T026 [US2] Implement /ready endpoint with database/Redis connectivity checks
- [X] T027 [US2] Create deployment/docker-compose.yml with Redis service and MCP server service
- [ ] T028 [US2] Test local Docker build with `docker build --tag hansard-mcp:latest .`
- [ ] T029 [US2] Test container startup with `docker run -p 8080:8080 --env-file .env.local hansard-mcp:latest`
- [ ] T030 [US2] Verify /health and /ready endpoints respond correctly via curl
- [ ] T031 [US2] Build and push image to GCR with `gcloud builds submit --tag gcr.io/$PROJECT_ID/hansard-mcp:latest`
- [ ] T032 [US2] Deploy to Cloud Run following quickstart.md Part 4.2 instructions
- [ ] T033 [US2] Verify Cloud Run deployment at https://mcp.simonkennedymp.com.au/health

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Environment-Based Configuration (Priority: P3)

**Goal**: Support flexible configuration via environment variables for dev/production

**Independent Test**:
1. Run server with different `.env` configurations (dev vs production)
2. Verify OAuth credentials are loaded from environment
3. Confirm database connections use environment variables
4. Validate no secrets are hardcoded in source code

### Implementation for User Story 3

- [ ] T034 [P] [US3] Update .env.example with FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID variable
- [ ] T035 [P] [US3] Update .env.example with FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET variable
- [ ] T036 [P] [US3] Update .env.example with FASTMCP_SERVER_AUTH_GITHUB_BASE_URL variable
- [ ] T037 [P] [US3] Update .env.example with JWT_SIGNING_KEY and TOKEN_ENCRYPTION_KEY (production)
- [ ] T038 [P] [US3] Update .env.example with REDIS_HOST and REDIS_PORT (production token storage)
- [ ] T039 [US3] Add environment variable validation in src/server.py startup (check required vars)
- [ ] T040 [US3] Store OAuth secrets in Google Secret Manager following quickstart.md Part 1.2
- [ ] T041 [US3] Grant Cloud Run service account access to secrets following quickstart.md Part 1.3
- [ ] T042 [US3] Update Cloud Run deployment with --set-secrets flags for OAuth credentials
- [ ] T043 [US3] Test local configuration with .env.local file (DANGEROUSLY_OMIT_AUTH=true)
- [ ] T044 [US3] Test production configuration with secrets from Secret Manager
- [ ] T045 [US3] Verify no secrets appear in logs or source code via grep audit

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Production OAuth Token Persistence (Priority: P4)

**Goal**: Enable persistent token storage via Redis for production deployments

**Independent Test**:
1. Create Redis instance in Cloud Memorystore
2. Configure server with REDIS_HOST and REDIS_PORT
3. Authenticate MCP client and obtain tokens
4. Restart server and verify tokens persist (client remains authenticated)

### Implementation for Production Token Persistence

- [ ] T046 [P] [US4] Create Redis instance in Cloud Memorystore following quickstart.md Part 6.1
- [ ] T047 [P] [US4] Add Redis client initialization in src/server.py for production mode
- [ ] T048 [US4] Configure GitHubProvider with client_storage=RedisStore in src/server.py
- [ ] T049 [US4] Implement token encryption using TOKEN_ENCRYPTION_KEY in src/server.py
- [ ] T050 [US4] Update Cloud Run deployment with REDIS_HOST and REDIS_PORT environment variables
- [ ] T051 [US4] Test token persistence by restarting Cloud Run service and verifying client authentication
- [ ] T052 [US4] Verify Redis storage patterns match data-model.md schema (oauth:client:*, oauth:token:*, oauth:transaction:*)

**Checkpoint**: Production OAuth token persistence is fully functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T053 [P] Add integration tests in tests/integration/test_oauth_flow.py for end-to-end authentication
- [ ] T054 [P] Add integration tests in tests/integration/test_docker_container.py for container health checks
- [ ] T055 Update CLAUDE.md with OAuth configuration and Docker deployment commands
- [ ] T056 Add monitoring alerts for OAuth failures and container health in Cloud Monitoring
- [ ] T057 Run quickstart.md validation from Part 1 through Part 6
- [ ] T058 Code cleanup: Remove any debug logging from OAuth implementation
- [ ] T059 Security audit: Verify JWT_SIGNING_KEY and TOKEN_ENCRYPTION_KEY are different secrets
- [ ] T060 Performance check: Verify authentication validation completes in <500ms

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P2): Can start after Foundational - No dependencies on US1 (but should integrate)
  - User Story 3 (P3): Can start after Foundational - Integrates with US1 and US2
  - Production Token Persistence (P4): Depends on US1 (OAuth working) and US3 (Redis config)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Integrates with US1/US2
- **Production Token Persistence (P4)**: Requires US1 complete (OAuth), benefits from US3 (config)

### Within Each User Story

- OAuth configuration (US1) before Docker integration (US2)
- Environment variables (US3) can be added in parallel with US1/US2 implementation
- Redis persistence (P4) requires OAuth working (US1)
- Health checks before Cloud Run deployment
- Secret Manager setup before production deployment

### Parallel Opportunities

- All Setup tasks (T001-T004) marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Within User Story 1: T010, T011, T015, T016 can run in parallel
- Within User Story 2: T019, T020, T027 can run in parallel
- Within User Story 3: T034-T038 (all .env updates) can run in parallel
- Within Production Persistence: T046, T047 can run in parallel

---

## Parallel Example: User Story 1 (OAuth Implementation)

```bash
# Launch all parallel OAuth configuration tasks together:
Task: "Update src/server.py to import GitHubProvider from fastmcp.server.auth.providers.github"
Task: "Add OAuth configuration to FastMCP initialization in src/server.py with FASTMCP_SERVER_AUTH environment variable"
Task: "Implement scripts/generate_secrets.py to generate random JWT_SIGNING_KEY and TOKEN_ENCRYPTION_KEY"
Task: "Add logging for authentication events (successful/failed) in src/server.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (OAuth Authentication)
4. **STOP and VALIDATE**: Test OAuth flow with MCP Inspector
5. Deploy with OAuth using DANGEROUSLY_OMIT_AUTH=false

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test OAuth independently → Deploy (MVP!)
3. Add User Story 2 → Test Docker container → Deploy to Cloud Run
4. Add User Story 3 → Test environment config → Production deployment
5. Add Production Token Persistence → Test Redis storage → Enable horizontal scaling
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (OAuth)
   - Developer B: User Story 2 (Docker)
   - Developer C: User Story 3 (Environment config)
3. Stories complete and integrate independently
4. Final integration: Production Token Persistence (requires all stories)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- OAuth Proxy pattern documentation: https://gofastmcp.com/servers/auth/oauth-proxy
- GitHub integration guide: https://gofastmcp.com/integrations/github
- Avoid: hardcoded secrets, same file conflicts, breaking existing RAG functionality
