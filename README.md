# rogue-eval
ROGUE benchmark audit and Inspect/Hawk evaluation setup

Start with [Day 1 setup and the first real episode](DAY1.md). The original
82-task map and native episode adapter are under `src/rogue_eval/`.
Infrastructure probes remain under `probes/`; they are not ROGUE results.

The [Days 2 and 3 preparation guide](DAY2_DAY3.md) maps the expanded configuration,
scorers and fixtures to our v3 architecture and cohort checkpoints. The default
remains 82 main tasks; the explicit variant catalog contains 30 domains and 702
public configs, with 74 original experiment presets. Offline tests do not close
the live desktop acceptance checkpoint.

## Hawk access

This project uses Generality Labs' existing Hawk deployment. The API reported
version `4.1.0` on 2026-11-18. Authentication uses Hawk's browser OAuth flow;
do not commit tokens, API keys, or ROGUE fixture credentials.

Install a compatible CLI with Python 3.13 or later:

```powershell
uv tool install --python 3.14 "hawk[cli]==4.0.0"
Copy-Item .env.example .env
hawk login
hawk version
hawk models
```

Hawk reads the project `.env` automatically. Login credentials stay in its local
credential store. The viewer is https://viewer.hawk.hawk.generalitylabs.ai.

## ROGUE environment integration

Access to Hawk does not establish that this deployment can run the original
ROGUE desktop environments. Before submitting a paid evaluation, verify with
the deployment operator which sandbox providers are enabled, whether desktop
VMs can be provisioned or reached, and the allowed networking and concurrency.
The original ROGUE VM lifecycle and scoring need an Inspect adapter and a
parity check. This repository now contains an offline-tested native adapter and
separate scorers; live parity remains unverified. Hawk PR18's external-AWS example
is a candidate deployment route, not a completed integration in this branch.

References: [Hawk CLI setup](https://hawk.metr.org/getting-started/installation/)
and [sandbox isolation](https://hawk.metr.org/user-guide/sandbox-network-isolation/).
