# Implementation file map

Start with [`rogue_eval.py`](rogue_eval.py). It builds the Inspect task, starts the native episode, and connects it to the scorers.

| Code | What it owns |
| --- | --- |
| [`rogue_eval.py`](rogue_eval.py) | Loads samples, verifies the upstream revision and task hash, runs the OSWorld episode through Inspect’s model bridge, and saves native evidence. |
| [`settings.py`](settings.py) | Resolves named experiments and validates the options forwarded to the native runner. |
| [`scoring.py`](scoring.py) | Reads native results and records task success, detected violations, and optional log-judge scores. |
| [`_upstream.py`](_upstream.py) | Contains the upstream detector, judge, and aggregation functions used by the adapter. |

| Packaged files | What they contain |
| --- | --- |
| [`data/tasks.json`](data/tasks.json) · [`data/variants/`](data/variants/) | Base tasks and original variant catalogs. [Variant guide](data/variants/README.md) |
| [`data/experiment_presets.json`](data/experiment_presets.json) · [`data/native_schema.json`](data/native_schema.json) | Named run settings and the native CLI options they use. |
| [`data/provenance.json`](data/provenance.json) · [`data/source_contracts.json`](data/source_contracts.json) · [`data/analysis_options.json`](data/analysis_options.json) | Upstream source hashes, code excerpts used by tests, and original analysis options. |
| [`eval.yaml`](eval.yaml) · [`__init__.py`](__init__.py) | Inspect metadata and the task export. |

Recommended reading for review. [Parameters, dataset, scoring, and deviations](../../docs/eval-reference.md)
