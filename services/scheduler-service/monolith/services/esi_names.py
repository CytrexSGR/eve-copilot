import os
# services/esi_names.py
"""Shared ESI name resolution with Redis caching."""
import aiohttp
import asyncio
import redis
from typing import Dict, List, Optional

# Redis cache for ESI names (24h TTL)
ESI_NAME_TTL = 86400


async def resolve_esi_names(
    ids: List[int],
    redis_client: Optional[redis.Redis] = None
) -> Dict[int, str]:
    """
    Resolve ESI IDs to names with Redis caching.

    Works for characters, corporations, and alliances (auto-detected by ESI).
    Uses batch endpoint POST /universe/names/ for efficiency.

    Args:
        ids: List of ESI IDs to resolve
        redis_client: Optional Redis client (creates new if not provided)

    Returns:
        Dict mapping ID -> name
    """
    if not ids:
        return {}

    if redis_client is None:
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

    results = {}
    ids_to_fetch = []

    # Check cache first
    for id_ in ids:
        if id_ is None:
            continue
        cache_key = f"esi:name:{id_}"
        cached = redis_client.get(cache_key)
        if cached:
            results[id_] = cached
        else:
            ids_to_fetch.append(id_)

    if not ids_to_fetch:
        return results

    # Batch fetch from ESI (POST /universe/names/)
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://esi.evetech.net/latest/universe/names/"
            # ESI limit is 1000 IDs per request
            for i in range(0, len(ids_to_fetch), 1000):
                batch = ids_to_fetch[i:i+1000]
                async with session.post(url, json=batch, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data:
                            name = item.get("name", f"Unknown {item['id']}")
                            results[item["id"]] = name
                            redis_client.setex(f"esi:name:{item['id']}", ESI_NAME_TTL, name)
    except Exception as e:
        # Fallback: return placeholder names for failed lookups
        for id_ in ids_to_fetch:
            if id_ not in results:
                results[id_] = f"Unknown ({id_})"

    return results


async def get_character_names(character_ids: List[int]) -> Dict[int, str]:
    """Convenience wrapper for character names."""
    return await resolve_esi_names([id_ for id_ in character_ids if id_])


async def get_alliance_names(alliance_ids: List[int]) -> Dict[int, str]:
    """Convenience wrapper for alliance names."""
    return await resolve_esi_names([id_ for id_ in alliance_ids if id_])


async def get_corporation_names(corp_ids: List[int]) -> Dict[int, str]:
    """Convenience wrapper for corporation names."""
    return await resolve_esi_names([id_ for id_ in corp_ids if id_])


def batch_resolve_alliance_names(alliance_ids: List[int]) -> Dict[int, str]:
    """
    Resolve alliance names using shared ESI name service.
    Sync wrapper around async resolve_esi_names.

    Args:
        alliance_ids: List of alliance IDs to resolve

    Returns:
        Dict mapping alliance_id to name
    """
    if not alliance_ids:
        return {}

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    return loop.run_until_complete(resolve_esi_names(alliance_ids, redis_client))
