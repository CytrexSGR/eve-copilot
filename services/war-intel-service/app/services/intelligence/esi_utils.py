"""
ESI utility functions for intelligence services.

Provides type name resolution via ESI API with Redis caching.
"""

import json
import logging
import httpx
from typing import Dict, List

from eve_shared import get_redis
from app.database import db_cursor

logger = logging.getLogger(__name__)


def resolve_type_names_via_esi(type_ids: List[int]) -> Dict[int, str]:
    """
    Resolve unknown item type names via ESI with Redis caching.
    Falls back to 'Unknown (type_id)' on failure.

    Args:
        type_ids: List of EVE type IDs to resolve

    Returns:
        Dict mapping type_id to resolved name
    """
    if not type_ids:
        return {}

    results = {}
    r = get_redis().client

    # Check Redis cache first
    for type_id in type_ids:
        if r:
            cached = r.get(f"esi:type:{type_id}")
            if cached:
                results[type_id] = cached
                continue
        # Need to fetch from ESI
        try:
            resp = httpx.get(
                f"https://esi.evetech.net/latest/universe/types/{type_id}/",
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                name = data.get("name", f"Unknown ({type_id})")
                results[type_id] = name
                if r:
                    r.setex(f"esi:type:{type_id}", 86400, name)  # 24h cache
            else:
                results[type_id] = f"Unknown ({type_id})"
        except Exception:
            results[type_id] = f"Unknown ({type_id})"

    return results


def resolve_type_info_via_esi(type_ids: List[int]) -> Dict[int, Dict]:
    """
    Resolve full type info (name, group, category) via ESI with Redis caching.

    Args:
        type_ids: List of EVE type IDs to resolve

    Returns:
        Dict mapping type_id to {name, group_name, category_name}
    """
    if not type_ids:
        return {}

    results = {}
    r = get_redis().client
    group_cache = {}  # Local cache for group lookups in this batch
    category_cache = {}  # Local cache for category lookups in this batch

    for type_id in type_ids:
        # Check Redis cache for full info
        cache_key = f"esi:type_full:{type_id}"
        if r:
            cached = r.get(cache_key)
            if cached:
                try:
                    results[type_id] = json.loads(cached)
                    continue
                except Exception:
                    pass

        # Fetch type info from ESI
        try:
            resp = httpx.get(
                f"https://esi.evetech.net/latest/universe/types/{type_id}/",
                timeout=5
            )
            if resp.status_code != 200:
                results[type_id] = {
                    "name": f"Unknown ({type_id})",
                    "group_name": "Unknown",
                    "category_name": "Unknown"
                }
                continue

            type_data = resp.json()
            name = type_data.get("name", f"Unknown ({type_id})")
            group_id = type_data.get("group_id")

            group_name = "Unknown"
            category_name = "Unknown"

            # Get group info
            if group_id:
                if group_id in group_cache:
                    group_name, category_id = group_cache[group_id]
                else:
                    try:
                        group_resp = httpx.get(
                            f"https://esi.evetech.net/latest/universe/groups/{group_id}/",
                            timeout=5
                        )
                        if group_resp.status_code == 200:
                            group_data = group_resp.json()
                            group_name = group_data.get("name", "Unknown")
                            category_id = group_data.get("category_id")
                            group_cache[group_id] = (group_name, category_id)
                        else:
                            category_id = None
                    except Exception:
                        category_id = None

                # Get category info
                if category_id:
                    if category_id in category_cache:
                        category_name = category_cache[category_id]
                    else:
                        try:
                            cat_resp = httpx.get(
                                f"https://esi.evetech.net/latest/universe/categories/{category_id}/",
                                timeout=5
                            )
                            if cat_resp.status_code == 200:
                                cat_data = cat_resp.json()
                                category_name = cat_data.get("name", "Unknown")
                                category_cache[category_id] = category_name
                        except Exception:
                            pass

            result = {
                "name": name,
                "group_name": group_name,
                "category_name": category_name
            }
            results[type_id] = result

            # Cache in Redis
            if r:
                r.setex(cache_key, 86400, json.dumps(result))  # 24h cache

        except Exception as e:
            logger.warning(f"Failed to resolve type {type_id} via ESI: {e}")
            results[type_id] = {
                "name": f"Unknown ({type_id})",
                "group_name": "Unknown",
                "category_name": "Unknown"
            }

    return results


def batch_resolve_alliance_names(alliance_ids: List[int]) -> Dict[int, str]:
    """
    Resolve alliance names via ESI with Redis caching.

    Args:
        alliance_ids: List of alliance IDs to resolve

    Returns:
        Dict mapping alliance_id to alliance name
    """
    if not alliance_ids:
        return {}

    results = {}
    r = get_redis().client
    to_fetch = []

    # Check Redis cache first
    for alliance_id in alliance_ids:
        if r:
            cached = r.get(f"esi:alliance:{alliance_id}")
            if cached:
                results[alliance_id] = cached
                continue
        to_fetch.append(alliance_id)

    # Batch fetch remaining via ESI POST /universe/names/
    if to_fetch:
        try:
            resp = httpx.post(
                "https://esi.evetech.net/latest/universe/names/",
                json=to_fetch,
                timeout=10
            )
            if resp.status_code == 200:
                for item in resp.json():
                    alliance_id = item.get("id")
                    name = item.get("name", f"Alliance {alliance_id}")
                    results[alliance_id] = name
                    if r:
                        r.setex(f"esi:alliance:{alliance_id}", 86400, name)
            else:
                # Fallback for failed batch
                for aid in to_fetch:
                    results[aid] = f"Alliance {aid}"
        except Exception as e:
            logger.warning(f"Failed to batch resolve alliance names: {e}")
            for aid in to_fetch:
                results[aid] = f"Alliance {aid}"

    return results


def batch_resolve_corporation_names(corporation_ids: List[int]) -> Dict[int, str]:
    """
    Resolve corporation names via ESI with Redis caching.

    Args:
        corporation_ids: List of corporation IDs to resolve

    Returns:
        Dict mapping corporation_id to corporation name
    """
    if not corporation_ids:
        return {}

    results = {}
    r = get_redis().client
    to_fetch = []

    # Check Redis cache first
    for corp_id in corporation_ids:
        if r:
            cached = r.get(f"esi:corporation:{corp_id}")
            if cached:
                results[corp_id] = cached
                continue
        to_fetch.append(corp_id)

    # Batch fetch remaining via ESI POST /universe/names/
    if to_fetch:
        try:
            resp = httpx.post(
                "https://esi.evetech.net/latest/universe/names/",
                json=to_fetch,
                timeout=10
            )
            if resp.status_code == 200:
                for item in resp.json():
                    corp_id = item.get("id")
                    name = item.get("name", f"Corp {corp_id}")
                    results[corp_id] = name
                    if r:
                        r.setex(f"esi:corporation:{corp_id}", 86400, name)
            else:
                # Fallback for failed batch
                for cid in to_fetch:
                    results[cid] = f"Corp {cid}"
        except Exception as e:
            logger.warning(f"Failed to batch resolve corporation names: {e}")
            for cid in to_fetch:
                results[cid] = f"Corp {cid}"

    return results


def batch_resolve_character_names(character_ids: List[int]) -> Dict[int, str]:
    """
    Resolve character names with 3-tier caching: DB -> Redis -> ESI.

    Args:
        character_ids: List of character IDs to resolve

    Returns:
        Dict mapping character_id to character name
    """
    if not character_ids:
        return {}

    results = {}
    r = get_redis().client
    to_check_redis = []
    to_fetch_esi = []

    # 1. Check database cache first (persistent)
    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT character_id, character_name
                FROM character_name_cache
                WHERE character_id = ANY(%s)
            """, (list(character_ids),))
            for row in cur.fetchall():
                results[row["character_id"]] = row["character_name"]
    except Exception as e:
        logger.warning(f"DB cache lookup failed: {e}")

    # Find IDs not in DB cache
    for char_id in character_ids:
        if char_id not in results:
            to_check_redis.append(char_id)

    # 2. Check Redis cache for remaining
    for char_id in to_check_redis:
        if r:
            cached = r.get(f"esi:character:{char_id}")
            if cached:
                results[char_id] = cached
                continue
        to_fetch_esi.append(char_id)

    # 3. Fetch remaining from ESI
    if to_fetch_esi:
        new_names = []  # For DB insert
        try:
            # ESI /universe/names/ supports up to 1000 IDs
            for i in range(0, len(to_fetch_esi), 1000):
                batch = to_fetch_esi[i:i+1000]
                resp = httpx.post(
                    "https://esi.evetech.net/latest/universe/names/",
                    json=batch,
                    timeout=10
                )
                if resp.status_code == 200:
                    for item in resp.json():
                        char_id = item.get("id")
                        name = item.get("name", f"Pilot {char_id}")
                        results[char_id] = name
                        new_names.append((char_id, name))
                        # Cache in Redis
                        if r:
                            r.setex(f"esi:character:{char_id}", 86400, name)
                else:
                    for cid in batch:
                        if cid not in results:
                            results[cid] = f"Pilot {cid}"
        except Exception as e:
            logger.warning(f"Failed to batch resolve character names via ESI: {e}")
            for cid in to_fetch_esi:
                if cid not in results:
                    results[cid] = f"Pilot {cid}"

        # 4. Store new names in database cache
        if new_names:
            try:
                with db_cursor() as cur:
                    cur.executemany("""
                        INSERT INTO character_name_cache (character_id, character_name, updated_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (character_id) DO UPDATE SET
                            character_name = EXCLUDED.character_name,
                            updated_at = NOW()
                    """, new_names)
                logger.info(f"Cached {len(new_names)} new character names in DB")
            except Exception as e:
                logger.warning(f"Failed to cache character names in DB: {e}")

    return results


def batch_resolve_alliance_info(alliance_ids: List[int]) -> Dict[int, Dict[str, str]]:
    """
    Resolve alliance names AND tickers via ESI with Redis caching.

    Args:
        alliance_ids: List of alliance IDs to resolve

    Returns:
        Dict mapping alliance_id to {"name": str, "ticker": str}
    """
    if not alliance_ids:
        return {}

    results = {}
    r = get_redis().client
    to_fetch = []

    # Check Redis cache first
    for alliance_id in alliance_ids:
        if r:
            cached = r.get(f"esi:alliance_info:{alliance_id}")
            if cached:
                try:
                    results[alliance_id] = json.loads(cached)
                    continue
                except Exception:
                    pass
        to_fetch.append(alliance_id)

    # Fetch each alliance individually (ESI doesn't have batch for tickers)
    for alliance_id in to_fetch:
        try:
            resp = httpx.get(
                f"https://esi.evetech.net/latest/alliances/{alliance_id}/",
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                info = {
                    "name": data.get("name", f"Alliance {alliance_id}"),
                    "ticker": data.get("ticker", "???")
                }
                results[alliance_id] = info
                if r:
                    r.setex(f"esi:alliance_info:{alliance_id}", 86400, json.dumps(info))
            else:
                results[alliance_id] = {"name": f"Alliance {alliance_id}", "ticker": "???"}
        except Exception as e:
            logger.warning(f"Failed to resolve alliance {alliance_id}: {e}")
            results[alliance_id] = {"name": f"Alliance {alliance_id}", "ticker": "???"}

    return results
