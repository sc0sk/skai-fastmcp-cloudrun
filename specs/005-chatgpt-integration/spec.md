# Feature Specification: ChatGPT Developer Mode Integration

**Feature Branch**: `005-chatgpt-integration`
**Created**: 2025-10-23
**Status**: Draft
**Input**: User description: "Enable ChatGPT Developer Mode integration with enhanced tool descriptions, read-only annotations, and Deep Research Mode support for search and fetch tools"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Journalist Uses ChatGPT Chat Mode for Quick Speech Lookup (Priority: P1)

A journalist working on a story about housing policy asks ChatGPT: "What has Simon Kennedy said about affordable housing?" ChatGPT uses the search tool to find relevant speeches and displays excerpts immediately without confirmation prompts, allowing the journalist to quickly identify quotable material.

**Why this priority**: This is the most common use case and represents the minimum viable product. Without seamless search in Chat Mode, the integration provides no value over existing web search capabilities. The readOnlyHint annotation is essential for eliminating friction in the user experience.

**Independent Test**: Can be fully tested by asking ChatGPT a single question about Simon Kennedy's speeches and verifying (1) the MCP search tool is invoked without confirmation prompts, (2) results are displayed within 5 seconds, and (3) ChatGPT uses the MCP tool instead of built-in web search.

**Acceptance Scenarios**:

1. **Given** ChatGPT has the Hansard MCP connector enabled, **When** a user asks "What did Simon Kennedy say about immigration?", **Then** ChatGPT invokes search_hansard_speeches without displaying a confirmation prompt
2. **Given** the search tool returns 5 relevant speeches, **When** ChatGPT processes the results, **Then** it displays excerpts with speaker, date, and relevance information in a readable format
3. **Given** the user asks a follow-up question about a specific speech, **When** ChatGPT needs full text, **Then** it invokes fetch_hansard_speech (also without confirmation) and displays the complete speech
4. **Given** the search query matches no speeches, **When** ChatGPT receives an empty result set, **Then** it explains no matching speeches were found and suggests alternative search terms

---

### User Story 2 - Researcher Uses Deep Research Mode for Comprehensive Policy Analysis (Priority: P2)

A policy researcher asks ChatGPT in Deep Research Mode: "Analyze Simon Kennedy's positions on housing policy over the past year, including voting patterns and rhetorical strategies." ChatGPT systematically searches multiple keyword combinations, fetches relevant speeches, analyzes patterns, and produces a comprehensive report with proper Hansard citations.

**Why this priority**: Deep Research Mode represents the high-value use case that justifies the MCP integration investment. It demonstrates the tool's ability to support systematic research workflows that require multiple coordinated tool calls. This scenario validates that both search and fetch tools work together in an automated research pipeline.

**Independent Test**: Can be tested by requesting a comprehensive research task that requires 10+ tool invocations. Success means ChatGPT produces a structured report with citations, thematic analysis, and proper attribution without user intervention beyond the initial prompt.

**Acceptance Scenarios**:

1. **Given** ChatGPT is in Deep Research Mode with Hansard connector, **When** a user requests comprehensive analysis of a policy topic, **Then** ChatGPT makes 10+ search queries with varying keywords to ensure comprehensive coverage
2. **Given** search results identify 15 relevant speeches, **When** ChatGPT analyzes patterns, **Then** it fetches full text for the most relevant speeches and extracts direct quotations with proper Hansard references
3. **Given** ChatGPT has analyzed multiple speeches, **When** it generates the final report, **Then** the report includes a summary section, key themes, evolution over time, and a citations section with Hansard references
4. **Given** the research task spans a date range, **When** ChatGPT searches speeches, **Then** it uses start_date and end_date parameters to filter results chronologically
5. **Given** Deep Research Mode completes its analysis, **When** the user receives the report, **Then** they can verify all citations by clicking through to original Hansard references

---

### User Story 3 - New User Connects MCP Server via ChatGPT Settings (Priority: P3)

A developer or researcher new to MCP wants to connect the Hansard server to their ChatGPT account. They navigate to ChatGPT settings, select "Developer Mode", create a new connector, enter the Cloud Run URL, and verify the connection. Within 2 minutes, the Hansard search and fetch tools are available in their ChatGPT interface.

**Why this priority**: While essential for onboarding, this is a one-time setup task that happens before any actual tool usage. It's lower priority than the core usage scenarios, but it must be frictionless to drive adoption. Clear documentation and a working public endpoint are the primary requirements.

**Independent Test**: Can be tested by a new user with no prior MCP experience following written instructions to connect the server. Success means the connection succeeds on first attempt and tools appear in ChatGPT's tool list within 2 minutes.

**Acceptance Scenarios**:

1. **Given** a user has a ChatGPT Pro/Team/Enterprise subscription, **When** they navigate to Settings > Developer Mode > Add Connector, **Then** they see a form requesting Name and URL
2. **Given** the user enters "Hansard Parliamentary Speeches" as name and the Cloud Run URL, **When** they click "Trust this connector" and Save, **Then** ChatGPT verifies the endpoint is reachable and displays "Connected successfully"
3. **Given** the connector is saved, **When** the user starts a new chat, **Then** search_hansard_speeches and fetch_hansard_speech appear in the available tools list
4. **Given** the connection fails due to incorrect URL, **When** ChatGPT displays an error, **Then** the error message clearly indicates "Could not reach server at [URL]" and suggests checking the URL format
5. **Given** the user wants to disconnect the server later, **When** they navigate back to connector settings, **Then** they can edit or remove the connector without affecting other MCP servers

---

### Edge Cases

- What happens when the Cloud Run server is temporarily unreachable due to cold start delays (15-30 seconds)?
- How does ChatGPT handle queries for speakers other than Simon Kennedy when the dataset only contains his speeches?
- What happens if a user asks about speeches before 2024-05-28 (the earliest date in the dataset)?
- How does the system behave when ChatGPT receives rate limiting errors from Cloud Run (429 status)?
- What happens if a user provides a speech_id from external sources that doesn't exist in the database?
- How does ChatGPT handle partial parameter matches (e.g., "Labour Party" vs "Labor")?
- What happens if the user doesn't enable Developer Mode but tries to use MCP tools in regular ChatGPT?
- How does the system handle concurrent requests from multiple users to the same Cloud Run instance?
- What happens if ChatGPT ignores the "prefer MCP tool" guidance and uses web browsing despite clear tool descriptions?
- How does the system behave when vector search returns zero results but the query is valid?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The search tool MUST include a "Use this when..." description that explicitly guides ChatGPT to prefer it over built-in web search for Simon Kennedy parliamentary queries
- **FR-002**: The search tool MUST have readOnlyHint=True annotation to eliminate confirmation prompts in ChatGPT Developer Mode
- **FR-003**: The fetch tool MUST have readOnlyHint=True and idempotentHint=True annotations to indicate safe, repeatable operations
- **FR-004**: Tool parameter descriptions MUST specify enum values explicitly (party: Liberal, Labor, Greens, National, Independent; chamber: House of Representatives, Senate)
- **FR-005**: Date parameters (start_date, end_date) MUST specify ISO 8601 format (YYYY-MM-DD) in their descriptions with examples
- **FR-006**: Tool descriptions MUST explicitly state "Do not use built-in browsing or web search for Simon Kennedy parliamentary data"
- **FR-007**: The server MUST be accessible via a public HTTP endpoint (Cloud Run URL) without authentication for ChatGPT connector compatibility
- **FR-008**: Tool descriptions MUST mention dataset scope (64 speeches from Simon Kennedy MP, 2024-2025) and limitations (only Simon Kennedy's speeches)
- **FR-009**: The search tool description MUST explain the workflow pattern: "Use search to find speeches, then fetch to get full text"
- **FR-010**: Both tools MUST return structured JSON responses with consistent field names and types that ChatGPT can parse reliably
- **FR-011**: Tool descriptions MUST guide ChatGPT to use multiple search queries with different keywords in Deep Research Mode for comprehensive coverage
- **FR-012**: Error responses MUST include user-friendly messages that ChatGPT can relay to users (e.g., "Speech not found: [ID]")
- **FR-013**: The server MUST support ChatGPT's expected MCP protocol format (tools/list, tools/call endpoints via HTTP transport)
- **FR-014**: Tool descriptions MUST be concise (under 500 characters) while remaining explicit about use cases and limitations
- **FR-015**: Both tools MUST work identically in Chat Mode and Deep Research Mode without requiring mode-specific logic

### Key Entities

- **MCP Connector**: User-created configuration in ChatGPT settings containing (1) connector name, (2) server URL, (3) trust status (checkbox), and (4) connection verification state. Connectors are persistent across chat sessions and enable tool discovery.

- **Tool Metadata**: Structured information for each MCP tool including (1) name (search_hansard_speeches, fetch_hansard_speech), (2) description with "Use this when" guidance, (3) annotations (readOnlyHint, idempotentHint), (4) parameter schemas with enums and format specifications, and (5) workflow guidance for complementary tool usage.

- **Tool Invocation Context**: Runtime information during tool execution including (1) ChatGPT mode (Chat vs Deep Research), (2) conversation history, (3) user query intent, (4) previous tool results, and (5) error/retry state. This context influences how ChatGPT chains multiple tool calls.

- **Search Result**: Structured data returned by search_hansard_speeches containing (1) chunk excerpts (500 chars max), (2) relevance scores, (3) speech metadata (speaker, party, chamber, date), (4) speech_id for fetching full text, and (5) Hansard references for citations.

- **Speech Document**: Complete parliamentary speech returned by fetch_hansard_speech containing (1) full text, (2) comprehensive metadata (title, speaker, party, chamber, electorate, state), (3) Hansard reference, (4) date, (5) topic tags, and (6) word count.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can connect the Hansard MCP server to ChatGPT in under 2 minutes by entering the Cloud Run URL, with 95%+ success rate on first attempt
- **SC-002**: Search tool invocations complete without confirmation prompts in 100% of cases (readOnlyHint annotation recognized by ChatGPT)
- **SC-003**: Fetch tool invocations complete without confirmation prompts in 100% of cases (readOnlyHint + idempotentHint annotations recognized)
- **SC-004**: ChatGPT prefers MCP search tool over built-in web search for Simon Kennedy queries in 90%+ of test cases when appropriate tool descriptions are present
- **SC-005**: Tool invocations complete within 5 seconds for 95% of requests (including Cloud Run cold start scenarios)
- **SC-006**: Deep Research Mode produces comprehensive reports with 10+ tool invocations and proper Hansard citations in 100% of test cases
- **SC-007**: Zero authentication errors when ChatGPT connects to the public Cloud Run endpoint (no OAuth required for read-only access)
- **SC-008**: Users rate the tool integration as "intuitive" or "very intuitive" in 80%+ of feedback surveys
- **SC-009**: ChatGPT successfully uses correct enum values for party and chamber parameters in 95%+ of invocations (no invalid parameter errors)
- **SC-010**: Error handling is user-friendly: when errors occur, ChatGPT relays actionable messages to users in 100% of cases

## Dependencies

- **Existing MCP Tools**: search_hansard_speeches and fetch_hansard_speech tools already implemented with readOnlyHint annotations and enhanced descriptions
- **Cloud Run Deployment**: Public HTTP endpoint already deployed and accessible without authentication
- **FastMCP Framework**: FastMCP 2.12.5+ with support for tool annotations (readOnlyHint, idempotentHint, openWorldHint)
- **ChatGPT Subscription**: Users must have ChatGPT Pro, Team, or Enterprise subscription to access Developer Mode and MCP connectors
- **ChatGPT Developer Mode**: Users must explicitly enable Developer Mode in ChatGPT settings (disabled by default)
- **HTTP Transport**: MCP server must use HTTP transport (already configured) as ChatGPT does not support stdio transport
- **Vector Database**: Cloud SQL PostgreSQL with pgvector already populated with 64 Simon Kennedy speeches
- **Vertex AI Embeddings**: Gemini-embedding-001 model already configured for semantic search

## Assumptions

- ChatGPT's MCP connector implementation follows the Model Context Protocol specification for HTTP transport
- The readOnlyHint and idempotentHint annotations are respected by ChatGPT's tool execution layer (as documented in MCP specification)
- ChatGPT's tool selection logic prioritizes tools with explicit "Use this when" guidance over built-in capabilities
- The Cloud Run URL remains stable and does not change after users create their connectors
- Cold start delays on Cloud Run (15-30 seconds) are acceptable for the first request after idle periods
- Users understand that Developer Mode must be enabled to use MCP connectors
- The dataset scope (64 speeches, 2024-2025, Simon Kennedy only) is sufficient for demonstrating integration value
- ChatGPT can parse and display structured JSON responses from both tools without custom formatting
- Deep Research Mode automatically makes multiple tool calls without requiring user prompts like "use the Hansard connector"
- The public Cloud Run endpoint has sufficient rate limiting to handle multiple concurrent ChatGPT users without degradation
- Tool descriptions remain under 500 characters to ensure they're fully processed by ChatGPT's tool selection layer

## Out of Scope

- Custom authentication for ChatGPT users (using public read-only endpoint instead)
- Rate limiting implementation beyond Cloud Run's default quotas (rely on platform defaults)
- Prompt engineering guidance for ChatGPT users (focus on tool metadata, not conversation strategies)
- Integration with other LLM platforms beyond ChatGPT (Claude Desktop and Cursor already supported via different MCP transports)
- Real-time speech ingestion or automatic updates (dataset is static 64 speeches)
- Support for other MPs or parliamentary speakers beyond Simon Kennedy
- Custom error handling beyond standard MCP protocol error responses
- Analytics or usage tracking for ChatGPT tool invocations
- Caching strategies for repeated queries (rely on Cloud Run and database performance)
- Support for ChatGPT free tier users (Developer Mode requires paid subscription)
- Custom UI or formatting for search results in ChatGPT (rely on ChatGPT's default JSON rendering)
- Migration path for users upgrading from built-in web search to MCP tools

## Risks & Mitigations

### Risk 1: ChatGPT Prefers Built-in Tools Over MCP Tools
**Impact**: Users get generic web search results instead of authoritative Hansard data, defeating the purpose of the integration.

**Likelihood**: Medium - ChatGPT has strong built-in web search capabilities and may default to familiar tools.

**Mitigation**:
- Write explicit "Use this when" guidance in tool descriptions emphasizing parliamentary speech queries
- Include "Do not use built-in browsing" warnings in descriptions
- Test tool selection behavior with 20+ query variations to identify patterns where ChatGPT defaults to web search
- Iterate on description wording based on test results

### Risk 2: Deep Research Mode Rate Limits Exceed Cloud Run Quotas
**Impact**: Users receive 429 errors during comprehensive research tasks, making Deep Research Mode unusable.

**Likelihood**: Low - Cloud Run defaults allow 1000 requests/minute, Deep Research Mode makes 10-20 calls per session.

**Mitigation**:
- Monitor Cloud Run metrics during Deep Research Mode testing to identify actual usage patterns
- Configure Cloud Run auto-scaling to handle burst traffic (min 1, max 10 instances)
- Implement retry logic with exponential backoff if rate limits are encountered
- Document expected rate limits in connector setup guide

### Risk 3: Users Forget to Enable Developer Mode
**Impact**: Users cannot create MCP connectors and cannot access Hansard tools, leading to confusion and support requests.

**Likelihood**: High - Developer Mode is opt-in and not widely known outside developer communities.

**Mitigation**:
- Create clear setup documentation with screenshots showing Developer Mode toggle location
- Include "Prerequisites" section in documentation: ChatGPT Pro/Team/Enterprise + Developer Mode enabled
- Add troubleshooting section: "Tools not appearing? Check Developer Mode is enabled"
- Consider reaching out to early users with setup assistance

### Risk 4: Cold Start Delays Create Perception of Slow Tool Performance
**Impact**: First request after idle period takes 15-30 seconds, users perceive tools as unreliable or slow.

**Likelihood**: Medium - Cloud Run cold starts are inevitable for infrequently used services.

**Mitigation**:
- Configure Cloud Run min instances to 1 (keeps one instance warm)
- Implement health check endpoint that ChatGPT can ping to warm up instance
- Document expected cold start behavior in connector description
- Use lifespan management to pre-initialize database connections on startup

### Risk 5: Tool Descriptions Exceed ChatGPT's Context Window for Tool Selection
**Impact**: ChatGPT truncates or ignores parts of tool descriptions, missing critical "Use this when" guidance.

**Likelihood**: Low - Current descriptions are ~300 characters, well under typical context limits.

**Mitigation**:
- Keep tool descriptions concise (under 500 characters) while remaining explicit
- Prioritize most important guidance at the beginning of descriptions
- Test with minimal vs verbose descriptions to find optimal length
- Monitor tool selection accuracy metrics to detect degradation

### Risk 6: Users Provide Incorrect Cloud Run URL Format
**Impact**: Connector creation fails, users cannot complete setup, high support burden.

**Likelihood**: Medium - URL format errors are common (missing https://, trailing slashes, typos).

**Mitigation**:
- Provide exact URL in setup documentation with copy-paste formatting
- Include example URL format: https://hansard-mcp-XXXXXXX-uc.a.run.app
- Document common errors: "URL must start with https://", "Do not include /tools or other paths"
- ChatGPT's connector verification provides immediate feedback on URL errors

### Risk 7: Vector Search Returns Irrelevant Results Due to Query Phrasing
**Impact**: Users receive speeches that don't match their intent, leading to frustration and distrust of tool accuracy.

**Likelihood**: Medium - Semantic search is sensitive to query phrasing; some queries may not align well with speech content.

**Mitigation**:
- Tool description guides ChatGPT to try multiple phrasings in Deep Research Mode
- Search tool accepts natural language and uses Vertex AI embeddings for semantic matching
- Monitor relevance scores in search results to identify low-quality matches
- Document query phrasing tips: "housing policy", "affordable housing", "first home buyers" vs "houses"
