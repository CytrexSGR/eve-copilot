"""Token and authentication models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class AuthUrlResponse(BaseModel):
    """Response for login endpoint."""
    auth_url: str


class OAuthTokenResponse(BaseModel):
    """OAuth token response."""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    character_id: int
    character_name: str


class CharacterInfo(BaseModel):
    """Character authentication info."""
    character_id: int
    character_name: str
    is_valid: bool
    needs_refresh: bool
    expires_at: str


class CharacterListResponse(BaseModel):
    """Response for characters list endpoint."""
    characters: List[CharacterInfo]


class StoredToken(BaseModel):
    """Token stored in database."""
    access_token: str
    refresh_token: str
    expires_at: datetime
    character_id: int
    character_name: str
    scopes: List[str]
    updated_at: datetime
    character_owner_hash: Optional[str] = None
    refresh_token_encrypted: Optional[bytes] = None
    is_encrypted: bool = False


class AuthState(BaseModel):
    """PKCE state for OAuth2 flow."""
    state: str
    code_verifier: str
    redirect_url: Optional[str] = None
    created_at: datetime
    expires_at: datetime
