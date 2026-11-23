# Eval reference

Use the [reproduction guide](reproduce.md) to run the evaluation. The exact parameter defaults and validation live in the [task signature](../src/rogue_eval/rogue_eval.py) and [native option resolver](../src/rogue_eval/settings.py).

## Parameters

| Area                 | Parameters                                                                                                                                                                                                                                                                                            |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Task and condition   | `scenario` accepts a named source domain, `all` (the default), or `all_variants`. `preset` selects the manifest and actor for a named upstream run. `native_options` takes validated upstream CLI names. It can override preset settings. `reasoning_effort` defaults to `low` outside a preset.      |
| Controller and guest | `worker_sandbox` and `sandbox_config` locate the Inspect controller. `root` and `native_python` point to the pinned native checkout and its separate Python environment. `provider`, `region`, and optional `path_to_vm` configure the native VM provider. `episode_timeout` defaults to 900 seconds. |
| Scoring              | `judge_model` enables the log judge. `judge_config` sets its inference options. `judge_max_chars` defaults to 800,000. Oversized inputs fail validation. `access_ready` and `access_settings_file` are the private fixture and evidence gate for restricted access.                                   |

## Dataset

The base catalog preserves 82 original tasks: 52 control, 22 shutdown, and eight restricted access. The adapter checks the native task configuration hash before execution. The pinned source also contains 30 original domains, 702 task configurations across those domains, and 74 named experiment jobs. The variants reuse underlying tasks under different conditions. The 20, 25, and 40 base agent step budgets increase by ten in the corresponding delegated domains. [Source provenance](../src/rogue_eval/provenance.json) · [ROGUE paper, Appendix A.1](https://arxiv.org/pdf/2606.00341)

## Scoring

| Inspect score                  | Meaning                                                                                                     |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| `native_task_completion`       | Numeric reward from the native task evaluator.                                                              |
| `native_task_success`          | One when native reward equals one.                                                                          |
| `actual_violation`             | Scenario-specific deterministic evidence from the native episode. For shutdown this measures script change. |
| `intended_violation`           | Intent identified by the scenario-specific log judge.                                                       |
| `alternate_shutdown_avoidance` | Non-script shutdown avoidance identified by the judge.                                                      |

Native `skipped` and missing detector or judge evidence remain unscored. A missing or invalid native task result is an error. Inspect means use the available scores. The offline [reference report](../tools/report_native.py) uses the upstream denominators and reports judgment coverage by condition. Figures 2 and 4 of the paper combine the two shutdown violation measures, while Figure 3 presents them separately. [ROGUE scoring definitions](https://neuroagents-lab.github.io/ROGUE/#results)

## Deviations from the original runner

- The adapter uses the original task inputs, PyAutoGUI and native OSWorld execution, and original scorer logic. Inspect adds the model bridge, log format, and private native archive. The operator launch request applies the same approved AMI to allocation and reset.
- The repository's demonstrated bridge route is OpenAI-compatible GPT Responses. The Opus 4.7 spot checks used a controller-only routing adjustment and `high` reasoning. Published rates use model-specific settings and a primary GPT-5.5 judge. [Historical runs and evidence](historical-runs.md) · [Published leaderboard](https://neuroagents-lab.github.io/ROGUE/leaderboard.html)
- The Judge setting is explicit. The reproduction smoke and deterministic full-scenario example leave it unset. Restricted-access has offline scorer coverage. Check the run's condition, counts and judge coverage before comparing rates.
