# nomad-simulation-entries

Curates a small, representative set of public NOMAD simulation entry IDs for testing. The tool queries the public NOMAD `/entries/query` API and uses metadata-only requests (no archive downloads).

## Quickstart

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
# ORCA-only scan, minimal fields
python -m scripts.collect_entries --outdir . --seed 0 --page-size 200 --codes ORCA --include-fields entry_id main_author --verbose
```

Outputs land in `data/` and `entries/by_code/`. Reruns with the same `--seed` are deterministic. Only simulation entries (as identified by `results.method.simulation.program_name`) are considered.

## What gets produced

- `entries/by_code/<CODE>.jsonl`: one representative entry per (code, main author) bucket.
- `data/code_overview.csv`: total entries, authors, and datasets per simulation code.
- `data/code_author_overview.csv`: entry counts per code/author.
- `data/code_author_dataset_overview.csv`: entry counts per code/author/dataset.
- `data/global_author_dataset_overview.csv`: entry counts per author/dataset across all codes.
- `data/run_metadata.json`: timestamp, args, base URL, and call counts.
- `data/query_index.json`: index of NOMAD API queries with full POST bodies for reproducibility.

## Query Index

Entries selected via `data/query_index.json` include a `query_ids` field linking to specific NOMAD API queries. The query index documents:

- Full NOMAD POST query bodies for reproducibility
- URL equivalents for browser testing
- Total entries found and selection criteria
- Query-specific notes (e.g., program name spelling)

Each entry in JSONL files includes:
- `query_ids`: List of query IDs (ordered by execution) from `query_index.json`
- `method_name`: List of methods (e.g., `["DFT"]`, `["GW"]`) ordered by execution
- `picked_by`: Source of entry selection (`"scan"` for automated, `"data/query_index.json"` for manual curation)

## Notes

- Always queries with `owner=public`.
- Selection is deterministic (seeded hashing of entry IDs) and deduplicated per code.
- You can limit processing to specific codes to iterate quickly.
