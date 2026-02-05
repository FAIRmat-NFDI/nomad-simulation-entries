# nomad-simulation-entries

Curates a small, representative set of public NOMAD simulation entry IDs for testing. The tool queries the public NOMAD `/entries/query` API and uses metadata-only requests (no archive downloads).

## Quickstart

```bash
# ORCA-only scan, minimal fields (one representative per author)
uv run python -m scripts.collect_entries --outdir . --seed 0 --page-size 200 --codes ORCA --include-fields entry_id main_author --verbose

# h5md parser entries (collect all entries)
uv run python -m scripts.collect_entries --outdir . --seed 0 --page-size 200 --codes "atomisticparsers:h5md_parser_entry_point" --query-by parser_name --include-fields entry_id main_author --collect-all --verbose
```

Outputs land in `data/` and `entries/by_code/`. Reruns with the same `--seed` are deterministic.

## What gets produced

- `entries/by_code/<CODE>.jsonl`: Entry IDs with metadata (one per author by default, or all entries with `--collect-all`)
- `entries/by_code/<CODE>_run_metadata.json`: Per-code collection metadata (timestamp, query parameters, statistics)
- `data/code_overview.csv`: Total entries, authors, and datasets per simulation code
- `data/code_author_overview.csv`: Entry counts per code/author
- `data/code_author_dataset_overview.csv`: Entry counts per code/author/dataset
- `data/global_author_dataset_overview.csv`: Entry counts per author/dataset across all codes
- `data/run_metadata.json`: Global run metadata (timestamp, args, base URL, and call counts)
- `data/query_index.json`: Index of NOMAD API queries with full POST bodies for reproducibility

## Metadata System

This repository uses a **hybrid metadata approach** combining entry-level, file-level, and query-level metadata:

### Entry-Level Metadata (in JSONL files)

Every entry includes fields documenting its collection:

**Required fields (all entries):**
- `entry_id`: NOMAD entry identifier
- `main_author`: Principal author
- `dataset_id`: Dataset ID or null
- `picked_by`: `"scan"` (automated) or `"data/query_index.json"` (manual curation)
- `query_ids`: List of query IDs from `query_index.json` (empty `[]` for legacy scans)
- `timestamp`: ISO 8601 timestamp when entry was collected

**Conditional fields:**
- `code`: Simulation program name (for `query_by=program_name`)
- `entry_point`: Parser entry point (for `query_by=parser_name`)
- `method_name`: List of methods like `["DFT"]`, `["GW"]` (for simulation codes)
- `workflow_name`: Workflow name (for simulation codes)
- `available_properties`: Available properties from NOMAD (for simulation codes)
- `bucket_entry_count`: Entries in author bucket before selection (for scans without `--collect-all`)

### File-Level Metadata (run_metadata.json)

Each code has a `<CODE>_run_metadata.json` file documenting the collection run:
- `timestamp`: When the collection was executed
- `query_by`: `"program_name"` or `"parser_name"`
- `collect_all`: Whether all entries were collected
- `query_ids`: Links to `query_index.json` definitions
- Statistics: `total_entries`, `picked_entries`, `n_main_authors`

### Query-Level Metadata (query_index.json)

Central registry at `data/query_index.json` documenting all NOMAD queries:
- Full NOMAD POST query bodies for reproducibility
- URL equivalents for browser testing
- Total entries found and selection criteria
- Query-specific notes (e.g., program name spelling)
- `query_type`: `"manual"` or `"automated_scan"`

**See [METADATA.md](METADATA.md) for complete schema specification.**

## Query Options

### Query by simulation code (default)

By default, the tool queries entries by `results.method.simulation.program_name`:

```bash
uv run python -m scripts.collect_entries --codes GROMACS LAMMPS --outdir . --seed 0 --page-size 200
```

Entries are stored with a `code` field indicating the simulation program.

### Query by parser entry point

To query by `parser_name` (e.g., for parsers like h5md), use `--query-by parser_name`:

```bash
uv run python -m scripts.collect_entries --codes "atomisticparsers:h5md_parser_entry_point" --query-by parser_name --outdir . --seed 0 --page-size 200
```

Entries are stored with an `entry_point` field indicating the parser entry point.

### Collect all entries vs. representatives

**Default behavior**: Selects one representative entry per (code, main_author) bucket using deterministic hashing.

```bash
# Get one representative per author for ORCA
uv run python -m scripts.collect_entries --codes ORCA --outdir .
```

**Collect all entries**: Use `--collect-all` to store every entry instead of just representatives.

```bash
# Get all h5md entries (useful for smaller datasets)
uv run python -m scripts.collect_entries --codes "atomisticparsers:h5md_parser_entry_point" --query-by parser_name --collect-all --outdir .
```

## Command-line options

- `--codes`: Simulation codes or parser entry points to process (required, space-separated)
- `--query-by`: Query by `program_name` (default) or `parser_name`
- `--collect-all`: Collect all entries instead of one representative per author
- `--outdir`: Output directory (default: current directory)
- `--seed`: Random seed for deterministic selection (default: 0)
- `--page-size`: Entries per API page (default: 500)
- `--max-authors-per-code`: Maximum authors per code (default: 25)
- `--include-fields`: Metadata fields to request (default: entry_id, main_author, datasets)
- `--author-quantity`: NOMAD quantity for author (default: main_author)
- `--base-url`: NOMAD API base URL (default: https://nomad-lab.eu/prod/v1/api/v1)
- `--verbose`: Enable debug logging

## Notes

- Always queries with `owner=public`
- Selection is deterministic (seeded hashing of entry IDs) and deduplicated per code
- You can limit processing to specific codes to iterate quickly
- Each code/parser gets its own metadata file saved alongside the entries JSONL
- Simulation code queries use `results.method.simulation.program_name`
- Parser queries use `parser_name`

### Metadata Design Rationale

The hybrid metadata approach was designed based on these principles:

1. **NOMAD query as source of truth**: The POST query body is the canonical definition of what was extracted
2. **Entry-level annotation**: Track collection method per entry (not per file) since files may be extended over time or contain entries from multiple sources
3. **Hybrid storage**: Both centralized (`query_index.json`) and per-file (`run_metadata.json`) metadata serve different purposes:
   - `query_index.json`: Query definitions and documentation (what queries exist)
   - `*_run_metadata.json`: Execution details (when/how queries were run)
4. **Full reproducibility**: Complete query bodies and timestamps allow verification and re-execution
5. **Automated documentation**: `collect_entries.py` automatically populates all metadata fields, and automated scan queries can be documented in `query_index.json` alongside manual queries
