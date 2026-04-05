"""ESI pagination helpers.

Supports two ESI pagination patterns:
1. X-Pages header pagination (most endpoints) - fetches all pages in parallel
2. Cursor-based pagination (wallet transactions, etc.) - sequential with from_id
"""

import logging
from typing import Any, Callable, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

MAX_PARALLEL_PAGES = 20  # Safety limit for parallel page fetches


def fetch_all_pages(
    request_fn: Callable[..., Any],
    method: str,
    endpoint: str,
    token: Optional[str] = None,
    params: Optional[Dict] = None,
    max_pages: int = MAX_PARALLEL_PAGES,
) -> List[Any]:
    """Fetch all pages of a paginated ESI endpoint using X-Pages header.

    Fetches page 1 first to get total pages from X-Pages header,
    then fetches remaining pages in parallel.

    Args:
        request_fn: Function with signature (method, endpoint, token, params) -> (data, headers)
        method: HTTP method
        endpoint: ESI endpoint path
        token: Optional auth token
        params: Optional query parameters
        max_pages: Safety limit for maximum pages to fetch

    Returns:
        Combined list of all results across all pages
    """
    params = dict(params) if params else {}
    params["page"] = 1

    result = request_fn(method, endpoint, token=token, params=params, return_headers=True)
    if result is None:
        return []

    data, headers = result
    if not isinstance(data, list):
        return [data] if data else []

    all_results = list(data)

    # Get total pages from X-Pages header
    total_pages_str = (
        headers.get("X-Pages") or headers.get("x-pages") or "1"
    )
    total_pages = min(int(total_pages_str), max_pages)

    if total_pages <= 1:
        return all_results

    # Fetch remaining pages in parallel
    def fetch_page(page_num: int) -> List[Any]:
        page_params = dict(params)
        page_params["page"] = page_num
        page_result = request_fn(
            method, endpoint, token=token, params=page_params
        )
        if isinstance(page_result, list):
            return page_result
        return []

    with ThreadPoolExecutor(max_workers=min(10, total_pages - 1)) as executor:
        futures = {
            executor.submit(fetch_page, p): p
            for p in range(2, total_pages + 1)
        }
        for future in as_completed(futures):
            page_num = futures[future]
            try:
                page_data = future.result()
                all_results.extend(page_data)
            except Exception as e:
                logger.warning(f"Failed to fetch page {page_num} of {endpoint}: {e}")

    return all_results


def fetch_cursor_pages(
    request_fn: Callable[..., Any],
    method: str,
    endpoint: str,
    token: Optional[str] = None,
    params: Optional[Dict] = None,
    cursor_param: str = "from_id",
    cursor_field: str = "id",
    max_iterations: int = 100,
) -> List[Dict]:
    """Fetch all records using cursor-based pagination.

    Used for wallet transactions and similar endpoints where pagination
    uses a from_id cursor rather than page numbers.

    Args:
        request_fn: Function with signature (method, endpoint, token, params) -> data
        method: HTTP method
        endpoint: ESI endpoint path
        token: Optional auth token
        params: Optional query parameters
        cursor_param: Query parameter name for cursor (default: from_id)
        cursor_field: Field in response to use as next cursor (default: id)
        max_iterations: Safety limit for maximum iterations

    Returns:
        Combined list of all results
    """
    params = dict(params) if params else {}
    all_results: List[Dict] = []

    for _ in range(max_iterations):
        data = request_fn(method, endpoint, token=token, params=params)
        if not isinstance(data, list) or len(data) == 0:
            break

        all_results.extend(data)

        # Get the minimum ID for backward pagination (ESI convention)
        ids = [item.get(cursor_field) for item in data if cursor_field in item]
        if not ids:
            break

        next_cursor = min(ids)
        params[cursor_param] = next_cursor

    return all_results
