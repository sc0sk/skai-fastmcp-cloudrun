"""TDD tests for Cloud SQL database connection and vector operations.

Test the database connection pipeline without deploying to Cloud Run:
1. CloudSQLEngine creates valid engine with IAM auth
2. MetadataStore can connect and query
3. VectorStore can connect and perform operations
4. MCP tools can execute end-to-end

Run with: pytest tests/test_db_connection_tdd.py -v
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import text


# Test 1: CloudSQLEngine creates engine with correct parameters
class TestCloudSQLEngine:
    """Test CloudSQLEngine initialization and connection creation."""
    
    def test_engine_creation_with_iam_auth(self):
        """Test that CloudSQLEngine creates an engine with IAM auth parameters."""
        from src.storage.cloud_sql_engine import CloudSQLEngine
        
        # Create engine manager
        engine_mgr = CloudSQLEngine(
            project_id="skai-fastmcp-cloudrun",
            region="us-central1",
            instance="hansard-db-v2",
            database="hansard",
            user=None,  # IAM auth
            password=None,
        )
        
        # Verify engine was created
        assert engine_mgr.engine is not None
        assert engine_mgr._instance_conn_name == "skai-fastmcp-cloudrun:us-central1:hansard-db-v2"
        
        # Cleanup
        engine_mgr.close()
    
    def test_engine_creation_with_password_auth(self):
        """Test that CloudSQLEngine can create engine with password auth (legacy)."""
        from src.storage.cloud_sql_engine import CloudSQLEngine
        
        # Create engine manager with password
        engine_mgr = CloudSQLEngine(
            project_id="skai-fastmcp-cloudrun",
            region="us-central1",
            instance="hansard-db-v2",
            database="hansard",
            user="test_user",
            password="test_pass",
        )
        
        # Verify engine was created
        assert engine_mgr.engine is not None
        
        # Cleanup
        engine_mgr.close()


# Test 2: MetadataStore can connect and query
class TestMetadataStore:
    """Test MetadataStore database operations."""
    
    @pytest.mark.asyncio
    async def test_metadata_store_connection(self):
        """Test that MetadataStore can connect to database."""
        from src.storage.metadata_store import MetadataStore
        
        # Create metadata store with IAM auth
        store = MetadataStore(
            project_id="skai-fastmcp-cloudrun",
            region="us-central1",
            instance="hansard-db-v2",
            database="hansard",
            user=None,
            password=None,
        )
        
        # Test connection by getting stats
        try:
            stats = await store.get_stats()
            assert "speech_count" in stats
            print(f"✅ MetadataStore connected. Speech count: {stats['speech_count']}")
        except Exception as e:
            pytest.fail(f"MetadataStore connection failed: {e}")
        finally:
            await store.close()
    
    @pytest.mark.asyncio
    async def test_metadata_store_respects_use_iam_auth_env(self):
        """Test that USE_IAM_AUTH env var forces IAM auth."""
        from src.storage.metadata_store import MetadataStore
        
        with patch.dict(os.environ, {
            "USE_IAM_AUTH": "true",
            "CLOUDSQL_USER": "should_be_ignored",
            "DATABASE_PASSWORD": "should_be_ignored",
        }):
            store = MetadataStore(
                project_id="skai-fastmcp-cloudrun",
                region="us-central1",
                instance="hansard-db-v2",
                database="hansard",
            )
            
            # Verify IAM auth is used (user/password cleared)
            assert store.user is None
            assert store.password is None
            
            await store.close()


# Test 3: VectorStore can connect and perform operations
class TestVectorStore:
    """Test VectorStore initialization and operations."""
    
    @pytest.mark.asyncio
    async def test_vector_store_initialization(self):
        """Test that VectorStore initializes without errors."""
        from src.storage.vector_store import get_default_vector_store
        
        # Force IAM auth
        with patch.dict(os.environ, {"USE_IAM_AUTH": "true"}):
            store = await get_default_vector_store()
            
            # This should trigger _ensure_store() and connect to DB
            try:
                store._ensure_store()
                print("✅ VectorStore initialized successfully")
            except RuntimeError as e:
                if "pgvector extension is not enabled" in str(e):
                    pytest.skip("pgvector extension not enabled in database")
                raise
            except Exception as e:
                pytest.fail(f"VectorStore initialization failed: {e}")


# Test 4: End-to-end search tool test
class TestSearchTool:
    """Test search_hansard_speeches tool end-to-end."""
    
    @pytest.mark.asyncio
    async def test_search_tool_execution(self):
        """Test that search tool can execute without errors."""
        from src.tools.search import search_hansard_speeches
        
        # Force IAM auth
        with patch.dict(os.environ, {"USE_IAM_AUTH": "true"}):
            try:
                # Execute search with simple query
                result = await search_hansard_speeches(
                    query="housing",
                    limit=3
                )
                
                # Verify result structure
                assert isinstance(result, dict)
                assert "speeches" in result
                assert "total_count" in result
                assert "query" in result
                
                print(f"✅ Search tool executed. Found {result['total_count']} speeches")
                
                # If we got results, verify structure
                if result["speeches"]:
                    speech = result["speeches"][0]
                    assert "chunk_id" in speech
                    assert "excerpt" in speech
                    assert "relevance_score" in speech
                    
            except Exception as e:
                pytest.fail(f"Search tool execution failed: {e}")


# Test 5: Ingest tool test (metadata only, no embeddings)
class TestIngestTool:
    """Test ingest_hansard_speech tool (metadata path only)."""
    
    @pytest.mark.asyncio
    async def test_ingest_tool_metadata_only(self):
        """Test that ingest tool can write to metadata store."""
        from src.tools.ingest import ingest_hansard_speech
        import uuid
        from datetime import date
        
        # Force IAM auth
        with patch.dict(os.environ, {"USE_IAM_AUTH": "true"}):
            # Create test speech data
            speech_data = {
                "title": f"Test Speech {uuid.uuid4()}",
                "full_text": "This is a test speech about housing policy and infrastructure development. " * 20,
                "speaker": "Simon Kennedy",
                "party": "Liberal",
                "chamber": "House of Representatives",  # Fixed: use full name, not abbreviation
                "electorate": "Fowler",
                "state": "NSW",
                "date": date.today().isoformat(),
                "hansard_reference": f"TEST-{uuid.uuid4()}",
            }
            
            try:
                # Ingest without embeddings (faster, tests metadata path only)
                result = await ingest_hansard_speech(
                    speech_data=speech_data,
                    generate_embeddings=False,
                )
                
                # Print result for debugging
                print(f"📋 Ingest result: {result}")
                
                # Verify result
                assert result["status"] == "success", f"Ingest failed: {result.get('message', 'Unknown error')}"
                assert result["speech_id"] is not None
                
                print(f"✅ Ingest tool executed. Speech ID: {result['speech_id']}")
                
                # Cleanup: delete the test speech
                from src.storage.metadata_store import get_default_metadata_store
                metadata_store = await get_default_metadata_store()
                await metadata_store.delete_speech(result["speech_id"])
                print(f"✅ Test speech cleaned up")
                
            except Exception as e:
                pytest.fail(f"Ingest tool execution failed: {e}")


# Test 6: Connection parameter debugging
class TestConnectionDebug:
    """Debug connection parameters to identify IAM auth issues."""
    
    @pytest.mark.asyncio
    async def test_connection_parameters_logged(self, caplog):
        """Test that connection parameters are logged for debugging."""
        import logging
        from src.storage.cloud_sql_engine import CloudSQLEngine
        
        # Set log level to capture INFO messages
        caplog.set_level(logging.INFO)
        
        # Create engine with IAM auth
        engine_mgr = CloudSQLEngine(
            project_id="skai-fastmcp-cloudrun",
            region="us-central1",
            instance="hansard-db-v2",
            database="hansard",
            user=None,
            password=None,
        )
        
        # Trigger a connection to see logs
        try:
            with engine_mgr.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
                assert result == 1
                print("✅ Connection successful with IAM auth")
        except Exception as e:
            # Check if logs contain connection details
            log_messages = [rec.message for rec in caplog.records]
            print(f"❌ Connection failed: {e}")
            print(f"📋 Log messages: {log_messages}")
            
            # Re-raise to fail test
            raise
        finally:
            engine_mgr.close()


if __name__ == "__main__":
    # Run tests with: python tests/test_db_connection_tdd.py
    pytest.main([__file__, "-v", "-s"])
