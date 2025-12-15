from __future__ import annotations

import hashlib
import re
from typing import Iterable, List, Mapping, Optional


def stable_pick(entries: List[Mapping[str, object]], seed: int) -> Optional[Mapping[str, object]]:
    """Deterministically choose an entry based on entry_id and seed."""
    best_entry = None
    best_hash = None
    for entry in entries:
        entry_id = entry.get("entry_id")
        if not entry_id:
            continue
        digest = hashlib.sha256(f"{seed}:{entry_id}".encode("utf-8")).hexdigest()
        if best_hash is None or digest < best_hash:
            best_hash = digest
            best_entry = entry
    return best_entry


_SAFE_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def normalize_code_name(code: str) -> str:
    """
    Produce a filesystem-safe filename fragment for a simulation code.
    """
    if not code:
        return "unknown"
    cleaned = _SAFE_RE.sub("_", code.strip())
    cleaned = cleaned.strip("_") or "unknown"
    return cleaned


def deduplicate_entries(entries: Iterable[Mapping[str, object]]) -> list[Mapping[str, object]]:
    """
    Drop entries with repeated entry_id while preserving the first occurrence.
    """
    seen: set[str] = set()
    unique: list[Mapping[str, object]] = []
    for entry in entries:
        entry_id = entry.get("entry_id")
        if not entry_id or entry_id in seen:
            continue
        seen.add(entry_id)
        unique.append(entry)
    return unique
