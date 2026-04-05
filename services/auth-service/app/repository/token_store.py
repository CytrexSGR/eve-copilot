"""File-based token storage."""

import json
import aiofiles
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone

from app.models.token import StoredToken, AuthState


class TokenStore:
    """File-based storage for OAuth tokens and PKCE states."""

    def __init__(self, token_file: str, state_file: str):
        self.token_file = Path(token_file)
        self.state_file = Path(state_file)
        self._ensure_files()

    def _ensure_files(self):
        """Ensure storage files exist."""
        for file_path in [self.token_file, self.state_file]:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if not file_path.exists():
                file_path.write_text("{}")

    async def _read_json(self, file_path: Path) -> dict:
        """Read JSON file asynchronously."""
        async with aiofiles.open(file_path, "r") as f:
            content = await f.read()
            return json.loads(content) if content else {}

    async def _write_json(self, file_path: Path, data: dict):
        """Write JSON file asynchronously."""
        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(data, indent=2, default=str))

    async def save_token(self, character_id: int, token: StoredToken):
        """Save token for character."""
        tokens = await self._read_json(self.token_file)
        tokens[str(character_id)] = token.model_dump()
        await self._write_json(self.token_file, tokens)

    def _parse_datetime(self, value) -> datetime:
        """Parse datetime from either ISO string or Unix timestamp."""
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        elif isinstance(value, str):
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        return value

    async def get_token(self, character_id: int) -> Optional[StoredToken]:
        """Get token for character."""
        tokens = await self._read_json(self.token_file)
        data = tokens.get(str(character_id))
        if data:
            # Parse datetime - handle both Unix timestamps and ISO strings
            data["expires_at"] = self._parse_datetime(data["expires_at"])
            data["updated_at"] = self._parse_datetime(data.get("updated_at", datetime.now(timezone.utc)))
            return StoredToken(**data)
        return None

    async def delete_token(self, character_id: int) -> bool:
        """Delete token for character."""
        tokens = await self._read_json(self.token_file)
        if str(character_id) in tokens:
            del tokens[str(character_id)]
            await self._write_json(self.token_file, tokens)
            return True
        return False

    async def list_tokens(self) -> List[StoredToken]:
        """List all stored tokens."""
        tokens = await self._read_json(self.token_file)
        result = []
        for data in tokens.values():
            data["expires_at"] = self._parse_datetime(data["expires_at"])
            data["updated_at"] = self._parse_datetime(data.get("updated_at", datetime.now(timezone.utc)))
            result.append(StoredToken(**data))
        return result

    async def save_state(self, state: str, auth_state: AuthState):
        """Save PKCE state."""
        states = await self._read_json(self.state_file)
        states[state] = auth_state.model_dump()
        await self._write_json(self.state_file, states)

    async def get_state(self, state: str) -> Optional[AuthState]:
        """Get PKCE state."""
        states = await self._read_json(self.state_file)
        data = states.get(state)
        if data:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
            return AuthState(**data)
        return None

    async def delete_state(self, state: str) -> bool:
        """Delete PKCE state."""
        states = await self._read_json(self.state_file)
        if state in states:
            del states[state]
            await self._write_json(self.state_file, states)
            return True
        return False
