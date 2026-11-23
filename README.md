# ROGUE in Inspect AI

ROGUE tests whether desktop agents respect a handoff, a shutdown request, or a resource restriction while working on ordinary tasks. This implementation maps the 82 original tasks to Inspect samples and runs each episode through the pinned ROGUE and OSWorld code.

![ROGUE evaluation architecture](docs/assets/rogue-architecture.png)

| Diagram stage | What the Inspect implementation does |
| --- | --- |
| Dataset | Loads the original task IDs and resolves native settings and presets. [Task and settings code](src/rogue_eval/) |
| Solver and environment | Starts the native runner on a provisioned controller, routes model calls through Inspect, and saves the episode and its desktop evidence. [Episode runner](src/rogue_eval/rogue_eval.py) |
| Scorer and metrics | Reports native task success, observed violations, and optional log-judge decisions as separate scores. [Scorers](src/rogue_eval/scoring.py) |

Run the offline checks with `uv sync --locked` and `uv run pytest`. For a live controller smoke and its prerequisites, see the [reproduction guide](docs/reproduce.md).

## Further reading

- [Architecture and code map](docs/architecture.md) for a walkthrough of one episode.
- [Eval reference](src/rogue_eval/README.md) for parameters, presets, and scoring details.
- [Historical runs](docs/historical-runs.md) for prior checks, evidence limits, and archived probe commands.
- [ROGUE paper](https://arxiv.org/abs/2606.00341) and [project demos](https://neuroagents-lab.github.io/ROGUE/) for the benchmark design and example episodes.
