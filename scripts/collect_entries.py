from __future__ import annotations

import argparse
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from . import schemas
from .nomad_api import fetch_entries_page
from .selection import deduplicate_entries, normalize_code_name, stable_pick

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect representative NOMAD entry IDs (scan-style)."
    )
    parser.add_argument("--base-url", default="https://nomad-lab.eu/prod/v1/api/v1")
    parser.add_argument("--outdir", default=".")
    parser.add_argument(
        "--codes",
        nargs="+",
        required=True,
        help="Simulation codes or parser names to process (required).",
    )
    parser.add_argument(
        "--query-by",
        default="program_name",
        choices=["program_name", "parser_name"],
        help="Query by program_name or parser_name (default: program_name).",
    )
    parser.add_argument(
        "--author-quantity",
        default=schemas.MAIN_AUTHOR_Q,
        help="Quantity to use for author.",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--page-size", type=int, default=500)
    parser.add_argument(
        "--polite-sleep",
        type=float,
        default=0.0,
        help="Unused in scan mode; kept for compatibility.",
    )
    parser.add_argument("--max-authors-per-code", type=int, default=25)
    parser.add_argument("--max-datasets-per-author", type=int, default=10)
    parser.add_argument(
        "--include-fields",
        nargs="+",
        default=None,
        help="Fields to request when fetching entries.",
    )
    parser.add_argument(
        "--collect-all",
        action="store_true",
        help="Collect all entries instead of one per (code, author) bucket.",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def read_csv(path: Path, fieldnames: List[str]) -> List[Dict]:
    """Read existing CSV file if it exists, return empty list otherwise."""
    if not path.exists():
        return []
    rows = []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)
    return rows


def write_csv(path: Path, rows: List[Dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_jsonl(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def normalize_author(raw: object) -> Optional[str]:
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw.strip() or None
    if isinstance(raw, dict):
        for key in ("name", "email"):
            val = raw.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return json.dumps(raw, sort_keys=True)
    return None


def iter_code_entries(
    base_url: str,
    code: str,
    author_quantity: str,
    page_size: int,
    include_fields: List[str],
    query_by: str = "program_name",
) -> Iterable[Dict]:
    page_after: Optional[str] = None
    if query_by == "parser_name":
        query = {"parser_name": code}
    else:
        query = {schemas.CODE_Q: code}
    while True:
        entries, next_val = fetch_entries_page(
            base_url=base_url,
            query=query,
            page_size=page_size,
            include_fields=include_fields,
            page_after_value=page_after,
        )
        for entry in entries:
            yield entry
        if not next_val:
            break
        page_after = next_val


def collect_code(
    base_url: str,
    code: str,
    author_quantity: str,
    seed: int,
    page_size: int,
    include_fields: List[str],
    max_authors: int,
    max_datasets: int,
    query_by: str = "program_name",
    collect_all: bool = False,
) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict], int, Dict]:
    author_counts: Dict[str, int] = {}
    representatives: Dict[str, Dict] = {}
    all_entries: List[Dict] = []
    total_entries = 0

    for entry in iter_code_entries(
        base_url, code, author_quantity, page_size, include_fields, query_by
    ):
        entry_id = entry.get("entry_id")
        if not entry_id:
            continue

        raw_author = entry.get(author_quantity) or entry.get("metadata", {}).get(
            "main_author"
        )
        author = normalize_author(raw_author)
        if not author:
            continue

        author_counts[author] = author_counts.get(author, 0) + 1
        total_entries += 1

        if collect_all:
            # Store all entries
            entry_data = {
                "entry_id": entry_id,
                "main_author": author,
                "dataset_id": None,
            }
            if query_by == "parser_name":
                entry_data["entry_point"] = code
            else:
                entry_data["code"] = code
            all_entries.append(entry_data)
        else:
            # Store one representative per author
            current = representatives.get(author)
            candidate = {
                "entry_id": entry_id,
                "main_author": author,
                "dataset_id": None,
            }
            if query_by == "parser_name":
                candidate["entry_pointpoint"] = code
            else:
                candidate["code"] = code
            pick = stable_pick([candidate] + ([current] if current else []), seed=seed)
            representatives[author] = pick

    # Trim authors according to limits
    top_authors = sorted(author_counts.items(), key=lambda x: -x[1])[:max_authors]

    picked_entries: List[Dict] = []
    if collect_all:
        # Return all entries without the picked_by metadata
        picked_entries = all_entries
    else:
        # Return one representative per author
        for author, _ in top_authors:
            rep = representatives.get(author)
            if not rep:
                continue
            rep["picked_by"] = "scan"
            rep["bucket_entry_count"] = author_counts[author]
            picked_entries.append(rep)

        picked_entries = deduplicate_entries(picked_entries)

    code_author_rows = [
        {"code": code, "main_author": author, "n_entries": cnt, "n_datasets": 0}
        for author, cnt in top_authors
    ]
    code_author_dataset_rows: List[Dict] = []
    global_author_dataset_rows: List[Dict] = []
    code_overview_row = {
        "code": code,
        "n_entries": total_entries,
        "n_main_authors": len(author_counts),
        "n_datasets": 0,
    }

    return (
        picked_entries,
        code_author_rows,
        code_author_dataset_rows,
        global_author_dataset_rows,
        total_entries,
        code_overview_row,
    )


def collect(args: argparse.Namespace) -> int:
    outdir = Path(args.outdir)
    entries_dir = outdir / "entries" / "by_code"
    data_dir = outdir / "data"
    entries_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    include_fields = args.include_fields or [
        "entry_id",
        args.author_quantity,
        schemas.DATASETS_Q,
    ]

    # Read existing CSV data to merge with new results
    existing_code_overview = {
        row["code"]: row
        for row in read_csv(
            data_dir / "code_overview.csv",
            ["code", "n_entries", "n_main_authors", "n_datasets"],
        )
    }
    existing_code_author = read_csv(
        data_dir / "code_author_overview.csv",
        ["code", "main_author", "n_entries", "n_datasets"],
    )
    existing_code_author_dataset = read_csv(
        data_dir / "code_author_dataset_overview.csv",
        ["code", "main_author", "dataset_id", "n_entries"],
    )
    existing_global_author_dataset = read_csv(
        data_dir / "global_author_dataset_overview.csv",
        ["main_author", "dataset_id", "n_entries"],
    )

    # Remove existing data for codes being processed (we'll replace it)
    codes_to_process = set(args.codes)
    existing_code_author = [
        row for row in existing_code_author if row["code"] not in codes_to_process
    ]
    existing_code_author_dataset = [
        row
        for row in existing_code_author_dataset
        if row["code"] not in codes_to_process
    ]

    code_overview_rows: List[Dict] = []
    code_author_rows: List[Dict] = []
    code_author_dataset_rows: List[Dict] = []
    global_author_dataset_rows: List[Dict] = []
    total_picked = 0
    codes_processed = 0

    for code in args.codes:
        logger.info("Processing code %s", code)
        (
            picked,
            ca_rows,
            cad_rows,
            global_rows,
            entries_count,
            overview_row,
        ) = collect_code(
            base_url=args.base_url,
            code=code,
            author_quantity=args.author_quantity,
            seed=args.seed,
            page_size=args.page_size,
            include_fields=include_fields,
            max_authors=args.max_authors_per_code,
            max_datasets=args.max_datasets_per_author,
            query_by=args.query_by,
            collect_all=args.collect_all,
        )
        codes_processed += 1
        total_picked += len(picked)
        code_overview_rows.append(overview_row)
        code_author_rows.extend(ca_rows)
        code_author_dataset_rows.extend(cad_rows)
        global_author_dataset_rows.extend(global_rows)

        if picked:
            filename = normalize_code_name(code) + ".jsonl"
            write_jsonl(entries_dir / filename, picked)
            
            # Save per-code run metadata
            metadata_filename = normalize_code_name(code) + "_run_metadata.json"
            code_metadata = {
                "timestamp": datetime.utcnow().isoformat(),
                "base_url": args.base_url,
                "code": code,
                "query_by": args.query_by,
                "collect_all": args.collect_all,
                "seed": args.seed,
                "page_size": args.page_size,
                "total_entries": entries_count,
                "picked_entries": len(picked),
                "n_main_authors": len(ca_rows),
            }
            with (entries_dir / metadata_filename).open("w", encoding="utf-8") as handle:
                json.dump(code_metadata, handle, indent=2, ensure_ascii=True)
        else:
            logger.info("No picks for code %s", code)

    # Merge new data with existing data for codes not processed this run
    # Update existing_code_overview with new data
    for row in code_overview_rows:
        existing_code_overview[row["code"]] = row
    merged_code_overview = list(existing_code_overview.values())

    # Merge code_author data
    merged_code_author = existing_code_author + code_author_rows

    # Merge code_author_dataset data
    merged_code_author_dataset = existing_code_author_dataset + code_author_dataset_rows

    # For global_author_dataset, we need to recompute from all code data
    # Build a map of (author, dataset) -> count across all codes
    global_counts: Dict[Tuple[str, Optional[str]], int] = {}
    for row in merged_code_author_dataset:
        key = (row["main_author"], row.get("dataset_id"))
        count = int(row["n_entries"])
        global_counts[key] = global_counts.get(key, 0) + count

    merged_global_author_dataset = [
        {"main_author": author, "dataset_id": dataset_id, "n_entries": count}
        for (author, dataset_id), count in sorted(global_counts.items())
    ]

    write_csv(
        data_dir / "code_overview.csv",
        merged_code_overview,
        ["code", "n_entries", "n_main_authors", "n_datasets"],
    )
    write_csv(
        data_dir / "code_author_overview.csv",
        merged_code_author,
        ["code", "main_author", "n_entries", "n_datasets"],
    )
    write_csv(
        data_dir / "code_author_dataset_overview.csv",
        merged_code_author_dataset,
        ["code", "main_author", "dataset_id", "n_entries"],
    )
    write_csv(
        data_dir / "global_author_dataset_overview.csv",
        merged_global_author_dataset,
        ["main_author", "dataset_id", "n_entries"],
    )

    run_metadata = {
        "timestamp": datetime.utcnow().isoformat(),
        "base_url": args.base_url,
        "args": vars(args),
        "total_codes_processed": codes_processed,
        "total_picked_entries": total_picked,
    }
    with (data_dir / "run_metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(run_metadata, handle, indent=2, ensure_ascii=True)

    return 0


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)
    try:
        exit_code = collect(args)
    except Exception as exc:  # pragma: no cover - CLI guard
        logger.exception("Collection failed: %s", exc)
        raise SystemExit(1) from exc
    raise SystemExit(exit_code)


if __name__ == "__main__":  # pragma: no cover
    main()
