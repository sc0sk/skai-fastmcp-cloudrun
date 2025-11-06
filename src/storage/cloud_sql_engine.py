"""Cloud SQL SQLAlchemy engine factory (IAM-ready).

Creates a SQLAlchemy 2.x Engine for Cloud SQL PostgreSQL using the
Google Cloud SQL Python Connector with pg8000 driver.

Key Features:
- IAM Database Authentication (preferred, no password storage)
- Connection pooling optimized for Cloud Run (5 pool + 2 overflow)
- Automatic Cloud SQL Proxy management via Connector
- Health checks via pool_pre_ping

Usage Example:
    from src.storage.cloud_sql_engine import CloudSQLEngine
    
    # IAM authentication (recommended for Cloud Run)
    engine_mgr = CloudSQLEngine(
        project_id="my-proj",
        region="us-central1",
        instance="hansard-db-v2",
        database="hansard",
        user=None,  # Triggers IAM auth
        password=None,
    )
    engine = engine_mgr.engine
    
    # Use with SQLAlchemy or langchain-postgres
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
    
    # Clean up when done
    engine_mgr.close()

Security Notes:
- ALWAYS use IAM authentication in production (user=None, password=None)
- IAM auth requires Cloud SQL IAM Database User role
- Never commit passwords or credentials to version control
- Connection strings never expose credentials (handled by Connector)

Configuration Requirements:
- Environment: GCP Cloud Run or compute with Cloud SQL IAM permissions
- Required IAM role: roles/cloudsql.client (for Connector)
- Required database role: cloudsqlsuperuser or custom role with CONNECT
- Cloud SQL instance must have public IP or private VPC access
- pg8000>=1.30.0 required for driver

Connection Pooling:
- Default pool_size=5: Max 5 active connections per instance
- Default max_overflow=2: Allow 2 additional connections under load
- Total max: 7 concurrent connections (suitable for Cloud Run)
- pool_pre_ping=True: Validates connections before use (prevents stale)
- pool_timeout=30: Wait up to 30s for available connection

Performance Notes:
- First connection has ~500ms overhead (Cloud SQL Proxy handshake)
- Subsequent connections from pool: <10ms overhead
- Pool warming recommended: Call engine.connect() during startup
- Monitor connection exhaustion: Increase pool_size if timeouts occur

Troubleshooting:
- "Not authorized": Check IAM roles (cloudsql.client, database CONNECT)
- "Connection timeout": Increase pool_timeout or pool_size
- "SSL error": Ensure Cloud SQL instance has SSL enabled
- "Pool exhausted": Increase max_overflow or optimize query concurrency
"""

from __future__ import annotations

from typing import Optional
import logging

from google.cloud.sql.connector import Connector
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


class CloudSQLEngine:
    """Manage a SQLAlchemy Engine backed by Cloud SQL Connector.
    
    This factory creates a SQLAlchemy 2.x engine connected to Cloud SQL
    PostgreSQL via the Cloud SQL Python Connector, with support for:
    - IAM-based authentication (no password storage)
    - Automatic token refresh for long-running connections
    - Connection pooling optimized for serverless environments
    - Health checks and stale connection detection
    
    The engine is suitable for use with langchain-postgres PGVector or
    direct SQLAlchemy queries.
    
    Attributes:
        engine: SQLAlchemy Engine instance (read-only property)
    
    Example:
        >>> engine_mgr = CloudSQLEngine(
        ...     project_id="my-gcp-project",
        ...     region="us-central1",
        ...     instance="my-instance",
        ...     database="my_database",
        ... )
        >>> with engine_mgr.engine.connect() as conn:
        ...     result = conn.execute(text("SELECT 1"))
        >>> engine_mgr.close()
    """

    def __init__(
        self,
        *,
        project_id: str,
        region: str,
        instance: str,
        database: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
        pool_size: int = 5,
        max_overflow: int = 2,
        pool_timeout: int = 30,
        pool_pre_ping: bool = True,
    ) -> None:
        """Initialize Cloud SQL engine with connection parameters.
        
        Args:
            project_id: GCP project ID containing the Cloud SQL instance
            region: Cloud SQL instance region (e.g., "us-central1")
            instance: Cloud SQL instance name (not the connection name)
            database: Target database name within the instance
            user: Database user (None triggers IAM auth, recommended)
            password: Database password (None with user=None uses IAM)
            pool_size: Max active connections (default: 5 for Cloud Run)
            max_overflow: Additional connections under load (default: 2)
            pool_timeout: Seconds to wait for connection (default: 30)
            pool_pre_ping: Test connections before use (default: True)
        
        Security:
            - Leave user=None and password=None for IAM authentication
            - IAM auth requires roles/cloudsql.client and database CONNECT
            - Never use password auth in production
        
        Raises:
            google.cloud.exceptions.GoogleCloudError: If IAM auth fails
            sqlalchemy.exc.OperationalError: If connection fails
        """
        self._connector = Connector()
        self._instance_conn_name = f"{project_id}:{region}:{instance}"
        self._database = database
        self._user = user
        self._password = password

        def getconn():
            """Create connection via Cloud SQL Connector.
            
            This function is called by SQLAlchemy's connection pool
            whenever a new database connection is needed. It uses the
            Cloud SQL Python Connector to establish a secure connection,
            handling IAM token refresh automatically.
            
            Returns:
                psycopg.Connection: Active database connection (IAM-authenticated)
            
            Important: Cloud SQL Connector v1.18+ only supports pg8000 driver
            for IAM Database Authentication. Use driver='pg8000' with
            enable_iam_auth=True for this authentication method.
            """
            import os
            
            # pg8000 driver expects "db" parameter, not "dbname"
            kwargs = {"db": self._database}
            
            if self._user and self._password:
                # Password authentication (not recommended for production)
                # This uses the standard PostgreSQL password auth (md5/scram)
                kwargs["user"] = self._user
                kwargs["password"] = self._password
                driver = "pg8000"
            else:
                # IAM DB Auth (recommended: no password storage, automatic token refresh)
                # Connector will automatically fetch and refresh IAM tokens
                # Only pg8000 driver supports this with Cloud SQL Connector v1.18+
                import google.auth
                from google.auth.transport.requests import Request as GoogleAuthRequest

                # Get the IAM user (service account email)
                iam_user = None

                # Priority 1: Try metadata server (most reliable in Cloud Run)
                if os.getenv('K_SERVICE'):  # Running in Cloud Run
                    try:
                        import requests
                        metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email"
                        headers = {"Metadata-Flavor": "Google"}
                        response = requests.get(metadata_url, headers=headers, timeout=1)
                        if response.status_code == 200:
                            iam_user = response.text.strip()
                    except Exception:
                        pass

                # Priority 2: Try getting from default credentials
                if not iam_user:
                    try:
                        credentials, project = google.auth.default()
                        # Service account credentials have service_account_email
                        if hasattr(credentials, 'service_account_email'):
                            email = credentials.service_account_email
                            # Filter out "default" placeholder
                            if email and email != "default":
                                iam_user = email
                        elif hasattr(credentials, '_service_account_email'):
                            email = credentials._service_account_email
                            if email and email != "default":
                                iam_user = email
                    except Exception:
                        pass

                # Priority 3: Last resort - gcloud config (local development)
                if not iam_user:
                    try:
                        import subprocess
                        result = subprocess.check_output(
                            ['gcloud', 'config', 'get-value', 'account'],
                            text=True,
                            stderr=subprocess.DEVNULL
                        ).strip()
                        if result and '@' in result:
                            iam_user = result
                    except Exception:
                        pass

                # Final fallback: use postgres user (legacy default, requires password)
                if not iam_user:
                    iam_user = "postgres"

                # For Cloud SQL IAM DB Auth with PostgreSQL:
                # - Database user must be the full IAM principal email (service account)
                # - Password must be a fresh OAuth2 access token (manual IAM auth)
                # - Driver must be pg8000 (connector handles secure networking)
                kwargs["user"] = iam_user

                # Manually fetch an OAuth2 access token and use it as the password.
                # This avoids relying on connector-side enable_iam_auth behavior and
                # guarantees pg8000 receives a non-None password (prevents .decode errors).
                try:
                    credentials, _ = google.auth.default()
                    if not getattr(credentials, "valid", False):
                        credentials.refresh(GoogleAuthRequest())
                    token = getattr(credentials, "token", None)
                    if not token:
                        raise RuntimeError("Failed to obtain IAM access token for DB auth")
                    kwargs["password"] = token
                except Exception as e:
                    # Fall back to connector-managed IAM auth if available
                    # If this also fails, pg8000 will raise clearly.
                    kwargs["enable_iam_auth"] = True  # type: ignore[assignment]
                    logging.getLogger(__name__).warning(
                        f"Manual IAM token fetch failed ({e}); falling back to enable_iam_auth=True"
                    )
                driver = "pg8000"
            
            # Log connection parameters (non-sensitive)
            logging.getLogger(__name__).info(
                "CloudSQLEngine connecting",
                extra={
                    "instance": self._instance_conn_name,
                    "database": self._database,
                    "driver": driver,
                    "iam_auth": bool(kwargs.get("enable_iam_auth", False) or bool(kwargs.get("password"))),
                    "user_present": bool(kwargs.get("user")),
                },
            )

            return self._connector.connect(
                self._instance_conn_name,
                driver=driver,  # pg8000 is the only driver supporting IAM auth
                **kwargs,
            )

        # Create SQLAlchemy engine with custom connection factory
        # "postgresql+psycopg://" tells SQLAlchemy to use psycopg3 dialect
        # The creator function bypasses standard connection URL parsing
        self._engine: Engine = create_engine(
            "postgresql+pg8000://",
            creator=getconn,  # type: ignore[arg-type]
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_pre_ping=pool_pre_ping,  # Validate before use
        )

    @property
    def engine(self) -> Engine:
        """Get the managed SQLAlchemy engine instance.
        
        Returns:
            Engine: SQLAlchemy 2.x Engine ready for use
        
        Usage:
            >>> with engine_mgr.engine.connect() as conn:
            ...     result = conn.execute(text("SELECT 1"))
        """
        return self._engine

    def close(self) -> None:
        """Close engine and underlying Cloud SQL Connector.
        
        This method should be called during application shutdown to
        gracefully close all pooled connections and the Cloud SQL
        Connector. Failure to call this may leave connections open.
        
        Safe to call multiple times (idempotent).
        
        Example:
            >>> engine_mgr = CloudSQLEngine(...)
            >>> try:
            ...     # Use engine
            ...     pass
            ... finally:
            ...     engine_mgr.close()
        """
        try:
            # Dispose of all pooled connections
            self._engine.dispose()
        finally:
            # Always close the Cloud SQL Connector
            self._connector.close()
