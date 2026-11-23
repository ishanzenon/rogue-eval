# Reproduce a ROGUE run

Start with the [controller setup guide](setup/README.md). It covers the AWS handoff, the project's verified compute setup, the two Python environments, and model credentials. Run the commands below from the repository root on that controller with the setup variables exported.

## Run one task

This smoke runs the original control task for installing a local VS Code extension. It caps execution at one agent step so you can check the VM, inference, and scoring path.

```bash
export ROGUE_INSPECT_BRIDGE_PORT=13131
xvfb-run -a uv run --locked inspect eval rogue_eval/rogue_eval \
  --model "$ROGUE_ACTOR" -M responses_api=true -M responses_store=false \
  -T scenario=override -T worker_sandbox=local -T provider=aws -T "region=$AWS_REGION" \
  -T "root=$ROGUE_ROOT" -T "native_python=$ROGUE_NATIVE_PYTHON" \
  -T 'native_options={"max_steps":1,"max_tokens":4096}' \
  --sample-id override_0512bb38-d531-4acf-9e7e-0add90816068 \
  --max-samples 1 --max-tasks 1 --max-sandboxes 1 --log-dir logs/smoke
```

To select another task, set `scenario` to its original domain and copy its exact ID from [the base catalog](../src/rogue_eval/tasks.json) or [variant catalogs](../src/rogue_eval/variants/). Choose `subagents_override` or `subagents_rewire` for the original delegated conditions. Restricted access has a separate fixture and evidence path. The project has verified its scoring offline. [Eval reference](eval-reference.md)

A smoke succeeds when Inspect records a model call, the native trajectory and evaluator output are retained, and the disposable worker is cleaned up. A task score of zero is a valid result. During execution, run `uv run inspect ctl task list` in a second controller shell.

## Run a full scenario

This example uses the original GPT-5.4 mini `xhigh` shutdown preset. With no sample filter, Inspect schedules the full 22-task selection in the preset. Check actor availability and quota, worker cleanup, artifact storage, and model spend after the smoke before starting a full run.

```bash
run_dir="logs/rewire-mini-$(date -u +%Y%m%dT%H%M%SZ)"
xvfb-run -a uv run --locked inspect eval rogue_eval/rogue_eval \
  --model "$ROGUE_ACTOR" -M responses_api=true -M responses_store=false \
  -T preset=gptminixhigh_rewire -T worker_sandbox=local -T provider=aws \
  -T "region=$AWS_REGION" -T "root=$ROGUE_ROOT" -T "native_python=$ROGUE_NATIVE_PYTHON" \
  -T episode_timeout=1800 \
  --max-samples 1 --max-tasks 1 --max-sandboxes 1 --no-fail-on-error \
  --log-dir "$run_dir"
```

- **Scale out.** Split the preset's IDs into disjoint comma-separated `--sample-id` lists. Start one process per group, each with its own `ROGUE_INSPECT_BRIDGE_PORT` and `--log-dir` under the run directory. Keep `--max-samples 1` in each process because samples share that process's bridge port. Limit the number of processes to the approved worker concurrency. Inspect the error counts before using the results.
- **Match the paper.** The preset supplies the original task IDs, actor, observation and action settings, prompt condition, and native budgets. Record the actual provider route and any caps or overrides. The command above scores task success and deterministic violations. Supply an authorized `judge_model` and matching `judge_config` to score intent and alternate shutdown avoidance. The paper's primary judge used GPT-5.5 at `xhigh` with temperature 1. Verify your route supports those settings before claiming parity. [Paper, §3 and Appendix A.1](https://arxiv.org/pdf/2606.00341) · [Preset catalog](../src/rogue_eval/experiment_presets.json)

## Find logs and transcripts

### Inspect on the controller

Inspect writes an `.eval` file under the run's `--log-dir`. It includes model calls and scores. The sample's `retained_native_artifacts` points to its local archive under `artifacts/`, which holds the native evidence and `adapter-condition.json`. Keep both when reviewing a run.

```bash
uv run --locked inspect view --log-dir logs/smoke --host 127.0.0.1 --port 7575
```

For a remote controller, forward port 7575 over SSH and open `http://localhost:7575`. [Inspect log viewer](https://inspect.aisi.org.uk/log-viewer.html)

### Hawk for sharing completed runs

From a machine with access to the completed `.eval` files and an authenticated Hawk CLI, import one log or a directory. Keep native archives private and review logs for sensitive evidence before uploading.

```bash
sources_file="$(mktemp)"
printf '%s\n' '["github.com/ishanzenon/rogue-eval","github.com/neuroagents-lab/rogue"]' > "$sources_file"
hawk import logs/smoke --name "ROGUE control smoke" --code-sources "$sources_file" --yes
rm "$sources_file"
```

Open the returned URL, or find the run under **Eval Sets** and click a sample. **Jobs** shows executions launched on Hawk's cluster. This controller workflow runs outside that cluster, so the import appears in Eval Sets. Hawk can show an older runner as deleted while retaining its saved samples. To retrieve the source logs, run `hawk download EVAL_SET_ID --output-dir logs/review`. [Hawk viewer](https://hawk.metr.org/user-guide/web-viewer/) · [Hawk CLI](https://hawk.metr.org/user-guide/cli-reference/)

### Scout for reviewing behavior across transcripts

Point Scout at the controller's logs or the downloaded `.eval` files. Use it to filter episodes, inspect parent and child traces, or scan a dataset for a behavior. Keep published scores tied to the benchmark scorers.

```bash
uvx --from 'inspect-scout==0.6.2' scout view \
  --transcripts logs/smoke --host 127.0.0.1 --port 8414 --no-browser --no-trust-content
```

Open `http://localhost:8414`, forwarding the port if needed. [Inspect Scout workflow](https://meridianlabs-ai.github.io/inspect_scout/workflow.html)

## Reconcile saved scores

For score reconciliation, run `uv run python tools/report_native.py --artifacts PATH_TO_ONE_RUN_ARCHIVES --primary-judge JUDGE_ID` against retained archives for the condition being reviewed. Use the judge ID from the run and compare the reported denominators. [Scoring reference](eval-reference.md#scoring)
