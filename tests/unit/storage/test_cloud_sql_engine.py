"""Unit tests for Cloud SQL engine factory."""

from unittest.mock import Mock, patch
from sqlalchemy.engine import Engine

from src.storage.cloud_sql_engine import CloudSQLEngine


class TestCloudSQLEngine:
    """Test CloudSQLEngine factory with mocked connector."""

    @patch('src.storage.cloud_sql_engine.Connector')
    @patch('src.storage.cloud_sql_engine.create_engine')
    def test_engine_creation_with_iam(
        self, mock_create_engine, mock_connector_class
    ):
        """Test engine creation with IAM authentication."""
        # Arrange
        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector
        mock_engine = Mock(spec=Engine)
        mock_create_engine.return_value = mock_engine

        # Act
        CloudSQLEngine(
            project_id="test-proj",
            region="us-central1",
            instance="test-instance",
            database="test-db",
            user=None,
            password=None,
        )

        # Assert
        mock_connector_class.assert_called_once()
        mock_create_engine.assert_called_once()

        # Verify connection string format
        call_args = mock_create_engine.call_args
        assert call_args[0][0] == "postgresql+psycopg://"
        assert "creator" in call_args[1]
        assert call_args[1]["pool_size"] == 5
        assert call_args[1]["max_overflow"] == 2
        assert call_args[1]["pool_pre_ping"] is True

    @patch('src.storage.cloud_sql_engine.Connector')
    @patch('src.storage.cloud_sql_engine.create_engine')
    def test_engine_creation_with_password(
        self, mock_create_engine, mock_connector_class
    ):
        """Test engine creation with password-based authentication."""
        # Arrange
        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector
        mock_engine = Mock(spec=Engine)
        mock_create_engine.return_value = mock_engine

        # Act
        CloudSQLEngine(
            project_id="test-proj",
            region="us-central1",
            instance="test-instance",
            database="test-db",
            user="testuser",
            password="testpass",
        )

        # Assert
        mock_connector_class.assert_called_once()
        mock_create_engine.assert_called_once()

    @patch('src.storage.cloud_sql_engine.Connector')
    @patch('src.storage.cloud_sql_engine.create_engine')
    def test_connection_factory_iam_auth(
        self, mock_create_engine, mock_connector_class
    ):
        """Test connection factory enables IAM auth."""
        # Arrange
        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector
        mock_engine = Mock(spec=Engine)
        mock_create_engine.return_value = mock_engine

        # Act
        CloudSQLEngine(
            project_id="test-proj",
            region="us-central1",
            instance="test-instance",
            database="test-db",
            user=None,
            password=None,
        )

        # Get the creator function that was passed to create_engine
        creator_func = mock_create_engine.call_args[1]["creator"]

        # Call the creator function
        mock_conn = Mock()
        mock_connector.connect.return_value = mock_conn
        creator_func()

        # Assert
        mock_connector.connect.assert_called_once()
        call_kwargs = mock_connector.connect.call_args[1]
        assert call_kwargs["db"] == "test-db"
        assert call_kwargs["enable_iam_auth"] is True
        assert "user" not in call_kwargs
        assert "password" not in call_kwargs

    @patch('src.storage.cloud_sql_engine.Connector')
    @patch('src.storage.cloud_sql_engine.create_engine')
    def test_connection_factory_password_auth(
        self, mock_create_engine, mock_connector_class
    ):
        """Test connection factory uses credentials."""
        # Arrange
        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector
        mock_engine = Mock(spec=Engine)
        mock_create_engine.return_value = mock_engine

        # Act
        CloudSQLEngine(
            project_id="test-proj",
            region="us-central1",
            instance="test-instance",
            database="test-db",
            user="testuser",
            password="testpass",
        )

        # Get the creator function
        creator_func = mock_create_engine.call_args[1]["creator"]

        # Call it
        mock_conn = Mock()
        mock_connector.connect.return_value = mock_conn
        creator_func()

        # Assert
        call_kwargs = mock_connector.connect.call_args[1]
        assert call_kwargs["db"] == "test-db"
        assert call_kwargs["user"] == "testuser"
        assert call_kwargs["password"] == "testpass"
        assert "enable_iam_auth" not in call_kwargs

    @patch('src.storage.cloud_sql_engine.Connector')
    @patch('src.storage.cloud_sql_engine.create_engine')
    def test_custom_pool_config(
        self, mock_create_engine, mock_connector_class
    ):
        """Test engine creation with custom pool configuration."""
        # Arrange
        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector
        mock_engine = Mock(spec=Engine)
        mock_create_engine.return_value = mock_engine

        # Act
        CloudSQLEngine(
            project_id="test-proj",
            region="us-central1",
            instance="test-instance",
            database="test-db",
            pool_size=10,
            max_overflow=5,
            pool_timeout=60,
        )

        # Assert
        call_args = mock_create_engine.call_args[1]
        assert call_args["pool_size"] == 10
        assert call_args["max_overflow"] == 5
        assert call_args["pool_timeout"] == 60

    @patch('src.storage.cloud_sql_engine.Connector')
    @patch('src.storage.cloud_sql_engine.create_engine')
    def test_engine_property(self, mock_create_engine, mock_connector_class):
        """Test that engine property returns the SQLAlchemy engine."""
        # Arrange
        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector
        mock_engine = Mock(spec=Engine)
        mock_create_engine.return_value = mock_engine

        # Act
        engine_mgr = CloudSQLEngine(
            project_id="test-proj",
            region="us-central1",
            instance="test-instance",
            database="test-db",
        )

        # Assert
        assert engine_mgr.engine is mock_engine

    @patch('src.storage.cloud_sql_engine.Connector')
    @patch('src.storage.cloud_sql_engine.create_engine')
    def test_close(self, mock_create_engine, mock_connector_class):
        """Test engine cleanup on close."""
        # Arrange
        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector
        mock_engine = Mock(spec=Engine)
        mock_create_engine.return_value = mock_engine

        # Act
        engine_mgr = CloudSQLEngine(
            project_id="test-proj",
            region="us-central1",
            instance="test-instance",
            database="test-db",
        )
        engine_mgr.close()

        # Assert
        mock_engine.dispose.assert_called_once()
        mock_connector.close.assert_called_once()

    @patch('src.storage.cloud_sql_engine.Connector')
    @patch('src.storage.cloud_sql_engine.create_engine')
    def test_instance_connection_name_format(self, mock_create_engine, mock_connector_class):
        """Test correct formatting of instance connection name."""
        # Arrange
        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector
        mock_engine = Mock(spec=Engine)
        mock_create_engine.return_value = mock_engine

        # Act
        engine_mgr = CloudSQLEngine(
            project_id="my-project",
            region="europe-west1",
            instance="my-db-instance",
            database="mydb",
        )
        
        # Get the creator and call it to trigger connector.connect
        creator_func = mock_create_engine.call_args[1]["creator"]
        mock_connector.connect.return_value = Mock()
        creator_func()

        # Assert - verify instance connection name format
        call_args = mock_connector.connect.call_args
        assert call_args[0][0] == "my-project:europe-west1:my-db-instance"
