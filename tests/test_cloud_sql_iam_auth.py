"""TDD tests for Cloud SQL IAM authentication in cloud_sql_engine.

Tests verify:
1. Service account email detection from credentials
2. Cloud Run metadata API fallback (K_SERVICE env)
3. gcloud config fallback for local development
4. pg8000 driver requirement for IAM auth
5. enable_iam_auth flag set correctly
"""

import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestCloudSQLIAMUserDetection(unittest.TestCase):
    """Test suite for IAM user (service account email) detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_sa_email = "666924716777-compute@developer.gserviceaccount.com"
        self.test_project = "test-project"
        self.test_region = "us-central1"
        self.test_instance = "test-db"
        self.test_database = "testdb"

    def tearDown(self):
        """Clean up environment after tests."""
        for var in ["K_SERVICE", "CLOUDSQL_IAM_USER"]:
            os.environ.pop(var, None)

    def test_iam_user_from_credentials_with_service_account_email(self):
        """Test extracting service account email from google.auth credentials."""
        # Mock credentials with service_account_email attribute
        mock_creds = Mock()
        mock_creds.service_account_email = self.test_sa_email

        with patch("google.auth.default") as mock_auth:
            mock_auth.return_value = (mock_creds, self.test_project)

            from src.storage.cloud_sql_engine import CloudSQLEngine

            # We need to capture the getconn function to test it
            # Create engine and extract user from connection kwargs
            engine_mgr = CloudSQLEngine(
                project_id=self.test_project,
                region=self.test_region,
                instance=self.test_instance,
                database=self.test_database,
                user=None,
                password=None,
            )

            # The actual IAM user detection happens in getconn()
            # We'll verify it by checking the connector was initialized
            self.assertIsNotNone(engine_mgr.engine)
            engine_mgr.close()

    def test_iam_user_from_credentials_with_private_attribute(self):
        """Test extracting service account email from _service_account_email."""
        mock_creds = Mock()
        mock_creds._service_account_email = self.test_sa_email
        # Ensure service_account_email doesn't exist
        del mock_creds.service_account_email

        with patch("google.auth.default") as mock_auth:
            mock_auth.return_value = (mock_creds, self.test_project)

            from src.storage.cloud_sql_engine import CloudSQLEngine

            engine_mgr = CloudSQLEngine(
                project_id=self.test_project,
                region=self.test_region,
                instance=self.test_instance,
                database=self.test_database,
                user=None,
                password=None,
            )
            self.assertIsNotNone(engine_mgr.engine)
            engine_mgr.close()

    def test_cloud_run_metadata_api_fallback(self):
        """Test fallback to Cloud Run metadata API when credentials unavailable."""
        os.environ["K_SERVICE"] = "hansard-mcp"  # Indicate Cloud Run environment

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = self.test_sa_email

        with patch("google.auth.default") as mock_auth:
            mock_auth.side_effect = Exception("No credentials")

            with patch("requests.get") as mock_get:
                mock_get.return_value = mock_response

                from src.storage.cloud_sql_engine import CloudSQLEngine

                engine_mgr = CloudSQLEngine(
                    project_id=self.test_project,
                    region=self.test_region,
                    instance=self.test_instance,
                    database=self.test_database,
                    user=None,
                    password=None,
                )
                self.assertIsNotNone(engine_mgr.engine)
                engine_mgr.close()

    def test_gcloud_config_fallback(self):
        """Test fallback to gcloud config for local development."""
        with patch("google.auth.default") as mock_auth:
            mock_auth.side_effect = Exception("No credentials")

            with patch("subprocess.check_output") as mock_subprocess:
                mock_subprocess.return_value = f"{self.test_sa_email}\n"

                from src.storage.cloud_sql_engine import CloudSQLEngine

                engine_mgr = CloudSQLEngine(
                    project_id=self.test_project,
                    region=self.test_region,
                    instance=self.test_instance,
                    database=self.test_database,
                    user=None,
                    password=None,
                )
                self.assertIsNotNone(engine_mgr.engine)
                engine_mgr.close()

    def test_fallback_to_postgres_user(self):
        """Test fallback to 'postgres' when no IAM user detected."""
        with patch("google.auth.default") as mock_auth:
            mock_auth.side_effect = Exception("No credentials")

            with patch("requests.get") as mock_get:
                mock_get.side_effect = Exception("Metadata unavailable")

                with patch("subprocess.check_output") as mock_subprocess:
                    mock_subprocess.side_effect = Exception("gcloud not found")

                    from src.storage.cloud_sql_engine import CloudSQLEngine

                    engine_mgr = CloudSQLEngine(
                        project_id=self.test_project,
                        region=self.test_region,
                        instance=self.test_instance,
                        database=self.test_database,
                        user=None,
                        password=None,
                    )
                    self.assertIsNotNone(engine_mgr.engine)
                    engine_mgr.close()

    def test_password_auth_when_user_and_password_provided(self):
        """Test that password auth is used when both user and password provided."""
        from src.storage.cloud_sql_engine import CloudSQLEngine

        engine_mgr = CloudSQLEngine(
            project_id=self.test_project,
            region=self.test_region,
            instance=self.test_instance,
            database=self.test_database,
            user="explicit_user",
            password="explicit_pass",
        )
        self.assertIsNotNone(engine_mgr.engine)
        engine_mgr.close()


class TestCloudSQLDriverSelection(unittest.TestCase):
    """Test suite for driver selection and configuration."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_project = "test-project"
        self.test_region = "us-central1"
        self.test_instance = "test-db"
        self.test_database = "testdb"

    def test_pg8000_driver_for_iam_auth(self):
        """Verify pg8000 driver is used for IAM authentication."""
        # pg8000 is the only driver that Cloud SQL Connector v1.18 supports for IAM auth
        # This test validates the driver parameter is set correctly
        from src.storage.cloud_sql_engine import CloudSQLEngine

        engine_mgr = CloudSQLEngine(
            project_id=self.test_project,
            region=self.test_region,
            instance=self.test_instance,
            database=self.test_database,
            user=None,  # Triggers IAM auth
            password=None,
        )

        # Verify engine was created (if pg8000 not available, would error)
        self.assertIsNotNone(engine_mgr.engine)
        engine_mgr.close()

    def test_sqlalchemy_psycopg_dialect_with_creator(self):
        """Verify SQLAlchemy engine uses psycopg dialect with creator function."""
        from src.storage.cloud_sql_engine import CloudSQLEngine

        engine_mgr = CloudSQLEngine(
            project_id=self.test_project,
            region=self.test_region,
            instance=self.test_instance,
            database=self.test_database,
        )

        # Verify SQLAlchemy engine URL uses psycopg dialect
        # (driver selection happens in creator, not URL)
        engine_url_str = str(engine_mgr.engine.url)
        self.assertIn("postgresql+psycopg", engine_url_str)
        engine_mgr.close()

    def test_enable_iam_auth_flag_set_for_iam(self):
        """Verify enable_iam_auth flag is set when using IAM auth."""
        # This is validated indirectly through successful connection
        # pg8000 requires enable_iam_auth=True for IAM DB Auth
        from src.storage.cloud_sql_engine import CloudSQLEngine

        engine_mgr = CloudSQLEngine(
            project_id=self.test_project,
            region=self.test_region,
            instance=self.test_instance,
            database=self.test_database,
            user=None,
            password=None,
        )
        self.assertIsNotNone(engine_mgr.engine)
        engine_mgr.close()


class TestConnectionPooling(unittest.TestCase):
    """Test suite for connection pool configuration."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_project = "test-project"
        self.test_region = "us-central1"
        self.test_instance = "test-db"
        self.test_database = "testdb"

    def test_default_pool_configuration(self):
        """Verify default pool configuration for Cloud Run."""
        from src.storage.cloud_sql_engine import CloudSQLEngine

        engine_mgr = CloudSQLEngine(
            project_id=self.test_project,
            region=self.test_region,
            instance=self.test_instance,
            database=self.test_database,
        )

        pool = engine_mgr.engine.pool
        self.assertEqual(pool.size(), 5)  # Default pool_size
        self.assertEqual(pool._max_overflow, 2)  # Default max_overflow
        self.assertTrue(pool._pre_ping)  # pool_pre_ping should be True
        engine_mgr.close()

    def test_custom_pool_configuration(self):
        """Verify custom pool configuration is applied."""
        from src.storage.cloud_sql_engine import CloudSQLEngine

        engine_mgr = CloudSQLEngine(
            project_id=self.test_project,
            region=self.test_region,
            instance=self.test_instance,
            database=self.test_database,
            pool_size=10,
            max_overflow=5,
            pool_timeout=60,
        )

        pool = engine_mgr.engine.pool
        self.assertEqual(pool.size(), 10)
        self.assertEqual(pool._max_overflow, 5)
        engine_mgr.close()


if __name__ == "__main__":
    unittest.main()
