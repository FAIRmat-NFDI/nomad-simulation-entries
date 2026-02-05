"""
Migrate existing JSONL entries to add timestamps, query_ids, and picked_by fields.
"""
import argparse
import json
from pathlib import Path
from typing import Dict, List


ENTRIES_DIR = Path("entries/by_code")


# Mapping of files to their migration parameters
MIGRATIONS = {
    "ORCA.jsonl": {
        "query_ids": ["orca_scan"],
        "timestamp": "2025-12-15T16:02:58.000000",
        "picked_by": "scan",
    },
    "GROMACS.jsonl": {
        "query_ids": ["gromacs_scan"],
        "timestamp": "2025-12-15T16:02:58.000000",
        "picked_by": "scan",
    },
    "atomisticparsers_h5md_parser_entry_point.jsonl": {
        "query_ids": ["h5md_parser_scan"],
        "timestamp": "2026-01-30T11:02:35.230869",
        "picked_by": "scan",
    },
    "VASP.jsonl": {
        "timestamp": "2026-01-30T12:00:00.000000",
        # picked_by and query_ids already exist
    },
    "FHI-aims.jsonl": {
        "timestamp": "2026-01-30T12:00:00.000000",
        # picked_by and query_ids already exist
    },
    "exciting.jsonl": {
        "timestamp": "2026-01-30T12:00:00.000000",
        # picked_by and query_ids already exist
    },
    "QuantumEspresso.jsonl": {
        "timestamp": "2026-01-30T12:00:00.000000",
        # picked_by and query_ids already exist
    },
}


def migrate_file(filepath: Path, params: Dict, dry_run: bool = False) -> None:
    """
    Migrate a single JSONL file by adding missing metadata fields.
    """
    print(f"Migrating {filepath.name}...")

    # Read all entries
    entries: List[Dict] = []
    with filepath.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))

    # Track changes
    changes = []
    updated_entries = []

    # Update each entry with missing fields
    for i, entry in enumerate(entries):
        entry_changes = []

        # Add query_ids if specified and not present
        if "query_ids" in params and "query_ids" not in entry:
            entry["query_ids"] = params["query_ids"]
            entry_changes.append(f"query_ids={params['query_ids']}")

        # Add timestamp if specified and not present
        if "timestamp" in params and "timestamp" not in entry:
            entry["timestamp"] = params["timestamp"]
            entry_changes.append(f"timestamp={params['timestamp']}")

        # Add picked_by if specified and not present
        if "picked_by" in params and "picked_by" not in entry:
            entry["picked_by"] = params["picked_by"]
            entry_changes.append(f"picked_by={params['picked_by']}")

        if entry_changes:
            changes.append((i, entry_changes))
            updated_entries.append(entry)

    # Report changes
    if changes:
        print(f"  Found {len(changes)} entries to update:")
        for idx, entry_changes in changes[:3]:  # Show first 3
            print(f"    Entry {idx}: Add {', '.join(entry_changes)}")
        if len(changes) > 3:
            print(f"    ... and {len(changes) - 3} more")
    else:
        print(f"  No changes needed (all entries already have required fields)")

    # Write back (unless dry-run)
    if not dry_run:
        with filepath.open("w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=True) + "\n")
        print(f"  ✓ Updated {len(entries)} entries")
    else:
        print(f"  [DRY RUN] Would update {len(entries)} entries")


def main():
    parser = argparse.ArgumentParser(description="Migrate JSONL entries to add metadata fields")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("=== DRY RUN MODE (no files will be modified) ===\n")

    base_dir = Path(__file__).parent.parent / ENTRIES_DIR

    for filename, params in MIGRATIONS.items():
        filepath = base_dir / filename
        if not filepath.exists():
            print(f"Skipping {filename} (not found)")
            continue

        migrate_file(filepath, params, dry_run=args.dry_run)
        print()

    if args.dry_run:
        print("=== DRY RUN COMPLETE ===")
        print("Run without --dry-run to apply changes")
    else:
        print("Migration complete!")


if __name__ == "__main__":
    main()
