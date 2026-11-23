# Contributing

Run `uv sync --locked`, then use `make test` for the offline suite and `make check` for lint, type checking, eval metadata, generated README sections, and pre-commit checks. The suite uses mocked models and workers. For an actual desktop run, see the [reproduction guide](docs/reproduce.md).

Update the version in [`src/rogue_eval/eval.yaml`](src/rogue_eval/eval.yaml) when a change can move scores. Run `make readmes` after changing generated README data. [Inspect Evals versioning](https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/TASK_VERSIONING.md)

## Verify upstream catalogs

Use a separate, clean checkout of ROGUE at `c6cb2a0022b23707dd647282abda99fa09488d98`. The sync command rewrites the packaged files from that checkout. An unchanged pin should produce an empty diff.

```bash
uv run python tools/sync_upstream.py PATH_TO_CLEAN_PINNED_ROGUE
git diff --exit-code -- src/rogue_eval
```
