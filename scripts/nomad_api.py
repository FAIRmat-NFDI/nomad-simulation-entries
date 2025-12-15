from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional

import requests

logger = logging.getLogger(__name__)

API_CALL_COUNT = 0
MAX_RETRIES = 5
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


@dataclass
class Bucket:
    value: str
    count: int
    entries: List[Dict]


def post_entries_query(base_url: str, payload: dict, timeout_s: int = 60) -> dict:
    """
    POST /entries/query with retries for transient failures.
    """
    global API_CALL_COUNT
    url = f"{base_url.rstrip('/')}/entries/query"
    backoff = 1.0
    for attempt in range(1, MAX_RETRIES + 1):
        API_CALL_COUNT += 1
        try:
            response = requests.post(url, json=payload, timeout=timeout_s)
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                raise
            logger.warning("Request exception on attempt %s: %s", attempt, exc)
            time.sleep(backoff)
            backoff *= 2
            continue

        if response.status_code in RETRYABLE_STATUS and attempt < MAX_RETRIES:
            logger.warning(
                "Retryable status %s on attempt %s; sleeping %.1fs",
                response.status_code,
                attempt,
                backoff,
            )
            time.sleep(backoff)
            backoff *= 2
            continue

        if not response.ok:
            logger.error(
                "Request failed (%s): %s",
                response.status_code,
                response.text,
            )
            response.raise_for_status()

        return response.json()

    # Should not reach here due to raise above.
    raise RuntimeError("Exceeded max retries")


def iter_terms_buckets(
    base_url: str,
    query: Optional[dict],
    quantity: str,
    page_size: int,
    include_entries: bool,
    entry_fields: Optional[List[str]],
    polite_sleep_s: float,
) -> Iterator[Bucket]:
    """
    Iterate over paginated term buckets for a given quantity.
    """
    if query is None:
        query = {}
    page_after: Optional[str] = None
    while True:
        terms: Dict = {
            "quantity": quantity,
            "size": page_size,
        }

        if page_after:
            terms["pagination"] = {"page_after_value": page_after}

        if include_entries:
            # NOMAD expects a list, not an object, for include; this asks for example entries per bucket.
            terms["include"] = ["entries"]

        payload = {
            "owner": "public",
            "query": query,
            "aggregations": {
                "buckets": {
                    "terms": terms,
                }
            },
        }

        result = post_entries_query(base_url, payload)
        agg = result.get("aggregations", {}).get("buckets", {})
        terms_obj = agg.get("terms", agg)
        buckets = terms_obj.get("buckets") or terms_obj.get("data") or []

        if not buckets:
            logger.debug("No buckets for quantity %s; aggregation payload: %s", quantity, agg)

    for bucket in buckets:
        yield Bucket(
            value=bucket.get("value"),
            count=int(bucket.get("count", 0)),
            entries=bucket.get("entries") or [],
        )

        next_page = terms_obj.get("pagination", {}).get("next_page_after_value")
        if not next_page:
            break

        page_after = next_page
        if polite_sleep_s:
            time.sleep(polite_sleep_s)


def fetch_terms(
    base_url: str,
    query: dict,
    quantity: str,
    page_size: int,
    polite_sleep_s: float,
) -> List[Bucket]:
    """
    Convenience wrapper to collect all term buckets into a list.
    """
    return list(
        iter_terms_buckets(
            base_url=base_url,
            query=query,
            quantity=quantity,
            page_size=page_size,
            include_entries=False,
            entry_fields=None,
            polite_sleep_s=polite_sleep_s,
        )
    )


def fetch_entries_page(
    base_url: str,
    query: dict,
    page_size: int,
    include_fields: Optional[List[str]],
    page_after_value: Optional[str] = None,
) -> tuple[List[Dict], Optional[str]]:
    """
    Fetch a single page of entries using /entries/query.
    """
    payload = {
        "owner": "public",
        "query": query or {},
        "pagination": {
            "page_size": page_size,
            "order_by": "entry_id",
            "order": "asc",
        },
    }
    if page_after_value:
        payload["pagination"]["page_after_value"] = page_after_value
    if include_fields:
        payload["required"] = {"include": include_fields}
    result = post_entries_query(base_url, payload)
    next_val = result.get("pagination", {}).get("next_page_after_value")
    return result.get("data") or [], next_val
