# Reproducing the evaluation

## Offline checks

Use Python 3.13 and the committed lockfile from the repository root.

```bash
uv sync --locked
uv run pytest
uv run ruff check
uv run ruff format --check
uv run basedpyright src tests tools
uv run inspect-evals-lint --all
uv run inspect-evals-readmes generate --check
uv run python tools/review_readiness.py
```

The readiness script writes its generated inventory to `artifacts/offline-readiness.json`. The [pinned source tools](../tools/sync_upstream.py) regenerate the packaged catalogs from the exact upstream revision below.

## Controller and native environment

The tested path ran Inspect on a dedicated Linux controller and gave the native ROGUE runner a disposable OSWorld desktop on EC2. The scoped role, launch request, approved image, networking, and cleanup scheduler are supplied by the operator. See the [example controller handoff](examples/worker-handoff.json) and the [original AWS setup guide](https://github.com/neuroagents-lab/ROGUE/blob/c6cb2a0022b23707dd647282abda99fa09488d98/AWS_SETUP.md).

```bash
git clone https://github.com/neuroagents-lab/ROGUE.git /opt/ROGUE
git -C /opt/ROGUE checkout c6cb2a0022b23707dd647282abda99fa09488d98
git -C /opt/ROGUE apply "$PWD/tools/patches/rogue-scoped-aws.patch"
git -C /opt/ROGUE apply "$PWD/tools/patches/rogue-inspect-responses.patch"
uv venv --python 3.11 /opt/rogue-venv
uv pip install --python /opt/rogue-venv/bin/python --torch-backend cpu -r /opt/ROGUE/requirements.txt
```

The controller used `build-essential`, `linux-libc-dev`, and `xvfb`. Install the native dependencies with the upstream requirements in their separate environment. Keep the patched checkout at the pinned commit, since the adapter verifies that commit and the input task hash. The [AWS patch](../tools/patches/rogue-scoped-aws.patch) applies the approved launch request to allocation and reset, with required TTL scheduling. The [Responses patch](../tools/patches/rogue-inspect-responses.patch) handles split reasoning and action messages from the Inspect bridge.

## One control smoke

From the controller's Inspect checkout, source the operator-provided AWS environment, set `ROGUE_AWS_LAUNCH_REQUEST` to the operator-provided JSON, and configure the model provider through its normal environment or secret store. Keep private configuration outside the checkout. The example below assumes an OpenAI-compatible provider configured for the chosen model.

```bash
xvfb-run -a uv run inspect eval rogue_eval/rogue_eval \
  --model openai/gpt-5.4-mini \
  -T scenario=override -T worker_sandbox=local -T provider=aws -T region=eu-west-2 \
  -T root=/opt/ROGUE -T native_python=/opt/rogue-venv/bin/python \
  -T 'native_options={"max_steps":1,"max_tokens":512}' \
  --sample-id override_0512bb38-d531-4acf-9e7e-0add90816068 \
  --max-samples 1 --max-tasks 1 --max-sandboxes 1 --retry-on-error 0 --log-dir logs/smoke
```

For the tested GL OpenRouter path, use an authorized gateway session and configure Inspect with the routed model name `openai/openrouter/openai/gpt-5.4-mini`, the operator's OpenAI-compatible gateway base URL, and `-M responses_api=true -M responses_store=false`. Inspect logs the routed identity and passes the native GPT alias to the upstream runner.

A smoke passes when the model call reaches the bridge, the native trajectory and result are saved, the expected scorer evidence is present, and the worker terminates. A task score of zero can be a valid outcome. Open logs with `uv run inspect view --log-dir logs/smoke`. Native archives live in `artifacts/`.

To validate saved scores offline:

```bash
uv run python tools/report_native.py --artifacts artifacts --primary-judge openai/gpt-5.4-mini
```

Use the judge ID recorded for the selected run. Compare scored denominators explicitly, because Inspect and the upstream aggregation handle unavailable judgments differently.
