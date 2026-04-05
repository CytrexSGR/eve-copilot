"""
Character Sync Service for EVE Co-Pilot

Refactored to use Template Method pattern with sync operation classes.
"""
import logging
from typing import Dict, Any, Optional

from src.core.config import get_settings
from src.core.database import DatabasePool
from src.services.character.service import CharacterService
from src.services.auth.service import AuthService
from src.services.auth.repository import AuthRepository
from src.integrations.esi.client import ESIClient

from services.character_sync.orchestrator import SyncOrchestrator
from services.character_sync.wallet_sync import WalletSync
from services.character_sync.skills_sync import SkillsSync
from services.character_sync.skill_queue_sync import SkillQueueSync
from services.character_sync.assets_sync import AssetsSync
from services.character_sync.orders_sync import OrdersSync
from services.character_sync.industry_jobs_sync import IndustryJobsSync
from services.character_sync.blueprints_sync import BlueprintsSync

logger = logging.getLogger(__name__)


def _create_character_service() -> CharacterService:
    """Create a CharacterService instance with proper dependencies."""
    settings = get_settings()
    db = DatabasePool(settings)
    esi_client = ESIClient()
    auth_repository = AuthRepository()
    auth_service = AuthService(auth_repository, esi_client, settings)
    return CharacterService(esi_client, auth_service, db)


class CharacterSyncService:
    """
    Service for syncing character data from ESI to PostgreSQL.

    Delegates to sync operation classes for each data type.
    """

    def __init__(self, character_service: Optional[CharacterService] = None):
        """Initialize with optional CharacterService injection."""
        self._character_service = character_service
        self._orchestrator = None

    @property
    def character_service(self) -> CharacterService:
        """Get or create CharacterService with lazy initialization."""
        if self._character_service is None:
            self._character_service = _create_character_service()
        return self._character_service

    @property
    def orchestrator(self) -> SyncOrchestrator:
        """Get or create SyncOrchestrator."""
        if self._orchestrator is None:
            self._orchestrator = SyncOrchestrator(self.character_service)
        return self._orchestrator

    def sync_wallet(self, character_id: int) -> Dict[str, Any]:
        """Sync character wallet balance."""
        return WalletSync(self.character_service).sync(character_id)

    def sync_skills(self, character_id: int) -> Dict[str, Any]:
        """Sync character skills."""
        return SkillsSync(self.character_service).sync(character_id)

    def sync_skill_queue(self, character_id: int) -> Dict[str, Any]:
        """Sync character skill queue."""
        return SkillQueueSync(self.character_service).sync(character_id)

    def sync_assets(self, character_id: int) -> Dict[str, Any]:
        """Sync character assets."""
        return AssetsSync(self.character_service).sync(character_id)

    def sync_orders(self, character_id: int) -> Dict[str, Any]:
        """Sync character market orders."""
        return OrdersSync(self.character_service).sync(character_id)

    def sync_industry_jobs(self, character_id: int) -> Dict[str, Any]:
        """Sync character industry jobs."""
        return IndustryJobsSync(self.character_service).sync(character_id)

    def sync_blueprints(self, character_id: int) -> Dict[str, Any]:
        """Sync character blueprints."""
        return BlueprintsSync(self.character_service).sync(character_id)

    def sync_all(self, character_id: int) -> Dict[str, Any]:
        """Sync all character data using orchestrator."""
        return self.orchestrator.sync_all(character_id)


# Module-level instance for backwards compatibility
character_sync_service = CharacterSyncService()
