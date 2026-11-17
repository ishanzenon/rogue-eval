# ROGUE prerequisite probe

The solver runs a read-only command in one small Kubernetes sandbox. It makes
no model calls and starts no guest VM. It checks architecture, KVM device access
and API version, installed VM/desktop binaries, Docker socket presence, and
public HTTPS access to selected Google endpoints. Google authentication and
Drive fixtures are not tested. Neither desktop boot nor VM reset is tested.

The eval-set config declares a model because Hawk requires one, but the solver
does not call it. One sample, no retries, a 45-second sample limit and automatic
cleanup constrain the work. Image pulls, node provisioning and package install
happen outside that sample limit; monitor startup and delete a stalled job.
The model cost limit does not cap infrastructure costs.

## Attempt on 2026-11-17

### Successful public-repository retry

Repository visibility was changed to public with the owner's authorization.
The completed run was `rogue-prerequisite-probe-p4bf4oxbmvgy377j`, using code
commit `eb3fa5167ec35b916dc475baeef4a442acc93823`. One sample succeeded in
16 seconds of evaluation time; startup time was additional. Monitoring reported
zero model calls. After deleting the completed job, monitoring showed zero pods.

| Check | Observation | Meaning |
| --- | --- | --- |
| Sandbox architecture | `x86_64` | The deployment scheduled an x86 sandbox, despite using an ARM runner. |
| KVM | `/dev/kvm` absent | The tested default sandbox does not expose hardware virtualization. This does not establish whether an operator-configured sandbox could expose it. |
| Docker | No binary or socket | This plain Python sandbox cannot directly run ROGUE's Docker provider as configured. |
| QEMU and desktop tools | Not installed | Expected for the deliberately small Python image; a custom image could supply binaries. |
| Google endpoints | DNS succeeded; HTTPS returned 302 for accounts, Drive and Docs | The configured allowlist permits initial HTTPS connections to those three hosts. Redirect targets, sign-in, browser flows and fixture access were not tested. |
| Desktop boot and reset | Not attempted | Still require a VM-capable configuration or a separate desktop worker. |

Raw probe output is in `public-repo-probe-output.json`. Two startup retries
exposed local packaging configuration and a missing deployment model-price entry;
both failed before executing a sample, and their compute jobs were deleted.
The wheel build now passes. The model-pricing-dependent `cost_limit` was removed
because this solver makes no inference calls; the remaining sample, concurrency,
time and retry bounds still apply. Cloud startup/compute cost is not measured.

Next verify an operator-supported KVM-enabled sandbox/device configuration or
an authorized external EC2 desktop worker. A custom image alone does not expose
KVM. Only after selecting that route should a single real ROGUE VM be booted,
its screenshot/action endpoints exercised, a disposable file changed, and reset
checked to restore the baseline. No claim of full ROGUE compatibility is made.

### Initial private-repository attempt

- Job: `rogue-prerequisite-probe-0ks670a76crtyrtv`.
- Submission accepted; Kubernetes runner provisioned and started.
- Package fetch failed: `fatal: could not read Username for 'https://github.com': terminal prompts disabled`.
- The runner cannot currently fetch `ishanzenon/rogue-eval`, a private repository.
- Zero model calls; no sample sandbox started. KVM, desktop boot, reset and
  sandbox networking remain unverified.
- Deleted the job's compute resources; monitoring confirmed zero remaining pods.
- Detailed diagnostic evidence is in `prerequisites-result.json`.

For future private repositories, configure authorized access, preferably the
deployment's GitHub App with access only to this repository. Do not forward a
broad personal GitHub token to the runner. An independently approved public
probe repository is another option; keep the main project private.

The deployment pins an Inspect fork based on `0.3.286`; the package's dependency
floor was adjusted after inspecting startup logs to allow that fork. Pin the
eval-set package URL to a commit containing this adjustment before retry.

If KVM is unavailable in the ordinary sandbox, that alone does not exclude a
deployment-configured VM provider or an authorized external EC2 desktop worker.
Those routes require separate verification with the operator.
