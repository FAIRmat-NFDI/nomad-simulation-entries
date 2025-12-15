# Running the collector

Recommended command (metadata-only, public simulation entries):

```bash
python -m scripts.collect_entries \
  --outdir . \
  --base-url https://nomad-lab.eu/prod/v1/api/v1 \
  --max-authors-per-code 25 \
  --max-datasets-per-author 10 \
  --min-entries-per-code 1 \
  --seed 0 \
  --polite-sleep 0.2
```

Expected outputs (simulation entries only):

- `entries/by_code/<CODE>.jsonl` containing picked entry IDs per code.
- CSV summaries in `data/`.
- `data/run_metadata.json` recording arguments and counts.

Troubleshooting:

- **HTTP 429 / 5xx**: increase `--polite-sleep` or rerun; retries are built in.
- **Empty buckets**: check `--min-entries-per-code` and the author/dataset limits.
- **Slow runs**: reduce `--page-size` (smaller batches) or narrow the scope with a custom `--author-quantity`.
