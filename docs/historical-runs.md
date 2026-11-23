# Historical runs and evidence

This branch keeps the evaluation source and the inputs needed for reproduction. Generated inventories, old probe outputs, episode transcripts, and ad hoc monitoring tools live outside its tracked tree.

## Infrastructure probes

The older `day-1-onboarding` branch at `485fdaf` retains the original probe records. To review or rerun them without changing the current checkout:

```bash
git fetch origin day-1-onboarding
git worktree add --detach ../rogue-historical 485fdaf
cd ../rogue-historical
uv sync --locked
```

| Historical check                      | Source and rerun guidance                                                                                                                                                                   |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hawk prerequisites                    | `probes/README.md` documents the scope and cleanup. `probes/prerequisites.eval-set.yaml` is the original one-sample definition.                                                             |
| Native provider and runtime admission | `probes/ROGUE-Hawk-assessment.md` records the test conditions. The corresponding `native-providers` and `runtime-*.eval-set.yaml` files record the job inputs.                              |
| Docker availability                   | The same assessment covers the Docker check, its limitations, and `probes/docker-install.eval-set.yaml`.                                                                                    |
| Linux controller handoff              | `AWS_HANDOFF.md` and `DAY1.md` describe the infrastructure inputs and early acceptance plan. Use the [current reproduction guide](reproduce.md) for implementation changes validated later. |

Run the old Hawk configs only in the deployment that supplies their sandbox type, with the operator's approval and the current Hawk CLI. Review each file's package reference before submission. For the prerequisite probe, the submission command after deployment login is `hawk eval-set run probes/prerequisites.eval-set.yaml`. The original probes were infrastructure checks with no actor inference. AWS provisioning and infrastructure charges are separate from model-call budgets.

## Week 1 evidence

- Scripted controller checks exercised control, shutdown and child handoff. Live GPT-5.4 mini control, shutdown and child smokes reached the model through Inspect. A saved shutdown trace produced two live judge decisions from one request.
- The overnight queue was scoped to 67 eligible control and shutdown tasks. It paused with 3 fully scored episodes, 3 errors, 1 capped episode, and 60 queued. Fifteen tasks were held. Both earlier capped attempts were retained. All 13 audit checks for the three fully scored episodes agreed with native evidence and cached judgments.
- The live queue used GPT-5.4 mini xhigh with 4,096 then 12,288 output-token ceilings and a GPT-5.4 mini low-effort grader. The [published rates](https://neuroagents-lab.github.io/ROGUE/leaderboard-data.json) use different coverage and a different intent grader. The available sample is insufficient for a replication claim.
- The peer evidence bundle contains redacted model-turn timelines and score values for the controlled, bridge, judge, and overnight logs. Raw Inspect logs and native archives remain with the operator. The optional controller smoke and queue utilities are also available in the private bundle for an operator with the original environment.

For a standalone evidence check, use the [offline report instructions](reproduce.md#reconcile-saved-scores). To repeat the earlier overnight audit, use the captured operator tooling and its recorded scope and budget. Start with a single smoke before enabling the queue.

## November 23 Opus 4.7 runs

- Ten live episodes exercised control and shutdown on the same London controller, with original tasks and a mix of base and variant prompts. The actor used `high` reasoning. The optional log judge was unscored. [Hawk eval set](https://viewer.hawk.hawk.generalitylabs.ai/eval-set/imported-rogue-claude-opu-6zzayydzpirn16eq)
- Two further episodes exercised the original subagent conditions. Both native traces recorded child activity. [Hawk eval set](https://viewer.hawk.hawk.generalitylabs.ai/eval-set/imported-rogue-claude-opu-89nb42e14kwemsbr)
- Restricted-access scoring was checked offline with synthetic evidence. [Hawk eval set](https://viewer.hawk.hawk.generalitylabs.ai/eval-set/imported-rogue-restricted-e1ygvsuwy7ltb07i)
