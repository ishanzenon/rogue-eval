# ROGUE AWS handoff

## TL;DR

- **Get us one known-good OSWorld desktop image in London.** Please copy the upstream ROGUE AMI into `eu-west-2`, or give us an existing copy with its source AMI so we can reproduce the same desktop.
- **Give the existing controller a scoped AWS role.** It needs to launch, reset and terminate its own disposable desktops. Reset replaces the guest from the AMI, so SSH access to the five Ubuntu boxes only gets us part of the way.
- **Use the private network we already tested.** Please give the new guests a security group that lets the controller reach OSWorld, Chrome and VLC without exposing their control ports publicly.
- **Prove it with one desktop and send everything back together.** A screenshot, a successful reset, proof that cleanup works after the runner exits, and the filled-in block below are enough for us to take it from there.

Upstream already has an [AWS setup guide](https://github.com/neuroagents-lab/ROGUE/blob/c6cb2a0022b23707dd647282abda99fa09488d98/AWS_SETUP.md). This handoff applies it to the GL allocation and to the pinned runner at `c6cb2a0022b23707dd647282abda99fa09488d98`.

## What we have

The existing EC2 controller and five Ubuntu hosts are in `eu-west-2b`. SSH works, and temporary listeners confirmed private TCP connectivity from the controller to the five hosts on ports 5000, 9222 and 8080. The allocated hosts use a base Ubuntu Server image and have no OSWorld desktop service. At preflight the controller had no EC2 instance profile. Use the controller for the handoff and keep the dev VM and all five existing instances out of the disposable worker lifecycle.

Run the first acceptance check from the existing controller. The eval team owns installing the pinned ROGUE Python 3.11 environment and locked Inspect environment, configuring the London AMI in the runner, and authorizing model access on the execution host. Small GPT and Claude calls through GL OpenRouter passed using the existing local Hawk login, including a synthetic image through GPT Responses. Remote runner authentication and adapter parity still need a smoke test. ECR is useful if we later package a Hawk runner container. The desktop boot image is an EC2 AMI.

## Provisioning

1. **Image.** Copy upstream’s `us-east-1` x86_64 desktop AMI `ami-0d23263edb96951d8` to `eu-west-2` if the source is accessible, or use a verified copy. Confirm launch and backing snapshot/KMS permissions, if applicable, from the actual runtime account. Return source and destination IDs, image owner, root device and minimum root volume size. Preserve the 1920×1080 OSWorld desktop, guest user, bundled apps and services. The pinned provider requests `t3.xlarge` at initial allocation and a 30 GiB gp3 root mapping at `/dev/sda1`. If the approved image or quotas require different settings, record them so we can adjust the runner before launching. [AWS AMI copy guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/CopyingAMIs.html)
2. **Networking.** Return the VPC, subnet, controller security group and dedicated worker security group. Allow worker inbound TCP 5000 (OSWorld), 9222 (Chrome) and 8080 (VLC) from the controller security group. If VNC or SSH is needed for debugging, restrict it to the approved admin path. Confirm controller access to AWS EC2 and Scheduler APIs and the GL gateway. Allow guest DNS/HTTPS for approved task assets and, for the restricted-access pilot, the dedicated Drive test account. The pinned provider uses the guest’s private IP but requests a public IP at launch and reset. Confirm that the approved launch policy allows that request while keeping control ports private, or flag private-only provisioning so we can change both launch paths and use the approved outbound route.
3. **Controller role.** Attach an EC2 instance profile to the existing controller so the SDK can use short-lived credentials. Verify from the controller under the runner’s OS user. Scope baseline runtime access to `ec2:DescribeImages`, `ec2:DescribeInstances` (including waiters), `ec2:RunInstances`, `ec2:StartInstances` and `ec2:TerminateInstances`. Scope launches to the approved region, AMI, subnet, security group and instance profile policy. `ec2:CreateImage` is for the optional save-state method and can stay outside the launch/reset role when using a prebuilt baseline. If policy requires ownership tags, tell us the exact keys and values. The pinned initial and replacement launch requests lack tag specifications, so we must add them to both before using tag-gated permissions. Include any required launch-time tagging and KMS authorization in the operator’s validation. Keep lifecycle permissions off the guests.
4. **Cleanup.** Pre-create the EventBridge Scheduler execution role with `scheduler.amazonaws.com` trust and permission to terminate only eligible disposable workers. Give the controller `scheduler:CreateSchedule` for the expected schedule namespace and `iam:PassRole` for that execution role, restricted to Scheduler. The pinned helper uses the default schedule group and names starting `osworld-ttl-`. Return the role ARN and approved TTL. We’ll set `ENABLE_TTL=true`, `DEFAULT_TTL_MINUTES`, `AWS_SCHEDULER_ROLE_ARN` and `AWS_AUTO_CREATE_SCHEDULER_ROLE=false` in the runner, along with `AWS_REGION`, `AWS_SUBNET_ID` and `AWS_SECURITY_GROUP_ID`. Reset terminates the old guest and launches a replacement. Check scheduling on both paths. Upstream can continue after scheduling fails and the reset path schedules after waiting for the replacement to run. Confirm an operator cleanup backstop for instances left in that gap, and check root-volume deletion on termination. [Scheduler execution role docs](https://docs.aws.amazon.com/scheduler/latest/UserGuide/setting-up.html)

## Acceptance on one disposable desktop

- From the controller, verify the intended role with `aws sts get-caller-identity` and verify the London AMI is `available`. Run an EC2 dry run with the real launch inputs. The expected authorized response is `DryRunOperation`. Use the same account, role, region, image, network, volume layout and tagging that the runner will use.
- Launch one disposable guest and get a screenshot from its private IP at `http://<private-ip>:5000/screenshot`. Confirm the desktop comes up at the expected resolution and the controller can reach Chrome and VLC. Save the guest instance ID and a timestamped screenshot or screenshot result.
- Create a disposable marker in the guest, reset from the approved AMI, and confirm a new instance ID, the old instance terminated, the marker gone and screenshots working again. A reboot alone does not establish reset.
- Verify the replacement has an enabled schedule for its exact instance ID. On the disposable guest, confirm the schedule actually terminates it after the runner exits. Clean up any leftovers and record the final status of both instances and their root volumes. Check the permissions and quota for five concurrent guests, starting with one for the smoke.

The operator and eval team can run this together. If the native runner is not installed during provisioning, the operator can verify the same infrastructure with the AWS CLI and an equivalent replacement, then we repeat the native reset path before running any model. After AWS acceptance, we run one capped control episode and validate scenario evidence, then check shutdown and restricted access with a dedicated test fixture.

## Return in one reply

Fill this in on the private handoff thread. Role ARNs and resource identifiers are sufficient.

```text
Runtime account / region:                         / eu-west-2
Controller alias or instance ID:
Controller instance profile / role ARN:
Source AMI region and ID / owner:
London AMI ID / owner / root device / minimum GiB:
VPC / worker subnet / availability zone:
Controller security group / worker security group:
Public IP policy / guest outbound path:
Approved instance type / pilot concurrency quota:
Required launch tags / KMS prerequisites, if any:
Scheduler execution role ARN / schedule group / TTL:
Cleanup backstop / operator contact:
Dry-run result / screenshot evidence:
Initial and replacement guest IDs / reset evidence:
TTL execution and final instance/volume status:
Anything that differs from the pinned runner:
```

Source for launch, reset and TTL behavior. [AWS manager](https://github.com/neuroagents-lab/ROGUE/blob/c6cb2a0022b23707dd647282abda99fa09488d98/desktop_env/providers/aws/manager.py), [AWS provider](https://github.com/neuroagents-lab/ROGUE/blob/c6cb2a0022b23707dd647282abda99fa09488d98/desktop_env/providers/aws/provider.py), [scheduler helper](https://github.com/neuroagents-lab/ROGUE/blob/c6cb2a0022b23707dd647282abda99fa09488d98/desktop_env/providers/aws/scheduler_utils.py).
