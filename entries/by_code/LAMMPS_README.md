# LAMMPS reference entries

This directory contains public NOMAD Central LAMMPS entry snapshots for end-to-end test
selection. The counts below are from **7 November 2026**. Entry availability and processing
status may change when the queries are rerun.

## Why the counts differ

| Search | Entries | Authors | What it includes |
| --- | ---: | ---: | --- |
| `results.method.simulation.program_name=LAMMPS` | 1,621 | 6 | Entries with a normalized LAMMPS program name. |
| The above plus exact `results.method.workflow_name=MolecularDynamics` | 22 | 3 | The narrower workflow search used in the NOMAD GUI. |
| Either LAMMPS `parser_name` | 3,504 | 10 | Processed and unprocessed entries, including those with no normalized program name. |

The 22 entries belong to Aleksandr Avdoshin (18), Vasiliy Znamenskiy (2), and Christopher
Daub (2). The other three authors in the 1,621-entry result have a missing workflow name
(Marcin Krynski, 1,583), `molecular_dynamics` instead of `MolecularDynamics` (Markus
Scheidgen, 14), or `GeometryOptimization` (Sergei Starikov, 2). The workflow filter therefore
explains the three-author result.

The parser-name search includes 1,883 unprocessed entries. They have no normalized LAMMPS
program name, so a program-name search misses them. Four authors occur only in this
unprocessed group: Luca Bellucci, Mersad Mostaghimi, Sandro Wieser, and Yi Wang.

## Files and intended use

| File | Rows | Purpose |
| --- | ---: | --- |
| [LAMMPS_catalog.jsonl](LAMMPS_catalog.jsonl) | 3,504 | Full parser-based metadata catalog; source for local selections. |
| [LAMMPS.jsonl](LAMMPS.jsonl) | 6 | One processed entry per author from the program-name search. |
| [LAMMPS_molecular_dynamics.jsonl](LAMMPS_molecular_dynamics.jsonl) | 22 | Every entry matching the exact GUI workflow filter, with raw-log details. |
| [LAMMPS_unprocessed_by_author.jsonl](LAMMPS_unprocessed_by_author.jsonl) | 7 | One unprocessed entry per author. |
| [LAMMPS_unprocessed_by_author_file_kind.jsonl](LAMMPS_unprocessed_by_author_file_kind.jsonl) | 13 | One per author, parser, and mainfile kind. |
| [LAMMPS_unprocessed_by_author_file_pattern.jsonl](LAMMPS_unprocessed_by_author_file_pattern.jsonl) | 26 | One per author, parser, filename pattern, and processing error. |

Each list has a neighboring `_run_metadata.json` file with its query or selection settings
and counts. [The query index](../../data/query_index.json) stores the reproducible NOMAD
POST bodies for the parser catalog, unprocessed subset, and exact molecular-dynamics search.

## What the metadata can distinguish

The catalog stores `entry_id`, `upload_id`, author, parser, processing status and errors,
program version, workflow, mainfile, filename pattern and kind, timestamps, and material
summary where NOMAD supplied one. The two parser identifiers are `parsers/lammps` (3,475
entries) and `atomisticparsers:lammps_parser_entry_point` (29 entries).

Among the 1,883 unprocessed entries, 1,882 have the generic error `process failed`; one
has no error text. Their mainfiles are classified by name as 1,673 logs, 205 data files,
4 output files, and 1 input file. `mainfile_kind` and `mainfile_pattern` are filename-based
grouping aids, not verified descriptions of file contents or failure causes.

NOMAD's search metadata supplies no `method_name` for any entry in this snapshot. Failed
entries also have no workflow result. Grouping unprocessed entries by method or workflow
therefore adds no variation; use parser and file fields instead. The 22 exact-workflow
entries all advertise a trajectory, but their processed archives contain zero calculations
and sparse trajectory details. Twenty raw logs contain only 92–232 bytes of startup text;
the two older Christopher Daub logs contain about 1.27 MB each of simulation output.
Three entries have an empty indexed program version although their raw headers say
`2 Aug 2023 - Update 2`.

## Select representatives

Run these commands from the repository root. Selection is deterministic for a fixed
catalog and seed. Each selected row records `selection_group` and `bucket_entry_count`;
the sidecar metadata records the seed and filters.

```bash
# One unprocessed entry per author (7 rows).
uv run --no-dev python -m scripts.entry_catalog select \
  --catalog entries/by_code/LAMMPS_catalog.jsonl \
  --status unprocessed --group-by main_author --seed 0 \
  --out entries/by_code/LAMMPS_unprocessed_by_author.jsonl

# One per author, parser, filename pattern, and error (26 rows).
uv run --no-dev python -m scripts.entry_catalog select \
  --catalog entries/by_code/LAMMPS_catalog.jsonl \
  --status unprocessed \
  --group-by main_author parser_name mainfile_pattern processing_error --seed 0 \
  --out entries/by_code/LAMMPS_unprocessed_by_author_file_pattern.jsonl

# Example: processed entries grouped by author, workflow, and file kind.
uv run --no-dev python -m scripts.entry_catalog select \
  --catalog entries/by_code/LAMMPS_catalog.jsonl \
  --status processed --group-by main_author workflow_name mainfile_kind --seed 0 \
  --out /tmp/LAMMPS_processed_examples.jsonl
```

The selector also accepts `--where mainfile_kind=log` and can group by `mainfile`,
`mainfile_basename`, `mainfile_topdir`, `program_version`, or other fields listed by
`uv run --no-dev python -m scripts.entry_catalog select --help`.

## Refresh the catalog

```bash
uv run --no-dev python -m scripts.entry_catalog collect \
  --code LAMMPS \
  --parser-names parsers/lammps atomisticparsers:lammps_parser_entry_point \
  --outdir .
```

Refreshing overwrites the catalog and its metadata. Regenerate any representative lists
you use afterward. The query index records this snapshot's counts and is not updated by
the collector, so revise its counts if a refresh changes the results.
