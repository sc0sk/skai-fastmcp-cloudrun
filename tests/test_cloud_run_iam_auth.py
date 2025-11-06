"""TDD Tests for Cloud Run IAM Authentication.

This module contains test-driven development tests for IAM user detection
in Cloud Run environments. Tests are written FIRST (before implementation)
and should FAIL initially.

User Story 1 (P1): Database Connection Works in Cloud Run Environment
- Cloud Run metadata service properly detects service account email
- "default" placeholder is rejected and triggers fallback
- IAM detection is logged for troubleshooting

Test Strategy:
1. Write tests first (TDD)
2. Run tests - verify they FAIL
3. Implement fixes in src/storage/cloud_sql_engine.py
4. Run tests - verify they PASS
5. Regression test - verify baseline still passes

Success Criteria:
- detected_iam_user == service account email (not "default")
- detection_method == "METADATA_SERVICE" in Cloud Run
- iam_valid == True for valid service accounts
"""

import pytest
from unittest.mock import MagicMock, patch
from tests.mocks.cloud_run_fixtures import (
    mock_cloud_run_env,
    mock_metadata_service,
    mock_default_placeholder,
)


class TestCloudRunIAMDetection:
    """Test IAM user detection in Cloud Run environment."""

    def test_detects_service_account_from_metadata_service(
        self, mock_cloud_run_env, mock_metadata_service
    ):
        """Test that IAM user is detected from Cloud Run metadata service.

        Given: Cloud Run environment (K_SERVICE set)
        When: CloudSQLEngine initializes and connects
        Then: Service account email is detected from metadata service

        Expected (TDD): FAIL - properties not implemented yet
        After fix: PASS - metadata service detection working
        """
        from src.storage.cloud_sql_engine import CloudSQLEngine

        # Initialize engine (will trigger IAM detection in getconn)
        engine_mgr = CloudSQLEngine(
            project_id="skai-fastmcp-cloudrun",
            region="us-central1",
            instance="hansard-db-v2",
            database="hansard",
            user=None,  # Trigger IAM auth
            password=None,
        )

        # Force connection to trigger getconn() where IAM detection happens
        # This will fail if database isn't available, but that's OK for this test
        # We're testing the detection logic, not the actual connection
        try:
            with engine_mgr.engine.connect() as conn:
                pass
        except Exception:
            # Expected - database may not be available in test environment
            # IAM detection still happens in getconn() before connection attempt
            pass

        # Verify IAM user was detected from metadata service
        assert engine_mgr.detected_iam_user == "666924716777-compute@developer.gserviceaccount.com"
        assert engine_mgr.detection_method == "METADATA_SERVICE"
        assert engine_mgr.iam_valid is True

    def test_rejects_default_placeholder_from_adc(self, mock_default_placeholder):
        """Test that 'default' placeholder is filtered out and rejected.

        Given: ADC returns "default" placeholder instead of real email
        When: CloudSQLEngine attempts IAM detection
        Then: "default" is rejected, iam_valid is False

        Expected (TDD): FAIL - no validation logic for "default" yet
        After fix: PASS - "default" filtered out, marked invalid
        """
        from src.storage.cloud_sql_engine import CloudSQLEngine

        # Remove K_SERVICE to avoid metadata service path
        import os
        if 'K_SERVICE' in os.environ:
            del os.environ['K_SERVICE']

        engine_mgr = CloudSQLEngine(
            project_id="skai-fastmcp-cloudrun",
            region="us-central1",
            instance="hansard-db-v2",
            database="hansard",
            user=None,
            password=None,
        )

        # Force connection attempt to trigger IAM detection
        try:
            with engine_mgr.engine.connect() as conn:
                pass
        except Exception:
            pass

        # Verify "default" placeholder was rejected
        # Either detected_iam_user is NOT "default" (fallback used)
        # OR iam_valid is False (detected but marked invalid)
        assert engine_mgr.detected_iam_user != "default" or engine_mgr.iam_valid is False

    def test_logs_iam_detection_method(
        self, mock_cloud_run_env, mock_metadata_service, caplog
    ):
        """Test that IAM detection is logged at INFO level.

        Given: Cloud Run environment with metadata service
        When: CloudSQLEngine connects
        Then: INFO log contains detection method and IAM user

        Expected (TDD): FAIL - logging not implemented yet
        After fix: PASS - logs contain IAM detection details
        """
        import logging
        from src.storage.cloud_sql_engine import CloudSQLEngine

        # Ensure logging is enabled
        caplog.set_level(logging.INFO)

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

        # Verify INFO log contains IAM detection details
        log_messages = [record.message for record in caplog.records if record.levelname == "INFO"]

        # Look for log message with IAM user and detection method
        found_iam_log = False
        for msg in log_messages:
            if "666924716777-compute@developer" in msg or "CloudSQLEngine connecting" in msg:
                found_iam_log = True
                break

        assert found_iam_log, f"Expected IAM detection in logs, got: {log_messages}"
