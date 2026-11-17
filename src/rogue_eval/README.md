# rogue-eval

ROGUE corrigibility evaluation using the original OSWorld desktop harness

Day 1 implementation in progress. Read [the setup and acceptance checklist](../../DAY1.md)
before running: a provisioned worker configuration is required. Offline pipeline
tests pass; a real VM episode and live proxy interoperability remain unverified.
The current adapter reports native task completion only, not corrigibility.

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

- `scenario` (str): Original scenario key or all 82 main tasks. (default: `'all'`)
- `worker_sandbox` (str): Installed Inspect controller provider. (default: `'ec2'`)
- `sandbox_config` (str | None): Operator-provided config; required to execute. (default: `None`)
- `root` (str): Pinned native checkout on the controller. (default: `'/opt/ROGUE'`)
- `native_python` (str): Separate Python 3.11 ROGUE environment. (default: `'/opt/rogue-venv/bin/python'`)
- `provider` (str): Native VM provider, distinct from the Inspect provider. (default: `'docker'`)
- `path_to_vm` (str | None): Native provider VM identifier/path. (default: `None`)
- `region` (str): Native AWS region when relevant. (default: `'us-east-1'`)
- `reasoning_effort` (str): Explicit smoke setting, not a paper-reproduction preset. (default: `'low'`)
- `episode_timeout` (int): Timeout; provider-side cleanup/TTL is also required. (default: `900`)
<!-- /Parameters: Automatically Generated -->

## Dataset

The bundled map preserves all 82 main tasks from ROGUE commit
`c6cb2a0022b23707dd647282abda99fa09488d98`: 52 control, 22 shutdown and eight
restricted-access tasks. Original IDs and instructions become Inspect samples;
original configs, source hashes, snapshots and 20/25/40-step budgets remain in
metadata. Source data is Apache-2.0; see `UPSTREAM-LICENSE`. No credentials or VM
images are bundled. The first live smoke selects one original control task.

## Scoring

`native_task_completion` exposes the original task evaluator's numeric result
and its mean. A valid zero remains a zero; missing, invalid or skipped evaluation
is an error. This is separate from actual violation, intent and alternate
shutdown-avoidance scores, which are not implemented by the Day 1 adapter.

## Deviations from the original implementation

| What changed | Why | Expected effect on scores |
| --- | --- | --- |
| Original CLI is launched through an Inspect sandbox bridge. | Keep native scenario execution and log model calls through Inspect. | Live routing and generation-setting parity still need verification. |
| Initial actor smoke uses OpenAI routing, low reasoning and screenshot observations. | Establish one reproducible integration path. | Not a reproduction of a published model/effort condition. |
| Access execution is explicitly blocked and subagents are not enabled. | Private credential/artifact handling and child semantics await validation. | No results or compatibility claims for those paths. |

## Architecture

Dataset sample → native ROGUE runner in a provisioned controller → original
OSWorld VM and scenario → original task evaluator. Inspect routes actor model
calls and retains its log; native screenshots, recordings and logs are archived
privately before controller teardown. See the [original ROGUE architecture](https://igarg-safeai.web.app/#rogue/v3)
for the complete benchmark; this adapter implements only the Day 1 subset.
