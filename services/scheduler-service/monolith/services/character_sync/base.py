"""Base class for character sync operations using Template Method pattern."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging
import psycopg2

from src.database import get_db_connection
from src.core.exceptions import AuthenticationError, ExternalAPIError
from src.services.character.service import CharacterService

logger = logging.getLogger(__name__)

# Valid sync column names for SQL injection prevention
VALID_SYNC_COLUMNS = {
    "wallets_synced_at", "skills_synced_at", "skill_queue_synced_at",
    "assets_synced_at", "orders_synced_at", "industry_jobs_synced_at",
    "blueprints_synced_at", "sp_history_synced_at"
}


class BaseSyncOperation(ABC):
    """
    Abstract base class for character sync operations.

    Uses Template Method pattern: sync() is the template that calls
    abstract hooks in sequence.

    Subclasses must implement:
        - fetch_from_esi(character_id): Fetch data from ESI
        - transform_data(raw_data): Transform ESI response to DB format
        - save_to_db(character_id, data, conn): Save to database
        - get_sync_column(): Return the sync timestamp column name

    Optional overrides:
        - get_result_key(): Key name for result count (default: 'count')
        - get_result_value(data): Value to return (default: len(data))
    """

    def __init__(self, character_service: CharacterService):
        """Initialize with CharacterService for ESI access.

        Args:
            character_service: CharacterService instance for API calls
        """
        self.character_service = character_service

    def sync(self, character_id: int) -> Dict[str, Any]:
        """
        Template method for sync operations.

        Executes the sync algorithm:
        1. Fetch from ESI
        2. Transform data
        3. Save to database
        4. Update timestamp
        5. Return result

        Args:
            character_id: EVE character ID to sync

        Returns:
            Dict with success status and operation results
        """
        logger.info(f"Starting {self.__class__.__name__} for character {character_id}")

        try:
            # Step 1: Fetch from ESI
            raw_data = self.fetch_from_esi(character_id)

            # Step 2: Transform data
            transformed_data = self.transform_data(raw_data)

            # Step 3: Save to database
            with get_db_connection() as conn:
                self.save_to_db(character_id, transformed_data, conn)
                conn.commit()
                self._update_sync_timestamp(conn, character_id, self.get_sync_column())

            # Step 4: Return success result
            result = {
                "success": True,
                "character_id": character_id,
                self.get_result_key(): self.get_result_value(transformed_data)
            }
            logger.info(f"{self.__class__.__name__} completed for character {character_id}")
            return result

        except (AuthenticationError, ExternalAPIError) as e:
            logger.error(f"API error in {self.__class__.__name__}: {e}")
            return {"success": False, "error": str(e)}
        except psycopg2.Error as e:
            logger.error(f"Database error in {self.__class__.__name__}: {e}")
            return {"success": False, "error": f"Database error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error in {self.__class__.__name__}: {e}")
            return {"success": False, "error": str(e)}

    def _update_sync_timestamp(self, conn, character_id: int, column: str) -> None:
        """Update sync timestamp in character_sync_status table.

        Args:
            conn: Database connection
            character_id: EVE character ID
            column: Column name to update (must be in VALID_SYNC_COLUMNS)

        Raises:
            ValueError: If column name is not in whitelist
        """
        if column not in VALID_SYNC_COLUMNS:
            raise ValueError(f"Invalid sync column: {column}")
        try:
            with conn.cursor() as cursor:
                # Ensure row exists
                cursor.execute("""
                    INSERT INTO character_sync_status (character_id)
                    VALUES (%s)
                    ON CONFLICT (character_id) DO NOTHING
                """, (character_id,))

                # Update the specific timestamp
                cursor.execute(f"""
                    UPDATE character_sync_status
                    SET {column} = NOW(), updated_at = NOW()
                    WHERE character_id = %s
                """, (character_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update sync timestamp: {e}")

    @abstractmethod
    def fetch_from_esi(self, character_id: int) -> Any:
        """Fetch data from ESI. Override in subclass.

        Args:
            character_id: EVE character ID

        Returns:
            Raw data from ESI (typically dict or list)
        """
        pass

    @abstractmethod
    def transform_data(self, raw_data: Any) -> List[Dict]:
        """Transform ESI response to database format. Override in subclass.

        Args:
            raw_data: Raw data from fetch_from_esi()

        Returns:
            List of dictionaries ready for database insertion
        """
        pass

    @abstractmethod
    def save_to_db(self, character_id: int, data: List[Dict], conn) -> None:
        """Save transformed data to database. Override in subclass.

        Args:
            character_id: EVE character ID
            data: Transformed data from transform_data()
            conn: Database connection
        """
        pass

    @abstractmethod
    def get_sync_column(self) -> str:
        """Return the sync timestamp column name.

        Returns:
            Column name (must be in VALID_SYNC_COLUMNS)
        """
        pass

    def get_result_key(self) -> str:
        """Return the key for result count. Override if needed.

        Returns:
            Key name for the count in result dict (default: 'count')
        """
        return "count"

    def get_result_value(self, data: List[Dict]) -> Any:
        """Return the value for result. Override if needed.

        Args:
            data: Transformed data

        Returns:
            Value to include in result (default: length of data)
        """
        return len(data) if isinstance(data, list) else 1
