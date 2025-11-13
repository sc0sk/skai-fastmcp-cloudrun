"""TDD Tests for IAM Authentication Error Handling.

This module contains test-driven development tests for clear error messages
when IAM authentication fails due to misconfiguration.

User Story 3 (P3): Clear Error Messages for Misconfiguration
- Clear error when IAM user detection fails completely
- Helpful error for pgvector extension not enabled (already implemented)
- Clear error for database user mismatch

Test Strategy:
1. Write tests first (TDD)
2. Run tests - verify current behavior
3. Enhance error messages in src/storage/cloud_sql_engine.py
4. Run tests - verify improved messages
5. Regression test - verify baseline still passes

Success Criteria:
- Error messages explicitly state the problem
- Error messages suggest remediation steps
- Troubleshooting time reduced by 75% (clearer messages)
"""

import pytest
from unittest.mock import MagicMock, patch


class TestIAMErrorHandling:
    """Test error handling and messages for IAM misconfiguration."""

    def test_pgvector_extension_check_already_works(self):
        """Test that pgvector extension validation provides clear error.

        This test verifies existing functionality from postgres_vector_store.py
        where extension check was added in commit 3ba327d.

        Expected: PASS (already implemented)
        """
        from src.storage.postgres_vector_store import PostgresVectorStoreService

        # Mock connection to simulate extension missing
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None  # Extension not found

        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value = mock_conn

        # Verify clear error message when extension missing
        with pytest.raises(RuntimeError) as exc_info:
            service = PostgresVectorStoreService(
                connection=mock_engine,
                collection_name="test",
            )

        error_message = str(exc_info.value)
        assert "pgvector extension is not enabled" in error_message
        assert "CREATE EXTENSION IF NOT EXISTS vector" in error_message

    @pytest.mark.skip(reason="Connector() initialization calls google.auth.default() before mocking - requires Connector mock")
    def test_fallback_detection_logs_warning(self, caplog, monkeypatch):
        """Test that fallback to 'postgres' user logs warning.

        Given: All IAM detection methods fail
        When: System falls back to 'postgres' user
        Then: Warning is logged with troubleshooting steps

        Expected (TDD): May need enhanced logging
        After fix: PASS - warning logged with suggestions
        """
        import logging
        from src.storage.cloud_sql_engine import CloudSQLEngine

        caplog.set_level(logging.WARNING)

        # Remove Cloud Run environment
        monkeypatch.delenv('K_SERVICE', raising=False)

        # Mock ADC to fail
        with patch('google.auth.default') as mock_auth:
            mock_auth.side_effect = Exception("No credentials")

            # Mock gcloud to fail
            with patch('subprocess.check_output') as mock_subprocess:
                mock_subprocess.side_effect = Exception("gcloud not available")

                engine_mgr = CloudSQLEngine(
                    project_id="skai-fastmcp-cloudrun",
                    region="us-central1",
                    instance="hansard-db-v2",
                    database="hansard",
                    user=None,
                    password=None,
                )

                # Force connection attempt
                try:
                    with engine_mgr.engine.connect() as conn:
                        pass
                except Exception:
                    pass

                # Verify fallback was detected
                assert engine_mgr.detected_iam_user == "postgres"
                assert engine_mgr.detection_method == "FALLBACK"
                assert engine_mgr.iam_valid is False

    def test_detection_status_exposed_for_debugging(self):
        """Test that IAM detection status is exposed via properties.

        This verifies the properties added in User Story 1 are working.

        Expected: PASS (already implemented in US1)
        """
        from src.storage.cloud_sql_engine import CloudSQLEngine

        # Create engine (won't connect, just check properties exist)
        engine_mgr = CloudSQLEngine(
            project_id="test",
            region="test",
            instance="test",
            database="test",
        )

        # Verify properties are accessible
        assert hasattr(engine_mgr, 'detected_iam_user')
        assert hasattr(engine_mgr, 'detection_method')
        assert hasattr(engine_mgr, 'iam_valid')

        # Initial state should be None/False (no connection attempted yet)
        assert engine_mgr.detected_iam_user is None
        assert engine_mgr.detection_method is None
        assert engine_mgr.iam_valid is False
