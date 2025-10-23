# Implementation Plan: Google Gemini CLI Integration

**Branch**: `009-gemini-cli-integration` | **Date**: 2025-10-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-gemini-cli-integration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature delivers comprehensive documentation and configuration templates for integrating the Hansard MCP server with Google Gemini CLI. The deliverables include:

- Setup guides for local STDIO transport (5-minute quickstart)
- Configuration templates for remote SSE/HTTP Cloud Run integration
- Verification test scenarios with sample commands
- Troubleshooting guide for common setup issues

This is a documentation-only feature with no code changes. The technical approach focuses on creating practical, copy-paste-ready configuration examples based on FastMCP's dual transport architecture.

## Technical Context

**Language/Version**: Markdown (documentation), JSON/YAML (configuration files)
**Primary Dependencies**: None (documentation-only feature)
**Storage**: N/A
**Testing**: Manual verification using provided test scenarios
**Target Platform**: Documentation for developers using Gemini CLI on Windows, macOS, Linux
**Project Type**: Documentation
**Performance Goals**: Users complete local setup in under 10 minutes
**Constraints**: Documentation must be under 5000 words per guide for clarity
**Scale/Scope**: 3 setup guides, 2 configuration templates, 3 test scenarios

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: PASSES - No constitution violations

**Analysis**:
- Documentation-only feature (no code, no authentication changes, no secrets)
- No new dependencies or infrastructure
- No impact on existing security model
- No complexity violations (single project, clear scope)

## Project Structure

### Documentation (this feature)

```
specs/009-gemini-cli-integration/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output - technical decisions
├── data-model.md        # Phase 1 output - config/test entities
├── quickstart.md        # Phase 1 output - 5-minute STDIO setup
├── contracts/           # Phase 1 output - example configs
│   ├── stdio-config.json        # Local STDIO configuration
│   ├── sse-config.json          # Remote SSE configuration
│   └── test-scenarios.json      # Verification test cases
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```
docs/
└── gemini-cli/          # New documentation directory
    ├── README.md        # Overview and navigation
    ├── local-setup.md   # STDIO transport setup guide
    ├── remote-setup.md  # SSE/HTTP Cloud Run setup guide
    ├── troubleshooting.md  # Common issues and solutions
    └── examples/        # Configuration examples
        ├── local-stdio-config.json
        ├── remote-sse-config.json
        └── test-commands.sh
```

**Structure Decision**: Documentation lives in new `docs/gemini-cli/` directory to separate user-facing guides from internal specs. Configuration examples are JSON format for consistency with Gemini CLI configuration files.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

N/A - No constitution violations

## Phase 0: Research (30 minutes)

**Objective**: Document technical decisions for Gemini CLI integration patterns

### Research Tasks

1. **Documentation Format and Structure** (5 min)
   - Review existing FastMCP documentation patterns
   - Analyze user-facing vs developer documentation styles
   - Decision: Markdown with code blocks for copy-paste

2. **Configuration File Format** (5 min)
   - Compare JSON vs YAML for Gemini CLI configs
   - Review Gemini CLI configuration documentation
   - Decision: JSON format (native Gemini CLI format)

3. **Testing Scenario Design** (10 min)
   - Define verification test structure (command, expected output, success criteria)
   - Identify 3 core test scenarios (discovery, search, fetch)
   - Decision: JSON test scenario format with shell command examples

4. **STDIO vs SSE Transport Setup Patterns** (5 min)
   - Document STDIO local server configuration approach
   - Document SSE remote Cloud Run endpoint configuration
   - Decision: Separate guides for each transport type

5. **Troubleshooting Guide Organization** (5 min)
   - Identify common error categories (connection, auth, version mismatch)
   - Define troubleshooting entry format (symptom, diagnosis, solution)
   - Decision: Categorized troubleshooting with diagnostic commands

**Output**: `research.md` with 5 technical decisions documented

## Phase 1: Design (60 minutes)

**Objective**: Create design artifacts and configuration templates

### Deliverables

1. **data-model.md** (15 min)
   - Configuration Profile entity (transport type, connection params, env vars)
   - Test Scenario entity (description, command, expected behavior)

2. **quickstart.md** (20 min)
   - Prerequisites section (Gemini CLI installation, version requirements)
   - 5-minute STDIO setup (copy-paste commands)
   - Verification steps (test commands with expected output)
   - Troubleshooting quick reference (3 common issues)

3. **contracts/stdio-config.json** (10 min)
   - Complete STDIO configuration example
   - Environment variables for local development
   - Comments explaining each parameter

4. **contracts/sse-config.json** (10 min)
   - Complete SSE configuration example
   - Cloud Run endpoint URL pattern
   - Authentication parameter placeholders

5. **contracts/test-scenarios.json** (5 min)
   - Test 1: Tool discovery verification
   - Test 2: Search query execution
   - Test 3: Speech fetch by ID

**Output**: 5 design artifacts in `specs/009-gemini-cli-integration/`

## Phase 2: Implementation (60 minutes)

**Objective**: Create user-facing documentation guides

**Note**: Implementation tasks will be defined in `tasks.md` using `/speckit.tasks` command. High-level scope:

- Create `docs/gemini-cli/` directory structure
- Write local-setup.md (STDIO guide)
- Write remote-setup.md (SSE guide)
- Write troubleshooting.md (common issues)
- Copy configuration examples from contracts/
- Create README.md navigation

## Time Estimates

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 0: Research | 30 min | research.md (5 decisions) |
| Phase 1: Design | 60 min | data-model.md, quickstart.md, 3 contract files |
| Phase 2: Implementation | 60 min | 4 documentation guides + examples |
| **Total** | **2.5 hours** | **9 files** |

## Dependencies

**Upstream**: None (documentation-only feature)
**Downstream**: None (optional user-facing documentation)
**Blockers**: None

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Gemini CLI config format changes | Medium | Version-pin documentation to Gemini CLI version |
| Cloud Run URL patterns evolve | Low | Use placeholder patterns with explanation |
| Authentication flow complexity | Medium | Provide both OAuth and development bypass examples |

## Success Metrics

- Users complete STDIO setup in under 10 minutes (SC-001)
- 90% success rate for SSE configuration from docs (SC-002)
- Troubleshooting resolves 80% of issues without support (SC-003)
- All test scenarios pass after correct setup (SC-004)
- Documentation clarity rated 4.0+ out of 5.0 (SC-005)

