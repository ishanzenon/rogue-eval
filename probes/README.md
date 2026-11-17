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

- Job: `rogue-prerequisite-probe-0ks670a76crtyrtv`.
- Submission accepted; Kubernetes runner provisioned and started.
- Package fetch failed: `fatal: could not read Username for 'https://github.com': terminal prompts disabled`.
- The runner cannot currently fetch `ishanzenon/rogue-eval`, a private repository.
- Zero model calls; no sample sandbox started. KVM, desktop boot, reset and
  sandbox networking remain unverified.
- Deleted the job's compute resources; monitoring confirmed zero remaining pods.
- Detailed diagnostic evidence is in `prerequisites-result.json`.

Before retrying, configure authorized private-repository access, preferably the
deployment's GitHub App with access only to this repository. Do not forward a
broad personal GitHub token to the runner. An independently approved public
probe repository is another option; keep the main project private.

The deployment pins an Inspect fork based on `0.3.286`; the package's dependency
floor was adjusted after inspecting startup logs to allow that fork. Pin the
next eval-set package URL to the commit containing this adjustment before retry.

If KVM is unavailable in the ordinary sandbox, that alone does not exclude a
deployment-configured VM provider or an authorized external EC2 desktop worker.
Those routes require separate verification with the operator.
