# ROGUE on GL Hawk: execution assessment

Checked 2026-11-17 against the supplied GL deployment (API reports Hawk 4.0.0).
ROGUE source: `c6cb2a0022b23707dd647282abda99fa09488d98`.

**ROGUE's original desktop VM execution is blocked with our current deployment
configuration and account permissions. Zero of the three selected ROGUE episodes
has run.** Successful infrastructure probe samples are not ROGUE task runs.
The evidence does not establish that Hawk cannot support ROGUE after operator
configuration, or rule out an unadvertised custom provider we cannot discover.

## Selected original tasks

| Scenario | Original task | Smoke-test intent | Current outcome |
| --- | --- | --- | --- |
| Human control | `override_0512bb38-d531-4acf-9e7e-0add90816068` | Install local VSIX in VS Code; preserve the native takeover popup and event logging. | Blocked before VM creation. |
| Shutdown | `rewire_0512bb38-d531-4acf-9e7e-0add90816068` | Same underlying VSIX task; preserve shutdown script, baseline, notice and original stopping/scoring behavior. | Blocked before VM creation. |
| Restricted access | `restrictedaccess_897e3b53-5d4d-444b-85cb-2cdc8a97d903` | Convert `form.docx` to PDF and upload to Drive `forms/`; preserve restricted credential-file rules. | Blocked before VM creation; Drive OAuth setup also incomplete locally. |

`selected-rogue-tasks.json` records their original manifests, file hashes,
instructions, setup step types and task evaluators. Control and shutdown share
a base task to reduce unrelated application differences. The access example is
a relatively simple document conversion, rather than a Thunderbird workflow.

## Execution paths checked

| Path | Evidence | Conclusion for our current access |
| --- | --- | --- |
| Default x86 Kubernetes sandbox | Completed prerequisite probe: `/dev/kvm` and Docker socket absent. | Not a provisioned OSWorld VM; native Docker provider is not usable as configured. |
| Native Docker provider on runner | Imported unmodified ROGUE Docker provider and constructed it. It raised `DockerException`: no Docker daemon socket. Runner has no Docker binary, daemon, socket or KVM device. | A concrete native-provider failure, before task setup. Absence of KVM alone is not the entire blocker: ROGUE has a slower software-emulation fallback, which still needs Docker. |
| gVisor | Actual x86 sandbox probe succeeded; kernel `4.19.0-gvisor`; no KVM or Docker socket. Public HTTPS to the three allowlisted Google hosts returned 302. | Working sandbox, without the original ROGUE Docker/VM stack. Initial HTTPS reachability does not verify Google sign-in, redirects, Drive fixtures or browser workflows. |
| Kata alias and concrete classes | Actual `kata` sandbox startup did not complete within the bounded test. Subsequent Kubernetes server-side dry runs rejected `kata`, `kata-lockdown`, `kata-peer`, `kata-open` with HTTP 403: `RuntimeClass ... not found`. | All documented Kata runtime names checked are absent from this cluster. This is an admission result, not an inference from waiting. |
| Nitro classes | Actual `nitro` sandbox startup did not complete within the bounded test. Kubernetes server-side dry runs rejected `nitro` and `nitro-32bit` with HTTP 403: `RuntimeClass ... not found`. | Documented Nitro runtime names checked are absent. |
| Native ROGUE AWS provider | Original manager import rejects missing `AWS_REGION`; subnet and security-group settings also absent. Using the runner's existing AWS credential chain, `DescribeImages` for ROGUE's AMI and `RunInstances(DryRun=True)` both returned `UnauthorizedOperation`. No instance was launched. | Region variables alone cannot fix the EC2 authorization denial. AMI availability to a future authorized role remains unverified. |
| Inspect EC2 VM plugin | Documented Inspect extension uses EC2/SSM/S3. Current runner EC2 launch dry run is denied. No separate authorized EC2 role/configuration was supplied. | Not an independently available desktop VM route with these credentials. The plugin alone would also not reproduce ROGUE's desktop image and scenario harness. |
| VMware / VirtualBox | Native ROGUE source needs `vmrun` / `VBoxManage`; runner has neither and no corresponding `/dev/vmmon` / `/dev/vboxdrv` devices. | No provided hypervisor host for these paths. Installing a Python SDK alone is insufficient. |
| Azure / Aliyun / Volcengine | Provider source reviewed; native configuration and credentials absent in the tested runner. Azure's automatic allocator is `NotImplementedError`. | No supplied alternative cloud VM service. These were not real cloud launch tests and are not platform-impossibility findings. |
| GCP | CLI lists it, but the pinned provider factory has no GCP branch; provider files are empty. | Not a functioning native path in this revision without implementation work. |
| Modal / Proxmox / external host | No endpoint, identity or configured desktop worker supplied. Proxmox and EC2 are documented Inspect VM extensions. | Possible infrastructure projects, not verified resources available through this Hawk login. No claim of having tested unsupplied services. |

Cluster-wide RuntimeClass listing was denied (403), so the audit cannot inventory
nonstandard runtime names. Instead, valid server-side Pod dry-run requests in
the audit job's own sandbox namespace tested each documented class. gVisor was
accepted; missing classes were explicitly rejected. Dry runs created no pods.
The earlier live Kata/Nitro tests were stopped; their waiting state alone was
not used as proof of absence.

## Fidelity requirements

Follow ROGUE's native runner and OSWorld-Verified VM image. Preserve task setup,
snapshots/reset, screenshots or accessibility observations, PyAutoGUI actions,
scenario-specific popups/scripts/password sentinel, episode termination, native
task evaluation, runtime evidence and ROGUE scoring. A desktop-only demo is not
an end-to-end scenario pass. A model declining or failing the benign task is not
an infrastructure failure if the native episode and scoring complete correctly.

The generic `inspect_evals/osworld` port is not a substitute: its documentation
describes a subset of OSWorld with unsupported Chrome and systemd-dependent
examples, and it does not implement ROGUE's scenario orchestration. We did not
silently swap in that container implementation or simplify the three tasks.

## What would unblock a real three-scenario test

Preferred route: operator-approved use of ROGUE's native AWS provider from the
trusted Hawk runner, controlling dedicated desktop workers. This is a proposal,
not an end-to-end tested route. It needs:

1. A scoped workload role permitting the native EC2 lifecycle. Observed required
   SDK calls are `DescribeImages`, `DescribeInstances`, `RunInstances`,
   `StartInstances`, `TerminateInstances` and `CreateImage`; account for snapshot
   and tagging permissions, cleanup, and any configured TTL scheduler separately.
   The exact least-privilege policy must match the chosen AMI/network/resources.
2. Accessible original AMI, explicit region/subnet/security group, cleanup/TTL,
   and a network route from the Hawk controller to the desktop's private IP.
   The current deployment runs in `eu-west-2`, while the pinned ROGUE image map
   provides `us-east-1` and `ap-east-1`. The native provider returns a private
   IP, so cross-region routing or an approved same-region image copy/controller
   arrangement is necessary; providing a public VM IP alone is not enough.
3. ROGUE's Python 3.11 environment/dependencies and model proxy integration,
   followed by desktop boot, screenshot/action and reset checks, then all three
   unmodified scenario episodes and native scoring. No actor/judge inference was
   tested by these infrastructure audits.
4. Dedicated test Google login plus Drive OAuth files and required fixture
   access. Local login JSON was validated without printing its values; the two
   OAuth files were absent at the last check. No test credentials were uploaded.

Alternative: an operator-provisioned KVM/Docker-capable dedicated worker or
appropriate isolated VM runtime, with the original desktop image and lifecycle.
Merely enabling Kata/Nitro does not prove nested KVM or native Docker support;
it requires another boot/reset check. Do not mount a shared node's Docker socket
or change cluster privileges as a workaround.

## Evidence and cost scope

- `native-providers-result.json`: original provider initialization errors and
  non-mutating AWS permission results.
- `runtime-results.json`: live runtime probes.
- `runtime-admission-result.json`: definitive Kubernetes admission responses.
- `audit-cleanup.json`: all five audit jobs have zero remaining pods.
- No model calls or judge calls; no EC2 desktop workers launched. Hawk runner,
  sandbox, cold-start node and log costs are infrastructure charges and were not
  measured. No API-credit estimate is presented as a total cloud-spend cap.

Sources:
[ROGUE setup](https://github.com/neuroagents-lab/ROGUE/tree/c6cb2a0022b23707dd647282abda99fa09488d98),
[Hawk runtimes](https://hawk.metr.org/getting-started/configuration/),
[Hawk sandbox providers](https://hawk.metr.org/user-guide/sandbox-network-isolation/),
[Inspect OSWorld limitations](https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/src/inspect_evals/osworld/README.md),
[Inspect VM extensions](https://engineering-playbook.aisi.org.uk/isolate.html).
