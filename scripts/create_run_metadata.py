"""
Create run_metadata.json files for entries that don't have them yet.
"""
import json
from pathlib import Path
from typing import Dict, List


ENTRIES_DIR = Path("entries/by_code")


# Metadata for files that need run_metadata.json created
RUN_METADATA = {
    "ORCA_run_metadata.json": {
        "timestamp": "2025-12-15T16:02:58.000000",
        "base_url": "https://nomad-lab.eu/prod/v1/api/v1",
        "code": "ORCA",
        "query_by": "program_name",
        "collect_all": False,
        "seed": 0,
        "page_size": 500,
        "total_entries": None,  # Unknown from legacy data
        "picked_entries": 21,
        "n_main_authors": 21,
        "query_ids": ["orca_scan"]
    },
    "GROMACS_run_metadata.json": {
        "timestamp": "2025-12-15T16:02:58.000000",
        "base_url": "https://nomad-lab.eu/prod/v1/api/v1",
        "code": "GROMACS",
        "query_by": "program_name",
        "collect_all": False,
        "seed": 0,
        "page_size": 500,
        "total_entries": None,  # Unknown from legacy data
        "picked_entries": 13,
        "n_main_authors": 13,
        "query_ids": ["gromacs_scan"]
    },
    "atomisticparsers_h5md_parser_entry_point_run_metadata.json": {
        # Update existing file to add query_ids
        "query_ids": ["h5md_parser_scan"]
    }
}


def main():
    base_dir = Path(__file__).parent.parent / ENTRIES_DIR

    for filename, metadata in RUN_METADATA.items():
        filepath = base_dir / filename

        if filepath.exists():
            # Update existing file
            print(f"Updating {filename}...")
            with filepath.open("r", encoding="utf-8") as f:
                existing = json.load(f)

            # Merge new fields
            existing.update(metadata)

            with filepath.open("w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=True)
                f.write("\n")

            print(f"  ✓ Updated with {list(metadata.keys())}")
        else:
            # Create new file
            print(f"Creating {filename}...")
            with filepath.open("w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=True)
                f.write("\n")

            print(f"  ✓ Created")

    print("\nRun metadata files ready!")


if __name__ == "__main__":
    main()
