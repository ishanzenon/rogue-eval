# rogue-eval
ROGUE benchmark audit and Inspect/Hawk evaluation setup

## Hawk access

This project uses Generality Labs' existing Hawk deployment. The API reported
version `4.0.0` on 2026-11-17. Authentication uses Hawk's browser OAuth flow;
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
parity check; this repository does not yet contain that implementation.

References: [Hawk CLI setup](https://hawk.metr.org/getting-started/installation/)
and [sandbox isolation](https://hawk.metr.org/user-guide/sandbox-network-isolation/).
