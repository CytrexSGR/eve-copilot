"""Root conftest for finance-service tests.

Sets required environment variables before any app imports trigger
pydantic ServiceConfig validation.
"""

import os

os.environ.setdefault("EVE_CLIENT_ID", "test_client_id")
os.environ.setdefault("EVE_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("EVE_CALLBACK_URL", "http://localhost/callback")
