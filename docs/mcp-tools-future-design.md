# MCP Tool Suite for Hierarchical Hansard Analysis (Future Design)

**Status**: Design document for future implementation
**Current MVP**: `search_hansard` and `fetch_speech` only
**Last Updated**: 2025-10-23

---

## Overview

This document outlines a comprehensive MCP tool suite for political and communications analysis of Australian Hansard speeches. The tools are designed to work with hierarchical chunking (sentence/paragraph/speech levels) and leverage rich YAML frontmatter metadata (29 fields including entities, themes, political stance, communications utility).

## Tool Categories

### Category 1: **Search & Retrieval Tools** ✅ MVP PRIORITY

#### 1. `search_hansard` ✅ IMPLEMENT FIRST
**Purpose**: General semantic search across all levels
```python
@mcp.tool()
async def search_hansard(
    query: str,
    level: Literal["sentence", "paragraph", "speech", "all"] = "all",
    party: str | None = None,
    chamber: Literal["House of Representatives", "Senate"] | None = None,
    date_from: str | None = None,  # ISO format
    date_to: str | None = None,
    limit: int = 10
) -> list[dict]:
    """
    Search Hansard speeches by semantic similarity at any granularity level.

    Examples:
    - Find sentences: level="sentence" for quotes
    - Find arguments: level="paragraph" for policy positions
    - Find speeches: level="speech" for full context
    - Best matches: level="all" searches everything

    Returns hierarchical results with parent context.
    """
```

**Use Cases**:
- General research queries
- Topic exploration
- Cross-party comparison

---

#### 2. `fetch_speech` ✅ IMPLEMENT FIRST
**Purpose**: Get complete speech by ID
```python
@mcp.tool()
async def fetch_speech(
    speech_id: str,
    include_chunks: bool = False
) -> dict:
    """
    Retrieve a complete speech with all metadata.

    Args:
        speech_id: Unique speech identifier (e.g., "267506-2024-05-28-129006")
        include_chunks: If True, returns all paragraph/sentence chunks

    Returns:
        - full_text: Complete speech text
        - metadata: All 29 fields (speaker, party, entities, themes, etc.)
        - chunks: Optional hierarchical breakdown
    """
```

**Use Cases**:
- Full speech context for attribution
- Verifying quotes in context
- Deep-dive research

---

### Category 2: **Quote & Soundbite Tools** (Media Analysis)

#### 3. `extract_quotes`
**Purpose**: Find quotable sentences
```python
@mcp.tool()
async def extract_quotes(
    topic: str,
    party: str | None = None,
    speaker: str | None = None,
    soundbite_potential: Literal["high", "medium", "low"] | None = None,
    controversy_level: Literal["high", "medium", "low"] | None = None,
    date_from: str | None = None,
    limit: int = 20
) -> list[dict]:
    """
    Extract quotable sentences optimized for media use.

    Perfect for:
    - Journalists finding soundbites
    - Social media content creation
    - Quote attribution and fact-checking

    Returns:
        - quote: Exact sentence text
        - speaker: Full name
        - party: Political party
        - date: When spoken
        - soundbite_potential: high/medium/low
        - controversy_level: high/medium/low
        - context: Surrounding paragraph
        - speech_link: Full speech reference
    """
```

**Target Users**: Journalists, media teams, PR professionals

---

#### 4. `find_mentions`
**Purpose**: Find mentions of specific people, organizations, or legislation
```python
@mcp.tool()
async def find_mentions(
    entity: str,
    entity_type: Literal["people", "organizations", "places", "legislation"],
    level: Literal["sentence", "paragraph", "speech"] = "sentence",
    party: str | None = None,
    sentiment: Literal["positive", "negative", "neutral"] | None = None,
    limit: int = 15
) -> list[dict]:
    """
    Find all mentions of a specific entity (person, org, place, legislation).

    Examples:
    - "Scott Morrison" in entity_type="people"
    - "GST" in entity_type="legislation"
    - Sentiment analysis from key_mentions metadata

    Returns mentions with context and sentiment.
    """
```

**Target Users**: Fact-checkers, political analysts

---

### Category 3: **Policy Analysis Tools** (Political Research)

#### 5. `analyze_policy_position`
**Purpose**: Compare policy positions across parties/speakers
```python
@mcp.tool()
async def analyze_policy_position(
    policy_area: str,  # e.g., "housing-affordability", "climate-change"
    party: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 10
) -> dict:
    """
    Analyze policy positions on a specific topic.

    Returns:
        - arguments: Paragraph-level policy arguments
        - key_positions: Summary by party
        - evidence_cited: Statistics and sources referenced
        - rhetoric_intent: ceremonial/deliberative/forensic
        - themes: Associated themes and subthemes
    """
```

**Target Users**: Policy analysts, political scientists

---

#### 6. `compare_speakers`
**Purpose**: Compare positions between speakers
```python
@mcp.tool()
async def compare_speakers(
    speakers: list[str],  # ["Simon Kennedy", "Jane Smith"]
    topic: str,
    limit_per_speaker: int = 5
) -> dict:
    """
    Compare how different speakers address the same topic.

    Returns:
        - by_speaker: Arguments from each speaker
        - common_themes: Shared themes/concerns
        - differences: Contrasting positions
        - evidence_comparison: Different data sources cited
    """
```

**Target Users**: Political analysts, debate researchers

---

#### 7. `track_policy_evolution`
**Purpose**: Track how policy discussions evolve over time
```python
@mcp.tool()
async def track_policy_evolution(
    policy_area: str,
    speaker: str | None = None,
    party: str | None = None,
    date_from: str,
    date_to: str,
    group_by: Literal["month", "quarter", "year"] = "month"
) -> list[dict]:
    """
    Track how policy discussions change over time.

    Returns chronological analysis:
        - time_period: Date range
        - speech_count: Number of speeches
        - themes: Dominant themes in period
        - key_arguments: Main policy positions
        - sentiment_trend: How controversy/support changes
    """
```

**Target Users**: Political historians, trend analysts

---

### Category 4: **Thematic Analysis Tools** (Research)

#### 8. `explore_themes`
**Purpose**: Discover thematic patterns
```python
@mcp.tool()
async def explore_themes(
    theme: str | None = None,  # e.g., "housing-affordability"
    party: str | None = None,
    chamber: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 10
) -> dict:
    """
    Explore thematic patterns in speeches.

    If theme specified: Returns speeches on that theme
    If theme is None: Returns most common themes in dataset

    Returns:
        - theme: Primary theme
        - subthemes: Related subthemes
        - speeches: Relevant speeches
        - key_speakers: Who talks about this most
        - related_entities: Associated people/orgs/places
    """
```

**Target Users**: Academic researchers, political scientists

---

#### 9. `find_similar_speeches`
**Purpose**: Find speeches similar to a given speech
```python
@mcp.tool()
async def find_similar_speeches(
    speech_id: str,
    similarity_basis: Literal["content", "themes", "entities", "rhetoric"] = "content",
    limit: int = 5
) -> list[dict]:
    """
    Find speeches similar to a reference speech.

    Args:
        speech_id: Reference speech
        similarity_basis:
            - "content": Semantic similarity of text
            - "themes": Similar themes/subthemes
            - "entities": Mentions similar people/orgs
            - "rhetoric": Similar rhetorical intent

    Returns similar speeches with similarity scores.
    """
```

**Target Users**: Researchers studying rhetorical patterns

---

### Category 5: **Communication Analysis Tools** (Media/PR)

#### 10. `analyze_rhetoric`
**Purpose**: Analyze rhetorical strategies
```python
@mcp.tool()
async def analyze_rhetoric(
    speaker: str | None = None,
    party: str | None = None,
    rhetoric_intent: Literal["ceremonial", "deliberative", "forensic"] | None = None,
    limit: int = 10
) -> dict:
    """
    Analyze rhetorical strategies and communication styles.

    Returns:
        - rhetoric_patterns: Common rhetorical intents
        - storytelling_techniques: Personal anecdotes, constituent stories
        - emotional_appeals: Identified appeals
        - evidence_usage: How statistics/sources are used
        - quotable_phrases: High soundbite potential
    """
```

**Target Users**: Communications professionals, speech writers

---

#### 11. `assess_media_value`
**Purpose**: Score content for media/social value
```python
@mcp.tool()
async def assess_media_value(
    topic: str,
    soundbite_potential: Literal["high", "medium", "low"] = "high",
    controversy_level: Literal["high", "medium", "low"] | None = None,
    local_news_value: Literal["high", "medium", "low"] | None = None,
    social_media_shareable: bool | None = None,
    limit: int = 15
) -> list[dict]:
    """
    Find content optimized for media and social media use.

    Uses communications_utility metadata to rank:
        - soundbite_potential
        - controversy_level
        - local_news_value
        - social_media_shareable

    Perfect for PR teams and political communications.
    """
```

**Target Users**: PR teams, political communications staff

---

### Category 6: **Advanced Query Tools** (Structured Data)

#### 12. `query_by_metadata`
**Purpose**: Complex metadata filtering
```python
@mcp.tool()
async def query_by_metadata(
    filters: dict,
    sort_by: Literal["date", "relevance", "word_count"] = "relevance",
    limit: int = 10
) -> list[dict]:
    """
    Advanced JSONB filtering for complex queries.

    Examples:
        filters = {
            "party": "LP",
            "policy_areas.primary": "housing-affordability",
            "content_analysis.interruptions": {"$gt": 0},
            "communications_utility.soundbite_potential": "high"
        }

    Supports nested JSONB queries with operators:
        - $eq, $ne, $gt, $gte, $lt, $lte
        - $in, $nin
        - Nested field access with dot notation
    """
```

**Target Users**: Data analysts, power users

---

#### 13. `aggregate_statistics`
**Purpose**: Generate statistical summaries
```python
@mcp.tool()
async def aggregate_statistics(
    group_by: Literal["speaker", "party", "chamber", "theme", "month"],
    metric: Literal["speech_count", "avg_word_count", "entity_mentions", "themes"],
    filters: dict | None = None
) -> dict:
    """
    Generate aggregate statistics across speeches.

    Examples:
    - Speech count by party
    - Average word count by chamber
    - Most mentioned entities by speaker
    - Theme distribution over time

    Returns structured aggregation results.
    """
```

**Target Users**: Data analysts, researchers

---

### Category 7: **Context & Relationship Tools**

#### 14. `get_parliamentary_context`
**Purpose**: Get parliamentary session context
```python
@mcp.tool()
async def get_parliamentary_context(
    speech_id: str
) -> dict:
    """
    Get full parliamentary context for a speech.

    Returns:
        - speech: The speech itself
        - debate_context: What debate/bill was being discussed
        - parliamentary_interaction: Points of order, interjections
        - legislative_metadata: Bill references, votes
        - same_debate_speeches: Other speeches in same debate
    """
```

**Target Users**: Parliamentary researchers, historians

---

#### 15. `trace_entity_relationships`
**Purpose**: Map relationships between entities
```python
@mcp.tool()
async def trace_entity_relationships(
    entity: str,
    entity_type: Literal["people", "organizations", "places", "legislation"],
    relationship_type: Literal["co-mentions", "allies", "opponents", "policy_links"],
    limit: int = 20
) -> dict:
    """
    Trace relationships between entities across speeches.

    Examples:
    - Who is mentioned alongside "Scott Morrison"?
    - Which policies link to "GST" legislation?
    - Who are identified as allies/opponents in key_mentions?

    Returns network of related entities with context.
    """
```

**Target Users**: Network analysts, political scientists

---

## Implementation Priority

### Phase 1: MVP (Current) ✅
- `search_hansard` - Core semantic search
- `fetch_speech` - Retrieve full speeches

### Phase 2: Media Tools
- `extract_quotes` - High value for journalists
- `find_mentions` - Entity tracking

### Phase 3: Policy Analysis
- `analyze_policy_position` - Core political analysis
- `compare_speakers` - Comparative research

### Phase 4: Advanced Features
- `explore_themes` - Thematic analysis
- `assess_media_value` - Communications analysis
- `query_by_metadata` - Power users

### Phase 5: Specialized
- Remaining tools based on user feedback

---

## Tool Usage by Persona

### Journalist
```
1. extract_quotes(topic="housing crisis", soundbite_potential="high")
2. find_mentions(entity="Scott Morrison", sentiment="negative")
3. assess_media_value(topic="tax reform", controversy_level="high")
```

### Political Analyst
```
1. analyze_policy_position(policy_area="climate-change")
2. compare_speakers(speakers=["Kennedy", "Smith"], topic="energy")
3. track_policy_evolution(policy_area="housing", date_from="2024-01-01")
```

### Fact-Checker
```
1. search_hansard(query="100 million dollars claim", level="sentence")
2. get_parliamentary_context(speech_id="...")
3. find_mentions(entity="statistic_claim", entity_type="evidence")
```

### Academic Researcher
```
1. explore_themes(theme="middle-australia")
2. analyze_rhetoric(rhetoric_intent="ceremonial")
3. aggregate_statistics(group_by="party", metric="themes")
```

---

## Key Design Principles

1. **Granularity Control**: Every tool respects the `level` hierarchy (sentence/paragraph/speech)
2. **Context Preservation**: Results always include parent context and links
3. **Metadata Rich**: Leverage all 29 YAML frontmatter fields
4. **Use-Case Optimized**: Different tools for different professional needs
5. **Composable**: Tools can be chained (search → fetch → analyze)

---

## Metadata Fields Available (29 total)

### Basic Identification
- `speaker`, `speaker_id`, `date`, `chamber`, `electorate`, `party`
- `parliament`, `session`, `period`, `utterance_id`, `source_file`

### Content Metadata
- `debate`, `summary`, `speech_type`, `rhetoric_intent`

### Entities (nested)
- `entities.people`, `entities.organizations`, `entities.places`, `entities.legislation`

### Thematic
- `themes`, `subthemes`, `tags`

### Policy
- `policy_areas.primary`, `policy_areas.secondary`, `policy_areas.tertiary`

### Political Analysis
- `political_stance.government_position`, `political_stance.criticism_targets`
- `political_stance.support_targets`, `political_stance.coalition_alignment`

### Legislative Context
- `legislative_metadata.bill_reference`, `legislative_metadata.vote_position`
- `legislative_metadata.amendment_moved`, `legislative_metadata.committee_reference`

### Content Analysis
- `content_analysis.word_count`, `content_analysis.interruptions`
- `content_analysis.quotes_included`, `content_analysis.statistical_claims`

### Key Mentions (with sentiment)
- `key_mentions.opponents`, `key_mentions.allies` (name, role, mentions, sentiment, context)

### Local References
- `local_references.suburbs`, `local_references.infrastructure`
- `local_references.community_groups`, `local_references.constituency_issues`

### Storytelling
- `storytelling.personal_anecdotes`, `storytelling.constituent_stories`
- `storytelling.historical_references`, `storytelling.emotional_appeals`

### Evidence Base
- `evidence_base.statistics`, `evidence_base.sources`, `evidence_base.verification_status`

### Parliamentary Interaction
- `parliamentary_interaction.points_of_order_received`
- `parliamentary_interaction.interjections_taken`
- `parliamentary_interaction.procedural_interventions`
- `parliamentary_interaction.cross_party_exchanges`

### Communications Utility
- `communications_utility.quotable_phrases`
- `communications_utility.soundbite_potential`
- `communications_utility.controversy_level`
- `communications_utility.local_news_value`
- `communications_utility.social_media_shareable`

---

## Technical Notes

### Vector Store Integration
All tools query LangChain's `PostgresVectorStore` with JSONB metadata filtering:

```python
results = await vector_store.similarity_search(
    query,
    filter={
        "level": "sentence",
        "party": "LP",
        "communications_utility.soundbite_potential": "high"
    },
    k=limit
)
```

### Hierarchical Context Retrieval
When returning sentence-level results, fetch parent context:

```python
# User gets sentence match
sentence_result = {..., "level": "sentence", "paragraph_index": 2}

# Automatically fetch parent paragraph
parent_paragraph = await vector_store.similarity_search(
    "",
    filter={
        "level": "paragraph",
        "speech_id": sentence_result["speech_id"],
        "paragraph_index": 2
    },
    k=1
)
```

### RAG Integration
Tools return structured data that can be fed directly to LLM context:

```python
def build_rag_context(search_results):
    context = []
    for result in search_results:
        context.append(f"""
QUOTE: "{result['matched_text']}"
SPEAKER: {result['speaker']} ({result['party']})
DATE: {result['date']}
CONTEXT: {result['paragraph_context']}
SOUNDBITE: {result['soundbite_potential']}
        """)
    return "\n\n".join(context)
```

---

## Future Enhancements

### Machine Learning Integration
- Sentiment analysis on speeches
- Topic modeling across time periods
- Predictive analysis of policy shifts

### Visualization Tools
- Network graphs of entity relationships
- Timeline visualizations of policy evolution
- Party position mapping on policy dimensions

### Real-Time Features
- Live speech ingestion from parliamentary API
- Notification system for keywords/topics
- Trending topics dashboard

### Export Tools
- CSV/JSON export for external analysis
- Integration with visualization tools (Tableau, PowerBI)
- API endpoints for third-party integrations

---

## References

- [LangChain Vector Stores Documentation](https://python.langchain.com/docs/integrations/vectorstores/)
- [PostgreSQL JSONB Indexing](https://www.postgresql.org/docs/current/datatype-json.html)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Australian Hansard XML Format](https://www.aph.gov.au/Parliamentary_Business/Hansard)
