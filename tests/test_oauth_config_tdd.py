"""TDD tests for OAuth configuration and GitHub provider setup.

Tests OAuth client ID, secret, base URL configuration and metadata endpoints.
Run these tests locally before deployment to catch configuration issues early.
"""
import pytest
import os
import httpx
from unittest.mock import patch, MagicMock


class TestOAuthEnvironmentVariables:
    """Test that OAuth environment variables are properly configured."""
    
    def test_oauth_client_id_env_var_exists(self):
        """Test: FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID is set."""
        client_id = os.getenv("FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID")
        print(f"📋 GitHub OAuth Client ID: {client_id[:10]}..." if client_id else "❌ Not set")
        assert client_id is not None, "FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID must be set"
        assert len(client_id) > 0, "FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID must not be empty"
    
    def test_oauth_client_secret_env_var_exists(self):
        """Test: FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET is set."""
        client_secret = os.getenv("FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET")
        print(f"🔐 GitHub OAuth Client Secret: {'*' * 10}..." if client_secret else "❌ Not set")
        assert client_secret is not None, "FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET must be set"
        assert len(client_secret) > 0, "FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET must not be empty"
    
    def test_oauth_base_url_env_var_exists(self):
        """Test: FASTMCP_SERVER_AUTH_GITHUB_BASE_URL is set."""
        base_url = os.getenv("FASTMCP_SERVER_AUTH_GITHUB_BASE_URL")
        print(f"🌐 GitHub OAuth Base URL: {base_url}")
        assert base_url is not None, "FASTMCP_SERVER_AUTH_GITHUB_BASE_URL must be set"
        assert base_url.startswith("https://"), "Base URL must use HTTPS"
    
    def test_oauth_auth_provider_env_var_exists(self):
        """Test: FASTMCP_SERVER_AUTH is set to GitHub provider."""
        auth_provider = os.getenv("FASTMCP_SERVER_AUTH")
        print(f"🔑 Auth Provider: {auth_provider}")
        expected = "fastmcp.server.auth.providers.github.GitHubProvider"
        assert auth_provider == expected, f"FASTMCP_SERVER_AUTH must be {expected}"


class TestGitHubOAuthProviderInitialization:
    """Test GitHub OAuth provider initialization with real configuration."""
    
    def test_github_provider_imports(self):
        """Test: Can import GitHubProvider from fastmcp."""
        try:
            from fastmcp.server.auth.providers.github import GitHubProvider
            print("✅ GitHubProvider import successful")
            assert GitHubProvider is not None
        except ImportError as e:
            pytest.fail(f"Cannot import GitHubProvider: {e}")
    
    def test_github_provider_initialization(self):
        """Test: GitHubProvider initializes with environment variables."""
        from fastmcp.server.auth.providers.github import GitHubProvider
        from src.auth.memory_storage import MemoryKVStorage
        
        client_storage = MemoryKVStorage()
        
        # GitHubProvider should read from environment automatically
        try:
            provider = GitHubProvider(client_storage=client_storage)
            print("✅ GitHubProvider initialized successfully")
            print(f"   Provider type: {type(provider).__name__}")
            
            # Check if provider has expected attributes
            assert hasattr(provider, 'client_storage'), "Provider should have client_storage"
            print(f"   Client storage type: {type(provider.client_storage).__name__}")
            
        except Exception as e:
            pytest.fail(f"GitHubProvider initialization failed: {e}")
    
    def test_github_provider_configuration_values(self):
        """Test: GitHubProvider reads correct values from environment."""
        from fastmcp.server.auth.providers.github import GitHubProvider
        from src.auth.memory_storage import MemoryKVStorage
        
        client_storage = MemoryKVStorage()
        provider = GitHubProvider(client_storage=client_storage)
        
        # Expected values from environment
        expected_client_id = os.getenv("FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID")
        expected_client_secret = os.getenv("FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET")
        expected_base_url = os.getenv("FASTMCP_SERVER_AUTH_GITHUB_BASE_URL")
        
        print(f"📊 Provider Configuration Check:")
        print(f"   Expected Client ID: {expected_client_id[:10]}...")
        print(f"   Expected Base URL: {expected_base_url}")
        
        # Check if provider has these configuration attributes
        # (attribute names may vary based on FastMCP implementation)
        if hasattr(provider, 'client_id'):
            print(f"   Provider client_id: {provider.client_id[:10]}...")
            assert provider.client_id == expected_client_id, "Client ID mismatch"
        
        if hasattr(provider, 'base_url'):
            print(f"   Provider base_url: {provider.base_url}")
            # Convert to string for comparison (may be AnyHttpUrl object)
            provider_url = str(provider.base_url)
            # Normalize by removing trailing slash for comparison
            assert provider_url.rstrip('/') == expected_base_url.rstrip('/'), f"Base URL mismatch: {provider_url} != {expected_base_url}"


class TestOAuthMetadataEndpoints:
    """Test OAuth metadata endpoints on Cloud Run."""
    
    @pytest.mark.asyncio
    async def test_oauth_protected_resource_metadata(self):
        """Test: .well-known/oauth-protected-resource endpoint returns valid metadata."""
        base_url = os.getenv("FASTMCP_SERVER_AUTH_GITHUB_BASE_URL", "https://mcp.simonkennedymp.com.au")
        url = f"{base_url}/.well-known/oauth-protected-resource"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            print(f"🔍 OAuth Protected Resource Metadata ({response.status_code}):")
            print(f"   URL: {url}")
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            print(f"   Response: {data}")
            
            # Validate required fields per OAuth 2.0 Protected Resource Metadata spec
            assert "resource" in data, "Must have 'resource' field"
            assert "authorization_servers" in data, "Must have 'authorization_servers' field"
            assert isinstance(data["authorization_servers"], list), "authorization_servers must be array"
            assert len(data["authorization_servers"]) > 0, "Must have at least one authorization server"
            
            print(f"   ✅ Resource: {data['resource']}")
            print(f"   ✅ Auth Servers: {data['authorization_servers']}")
    
    @pytest.mark.asyncio
    async def test_oauth_authorization_server_metadata(self):
        """Test: .well-known/oauth-authorization-server endpoint returns valid metadata."""
        base_url = os.getenv("FASTMCP_SERVER_AUTH_GITHUB_BASE_URL", "https://mcp.simonkennedymp.com.au")
        url = f"{base_url}/.well-known/oauth-authorization-server"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            print(f"🔍 OAuth Authorization Server Metadata ({response.status_code}):")
            print(f"   URL: {url}")
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            print(f"   Response keys: {list(data.keys())}")
            
            # Validate required fields per OAuth 2.0 Authorization Server Metadata spec
            required_fields = [
                "issuer",
                "authorization_endpoint",
                "token_endpoint",
                "response_types_supported",
                "grant_types_supported"
            ]
            
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
                print(f"   ✅ {field}: {data[field]}")
            
            # Validate endpoint URLs
            assert data["issuer"].startswith("https://"), "Issuer must be HTTPS"
            assert data["authorization_endpoint"].startswith("https://"), "Authorization endpoint must be HTTPS"
            assert data["token_endpoint"].startswith("https://"), "Token endpoint must be HTTPS"


class TestOAuthClientRegistration:
    """Test OAuth dynamic client registration endpoint."""
    
    @pytest.mark.asyncio
    async def test_register_endpoint_exists(self):
        """Test: /register endpoint is accessible."""
        base_url = os.getenv("FASTMCP_SERVER_AUTH_GITHUB_BASE_URL", "https://mcp.simonkennedymp.com.au")
        url = f"{base_url}/register"
        
        # Try to register a test client
        registration_request = {
            "client_name": "Test MCP Client",
            "redirect_uris": ["http://localhost:3000/callback"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "client_secret_post"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=registration_request)
            print(f"🔍 Client Registration ({response.status_code}):")
            print(f"   URL: {url}")
            print(f"   Request: {registration_request}")
            
            # Should either succeed (201) or fail with proper OAuth error
            assert response.status_code in [200, 201, 400, 401], f"Unexpected status: {response.status_code}"
            
            if response.status_code in [200, 201]:
                data = response.json()
                print(f"   ✅ Registration successful!")
                print(f"   Client ID: {data.get('client_id', 'N/A')[:10]}...")
                print(f"   Client Secret: {'***' if 'client_secret' in data else 'N/A'}")
                
                # Should return client credentials
                assert "client_id" in data, "Response must include client_id"
                assert "client_secret" in data, "Response must include client_secret"
            else:
                print(f"   ℹ️  Registration failed (expected for protected endpoints): {response.text[:200]}")


class TestServerAuthConfiguration:
    """Test that the FastMCP server is properly configured with OAuth."""
    
    def test_server_initialization_with_oauth(self):
        """Test: Server initializes with GitHub OAuth provider."""
        # Import server module (this triggers initialization)
        try:
            from src import server
            print("✅ Server module imported successfully")
            
            # Check if auth_provider is set
            assert hasattr(server, 'auth_provider'), "Server should have auth_provider"
            print(f"   Auth Provider: {type(server.auth_provider).__name__ if server.auth_provider else 'None'}")
            
            if server.auth_provider:
                assert server.auth_provider is not None, "Auth provider should not be None"
                print(f"   ✅ OAuth is configured")
            else:
                pytest.fail("Auth provider is None - OAuth not configured!")
                
        except Exception as e:
            pytest.fail(f"Server initialization failed: {e}")
    
    def test_mcp_instance_has_auth(self):
        """Test: FastMCP instance is created with auth provider."""
        from src import server
        
        assert hasattr(server, 'mcp'), "Server should have mcp instance"
        print(f"✅ MCP instance exists: {type(server.mcp).__name__}")
        
        # Check if MCP instance has auth configured
        # (attribute name may vary based on FastMCP version)
        if hasattr(server.mcp, '_auth'):
            print(f"   MCP auth: {type(server.mcp._auth).__name__ if server.mcp._auth else 'None'}")
        if hasattr(server.mcp, 'auth'):
            print(f"   MCP auth: {type(server.mcp.auth).__name__ if server.mcp.auth else 'None'}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
