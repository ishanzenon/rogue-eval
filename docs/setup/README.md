# Controller setup

Use this once for the smoke test or a larger run. Run commands from the repository root on a dedicated Ubuntu controller. The controller runs Inspect and the native ROGUE harness. ROGUE boots a fresh OSWorld desktop on EC2 for each episode.

## 1. Install controller prerequisites

```bash
sudo apt-get update
sudo apt-get install -y git build-essential linux-libc-dev xvfb xauth unzip
```

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and the [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html). Make both available on `PATH` in the shell that runs Inspect. The AWS CLI is used for the preflight below.

## 2. Provision the controller and desktop workers

| Resource | Verified project setup | ROGUE paper |
| --- | --- | --- |
| Controller | One `t3.large` in London, 2 vCPU and 8 GiB RAM. The controller has a 96 GiB root filesystem. | One `t3.large`, 8 GB RAM and 50 GB EBS. |
| Desktop | Disposable `t3.xlarge`, 4 vCPU and 16 GiB RAM, from an approved 1920×1080 OSWorld AMI. Start with one worker. | Five to ten parallel `t3.xlarge` workers. |
| Inference | Hosted API for actor and optional judge. The controller and guests use CPU instances. | Hosted model APIs via LiteLLM. |

The controller and worker types follow the paper closely. The London region, scoped AWS role, and Inspect model bridge are deployment choices. Check instance, vCPU, and storage quotas for the intended parallelism before a larger run. [ROGUE paper, §3 and Appendix A.1](https://arxiv.org/pdf/2606.00341) · [Pinned upstream AWS setup](https://github.com/neuroagents-lab/ROGUE/blob/c6cb2a0022b23707dd647282abda99fa09488d98/AWS_SETUP.md)

Get these from the AWS operator:

- **AMI and launch request.** An available OSWorld AMI in the worker region and a complete EC2 `RunInstances` JSON request for the approved instance type, network interfaces, security group, volume mapping and tags. Set `MinCount` and `MaxCount` to one. Ensure the role can launch from the AMI and access its backing snapshot and KMS key where applicable. Enable root-volume deletion on termination.
- **Network.** Allow the controller to reach the guest's private IP on TCP 5000 (OSWorld), 9222 (Chrome), and 8080 (VLC). Allow the controller to reach AWS APIs and the model gateway, and supply guest outbound access for the approved tasks.
- **Runtime role and cleanup.** The controller role needs EC2 discovery, launch, start and termination scoped to disposable workers. The controller also needs `scheduler:CreateSchedule` and `iam:PassRole` for a Scheduler execution role that can terminate those workers. Use an instance profile or another approved short-lived AWS credential source. Configure the TTL to cover the episode timeout plus guest boot and reset.

Put the launch request and a Bash environment file in a private directory outside the checkout, for example `~/.config/rogue/`. Create the directory with `mkdir -m 700 -p "$HOME/.config/rogue"`. Save the following as `controller.env` in that directory and substitute the operator's values.

```bash
export AWS_REGION=eu-west-2
export AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_SUBNET_ID=subnet-REPLACE
export AWS_SECURITY_GROUP_ID=sg-REPLACE
export AWS_SCHEDULER_ROLE_ARN=arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME
export AWS_AUTO_CREATE_SCHEDULER_ROLE=false
export ENABLE_TTL=true
export DEFAULT_TTL_MINUTES=40
export ROGUE_AWS_LAUNCH_REQUEST="$HOME/.config/rogue/launch-request.json"
```

```bash
chmod 600 "$HOME/.config/rogue/"{controller.env,launch-request.json}
source "$HOME/.config/rogue/controller.env"
aws sts get-caller-identity
aws ec2 run-instances --region "$AWS_REGION" \
  --cli-input-json "file://$ROGUE_AWS_LAUNCH_REQUEST" --dry-run
```

`DryRunOperation` is the expected authorization result and exits nonzero. Before scaling, verify a private screenshot, reset to a new guest from the AMI, and cloud-side expiry of a test worker. The smoke test also checks the adapter's normal cleanup.

## 3. Install Inspect and the pinned native runner

```bash
uv sync --locked
uv run pytest

export ROGUE_RUNTIME="$HOME/rogue-runtime"
export ROGUE_ROOT="$ROGUE_RUNTIME/upstream"
export ROGUE_NATIVE_PYTHON="$ROGUE_RUNTIME/native-venv/bin/python"
mkdir -p "$ROGUE_RUNTIME"
git clone https://github.com/neuroagents-lab/ROGUE.git "$ROGUE_ROOT"
git -C "$ROGUE_ROOT" checkout --detach c6cb2a0022b23707dd647282abda99fa09488d98
git -C "$ROGUE_ROOT" apply "$PWD/docs/setup/patches/rogue-scoped-aws.patch"
git -C "$ROGUE_ROOT" apply "$PWD/docs/setup/patches/rogue-inspect-responses.patch"
uv venv --python 3.11 "$ROGUE_RUNTIME/native-venv"
uv pip install --python "$ROGUE_NATIVE_PYTHON" --torch-backend cpu \
  -r "$ROGUE_ROOT/requirements.txt"
uv pip freeze --python "$ROGUE_NATIVE_PYTHON" > "$ROGUE_RUNTIME/native-versions.txt"
```

Inspect uses Python 3.13 from the repository lockfile. Keep the native checkout at the pinned commit and preserve the original task JSON files. The adapter checks both before running a sample. Re-export `ROGUE_ROOT` and `ROGUE_NATIVE_PYTHON` in new shells or keep the exports in `controller.env`.

| Path | Why it is in the repository |
| --- | --- |
| [`patches/rogue-scoped-aws.patch`](patches/rogue-scoped-aws.patch) | Uses the operator's launch request for initial boot and reset, and requires a TTL schedule for those workers. |
| [`patches/rogue-inspect-responses.patch`](patches/rogue-inspect-responses.patch) | Lets the pinned native runner handle split reasoning and action items returned through Inspect's Responses bridge. |
| [`tools/`](../../tools/) Python scripts | Check package readiness, sync catalogs from a separate clean pinned checkout, and report scores from saved native evidence. |

## 4. Configure inference on the controller

The worked commands use the GPT Responses route. Use a direct OpenAI API credential provided to the controller as `OPENAI_API_KEY` and set `ROGUE_ACTOR=openai/gpt-5.4-mini`, or use the project's GL Hawk gateway below. Start in a shell with the desired endpoint and credentials before launching Inspect.

For GL, install the [Hawk CLI](https://hawk.metr.org/getting-started/installation/) at the deployment's version and log in from the controller shell. The login account needs access to the routed model and to any eval sets it imports.

```bash
export HAWK_API_URL=https://api.hawk.hawk.generalitylabs.ai
export HAWK_LOG_VIEWER_URL=https://viewer.hawk.hawk.generalitylabs.ai
hawk auth login --no-browser
export OPENAI_BASE_URL=https://middleman.hawk.generalitylabs.ai/openai/v1
export OPENAI_API_KEY="$(hawk auth access-token)"
export ROGUE_ACTOR=openai/openrouter/openai/gpt-5.4-mini
```

Refresh the gateway token before launching each group of samples and size groups to fit its lifetime. Keep secrets out of shell history, committed files and logs. The native runner uses the Inspect bridge for inference. Inspect uses the provider credential supplied in the controller shell.

Continue with the [one-task smoke test](../reproduce.md#run-one-task).
