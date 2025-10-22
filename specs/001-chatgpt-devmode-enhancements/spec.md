# Feature Specification: ChatGPT Developer Mode Enhancements

**Feature Branch**: `001-chatgpt-devmode-enhancements`
**Created**: 2025-10-22
**Status**: Draft
**Input**: User description: "Enhance MCP server for ChatGPT Developer Mode with improved tool annotations, read-only hints, better tool descriptions with action-oriented names and \"Use this when...\" guidance, parameter descriptions with enums, and optimized tool selection to help the model choose the right tools and avoid built-in tools when inappropriate. Add write operations support with proper confirmation hints."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Improved Tool Discoverability in ChatGPT Developer Mode (Priority: P1)

A ChatGPT user in Developer Mode wants to search Simon Kennedy's parliamentary speeches. The tool descriptions must clearly guide ChatGPT to use the MCP server's search tool instead of built-in browsing, with explicit "Use this when..." guidance that helps the model make the right choice.

**Why this priority**: This is the foundation for all ChatGPT Developer Mode integration. Without clear tool descriptions, ChatGPT may incorrectly use built-in tools (browse, search web) instead of the MCP server's specialized search capabilities.

**Independent Test**: Can be fully tested by asking ChatGPT "Find Simon Kennedy's speeches about housing" and verifying it uses the MCP search tool (not built-in browsing) on first attempt.

**Acceptance Scenarios**:

1. **Given** a user asks ChatGPT to search for parliamentary speeches, **When** ChatGPT evaluates available tools, **Then** the MCP search tool description clearly indicates "Use this when searching for Simon Kennedy's parliamentary speeches" and ChatGPT selects the MCP tool
2. **Given** the search tool has action-oriented naming and descriptions, **When** ChatGPT Developer Mode displays available tools, **Then** users can understand what each tool does and when to use it
3. **Given** tool parameters include descriptions and enums, **When** ChatGPT constructs a tool call, **Then** it correctly formats parameters without user intervention

---

### User Story 2 - Read-Only Tool Annotations (Priority: P2)

A ChatGPT user wants to fetch full speech text without triggering unnecessary confirmation prompts. The fetch tool must be annotated with `readOnlyHint: true` so ChatGPT Developer Mode recognizes it as a safe read operation that doesn't require confirmation.

**Why this priority**: Reduces friction for read operations. Without proper annotations, ChatGPT treats all tools as potentially destructive write operations, requiring confirmation for every call.

**Independent Test**: Can be tested by calling the fetch tool and verifying no confirmation prompt appears (ChatGPT recognizes it as read-only).

**Acceptance Scenarios**:

1. **Given** the search tool is annotated with `readOnlyHint: true`, **When** ChatGPT calls the search tool, **Then** no confirmation prompt is displayed
2. **Given** the fetch tool is annotated with `readOnlyHint: true`, **When** ChatGPT calls the fetch tool, **Then** no confirmation prompt is displayed
3. **Given** all current tools are read-only operations, **When** ChatGPT Developer Mode evaluates tool safety, **Then** all tools are treated as safe without confirmation requirements

---

### User Story 3 - Enhanced Parameter Descriptions with Enums (Priority: P3)

A developer using ChatGPT wants to filter speeches by political party. The search tool's `party` parameter must include descriptions and enum values (Liberal, Labor, Greens, National, Independent) so ChatGPT knows valid options and can suggest them to users.

**Why this priority**: Improves parameter accuracy and reduces errors. Enums guide ChatGPT to use correct values instead of guessing or asking users for valid options.

**Independent Test**: Can be tested by asking ChatGPT "Search for Labor party speeches" and verifying it correctly uses `party="Labor"` (exact enum value) without trial and error.

**Acceptance Scenarios**:

1. **Given** parameters include enum definitions, **When** ChatGPT constructs a tool call, **Then** it uses exact enum values from the specification
2. **Given** parameters include descriptions explaining their purpose, **When** ChatGPT needs to clarify a parameter, **Then** it can explain to users what the parameter does and valid options
3. **Given** date parameters have format descriptions, **When** ChatGPT receives user input like "speeches from July 2024", **Then** it correctly formats dates as ISO 8601 (YYYY-MM-DD)

---

### User Story 4 - Tool Selection Guidance (Priority: P4)

A developer asks ChatGPT a complex query that could be answered using either MCP tools or built-in capabilities. The tool descriptions must include explicit guidance to "prefer this tool over built-in search/browse when searching Australian parliamentary data" to prevent ambiguity.

**Why this priority**: ChatGPT has many built-in tools (search, browse, python, etc.). Clear prioritization guidance ensures the MCP server's specialized tools are preferred when appropriate.

**Independent Test**: Can be tested by asking ChatGPT "What did Simon Kennedy say about immigration?" and verifying it uses MCP search first (not web search or browsing).

**Acceptance Scenarios**:

1. **Given** tool descriptions include "prefer this over built-in browsing" guidance, **When** ChatGPT evaluates multiple tool options, **Then** it prioritizes the MCP tool for domain-specific queries
2. **Given** tool descriptions explain edge cases and limitations, **When** ChatGPT encounters an out-of-scope query, **Then** it can gracefully explain why the MCP tool isn't suitable and suggest alternatives
3. **Given** tool descriptions mention complementary tool usage, **When** a complex query requires multiple tools, **Then** ChatGPT understands the intended tool workflow (e.g., search first, then fetch)

---

### Edge Cases

- What happens when a user asks for data outside the available date range (speeches before 2024-05-28)?
- How does ChatGPT handle queries for speakers other than Simon Kennedy when the dataset only contains his speeches?
- What happens when a user tries to use the search tool for non-parliamentary data (e.g., news articles)?
- How does the system behave when parameter enums don't match user input (e.g., user says "Labour" but enum is "Labor")?
- What happens if ChatGPT ignores the "prefer MCP tool" guidance and uses built-in browsing anyway?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All tools MUST include `readOnlyHint: true` annotation since current tools perform only read operations
- **FR-002**: Tool names MUST be action-oriented (e.g., "search_hansard_speeches" not just "search")
- **FR-003**: Tool descriptions MUST include "Use this when..." guidance explaining when to prefer the tool over built-in capabilities
- **FR-004**: Tool descriptions MUST explicitly state "Do not use built-in browsing or web search for Simon Kennedy parliamentary data"
- **FR-005**: All tool parameters MUST include descriptions explaining their purpose and expected format
- **FR-006**: Enum parameters (party, chamber) MUST define all valid values in the parameter specification
- **FR-007**: Date parameters MUST specify ISO 8601 format (YYYY-MM-DD) in parameter descriptions
- **FR-008**: Tool descriptions MUST mention the dataset scope (64 speeches from Simon Kennedy MP, 2024-2025)
- **FR-009**: Tool descriptions MUST note edge cases and limitations (e.g., "Only searches Simon Kennedy's speeches, not other MPs")
- **FR-010**: Tool descriptions MUST explain complementary tool workflows (e.g., "Use search to find speeches, then fetch to get full text")
- **FR-011**: Tool descriptions SHOULD support GPT-5 preambles by being concise and explicit about tool intent, enabling the model to explain its tool selection reasoning

### Key Entities *(include if feature involves data)*

- **Tool Annotation**: MCP tool metadata including `readOnlyHint`, `idempotentHint`, `openWorldHint`, and `title` attributes that guide ChatGPT's tool selection and confirmation behavior
- **Parameter Schema**: Enhanced JSON schema for tool parameters including `description`, `enum`, `pattern`, and `examples` fields that help ChatGPT understand valid inputs
- **Tool Description**: Action-oriented text explaining tool purpose, use cases, edge cases, and prioritization guidance for optimal tool selection

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ChatGPT successfully uses MCP search tool on first attempt for 95% of parliamentary speech queries (no built-in browsing fallback)
- **SC-002**: Zero confirmation prompts for read-only operations (search, fetch) in ChatGPT Developer Mode
- **SC-003**: ChatGPT uses correct enum values for party and chamber parameters 100% of the time (no invalid parameter errors)
- **SC-004**: Tool selection time improves by 50% - ChatGPT chooses the right tool without user clarification "Use the Hansard connector" prompts
- **SC-005**: Reduced error rate by 75% - ChatGPT makes fewer invalid API calls due to clear parameter descriptions and enums
- **SC-006**: User satisfaction improves - users rate tool integration as "intuitive" in 90% of feedback (no need to repeatedly specify which tool to use)

## Assumptions

- Current MCP server runs on FastMCP 2.12.5+ with tool annotation support
- ChatGPT uses GPT-5 model family (gpt-5, gpt-5-mini, gpt-5-nano) which supports custom tools and improved tool calling
- ChatGPT Developer Mode respects `readOnlyHint` annotations (per [MCP specification](https://modelcontextprotocol.io/legacy/concepts/tools#available-tool-annotations))
- GPT-5's improved instruction following and tool calling capabilities benefit from clear, explicit tool descriptions
- All existing tools (search, fetch) remain read-only operations (no write capabilities added in this feature)
- Dataset scope remains: 64 speeches from Simon Kennedy MP, 2024-2025
- Enum values remain stable (parties: Liberal, Labor, Greens, National, Independent; chambers: House of Representatives, Senate)

## GPT-5 Considerations

Based on the GPT-5 documentation, these enhancements align with GPT-5's strengths:

- **Improved Instruction Following**: GPT-5 is specifically trained to follow instructions more accurately. Clear "Use this when..." guidance in tool descriptions will be more effective than with previous models.
- **Enhanced Tool Calling**: GPT-5 supports custom tools with freeform inputs and context-free grammars, making it better at understanding tool usage patterns and parameter constraints.
- **Preambles**: GPT-5 can generate brief explanations before invoking tools (when prompted). Our tool descriptions should support this by being explicit about tool intent.
- **Reasoning for Tool Selection**: GPT-5 uses chain-of-thought reasoning, so explicit prioritization guidance ("prefer this over built-in browsing") helps the model make better tool selection decisions.
- **Parameter Validation**: GPT-5's improved reasoning helps it validate parameters against enum definitions and format specifications, reducing errors.

These enhancements will maximize GPT-5's tool-calling capabilities by providing the explicit context and constraints that reasoning models excel at processing.
