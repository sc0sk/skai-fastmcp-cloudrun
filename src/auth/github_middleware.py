"""
Starlette middleware for GitHub OAuth access control.

Enforces username and email allowlists for GitHub-authenticated users.
"""
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from src.auth.github_access_control import is_user_allowed

logger = logging.getLogger(__name__)


class GitHubAccessControlMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce GitHub username and email allowlists.

    Checks authenticated user's GitHub username and email against allowlists.
    Returns 403 Forbidden if user is not authorized.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Check user authorization before processing request.

        Args:
            request: Starlette HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response (403 if unauthorized, or response from next handler)
        """
        # Skip auth check for OAuth endpoints (need to authenticate first)
        if request.url.path.startswith(("/.well-known", "/authorize", "/token", "/register", "/auth")):
            return await call_next(request)

        # Skip auth check for health/readiness endpoints
        if request.url.path in ("/health", "/", "/favicon.ico"):
            return await call_next(request)

        # Check if request has authenticated user
        # FastMCP stores user info in request.state after OAuth authentication
        user = getattr(request.state, "user", None)

        if user:
            # Extract GitHub username and email from user claims
            github_username = user.get("login") if isinstance(user, dict) else getattr(user, "login", None)
            email = user.get("email") if isinstance(user, dict) else getattr(user, "email", None)

            # Check if user is allowed
            if not is_user_allowed(github_username, email):
                logger.warning(
                    f"Access denied for GitHub user: {github_username} ({email})",
                    extra={"username": github_username, "email": email, "path": request.url.path}
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "forbidden",
                        "error_description": f"Access denied. User '{github_username}' is not authorized to access this resource."
                    }
                )

            logger.debug(f"Access granted for GitHub user: {github_username}")

        # User is authorized or endpoint doesn't require auth
        return await call_next(request)
