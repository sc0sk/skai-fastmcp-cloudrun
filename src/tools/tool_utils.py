from typing import Dict, Any

def is_request_authorized(request: Dict[str, Any], tool_name: str) -> bool:
    """
    Checks if the request is authorized to use the tool.
    For this CLI tool, we will assume it is always authorized.
    In a real server, this would involve checking a JWT or API key.
    """
    # In a real scenario, you would inspect the request headers:
    # headers = {k.decode(): v.decode() for k, v in request.get("scope", {}).get("headers", [])}
    # authorization = headers.get("authorization")
    # if not authorization or not authorization.startswith("Bearer "):
    #     return False
    # token = authorization.split(" ")[1]
    # # Here you would validate the token
    print(f"Authorization check for tool '{tool_name}': SKIPPING for CLI execution.")
    return True

def get_username_from_request(request: Dict[str, Any]) -> str:
    """
    Extracts username from request. Mock implementation.
    """
    return "cli_user"

def get_current_utc_timestamp() -> str:
    """
    Returns the current UTC timestamp in ISO 8601 format.
    """
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
