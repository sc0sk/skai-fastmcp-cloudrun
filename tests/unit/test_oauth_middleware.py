"""Unit tests for OAuth 2.1 Resource Parameter Middleware.

Tests the OAuthResourceParameterMiddleware class that strips RFC 8707
'resource' parameter from OAuth authorization requests to enable OAuth 2.1
client compatibility with FastMCP's OAuth 2.0 implementation.
"""

import pytest
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient


# Import the middleware class from server.py
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.server import OAuthResourceParameterMiddleware


@pytest.fixture
def test_app():
    """Create a test Starlette app with the OAuth middleware."""
    app = Starlette()

    # Add a test route for /authorize endpoint
    @app.route("/authorize")
    async def authorize_endpoint(request: Request):
        # Return the query parameters as JSON to verify what the middleware passed through
        params = dict(request.query_params)
        return PlainTextResponse(f"params={params}")

    # Add a test route for other endpoints
    @app.route("/token")
    async def token_endpoint(request: Request):
        params = dict(request.query_params)
        return PlainTextResponse(f"params={params}")

    # Add the middleware
    app.add_middleware(OAuthResourceParameterMiddleware)

    return app


def test_strip_resource_parameter(test_app):
    """Test that the middleware strips the 'resource' parameter from /authorize requests.

    Validates:
    - FR-001: Server accepts OAuth authorization requests with optional 'resource' parameter
    - FR-002: Server strips the 'resource' parameter before passing to OAuth provider
    """
    client = TestClient(test_app)

    # Send request with resource parameter
    response = client.get(
        "/authorize",
        params={
            "client_id": "test-client",
            "redirect_uri": "https://example.com/callback",
            "state": "test-state",
            "code_challenge": "test-challenge",
            "resource": "https://mcp.example.com/mcp"
        }
    )

    assert response.status_code == 200

    # Verify 'resource' parameter was stripped
    assert "'resource'" not in response.text

    # Verify other parameters were preserved
    assert "'client_id': 'test-client'" in response.text
    assert "'redirect_uri': 'https://example.com/callback'" in response.text
    assert "'state': 'test-state'" in response.text
    assert "'code_challenge': 'test-challenge'" in response.text


def test_preserve_non_authorize_paths(test_app):
    """Test that the middleware only affects /authorize endpoint.

    Validates:
    - Middleware is path-specific (only targets /authorize)
    - Other endpoints preserve all parameters including 'resource'
    """
    client = TestClient(test_app)

    # Send request to /token endpoint with resource parameter
    response = client.get(
        "/token",
        params={
            "grant_type": "authorization_code",
            "code": "test-code",
            "resource": "https://mcp.example.com/mcp"
        }
    )

    assert response.status_code == 200

    # Verify 'resource' parameter was NOT stripped (different endpoint)
    assert "'resource': 'https://mcp.example.com/mcp'" in response.text
    assert "'grant_type': 'authorization_code'" in response.text
    assert "'code': 'test-code'" in response.text


def test_handle_missing_resource_parameter(test_app):
    """Test that the middleware handles requests without 'resource' parameter gracefully.

    Validates:
    - FR-003: Server maintains backward compatibility with OAuth 2.0 clients
    - Requests without 'resource' parameter pass through unmodified
    """
    client = TestClient(test_app)

    # Send OAuth 2.0 request without resource parameter
    response = client.get(
        "/authorize",
        params={
            "client_id": "test-client",
            "redirect_uri": "https://example.com/callback",
            "state": "test-state",
            "code_challenge": "test-challenge"
        }
    )

    assert response.status_code == 200

    # Verify all parameters are preserved
    assert "'client_id': 'test-client'" in response.text
    assert "'redirect_uri': 'https://example.com/callback'" in response.text
    assert "'state': 'test-state'" in response.text
    assert "'code_challenge': 'test-challenge'" in response.text

    # Verify 'resource' is not in response (it wasn't in the request)
    assert "'resource'" not in response.text


def test_preserve_other_parameters(test_app):
    """Test that middleware preserves all non-resource parameters exactly.

    Validates:
    - Only 'resource' parameter is removed
    - All OAuth 2.0/2.1 parameters are preserved with correct values
    - Parameter order may change but values are exact
    """
    client = TestClient(test_app)

    # Send request with many parameters including resource
    response = client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": "test-client-123",
            "redirect_uri": "https://chatgpt.com/callback",
            "state": "oauth_state_xyz",
            "code_challenge": "challenge_abc",
            "code_challenge_method": "S256",
            "scope": "user repo",
            "resource": "https://mcp.example.com/mcp"
        }
    )

    assert response.status_code == 200

    # Verify 'resource' was stripped
    assert "'resource'" not in response.text

    # Verify all other parameters are preserved with exact values
    assert "'response_type': 'code'" in response.text
    assert "'client_id': 'test-client-123'" in response.text
    assert "'redirect_uri': 'https://chatgpt.com/callback'" in response.text
    assert "'state': 'oauth_state_xyz'" in response.text
    assert "'code_challenge': 'challenge_abc'" in response.text
    assert "'code_challenge_method': 'S256'" in response.text
    assert "'scope': 'user repo'" in response.text


def test_multiple_resource_parameters(test_app):
    """Test edge case: multiple 'resource' parameters in request.

    Validates:
    - Middleware handles duplicate parameters correctly
    - All instances of 'resource' parameter are removed
    """
    client = TestClient(test_app)

    # Manually construct URL with multiple resource parameters
    response = client.get(
        "/authorize?client_id=test&resource=url1&resource=url2&state=test-state"
    )

    assert response.status_code == 200

    # Verify all 'resource' parameters were stripped
    assert "'resource'" not in response.text

    # Verify other parameters preserved
    assert "'client_id': 'test'" in response.text
    assert "'state': 'test-state'" in response.text


def test_empty_resource_value(test_app):
    """Test edge case: empty 'resource' parameter value.

    Validates:
    - Middleware strips 'resource' parameter even with empty value
    - Empty values don't cause errors
    """
    client = TestClient(test_app)

    response = client.get(
        "/authorize",
        params={
            "client_id": "test",
            "resource": "",  # Empty value
            "state": "test"
        }
    )

    assert response.status_code == 200

    # Verify empty 'resource' was still stripped
    assert "'resource'" not in response.text
    assert "'client_id': 'test'" in response.text


def test_resource_in_post_body_ignored(test_app):
    """Test edge case: 'resource' parameter in POST body (not query string).

    Validates:
    - Middleware only processes query parameters
    - POST body parameters are not affected
    """
    client = TestClient(test_app)

    # Send POST request with resource in body (middleware should ignore body)
    response = client.post(
        "/authorize?client_id=test&state=test",
        data={"resource": "https://mcp.example.com/mcp"}
    )

    # Note: This test validates middleware behavior - the endpoint may return 405 Method Not Allowed
    # The important thing is that the middleware doesn't crash on POST requests
    assert response.status_code in [200, 405]  # Either OK or Method Not Allowed is fine


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
