"""Admin role authorization for ingestion operations."""
from typing import Optional
from fastmcp import Context
from config import get_admin_role_claim, get_admin_role_value

async def require_admin_role(ctx: Optional[Context]) -> bool:
    """Verify user has admin role from JWT token.
    
    Args:
        ctx: FastMCP context with user claims
        
    Returns:
        True if admin
        
    Raises:
        PermissionError: If user is not admin or not authenticated
    """
    if not ctx or not ctx.user:
        raise PermissionError("Authentication required for ingestion operations")
    
    role_claim = get_admin_role_claim()
    required_role = get_admin_role_value()
    
    user_role = ctx.user.get(role_claim) if isinstance(ctx.user, dict) else None
    
    if user_role != required_role:
        raise PermissionError(f"Admin privileges required. User role: {user_role}")
    
    return True
