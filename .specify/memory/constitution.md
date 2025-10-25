# Spec-Driven Development Constitution (skai-fastmcp-cloudrun)

## Core Principles

### I. Spec-First (NON-NEGOTIABLE)
Every feature starts as a spec under `specs/<NNN>-<name>/` with, at minimum: `spec.md`, `plan.md`, and `tasks.md`. Implementation does not begin until these exist and are reviewed. Specs must define user stories, functional and non-functional requirements, acceptance criteria, risks, and a rollout/rollback plan.

### II. Test-First Quality Gates
All work must pass: (1) Build, (2) Lint/Typecheck, (3) Tests. For code changes, write or update minimal tests (unit, integration, or e2e) that fail before implementation and pass after. Green-before-done: do not merge with failing gates.

### III. Async-Safe, Contract-Driven Design
Public interfaces are stable contracts. Async services must not block the event loop; wrap sync libs using thread executors when necessary. Breaking contract changes require versioned rollouts or feature flags with explicit deprecation notes.

### IV. Security by Default
Credentials are never embedded. Cloud SQL uses IAM database authentication via the official connector (no password-based auth). Principle of least privilege for service accounts. Logs must avoid sensitive data.

### V. Operational Simplicity
Prefer standard, well-supported libraries. Keep configuration in environment variables with safe defaults. Add observability (structured logs, minimal metrics) for new components that affect production behavior.

## Technology Constraints

- Runtime: Python 3.11+ on Cloud Run
- Data: Cloud SQL PostgreSQL with `pgvector`
- Retrievers: LangChain 1.0+
- Vector Store: `langchain-postgres` with `psycopg` (psycopg3) via SQLAlchemy 2.x
- Connectivity: `google-cloud-sql-connector` with automatic IAM DB auth (no passwords)
- Embeddings: Vertex AI `text-embedding-005` (or successor), configured per environment

## Development Workflow

1) Author specs (`spec.md`, `plan.md`, `tasks.md`) → review
2) Initialize feature branch `NNN-<name>`; scaffold code and tests
3) Implement behind a feature flag when behavior changes are user-facing
4) Validate with unit + integration tests; capture performance baseline when relevant
5) Staged rollout: dev → staging → production with monitoring; maintain immediate rollback
6) Cleanup legacy code/flags after stability window

## Governance

- This constitution supersedes ad-hoc practices. Conflicts must be resolved by adjusting specs/plans/tasks to comply. Proposals to amend principles require an explicit "Constitution Update" PR describing rationale and migration impact.
- Code reviews must verify adherence to Spec-First, Quality Gates, Security constraints, and Tech constraints.

**Version**: 1.0.0 | **Ratified**: 2025-10-25 | **Last Amended**: 2025-10-25
