# Implementation file map

Start with `rogue_eval.py` and follow the scorer calls into `scoring.py`.

| Path | What to review |
| --- | --- |
| [`rogue_eval.py`](rogue_eval.py) | Inspect task and sample construction, native command, bridge, and archive capture. |
| [`settings.py`](settings.py) · [`native_schema.json`](data/native_schema.json) · [`experiment_presets.json`](data/experiment_presets.json) | Validation and translation of native options and named experiment conditions. |
| [`scoring.py`](scoring.py) · [`_upstream.py`](_upstream.py) | Inspect scorer wiring and the upstream detector, prompt, and aggregation functions it calls. |
| [`tasks.json`](data/tasks.json) · [`variants/`](data/variants/) | Original base and variant sample catalogs. |
| [`provenance.json`](data/provenance.json) · [`source_contracts.json`](data/source_contracts.json) · [`analysis_options.json`](data/analysis_options.json) | Source revision, integrity hashes, and mirrored upstream analysis options. |
| [`eval.yaml`](eval.yaml) · [`__init__.py`](__init__.py) | Eval metadata and task registration. |

Recommended reading before reviewing behavior or results. [Parameters, dataset, scoring, and deviations](../../docs/eval-reference.md)

<!-- Contributors: Automatically Generated -->
Contributed by [@ishanzenon](https://github.com/ishanzenon)
<!-- /Contributors: Automatically Generated -->
