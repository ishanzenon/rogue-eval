# ROGUE eval for Inspect AI

This package adapts ROGUE's original OSWorld desktop runner to Inspect AI. It preserves the 82 main task IDs, their native configurations, and the scoring evidence for human control, shutdown, and restricted access.

## Start here

- [Architecture and review guide](docs/architecture.md) maps an episode to the dataset, runner, and scorers.
- [Reproduction guide](docs/reproduce.md) covers offline verification and a live smoke episode on a provisioned controller.
- [Historical runs](docs/historical-runs.md) records earlier probes, audit conditions, and where to find their commands and evidence.

## Check the package locally

```bash
uv sync --locked
uv run pytest
uv run inspect-evals-lint --all
uv run inspect-evals-readmes generate --check
```

Local checks make no model calls and provision no desktops. The [evaluation reference](src/rogue_eval/README.md) lists the parameters and scorer outputs.
