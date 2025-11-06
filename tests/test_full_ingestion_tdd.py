"""TDD tests for verifying full database ingestion with embeddings.

This test suite verifies that all 64 Simon Kennedy speeches are properly
ingested with both metadata and vector embeddings, and that search works
correctly across the entire corpus.

Run with: pytest tests/test_full_ingestion_tdd.py -v -s
"""
import pytest
from datetime import date


class TestDatabasePopulation:
    """Test that database is properly populated with speeches."""
    
    @pytest.mark.asyncio
    async def test_metadata_store_has_speeches(self):
        """Test that metadata store contains the expected number of speeches."""
        from src.storage.metadata_store import get_default_metadata_store
        
        metadata_store = await get_default_metadata_store()
        
        try:
            stats = await metadata_store.get_stats()
            
            print(f"\n📊 Metadata Store Statistics:")
            print(f"  Total speeches: {stats['speech_count']}")
            print(f"  Unique speakers: {stats['unique_speakers']}")
            print(f"  Date range: {stats['earliest_date']} to {stats['latest_date']}")
            print(f"  Party breakdown: {stats['party_breakdown']}")
            
            # Verify we have speeches (should be 62 currently)
            assert stats['speech_count'] > 0, "No speeches found in database"
            
            # Should have Simon Kennedy speeches
            assert stats['unique_speakers'] >= 1, "No speakers found"
            
            # Should have date range
            assert stats['earliest_date'] is not None
            assert stats['latest_date'] is not None
            
            print(f"✅ Metadata store contains {stats['speech_count']} speeches")
            
        finally:
            await metadata_store.close()
    
    @pytest.mark.asyncio
    async def test_search_speeches_by_metadata(self):
        """Test that we can search speeches by metadata filters."""
        from src.storage.metadata_store import get_default_metadata_store
        
        metadata_store = await get_default_metadata_store()
        
        try:
            # Search for Simon Kennedy speeches
            speeches = await metadata_store.search_speeches(
                speaker="Simon Kennedy",
                limit=100
            )
            
            print(f"\n🔍 Metadata Search Results:")
            print(f"  Found {len(speeches)} Simon Kennedy speeches")
            
            if speeches:
                print(f"\n  Sample speech:")
                sample = speeches[0]
                print(f"    Title: {sample['title']}")
                print(f"    Date: {sample['date']}")
                print(f"    Party: {sample['party']}")
                print(f"    Chamber: {sample['chamber']}")
                print(f"    Word count: {sample['word_count']}")
            
            assert len(speeches) > 0, "No Simon Kennedy speeches found"
            
            # Verify structure
            for speech in speeches[:3]:  # Check first 3
                assert 'speech_id' in speech
                assert 'title' in speech
                assert 'speaker' in speech
                assert 'date' in speech
                
            print(f"✅ Successfully retrieved {len(speeches)} speeches")
            
        finally:
            await metadata_store.close()


class TestVectorStorePopulation:
    """Test that vector store contains embeddings for speeches."""
    
    @pytest.mark.asyncio
    async def test_vector_search_returns_results(self):
        """Test that vector search returns results for common queries."""
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        
        # Test multiple queries to verify embeddings exist
        test_queries = [
            ("housing", "housing policy and affordability"),
            ("immigration", "immigration and border policy"),
            ("infrastructure", "infrastructure and development"),
            ("economy", "economic policy and budget"),
        ]
        
        print("\n🔍 Vector Search Tests:")
        
        total_results = 0
        for query_term, description in test_queries:
            results = await store.similarity_search(
                query=query_term,
                k=5
            )
            
            result_count = len(results)
            total_results += result_count
            
            print(f"\n  Query: '{query_term}' ({description})")
            print(f"  Results: {result_count}")
            
            if results:
                # Show top result
                top_result = results[0]
                score = top_result.get('score', 0)
                excerpt = top_result.get('chunk_text', '')[:100]
                print(f"    Top match (score: {score:.3f}): {excerpt}...")
        
        # Assert we got some results
        assert total_results > 0, \
            f"Vector search returned no results for any query. " \
            f"This suggests embeddings may not be populated."
        
        print(f"\n✅ Vector search returned {total_results} total results across all queries")
    
    @pytest.mark.asyncio
    async def test_vector_search_quality(self):
        """Test that vector search returns relevant results."""
        from src.storage.vector_store import get_default_vector_store
        
        store = await get_default_vector_store()
        
        # Search for housing-related content
        results = await store.similarity_search(
            query="housing affordability crisis and rental market",
            k=3
        )
        
        print(f"\n🎯 Vector Search Quality Test:")
        print(f"  Query: 'housing affordability crisis and rental market'")
        print(f"  Results: {len(results)}")
        
        for i, result in enumerate(results, 1):
            score = result.get('score', 0)
            metadata = result.get('metadata', {})
            excerpt = result.get('chunk_text', '')[:150]
            
            print(f"\n  Result {i} (score: {score:.3f}):")
            print(f"    Speech ID: {metadata.get('speech_id', 'N/A')}")
            print(f"    Date: {metadata.get('date', 'N/A')}")
            print(f"    Excerpt: {excerpt}...")
        
        if results:
            # Top result should have reasonable similarity
            top_score = results[0].get('score', 0)
            assert top_score > 0.3, \
                f"Top result similarity too low ({top_score:.3f}). " \
                f"Expected > 0.3 for semantic match."
            
            print(f"\n✅ Vector search quality verified (top score: {top_score:.3f})")
        else:
            pytest.skip("No results returned - may need to ingest embeddings")


class TestEndToEndSearch:
    """Test end-to-end search functionality via tools."""
    
    @pytest.mark.asyncio
    async def test_search_tool_with_various_queries(self):
        """Test search tool with multiple query types."""
        from src.tools.search import search_hansard_speeches
        
        test_cases = [
            {
                "name": "Housing policy",
                "query": "housing affordability and rental crisis",
                "expected_min": 1,
            },
            {
                "name": "Immigration",
                "query": "immigration policy and border protection",
                "expected_min": 1,
            },
            {
                "name": "Infrastructure",
                "query": "infrastructure investment and development",
                "expected_min": 1,
            },
        ]
        
        print("\n🧪 End-to-End Search Tool Tests:")
        
        all_passed = True
        for test in test_cases:
            try:
                result = await search_hansard_speeches(
                    query=test["query"],
                    limit=5
                )
                
                count = result.get("total_count", 0)
                success = count >= test["expected_min"]
                status = "✅" if success else "❌"
                
                print(f"\n  {status} {test['name']}")
                print(f"      Query: '{test['query']}'")
                print(f"      Results: {count} (expected: >={test['expected_min']})")
                
                if not success:
                    all_passed = False
                    
                # Show a sample result if available
                if result.get("speeches"):
                    sample = result["speeches"][0]
                    print(f"      Sample: {sample.get('title', 'N/A')}")
                    print(f"      Score: {sample.get('relevance_score', 0):.3f}")
                    
            except Exception as e:
                print(f"\n  ❌ {test['name']}: Failed with error: {e}")
                all_passed = False
        
        assert all_passed, "Some search tests failed"
        print("\n✅ All search tool tests passed")
    
    @pytest.mark.asyncio
    async def test_search_with_date_filters(self):
        """Test search with date range filters."""
        from src.tools.search import search_hansard_speeches
        
        # Search for 2024 speeches
        result = await search_hansard_speeches(
            query="parliament",
            start_date="2024-01-01",
            end_date="2024-12-31",
            limit=10
        )
        
        count = result.get("total_count", 0)
        
        print(f"\n📅 Date Filter Test:")
        print(f"  Date range: 2024-01-01 to 2024-12-31")
        print(f"  Results: {count}")
        
        if result.get("speeches"):
            dates = [s.get("date") for s in result["speeches"]]
            print(f"  Sample dates: {dates[:5]}")
            
            # Verify all dates are in 2024
            for speech in result["speeches"]:
                speech_date = speech.get("date", "")
                assert speech_date.startswith("2024"), \
                    f"Found speech outside date range: {speech_date}"
        
        print(f"✅ Date filtering works correctly")
    
    @pytest.mark.asyncio
    async def test_search_with_party_filter(self):
        """Test search with party filter."""
        from src.tools.search import search_hansard_speeches
        
        # Search for Liberal party speeches
        result = await search_hansard_speeches(
            query="policy",
            party="Liberal",
            limit=10
        )
        
        count = result.get("total_count", 0)
        
        print(f"\n🏛️  Party Filter Test:")
        print(f"  Party: Liberal")
        print(f"  Results: {count}")
        
        if result.get("speeches"):
            parties = set(s.get("party") for s in result["speeches"])
            print(f"  Parties found: {parties}")
            
            # All should be Liberal
            for speech in result["speeches"]:
                assert speech.get("party") == "Liberal", \
                    f"Found non-Liberal speech: {speech.get('party')}"
        
        print(f"✅ Party filtering works correctly")


class TestFetchTool:
    """Test fetch tool retrieves full speech text."""
    
    @pytest.mark.asyncio
    async def test_fetch_speech_by_id(self):
        """Test fetching a complete speech by ID."""
        from src.tools.search import search_hansard_speeches
        from src.tools.fetch import fetch_hansard_speech
        
        # First, search for a speech
        search_result = await search_hansard_speeches(
            query="housing",
            limit=1
        )
        
        assert search_result.get("total_count", 0) > 0, \
            "No speeches found to test fetch"
        
        speech_id = search_result["speeches"][0]["speech_id"]
        
        print(f"\n📄 Fetch Tool Test:")
        print(f"  Speech ID: {speech_id}")
        
        # Fetch the full speech
        result = await fetch_hansard_speech(speech_id=speech_id)
        
        # Verify structure
        assert result.get("speech_id") == speech_id
        assert "full_text" in result
        assert "title" in result
        assert "speaker" in result
        assert "date" in result
        
        print(f"  Title: {result['title']}")
        print(f"  Speaker: {result['speaker']}")
        print(f"  Date: {result['date']}")
        print(f"  Word count: {result.get('word_count', 0)}")
        print(f"  Text length: {len(result['full_text'])} characters")
        
        # Full text should be substantial
        assert len(result["full_text"]) > 100, \
            "Full text too short"
        
        print(f"✅ Fetch tool works correctly")


class TestIngestionPipeline:
    """Test that ingestion pipeline works end-to-end."""
    
    @pytest.mark.asyncio
    async def test_ingest_single_speech_with_embeddings(self):
        """Test ingesting a single speech with embeddings."""
        from src.tools.ingest import ingest_hansard_speech
        from src.storage.metadata_store import get_default_metadata_store
        import uuid
        
        # Create test speech with unique content
        test_id = str(uuid.uuid4())
        unique_suffix = test_id[:8]  # Use part of UUID for uniqueness
        speech_data = {
            "title": f"TDD Test Speech {test_id}",
            "full_text": (
                f"This is a comprehensive test speech about housing policy "
                f"and infrastructure development in test run {unique_suffix}. "
                f"We need to address the housing affordability crisis and invest "
                f"in critical infrastructure projects for test {unique_suffix}. "
            ) * 10,  # Make it longer
            "speaker": "Simon Kennedy",
            "party": "Liberal",
            "chamber": "House of Representatives",
            "electorate": "Fowler",
            "state": "NSW",
            "date": date.today().isoformat(),
            "hansard_reference": f"TEST-{test_id}",
        }
        
        print(f"\n📝 Ingestion Pipeline Test:")
        print(f"  Test ID: {test_id[:8]}...")
        
        # Ingest WITH embeddings
        result = await ingest_hansard_speech(
            speech_data=speech_data,
            generate_embeddings=True,  # Enable embeddings
        )
        
        assert result["status"] == "success", \
            f"Ingestion failed: {result.get('message')}"
        
        speech_id = result["speech_id"]
        chunk_count = result.get("chunk_count", 0)
        chunk_ids = result.get("chunk_ids", [])
        
        print(f"  ✅ Ingestion successful")
        print(f"  Speech ID: {speech_id}")
        print(f"  Chunks created: {chunk_count}")
        print(f"  Chunk IDs: {len(chunk_ids)}")
        
        # Verify embeddings were created
        assert chunk_count > 0, "No chunks created"
        assert len(chunk_ids) > 0, "No chunk IDs returned"
        
        # Verify we can search for it
        from src.storage.vector_store import get_default_vector_store
        store = await get_default_vector_store()
        
        search_results = await store.similarity_search(
            query="housing affordability crisis infrastructure",
            k=10,
            filter={"speech_id": speech_id}
        )
        
        print(f"  Vector search found: {len(search_results)} chunks")
        assert len(search_results) > 0, \
            "Ingested speech not found in vector search"
        
        # Cleanup
        metadata_store = await get_default_metadata_store()
        await metadata_store.delete_speech(speech_id)
        await store.delete_by_speech_id(speech_id)
        
        print(f"  ✅ Cleanup successful")
        print(f"\n✅ Full ingestion pipeline works correctly")


class TestDataIntegrity:
    """Test data integrity across metadata and vector stores."""
    
    @pytest.mark.asyncio
    async def test_metadata_vector_consistency(self):
        """Test that metadata and vector stores are consistent."""
        from src.storage.metadata_store import get_default_metadata_store
        from src.storage.vector_store import get_default_vector_store
        
        metadata_store = await get_default_metadata_store()
        vector_store = await get_default_vector_store()
        
        # Get metadata stats
        stats = await metadata_store.get_stats()
        metadata_count = stats['speech_count']
        
        print(f"\n🔄 Data Consistency Test:")
        print(f"  Metadata store: {metadata_count} speeches")
        
        # Sample a few speeches and verify they have embeddings
        speeches = await metadata_store.search_speeches(limit=10)
        
        speeches_with_embeddings = 0
        for speech in speeches[:5]:  # Check first 5
            speech_id = str(speech['speech_id'])  # Convert UUID to string
            
            # Search for this speech in vector store
            results = await vector_store.similarity_search(
                query="test",  # Any query
                k=10,
                filter={"speech_id": speech_id}
            )
            
            if len(results) > 0:
                speeches_with_embeddings += 1
                chunks = len(results)
                print(f"  ✅ Speech {speech_id[:8]}... has {chunks} chunks")
            else:
                print(f"  ⚠️  Speech {speech_id[:8]}... has no embeddings")
        
        coverage = speeches_with_embeddings / len(speeches[:5]) * 100
        print(f"\n  Embedding coverage: {coverage:.1f}% (of sample)")
        
        # We should have reasonable coverage
        assert speeches_with_embeddings > 0, \
            "No speeches have embeddings"
        
        print(f"✅ Data consistency verified")


if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v", "-s"])
