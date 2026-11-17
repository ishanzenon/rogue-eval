# Day 1: original ROGUE setup and first Inspect episode

Checkpoint: one original human-control episode executes through Inspect, with
native task scoring, model-call logs, retained desktop evidence and verified
VM cleanup. This combines the plan's initial setup with its first-episode goal;
it does not change the cohort calendar or mark later scorer work complete.

## Checklist

- [x] Template-based repo, pinned dependencies and the complete original
  52-control / 22-shutdown / 8-access task map pass offline checks.
- [ ] Confirm the delivered VM's provider, original image, lifecycle/reset
  controls, network route and automatic cleanup; record any deviation.
- [ ] Run the selected original control task through the native ROGUE runner
  and Inspect bridge; retain the `.eval` log and native artifact archive.
- [ ] Inspect the screenshots/recording, popup and stop reason, task score,
  model routing and reset/cleanup. Record the result and bring the three focused
  Q&A questions below to the cohort session.

Prepared in this branch: GL template scaffold, local 82-task dataset, native
episode adapter, offline tests, source/config hash checks, artifact retention,
template CI and a locked development environment. The real VM acceptance test
has not run. Nothing in `probes/` counts as completing this checkpoint.

Validated locally: 19 offline tests, Ruff code checks, type checking, evaluation
metadata (23 applicable checks passing) and generated README consistency. The
tests cover native success/zero, skipped evaluation and runner failure, with
evidence retention in all three mocked paths. No actor/judge API calls were
made. Full template hook/workflow checks are tracked with the review branch.

## What to ask for with the VM

Use `configs/worker-handoff.example.json` as a short handoff form. No passwords,
API keys or OAuth tokens belong in it or in the public repo. We need to know:

| Detail | Why it matters |
| --- | --- |
| Who provides it, and what exactly it is | A controller host with Docker/KVM is different from an already booted OSWorld guest. |
| Native provider and VM identifier | Docker, VMware and AWS have different start/reset/stop interfaces. An IP or viewer alone does not establish that lifecycle. |
| Image and snapshot provenance | Preserve the original OSWorld-Verified desktop and ROGUE's task setup. |
| Controller access and private network reachability | The native agent runs on the controller; PyAutoGUI actions execute in the desktop guest. |
| Snapshot/reset and cleanup/TTL | Reset must restore the baseline; shutdown must target the guest. Timeouts must not leave billable workers. |
| Inspect sandbox provider/config for that controller | The adapter uses `sandbox().exec()` and Inspect's sandbox agent bridge. The controller may be a dedicated EC2 VM or an operator-supported equivalent. |

For Docker, the controller must actually run nested containers and expose KVM
for the documented accelerated path. Installing Docker in our current default
Hawk pod was insufficient: image import was denied by the host kernel. Do not
reuse that pod as if this prerequisite were resolved.

If the supplied resource is just a prebuilt guest, identify its provider and
reset API first. We will choose the connection config after that handoff, rather
than silently replacing the original provider or inventing an IP-only reset.

## Controller preparation

The operator-provided controller must contain:

- Original ROGUE checkout at `/opt/ROGUE`, commit
  `c6cb2a0022b23707dd647282abda99fa09488d98`, including setup assets.
- Its own Python 3.11 environment at `/opt/rogue-venv/bin/python`, with the native
  `requirements.txt` installed according to ROGUE's setup guide. The Inspect
  controller environment is separate (Python 3.13+).
- A working original VM provider, screenshot/action endpoints and native reset;
  archive tool `tar`; private writable result storage and cleanup/TTL.
- Connectivity to task assets and the bridge. Real provider API keys stay in
  Inspect/Hawk, not in the desktop guest. The native actor receives a local
  bridge URL with a placeholder key.

Before an episode, perform a no-model boot/reset test: boot the original image,
retrieve a screenshot, execute a benign GUI action, change a disposable file,
restore the baseline and prove the change disappeared. Save this evidence
privately. Do not trigger the shutdown scenario before isolation is established.

## Offline checks now

```powershell
uv sync --locked
uv run pytest
uv run ruff check
uv run ruff format --check
uv run basedpyright src tests
uv run inspect-evals-lint --all
uv run inspect-evals-readmes generate --check
```

The test with a mocked worker exercises the actual Inspect pipeline and native
score handling. It is explicitly not evidence of a working desktop or of live
LiteLLM/model-proxy interoperability.

## First live episode once the worker is connected

Selected sample:
`override_0512bb38-d531-4acf-9e7e-0add90816068` — install a local VSIX extension
in VS Code while retaining ROGUE's native human-control intervention.

Example for an operator-provided EC2 **controller**, with ROGUE's Docker provider
running on that host (adapt both provider names to the actual handoff):

```powershell
uv run inspect eval rogue_eval/rogue_eval -T scenario=override -T worker_sandbox=ec2 -T sandbox_config=configs/worker.local.yaml -T provider=docker --sample-id override_0512bb38-d531-4acf-9e7e-0add90816068 --model openai/gpt-5.4-mini --max-samples 1 --max-tasks 1 --max-sandboxes 1 --retry-on-error 0 --log-dir logs/day1
```

This command requires the chosen Inspect sandbox extension and real operator
configuration. `worker.local.yaml` is deliberately not fabricated. Install the
extension only after choosing the VM path. For hosted Hawk, the same task goes
in an eval-set declaration that includes its actor model and any needed provider
packages/config; no paid launch is prepared against an imaginary worker.

The native command uses 20 control steps, trajectory history 20, screenshots,
PyAutoGUI, per-step recording and `reasoning_effort=low`. This is a labeled
infrastructure smoke setting, not a reproduction of a published model/effort
condition. Native model names are retained through bridge aliases; generation
settings are forwarded. Live routing parity still needs verification.

Task score zero can be a valid completed episode. Missing or `skipped` task
evaluation is an error; it is never silently turned into zero. Native artifacts
are copied to private, Git-ignored `artifacts/` before sandbox teardown. Retain
these alongside the Inspect log and manually verify both records refer to the
same episode. Provider cleanup remains a separate acceptance check.

## Scope and decisions

Day 1 emits **native task completion only**. Actual violation, intent and
alternate-shutdown-avoidance scorers are not implemented by this adapter yet;
they must not be inferred from task completion. Subagents, alternative agent
scaffolds and cross-provider actor parity remain later work. Access episodes
fail before execution until Drive/private-artifact handling is validated.

The template's question-answer example was removed. Our prior infrastructure
probe source is preserved under `probes/infra/`, separate from the benchmark
package, with evidence in `probes/`; old pinned
Hawk configs continue to reference their original commits. The public repo's
own code is MIT; bundled original task data retains its Apache-2.0 attribution
and license in `src/rogue_eval/UPSTREAM-LICENSE`.

## Three cohort Q&A questions

1. For original ROGUE fidelity, is a sandbox-agent bridge around the native
   runner the preferred integration, given the generic Inspect OSWorld port's
   documented Chrome/systemd exclusions?
2. What is GL's supported controller/guest lifecycle for desktop benchmarks,
   including reset, real guest shutdown, private networking and timeout cleanup?
3. How should we represent native skipped evaluation separately from failure,
   and task completion separately from ROGUE's actual/intent/alternate scores?

Sources: participant mega-doc (Week 1 onboarding and Q&A requirements),
[existing checkpoint sheet](https://docs.google.com/spreadsheets/d/1hI3-ORJ4_0Y1xykdr3WI3fbJLbmpfXuGjwMZOdiR0ts/edit),
[GL template](https://github.com/Generality-Labs/inspect-evals-template/tree/b4babf21d7c956c86969b35b4640bc85cfa9f8ab),
[ROGUE](https://github.com/neuroagents-lab/ROGUE/tree/c6cb2a0022b23707dd647282abda99fa09488d98),
[scenario budgets](https://github.com/neuroagents-lab/ROGUE/blob/c6cb2a0022b23707dd647282abda99fa09488d98/scripts/experiment_runner.sh),
[Inspect bridge](https://inspect.aisi.org.uk/agent-bridge.html),
[OSWorld port limits](https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/src/inspect_evals/osworld/README.md#unsupported-samples).
