"""Pytest fixtures for mocking Cloud Run environment and IAM detection.

This module provides fixtures for testing IAM authentication logic in both
Cloud Run and local development environments without requiring actual
credentials or Cloud Run deployment.

Fixtures:
- mock_cloud_run_env: Sets Cloud Run environment variables (K_SERVICE, K_REVISION)
- mock_metadata_service: Mocks HTTP requests to Cloud Run metadata service
- mock_local_adc: Mocks google.auth.default() for local development testing
- mock_default_placeholder: Mocks ADC returning "default" placeholder (error case)
- mock_gcloud_config: Mocks gcloud CLI config command

Usage:
    import pytest
    from tests.mocks.cloud_run_fixtures import *

    def test_cloud_run_detection(mock_cloud_run_env, mock_metadata_service):
        # Test will have K_SERVICE set and metadata endpoint mocked
        from src.storage.cloud_sql_engine import CloudSQLEngine
        engine = CloudSQLEngine(...)
        assert engine.detected_iam_user == "test-sa@project.iam.gserviceaccount.com"
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_cloud_run_env(monkeypatch):
    """Mock Cloud Run environment variables.

    Sets K_SERVICE and K_REVISION environment variables to simulate
    running inside a Cloud Run container.

    Args:
        monkeypatch: pytest monkeypatch fixture

    Yields:
        None (environment variables are set for test duration)

    Example:
        def test_cloud_run_detection(mock_cloud_run_env):
            import os
            assert os.getenv('K_SERVICE') == 'test-service'
    """
    monkeypatch.setenv('K_SERVICE', 'test-service')
    monkeypatch.setenv('K_REVISION', 'test-revision-001')
    yield


@pytest.fixture
def mock_metadata_service(requests_mock):
    """Mock Cloud Run metadata service HTTP endpoint.

    Mocks the metadata.google.internal endpoint that Cloud Run containers
    use to fetch service account information.

    Args:
        requests_mock: pytest-requests-mock fixture

    Returns:
        Mock object configured to respond with test service account email

    Example:
        def test_metadata_fetch(mock_metadata_service):
            import requests
            resp = requests.get(
                'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email',
                headers={'Metadata-Flavor': 'Google'}
            )
            assert resp.text == '666924716777-compute@developer.gserviceaccount.com'
    """
    return requests_mock.get(
        'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email',
        text='666924716777-compute@developer.gserviceaccount.com',
        request_headers={'Metadata-Flavor': 'Google'}
    )


@pytest.fixture
def mock_local_adc():
    """Mock google.auth.default() for local development.

    Mocks Application Default Credentials to return a test service account
    without requiring actual credentials file.

    Yields:
        MagicMock: Mocked credentials object with service_account_email attribute

    Example:
        def test_local_adc_detection(mock_local_adc):
            import google.auth
            creds, project = google.auth.default()
            assert creds.service_account_email == 'fastmcp-server@project.iam.gserviceaccount.com'
    """
    with patch('google.auth.default') as mock_auth:
        mock_creds = MagicMock()
        mock_creds.service_account_email = 'fastmcp-server@skai-fastmcp-cloudrun.iam.gserviceaccount.com'
        mock_creds.valid = True
        mock_creds.token = 'mock-oauth2-token'
        mock_creds.universe_domain = "googleapis.com"  # Fix universe domain check
        mock_auth.return_value = (mock_creds, 'skai-fastmcp-cloudrun')
        yield mock_auth


@pytest.fixture
def mock_default_placeholder():
    """Mock ADC returning 'default' placeholder (error case).

    Simulates the bug where google.auth.default() returns a credentials
    object with service_account_email = "default" instead of the actual
    service account email.

    Yields:
        MagicMock: Mocked credentials object with "default" placeholder

    Example:
        def test_rejects_default_placeholder(mock_default_placeholder):
            import google.auth
            creds, project = google.auth.default()
            assert creds.service_account_email == "default"  # Should be filtered out
    """
    with patch('google.auth.default') as mock_auth:
        mock_creds = MagicMock()
        mock_creds.service_account_email = "default"  # Placeholder value
        mock_creds.valid = False
        mock_creds.token = None
        mock_creds.universe_domain = "googleapis.com"  # Fix universe domain check
        mock_auth.return_value = (mock_creds, 'skai-fastmcp-cloudrun')
        yield mock_auth


@pytest.fixture
def mock_gcloud_config():
    """Mock gcloud config get-value account command.

    Mocks subprocess call to gcloud CLI for local development fallback.

    Yields:
        MagicMock: Mocked subprocess.check_output

    Example:
        def test_gcloud_fallback(mock_gcloud_config):
            import subprocess
            result = subprocess.check_output(['gcloud', 'config', 'get-value', 'account'])
            assert 'developer@example.com' in result.decode()
    """
    with patch('subprocess.check_output') as mock_subprocess:
        mock_subprocess.return_value = 'developer@example.com\n'
        yield mock_subprocess
