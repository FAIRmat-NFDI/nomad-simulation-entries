"""Collect parser-based entry metadata and select deterministic test candidates."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .nomad_api import fetch_entries_page
from .selection import normalize_code_name, stable_pick

BASE_URL = "https://nomad-lab.eu/prod/v1/api/v1"
INCLUDE_FIELDS = [
    "entry_id",
    "upload_id",
    "main_author",
    "parser_name",
    "mainfile",
    "processed",
    "processing_errors",
    "entry_create_time",
    "upload_create_time",
    "results.method.simulation.program_name",
    "results.method.simulation.program_version",
    "results.method.workflow_name",
    "results.method.method_name",
    "results.properties.available_properties",
    "results.material.structural_type",
    "results.material.chemical_formula_reduced",
    "results.material.elements",
]
GROUP_FIELDS = (
    "main_author",
    "upload_id",
    "parser_name",
    "program_name",
    "program_version",
    "method_name",
    "workflow_name",
    "mainfile",
    "mainfile_kind",
    "mainfile_basename",
    "mainfile_pattern",
    "mainfile_topdir",
    "processing_error",
)


def nested(data: dict, *parts: str) -> Any:
    value: Any = data
    for part in parts:
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def scalar(value: Any) -> str | None:
    """Keep indexed scalar/list method and workflow names usable as group keys."""
    if isinstance(value, str):
        return value or None
    if isinstance(value, list):
        names = [str(item) for item in value if item is not None]
        return ";".join(names) or None
    return None


def file_kind(mainfile: str) -> str:
    name = PurePosixPath(mainfile).name.lower()
    if name.startswith("data.") or name.endswith(".data"):
        return "data"
    if (
        name.startswith("log.")
        or name.endswith((".log", ".lmp", ".lammps"))
    ):
        return "log"
    if name.startswith("input.") or name.endswith(".in"):
        return "input"
    if name.endswith((".out", ".txt")):
        return "output"
    return "other"


def normalize_entry(raw: dict, code: str) -> dict:
    entry_id = raw.get("entry_id")
    if not entry_id:
        raise ValueError("NOMAD returned an entry without entry_id")
    author = raw.get("main_author")
    author_name = author.get("name") if isinstance(author, dict) else author
    mainfile = raw.get("mainfile") or ""
    path = PurePosixPath(mainfile)
    method = nested(raw, "results", "method") or {}
    simulation = method.get("simulation") or {}
    material = nested(raw, "results", "material") or {}
    properties = nested(raw, "results", "properties") or {}
    processed = raw.get("processed")
    errors = raw.get("processing_errors") or []
    if not isinstance(errors, list):
        errors = [str(errors)]
    return {
        "entry_id": entry_id,
        "upload_id": raw.get("upload_id"),
        "code": code,
        "main_author": author_name,
        "parser_name": raw.get("parser_name"),
        "processed": processed,
        "status": (
            "processed" if processed is True else
            "unprocessed" if processed is False else "unknown"
        ),
        "processing_errors": errors,
        "processing_error": str(errors[0]) if errors else None,
        "program_name": simulation.get("program_name"),
        "program_version": simulation.get("program_version") or None,
        "method_name": scalar(method.get("method_name")),
        "workflow_name": scalar(method.get("workflow_name")),
        "mainfile": mainfile,
        "mainfile_basename": path.name,
        "mainfile_pattern": re.sub(r"\d+", "#", path.name),
        "mainfile_kind": file_kind(mainfile),
        "mainfile_topdir": mainfile.split("/", 1)[0],
        "entry_create_time": raw.get("entry_create_time"),
        "upload_create_time": raw.get("upload_create_time"),
        "available_properties": properties.get("available_properties") or [],
        "structural_type": material.get("structural_type"),
        "chemical_formula_reduced": material.get("chemical_formula_reduced"),
        "elements": material.get("elements") or [],
    }


def collect_entries(base_url: str, parser_names: list[str], page_size: int) -> list[dict]:
    if page_size < 1:
        raise ValueError("page_size must be positive")
    query = {"parser_name:any": parser_names}
    rows: list[dict] = []
    after: str | None = None
    seen: set[str] = set()
    while True:
        page, after = fetch_entries_page(
            base_url=base_url,
            query=query,
            page_size=page_size,
            include_fields=INCLUDE_FIELDS,
            page_after_value=after,
        )
        for entry in page:
            entry_id = entry.get("entry_id")
            if not entry_id or entry_id in seen:
                raise ValueError(f"Missing or repeated entry_id: {entry_id!r}")
            seen.add(entry_id)
            rows.append(entry)
        if not after:
            break
    return rows


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def select_representatives(
    rows: Iterable[dict],
    *,
    status: str,
    group_by: list[str],
    where: dict[str, str],
    seed: int,
) -> list[dict]:
    if not group_by or any(field not in GROUP_FIELDS for field in group_by):
        raise ValueError(f"group_by must use: {', '.join(GROUP_FIELDS)}")
    buckets: dict[tuple, list[dict]] = {}
    for row in rows:
        if status != "all" and row.get("status") != status:
            continue
        if any(str(row.get(field)) != value for field, value in where.items()):
            continue
        key = tuple(row.get(field) for field in group_by)
        buckets.setdefault(key, []).append(row)

    selected: list[dict] = []
    for key in sorted(buckets, key=lambda values: tuple(str(v) for v in values)):
        bucket = buckets[key]
        picked = stable_pick(bucket, seed=seed)
        if picked is None:
            continue
        selected.append({
            **picked,
            "picked_by": "catalog_scan",
            "bucket_entry_count": len(bucket),
            "selection_group": dict(zip(group_by, key)),
        })
    return selected


def parse_where(items: list[str]) -> dict[str, str]:
    filters: dict[str, str] = {}
    for item in items:
        field, separator, value = item.partition("=")
        if not separator or field not in GROUP_FIELDS:
            raise ValueError(f"Expected FIELD=VALUE where FIELD is one of: {', '.join(GROUP_FIELDS)}")
        filters[field] = value
    return filters


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="Fetch all public parser matches")
    collect.add_argument("--code", required=True)
    collect.add_argument("--parser-names", nargs="+", required=True)
    collect.add_argument("--outdir", default=".")
    collect.add_argument("--base-url", default=BASE_URL)
    collect.add_argument("--page-size", type=int, default=500)

    select = commands.add_parser("select", help="Pick one entry per metadata group")
    select.add_argument("--catalog", type=Path, required=True)
    select.add_argument("--out", type=Path, required=True)
    select.add_argument("--status", choices=["all", "processed", "unprocessed"], default="all")
    select.add_argument("--group-by", nargs="+", choices=GROUP_FIELDS, default=["main_author"])
    select.add_argument("--where", action="append", default=[], metavar="FIELD=VALUE")
    select.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    if args.command == "collect":
        raw = collect_entries(args.base_url, args.parser_names, args.page_size)
        rows = [normalize_entry(entry, args.code) for entry in raw]
        stem = normalize_code_name(args.code) + "_catalog"
        directory = Path(args.outdir) / "entries" / "by_code"
        output = directory / f"{stem}.jsonl"
        write_jsonl(output, rows)
        metadata = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "base_url": args.base_url,
            "owner": "public",
            "query": {"parser_name:any": args.parser_names},
            "required_include": INCLUDE_FIELDS,
            "total_entries": len(rows),
            "status_counts": dict(Counter(row["status"] for row in rows)),
            "parser_counts": dict(Counter(row["parser_name"] for row in rows)),
            "n_main_authors": len({row["main_author"] for row in rows}),
        }
        (directory / f"{stem}_run_metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Wrote {len(rows)} entries to {output}")
    else:
        if args.catalog.resolve() == args.out.resolve():
            parser.error("--out must differ from --catalog")
        try:
            where = parse_where(args.where)
        except ValueError as exc:
            parser.error(str(exc))
        catalog_rows = read_jsonl(args.catalog)
        picked = select_representatives(
            catalog_rows, status=args.status,
            group_by=args.group_by, where=where, seed=args.seed,
        )
        write_jsonl(args.out, picked)
        metadata = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "catalog": str(args.catalog),
            "total_catalog_entries": len(catalog_rows),
            "status": args.status,
            "group_by": args.group_by,
            "where": where,
            "seed": args.seed,
            "matched_entries": sum(row["bucket_entry_count"] for row in picked),
            "picked_entries": len(picked),
        }
        args.out.with_name(args.out.stem + "_run_metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Wrote {len(picked)} representatives to {args.out}")


if __name__ == "__main__":
    main()
