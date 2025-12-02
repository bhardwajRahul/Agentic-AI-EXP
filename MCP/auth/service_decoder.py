import functools
import logging
import os
from typing import Callable, Dict
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = {
    "gmail": [
        "https://mail.google.com/",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.settings.basic",
        "https://www.googleapis.com/auth/gmail.settings.sharing",
    ],
    "calendar_read": [
        "https://www.googleapis.com/auth/calendar.readonly",
    ],
    "calendar_events": [
        "https://www.googleapis.com/auth/calendar.events",
    ],
    "calendar": [
        "https://www.googleapis.com/auth/calendar",
    ],
}

_service_cache: Dict[str, any] = {}


def get_google_service(
    service_type: str,
    scope_key: str,
    token_path: str,
    creds_path: str,
    force_refresh: bool = False,
):
    """
    Get or create Google API service with proper authentication.

    Args:
        service_type: Type of service ('gmail', 'calendar', etc.)
        scope_key: Key for scopes in SCOPES dict
        token_path: Path to token file
        creds_path: Path to credentials file
        force_refresh: Force creation of new service

    Returns:
        Authenticated Google API service
    """

    cache_key = f"{service_type}_{scope_key}"
    if not force_refresh and cache_key in _service_cache:
        logger.info(f"Using cached service for {cache_key}")
        return _service_cache[cache_key]

    creds = None
    scopes = SCOPES.get(scope_key, [])

    logger.info(f"Authenticating {service_type} with scopes: {scope_key}")

    if os.path.exists(token_path):
        logger.info(f"Loading token from {token_path}")
        try:
            creds = Credentials.from_authorized_user_file(token_path, scopes)
        except Exception as e:
            logger.error(f"Failed to load token: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired token")
            try:
                creds.refresh(Request())
                logger.info("Token refreshed successfully")
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                logger.info("Will request new token")
                creds = None

        if not creds:
            logger.info("Requesting new token from user")
            if not os.path.exists(creds_path):
                raise FileNotFoundError(
                    f"Credentials file not found: {creds_path}\n"
                    f"Please download it from Google Cloud Console"
                )

            flow = InstalledAppFlow.from_client_secrets_file(creds_path, scopes)
            creds = flow.run_local_server(port=0)
            logger.info("New token obtained")

        try:
            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())
                logger.info(f"Token saved to {token_path}")
        except Exception as e:
            logger.error(f"Failed to save token: {e}")

    version = "v1"
    service = build(service_type, version, credentials=creds)
    logger.info(f"Service {service_type} v{version} built successfully")

    _service_cache[cache_key] = service

    return service


def require_google_service(service_type: str, scope_key: str):
    """
    Decorator to inject authenticated Google service into function.

    Args:
        service_type: Type of service ('gmail', 'calendar', etc.)
        scope_key: Key for scopes in SCOPES dict

    Usage:
        @require_google_service("gmail", "gmail")
        async def send_email(service, recipient: str, subject: str, body: str):
            # service is automatically injected as first parameter
            result = service.users().messages().send(...).execute()
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get paths from environment or use defaults
            base_dir = Path(__file__).parent.parent
            token_path = os.getenv(
                "GOOGLE_TOKEN_PATH", str(base_dir / "cred" / "token.json")
            )
            creds_path = os.getenv(
                "GOOGLE_CREDENTIALS_PATH", str(base_dir / "cred" / "credentials.json")
            )

            # Get authenticated service
            try:
                service = get_google_service(
                    service_type, scope_key, token_path, creds_path
                )
            except FileNotFoundError as e:
                logger.error(str(e))
                return {"error": str(e)}
            except Exception as e:
                logger.error(f"Authentication failed: {e}")
                return {"error": f"Authentication failed: {str(e)}"}

            # Inject service as first argument
            return await func(service, *args, **kwargs)

        return wrapper

    return decorator


def clear_service_cache():
    """Clear the service cache to force re-authentication"""
    global _service_cache
    _service_cache.clear()
    logger.info("Service cache cleared")
