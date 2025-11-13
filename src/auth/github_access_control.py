"""
GitHub OAuth access control for FastMCP.

Restricts access to specific GitHub usernames and email addresses.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_allowed_github_usernames() -> list[str]:
    """
    Get allowed GitHub usernames from environment or Secret Manager.

    Returns:
        List of allowed GitHub usernames (or ['*'] for all users)
    """
    # Check environment variable first
    usernames_str = os.getenv("GITHUB_ALLOWED_USERNAMES", "")

    if usernames_str:
        # Split comma-separated list
        usernames = [u.strip() for u in usernames_str.split(",") if u.strip()]
        if usernames:
            logger.info(f"Loaded {len(usernames)} allowed GitHub usernames from environment")
            return usernames

    # Default: allow all (wildcard)
    logger.warning("No GitHub username restrictions configured - allowing all users")
    return ["*"]


def get_allowed_emails() -> list[str]:
    """
    Get allowed email addresses from environment.

    Returns:
        List of allowed email addresses (or [] for no email restrictions)
    """
    emails_str = os.getenv("GITHUB_ALLOWED_EMAILS", "")

    if emails_str:
        emails = [e.strip() for e in emails_str.split(",") if e.strip()]
        if emails:
            logger.info(f"Loaded {len(emails)} allowed email addresses")
            return emails

    return []


def is_user_allowed(github_username: Optional[str], email: Optional[str] = None) -> bool:
    """
    Check if a GitHub user is allowed to access the MCP server.

    Args:
        github_username: GitHub username (login)
        email: User's email address (optional)

    Returns:
        True if user is allowed, False otherwise
    """
    allowed_usernames = get_allowed_github_usernames()
    allowed_emails = get_allowed_emails()

    # If wildcard, allow everyone
    if "*" in allowed_usernames and not allowed_emails:
        return True

    # Check username allowlist
    if github_username and github_username in allowed_usernames:
        logger.info(f"User {github_username} authorized via username allowlist")
        return True

    # Check email allowlist
    if email and allowed_emails and email in allowed_emails:
        logger.info(f"User {email} authorized via email allowlist")
        return True

    # User not authorized
    logger.warning(
        f"Access denied for user: {github_username} ({email}). "
        f"Allowed usernames: {allowed_usernames}, Allowed emails: {allowed_emails}"
    )
    return False
