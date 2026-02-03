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
