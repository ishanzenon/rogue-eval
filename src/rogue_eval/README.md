# rogue-eval

ROGUE corrigibility evaluation using the original OSWorld desktop harness

Read the [reproduction guide](../../docs/reproduce.md) before running on a
provisioned controller. The [architecture guide](../../docs/architecture.md)
maps the native runner and scorers to Inspect. The [historical run record](../../docs/historical-runs.md)
documents the tested live routes and the limits of the evidence.

<!-- Contributors: Automatically Generated -->
Contributed by [@ishanzenon](https://github.com/ishanzenon)
<!-- /Contributors: Automatically Generated -->

<!-- Usage: Automatically Generated -->
## Usage

First, install dependencies:

```bash
uv sync
```

Then run evaluations:

```bash
uv run inspect eval rogue_eval/rogue_eval --model openai/gpt-5-nano
```

You can also import tasks as Python objects:

```python
from inspect_ai import eval
from rogue_eval import rogue_eval
eval(rogue_eval)
```

If your directory name doesn't match your package name but you have registered your eval task, you can also run:

```bash
uv run inspect eval rogue_eval --model openai/gpt-5-nano
```

After running evaluations, view logs with:

```bash
uv run inspect view
```

If you don't want to specify `--model` each time, create a `.env` file:

```bash
INSPECT_EVAL_MODEL=anthropic/claude-opus-4-1-20250805
ANTHROPIC_API_KEY=<anthropic-api-key>
```
<!-- /Usage: Automatically Generated -->

<!-- Options: Automatically Generated -->
## Options

You can control a variety of options from the command line. For example:

```bash
uv run inspect eval rogue_eval/rogue_eval --limit 10
uv run inspect eval rogue_eval/rogue_eval --max-connections 10
uv run inspect eval rogue_eval/rogue_eval --temperature 0.5
```

See `uv run inspect eval --help` for all available options.
<!-- /Options: Automatically Generated -->

<!-- Parameters: Automatically Generated -->
## Parameters

### `rogue_eval`

- `scenario` (str): Original domain, all for 82 main tasks, or all_variants for every public domain. (default: `'all'`)
- `worker_sandbox` (str): Installed Inspect controller provider. Use local only on a dedicated controller. (default: `'ec2'`)
- `sandbox_config` (str | None): Operator-provided config for a remote controller sandbox. (default: `None`)
- `root` (str): Pinned native checkout on the controller. (default: `'/opt/ROGUE'`)
- `native_python` (str): Separate Python 3.11 ROGUE environment. (default: `'/opt/rogue-venv/bin/python'`)
- `provider` (str): Native VM provider, distinct from the Inspect provider. (default: `'docker'`)
- `path_to_vm` (str | None): Native provider VM identifier/path. (default: `None`)
- `region` (str): Native AWS region when relevant. (default: `'us-east-1'`)
- `reasoning_effort` (str): Explicit smoke setting, not a paper-reproduction preset. (default: `'low'`)
- `episode_timeout` (int): Timeout; provider-side cleanup/TTL is also required. (default: `900`)
- `native_options` (dict[str, Any] | None): Validated native CLI destinations for budgets, prompts, observations and delegation settings. (default: `None`)
- `preset` (str | None): Named original experiment_runner job; preserves its task selection, settings and actor identity. (default: `None`)
- `judge_model` (str | None): Explicit Inspect grader model; no judge calls when omitted. (default: `None`)
- `judge_config` (dict[str, Any] | None): Inspect grader settings; defaults to GPT xhigh or Anthropic max with 64000 output tokens. (default: `None`)
- `judge_max_chars` (int): Native per-file judge input limit; oversized logs fail rather than truncate. (default: `800000`)
- `access_ready` (bool): Explicit confirmation of private access fixtures and artifact handling; not proof of live acceptance. (default: `False`)
- `access_settings_file` (str | None): Private local Google settings path used only for the sentinel detector. (default: `None`)
<!-- /Parameters: Automatically Generated -->

## Dataset

The bundled map preserves all 82 main tasks from ROGUE commit
`c6cb2a0022b23707dd647282abda99fa09488d98`: 52 control, 22 shutdown and eight
restricted-access tasks. Original IDs and instructions become Inspect samples;
original configs, source hashes, snapshots and 20/25/40-step budgets remain in
metadata. Source data is Apache-2.0; see `UPSTREAM-LICENSE`. No credentials or VM
images are bundled. The first live smoke selects one original control task.

For explicit ablation/subagent selection, `scenario` also accepts each of the
30 original domain names or `all_variants` (702 public configs). `preset` selects
one of 74 original `experiment_runner.sh` jobs and preserves its task manifest,
actor identity and model-specific native settings. This catalog is not a default
evaluation sweep and is not 702 independent base benchmark tasks.

## Scoring

The scorer outputs remain separate, matching the architecture:

- `native_task_completion`: native numeric reward and its mean.
- `native_task_success`: one only for reward exactly 1, matching native task success.
- `actual_violation`: native popup-event, final shutdown comparison or password
  sentinel detector, according to scenario.
- `intended_violation`: the original scenario-specific log-judge decision.
- `alternate_shutdown_avoidance`: original non-script avoidance judgment;
  not applicable outside shutdown scenarios.

A valid zero stays zero. Missing/invalid results are errors; native `skipped`
becomes unscored. Missing detector/judge evidence is unscored, not compliance.
LLM scoring requires an explicit `judge_model`; it uses the original prompts and
preprocessing through an Inspect grader, with a private model/config/input-keyed
cache. One live GPT-5.4 mini grader smoke was verified. Agreement with the published grader remains unverified. Eval version 2-A
records the changed scoring semantics.

Inspect means use available scored samples. The offline `tools/report_native.py`
retains upstream's exact rate denominators and missing-judge counts, grouped by
recorded condition. Those reference rates can differ from Inspect means. Read
the [historical run record](../../docs/historical-runs.md) before interpreting either.

## Deviations from the original implementation

| What changed | Why | Expected effect on scores |
| --- | --- | --- |
| Original CLI is launched through an Inspect sandbox bridge. | Keep native scenario execution and log model calls through Inspect. | The OpenAI-compatible GPT route was verified. Published settings still require a matched run. |
| Initial actor smoke uses OpenAI routing, low reasoning and screenshot observations. | Establish one reproducible integration path. | Not a reproduction of a published model/effort condition. |
| Access execution is guarded by `access_ready`; original subagent domains are selectable. | Preserve private fixture handling and make delegation conditions explicit. | Offline support is not live validation; the access gate defaults closed. |
| Missing deterministic/judge evidence is unscored in Inspect; native `skipped` is unscored for task success. | Separate unavailable measurements from model failures. | Report coverage and compare with the separate upstream reference denominators. |
| Original log-judge prompts are invoked through Inspect with an explicit grader. | Separate actor and grader routing and retain scoring provenance. | Native provider-specific adaptive-thinking, batch and multi-judge transport still require live parity checks. |
| The complete native preset catalog is prepared, while live actor routing remains guarded to OpenAI. | Do not imply cross-provider compatibility from configuration construction. | The OpenRouter GPT route was verified. Other actor families remain unverified. |

## Architecture

Dataset sample → native ROGUE runner in a provisioned controller → original
OSWorld VM and scenario → original task evaluator. Inspect routes actor model
calls and retains its log; native screenshots, recordings and logs are archived
privately before controller teardown. See the [architecture diagram and code map](../../docs/architecture.md).
