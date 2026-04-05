"""Doctrine clustering service using DBSCAN.

This service clusters fleet snapshots using DBSCAN with cosine similarity
to detect recurring fleet doctrines from zkillboard data.

Algorithm:
1. Fetch fleet snapshots from database
2. Normalize composition vectors (unit vectors for cosine similarity)
3. Build distance matrix using cosine distance
4. Run DBSCAN with epsilon=0.3, min_samples=5
5. Create/update doctrine templates from clusters

Distance metric: cosine_distance = 1 - cosine_similarity
Epsilon: 0.3 (30% dissimilarity threshold)
Min samples: 5 (minimum 5 snapshots to form a doctrine)
"""

from typing import List, Dict, Tuple
from datetime import datetime
import json
import numpy as np
from sklearn.cluster import DBSCAN
from src.database import get_db_connection
from services.war_economy.doctrine.models import (
    FleetSnapshot,
    DoctrineTemplate,
    ShipEntry
)

# Ship types to exclude from doctrine detection (not combat ships)
EXCLUDED_SHIP_TYPES = {
    670,     # Capsule (Pod)
    33328,   # Capsule - Genolution 'Auroral' 197-variant
}


class DoctrineClusteringService:
    """Service for clustering fleet snapshots into doctrine templates."""

    def __init__(self):
        """Initialize clustering service with DBSCAN parameters."""
        self.epsilon = 0.3  # 30% dissimilarity threshold
        self.min_samples = 5  # Minimum 5 observations to form doctrine
        self.metric = 'precomputed'  # Use precomputed distance matrix
        self._ship_name_cache: dict = {}  # Cache for ship names

    def _get_ship_name(self, type_id: int) -> str:
        """Get ship name from type_id using database lookup with caching."""
        if type_id in self._ship_name_cache:
            return self._ship_name_cache[type_id]

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                        (type_id,)
                    )
                    row = cur.fetchone()
                    name = row[0] if row else f"Ship {type_id}"
                    self._ship_name_cache[type_id] = name
                    return name
        except Exception:
            return f"Ship {type_id}"

    def _generate_doctrine_name(self, composition: dict) -> str:
        """Generate doctrine name based on top ship in composition."""
        if not composition:
            return "Unnamed Doctrine"

        # Find ship with highest ratio
        top_ship_id = max(composition.keys(), key=lambda k: composition[k])
        top_ship_name = self._get_ship_name(int(top_ship_id))

        return f"{top_ship_name} Fleet"

    def cluster_snapshots(
        self,
        hours_back: int = 168  # 7 days default
    ) -> int:
        """Cluster fleet snapshots and create/update doctrine templates.

        Args:
            hours_back: How many hours of historical data to cluster

        Returns:
            Number of doctrines created/updated
        """
        # 1. Fetch snapshots from database
        snapshots = self._fetch_snapshots(hours_back)

        if len(snapshots) < self.min_samples:
            return 0

        # 2. Normalize all vectors
        normalized_vectors = [s.normalize_vector() for s in snapshots]

        # Filter out empty vectors
        valid_indices = [
            i for i, vec in enumerate(normalized_vectors) if len(vec) > 0
        ]

        if len(valid_indices) < self.min_samples:
            return 0

        valid_snapshots = [snapshots[i] for i in valid_indices]
        valid_vectors = [normalized_vectors[i] for i in valid_indices]

        # 3. Build distance matrix
        distance_matrix = self._build_distance_matrix(valid_vectors)

        # 4. Run DBSCAN
        dbscan = DBSCAN(
            eps=self.epsilon,
            min_samples=self.min_samples,
            metric=self.metric
        )
        cluster_labels = dbscan.fit_predict(distance_matrix)

        # 5. Process clusters (ignore noise: label=-1)
        unique_labels = set(cluster_labels)
        unique_labels.discard(-1)  # Remove noise label

        doctrines_created = 0

        for label in unique_labels:
            # Get snapshots in this cluster
            cluster_mask = cluster_labels == label
            cluster_snapshots = [
                valid_snapshots[i] for i, mask in enumerate(cluster_mask) if mask
            ]

            # Create or update doctrine
            if self._should_create_new_doctrine(cluster_snapshots):
                self._save_doctrine(cluster_snapshots)
                doctrines_created += 1
            else:
                # Update existing similar doctrine
                existing = self._find_similar_doctrine(cluster_snapshots)
                if existing:
                    self._update_existing_doctrine(existing, cluster_snapshots)
                    self._save_doctrine_update(existing)
                    doctrines_created += 1
                else:
                    # No similar doctrine found, create new
                    self._save_doctrine(cluster_snapshots)
                    doctrines_created += 1

        # Mark all processed snapshots as processed
        if valid_snapshots:
            self._mark_snapshots_processed([s.id for s in valid_snapshots])

        return doctrines_created

    def _mark_snapshots_processed(self, snapshot_ids: List[int]) -> None:
        """Mark snapshots as processed so they won't be clustered again.

        Args:
            snapshot_ids: List of snapshot IDs to mark as processed
        """
        if not snapshot_ids:
            return

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                placeholders = ','.join(['%s'] * len(snapshot_ids))
                cur.execute(f"""
                    UPDATE doctrine_fleet_snapshots
                    SET processed = TRUE
                    WHERE id IN ({placeholders})
                """, snapshot_ids)
                conn.commit()

    def _fetch_snapshots(self, hours_back: int) -> List[FleetSnapshot]:
        """Fetch fleet snapshots from database.

        Args:
            hours_back: How many hours of historical data to fetch

        Returns:
            List of FleetSnapshot objects
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        id, timestamp, system_id, region_id,
                        ships, total_pilots, killmail_ids, created_at
                    FROM doctrine_fleet_snapshots
                    WHERE timestamp > NOW() - INTERVAL '%s hours'
                      AND processed = FALSE
                    ORDER BY timestamp DESC
                """, (hours_back,))

                rows = cur.fetchall()

                snapshots = []
                for row in rows:
                    # Convert JSONB ships to ShipEntry objects, filtering out non-combat ships
                    ships = [
                        ShipEntry(type_id=ship['type_id'], count=ship['count'])
                        for ship in row[4]
                        if ship['type_id'] not in EXCLUDED_SHIP_TYPES
                    ]

                    # Skip snapshots with no valid combat ships
                    if not ships:
                        continue

                    snapshot = FleetSnapshot(
                        id=row[0],
                        timestamp=row[1],
                        system_id=row[2],
                        region_id=row[3],
                        ships=ships,
                        total_pilots=row[5],
                        killmail_ids=row[6],
                        created_at=row[7]
                    )
                    snapshots.append(snapshot)

                return snapshots

    def _build_distance_matrix(
        self,
        vectors: List[Dict[str, float]]
    ) -> np.ndarray:
        """Build pairwise distance matrix for DBSCAN.

        Args:
            vectors: List of normalized composition vectors

        Returns:
            NxN distance matrix where N is number of vectors
        """
        n = len(vectors)
        distance_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(i + 1, n):
                distance = self._calculate_cosine_distance(vectors[i], vectors[j])
                distance_matrix[i][j] = distance
                distance_matrix[j][i] = distance  # Symmetric

        return distance_matrix

    def _calculate_cosine_distance(
        self,
        vec1: Dict[str, float],
        vec2: Dict[str, float]
    ) -> float:
        """Calculate cosine distance between two normalized vectors.

        Cosine distance = 1 - cosine_similarity
        For normalized vectors: cosine_sim = dot_product(vec1, vec2)

        Args:
            vec1: First normalized vector (type_id -> ratio)
            vec2: Second normalized vector (type_id -> ratio)

        Returns:
            Cosine distance (0.0 = identical, 2.0 = opposite)
        """
        # Find common type_ids
        common_types = set(vec1.keys()) & set(vec2.keys())

        if not common_types:
            # No common types = orthogonal vectors
            return 1.0

        # Calculate dot product (cosine similarity for unit vectors)
        cosine_similarity = sum(vec1[type_id] * vec2[type_id] for type_id in common_types)

        # Convert to distance and clamp to [0.0, 2.0] to handle floating point errors
        cosine_distance = max(0.0, min(2.0, 1.0 - cosine_similarity))

        return cosine_distance

    def _should_create_new_doctrine(
        self,
        cluster_snapshots: List[FleetSnapshot]
    ) -> bool:
        """Determine if cluster should create new doctrine or update existing.

        Args:
            cluster_snapshots: Snapshots in cluster

        Returns:
            True if should create new, False if should update existing
        """
        existing = self._find_similar_doctrine(cluster_snapshots)
        return existing is None

    def _find_similar_doctrine(
        self,
        cluster_snapshots: List[FleetSnapshot]
    ) -> DoctrineTemplate | None:
        """Find existing doctrine most similar to this cluster.

        Searches ALL existing doctrines in the region and returns the most
        similar one (lowest cosine distance) if it's within threshold.

        Args:
            cluster_snapshots: Snapshots in cluster

        Returns:
            Most similar DoctrineTemplate if distance < 0.25, else None
        """
        # Calculate average composition for cluster
        cluster_doctrine = self._create_doctrine_from_cluster(cluster_snapshots)
        cluster_vec = cluster_doctrine.composition

        # Get region from majority of snapshots
        region_counts = {}
        for snapshot in cluster_snapshots:
            region_counts[snapshot.region_id] = region_counts.get(snapshot.region_id, 0) + 1
        majority_region = max(region_counts.keys(), key=lambda k: region_counts[k])

        # Fetch ALL existing doctrines from same region
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        id, doctrine_name, alliance_id, region_id,
                        composition, confidence_score, observation_count,
                        first_seen, last_seen, total_pilots_avg,
                        primary_doctrine_type, created_at, updated_at
                    FROM doctrine_templates
                    WHERE region_id = %s
                    ORDER BY observation_count DESC
                """, (majority_region,))

                rows = cur.fetchall()

                if not rows:
                    return None

                # Find the most similar doctrine (lowest distance)
                best_match = None
                best_distance = float('inf')

                for row in rows:
                    existing_vec = row[4]  # composition JSONB
                    distance = self._calculate_cosine_distance(cluster_vec, existing_vec)

                    if distance < best_distance:
                        best_distance = distance
                        best_match = row

                # Only return if within similarity threshold (75%+ similar)
                if best_distance < 0.25 and best_match is not None:
                    return DoctrineTemplate(
                        id=best_match[0],
                        doctrine_name=best_match[1],
                        alliance_id=best_match[2],
                        region_id=best_match[3],
                        composition=best_match[4],
                        confidence_score=best_match[5],
                        observation_count=best_match[6],
                        first_seen=best_match[7],
                        last_seen=best_match[8],
                        total_pilots_avg=best_match[9],
                        primary_doctrine_type=best_match[10],
                        created_at=best_match[11],
                        updated_at=best_match[12]
                    )

                return None

    def _create_doctrine_from_cluster(
        self,
        cluster_snapshots: List[FleetSnapshot]
    ) -> DoctrineTemplate:
        """Create doctrine template from cluster snapshots.

        Args:
            cluster_snapshots: All snapshots in cluster

        Returns:
            New DoctrineTemplate with averaged composition
        """
        # Calculate average composition across all snapshots
        composition_sum = {}
        composition_count = {}

        for snapshot in cluster_snapshots:
            normalized = snapshot.normalize_vector()
            for type_id, ratio in normalized.items():
                composition_sum[type_id] = composition_sum.get(type_id, 0.0) + ratio
                composition_count[type_id] = composition_count.get(type_id, 0) + 1

        # Average and re-normalize
        avg_composition = {
            type_id: composition_sum[type_id] / composition_count[type_id]
            for type_id in composition_sum.keys()
        }

        # Normalize to unit vector
        magnitude = sum(v ** 2 for v in avg_composition.values()) ** 0.5
        if magnitude > 0:
            avg_composition = {
                type_id: ratio / magnitude
                for type_id, ratio in avg_composition.items()
            }

        # Calculate confidence score
        observation_count = len(cluster_snapshots)
        confidence_score = min(1.0, 1.0 - (1.0 / (observation_count ** 0.5)))

        # Get temporal bounds
        timestamps = [s.timestamp for s in cluster_snapshots]
        first_seen = min(timestamps)
        last_seen = max(timestamps)

        # Calculate average pilot count
        total_pilots_avg = int(
            sum(s.total_pilots for s in cluster_snapshots) / len(cluster_snapshots)
        )

        # Determine majority region
        region_counts = {}
        for snapshot in cluster_snapshots:
            region_counts[snapshot.region_id] = region_counts.get(snapshot.region_id, 0) + 1
        majority_region = max(region_counts.keys(), key=lambda k: region_counts[k])

        now = datetime.now()

        # Generate doctrine name based on top ship
        doctrine_name = self._generate_doctrine_name(avg_composition)

        return DoctrineTemplate(
            id=None,
            doctrine_name=doctrine_name,
            alliance_id=None,
            region_id=majority_region,
            composition=avg_composition,
            confidence_score=confidence_score,
            observation_count=observation_count,
            first_seen=first_seen,
            last_seen=last_seen,
            total_pilots_avg=total_pilots_avg,
            primary_doctrine_type=None,
            created_at=now,
            updated_at=now
        )

    def _update_existing_doctrine(
        self,
        existing: DoctrineTemplate,
        new_snapshots: List[FleetSnapshot]
    ) -> None:
        """Update existing doctrine with new cluster observations.

        Uses DoctrineTemplate.update_from_observation() for each snapshot.

        Args:
            existing: Existing doctrine to update (modified in-place)
            new_snapshots: New snapshots to incorporate
        """
        for snapshot in new_snapshots:
            normalized = snapshot.normalize_vector()
            existing.update_from_observation(
                composition=normalized,
                timestamp=snapshot.timestamp,
                pilot_count=snapshot.total_pilots
            )

    def _save_doctrine(
        self,
        cluster_snapshots: List[FleetSnapshot]
    ) -> None:
        """Save new doctrine template to database.

        Uses INSERT ... ON CONFLICT to handle race conditions where
        a similar doctrine was created between our check and save.

        Args:
            cluster_snapshots: Snapshots in cluster
        """
        doctrine = self._create_doctrine_from_cluster(cluster_snapshots)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Use ON CONFLICT to update if doctrine already exists
                cur.execute("""
                    INSERT INTO doctrine_templates (
                        doctrine_name, alliance_id, region_id,
                        composition, confidence_score, observation_count,
                        first_seen, last_seen, total_pilots_avg,
                        primary_doctrine_type, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (doctrine_name, region_id) DO UPDATE SET
                        observation_count = doctrine_templates.observation_count + EXCLUDED.observation_count,
                        last_seen = GREATEST(doctrine_templates.last_seen, EXCLUDED.last_seen),
                        first_seen = LEAST(doctrine_templates.first_seen, EXCLUDED.first_seen),
                        total_pilots_avg = (doctrine_templates.total_pilots_avg + EXCLUDED.total_pilots_avg) / 2,
                        confidence_score = LEAST(1.0, 1.0 - (1.0 / SQRT(
                            doctrine_templates.observation_count + EXCLUDED.observation_count
                        ))),
                        updated_at = NOW()
                """, (
                    doctrine.doctrine_name,
                    doctrine.alliance_id,
                    doctrine.region_id,
                    json.dumps(doctrine.composition),
                    doctrine.confidence_score,
                    doctrine.observation_count,
                    doctrine.first_seen,
                    doctrine.last_seen,
                    doctrine.total_pilots_avg,
                    doctrine.primary_doctrine_type,
                    doctrine.created_at,
                    doctrine.updated_at
                ))
                conn.commit()

    def _save_doctrine_update(
        self,
        doctrine: DoctrineTemplate
    ) -> None:
        """Save updated doctrine template to database.

        Args:
            doctrine: Updated doctrine template
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE doctrine_templates
                    SET
                        composition = %s,
                        confidence_score = %s,
                        observation_count = %s,
                        last_seen = %s,
                        total_pilots_avg = %s,
                        updated_at = %s
                    WHERE id = %s
                """, (
                    json.dumps(doctrine.composition),
                    doctrine.confidence_score,
                    doctrine.observation_count,
                    doctrine.last_seen,
                    doctrine.total_pilots_avg,
                    doctrine.updated_at,
                    doctrine.id
                ))
                conn.commit()
