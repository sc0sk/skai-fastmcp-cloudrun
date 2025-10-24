"""Unit tests for admin authentication."""
import pytest
from tools.ingestion_utils.auth import require_admin_role
from fastmcp import Context
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_require_admin_role_valid():
    """Test admin role verification with valid admin user."""
    ctx = MagicMock(spec=Context)
    ctx.user = {"role": "admin"}
    
    with patch('tools.ingestion_utils.auth.get_admin_role_claim', return_value='role'):
        with patch('tools.ingestion_utils.auth.get_admin_role_value', return_value='admin'):
            result = await require_admin_role(ctx)
            assert result is True


@pytest.mark.asyncio
async def test_require_admin_role_invalid():
    """Test admin role verification with non-admin user."""
    ctx = MagicMock(spec=Context)
    ctx.user = {"role": "user"}
    
    with patch('tools.ingestion_utils.auth.get_admin_role_claim', return_value='role'):
        with patch('tools.ingestion_utils.auth.get_admin_role_value', return_value='admin'):
            with pytest.raises(PermissionError, match="Admin privileges required"):
                await require_admin_role(ctx)


@pytest.mark.asyncio
async def test_require_admin_role_no_auth():
    """Test admin role verification without authentication."""
    ctx = None
    
    with pytest.raises(PermissionError, match="Authentication required"):
        await require_admin_role(ctx)


@pytest.mark.asyncio
async def test_require_admin_role_no_user():
    """Test admin role verification with context but no user."""
    ctx = MagicMock(spec=Context)
    ctx.user = None
    
    with pytest.raises(PermissionError, match="Authentication required"):
        await require_admin_role(ctx)
