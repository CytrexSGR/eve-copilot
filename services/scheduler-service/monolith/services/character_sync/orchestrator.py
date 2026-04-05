"""Orchestrator for character sync operations."""
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from src.services.character.service import CharacterService
from .wallet_sync import WalletSync
from .skills_sync import SkillsSync
from .skill_queue_sync import SkillQueueSync
from .assets_sync import AssetsSync
from .orders_sync import OrdersSync
from .industry_jobs_sync import IndustryJobsSync
from .blueprints_sync import BlueprintsSync

logger = logging.getLogger(__name__)


class SyncOrchestrator:
    """
    Orchestrates character sync operations.

    Coordinates all sync operations and aggregates results.
    Future: Add parallel execution with asyncio.
    """

    def __init__(self, character_service: Optional[CharacterService] = None):
        """Initialize with optional CharacterService."""
        self._character_service = character_service

    @property
    def character_service(self) -> CharacterService:
        """Lazy-load CharacterService."""
        if self._character_service is None:
            from services.character_sync_service import _create_character_service
            self._character_service = _create_character_service()
        return self._character_service

    def sync_all(self, character_id: int) -> Dict[str, Any]:
        """
        Run all sync operations for a character.

        Continues even if some syncs fail. Returns aggregated results.
        """
        logger.info(f"Starting full sync for character {character_id}")

        sync_operations = {
            "wallet": WalletSync(self.character_service),
            "skills": SkillsSync(self.character_service),
            "skill_queue": SkillQueueSync(self.character_service),
            "assets": AssetsSync(self.character_service),
            "orders": OrdersSync(self.character_service),
            "industry_jobs": IndustryJobsSync(self.character_service),
            "blueprints": BlueprintsSync(self.character_service),
        }

        results = {
            "character_id": character_id,
        }

        # Execute all syncs
        for name, operation in sync_operations.items():
            results[name] = operation.sync(character_id)

        # Count successes
        success_count = sum(
            1 for name in sync_operations.keys()
            if results.get(name, {}).get("success", False)
        )
        failure_count = len(sync_operations) - success_count

        results["success"] = success_count > 0
        results["summary"] = {
            "successful_syncs": success_count,
            "failed_syncs": failure_count,
            "synced_at": datetime.now().isoformat()
        }

        logger.info(f"Full sync completed: {success_count}/{len(sync_operations)} successful")
        return results
