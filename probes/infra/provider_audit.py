"""Read-only checks of the native ROGUE provider prerequisites on a Hawk runner."""

import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.solver import solver

ROGUE_COMMIT = "c6cb2a0022b23707dd647282abda99fa09488d98"


def collect():
    report = {"rogue_commit": ROGUE_COMMIT, "model_calls_by_probe": 0}
    report["runner_binaries"] = {
        n: shutil.which(n)
        for n in ["docker", "dockerd", "vmrun", "VBoxManage", "qemu-system-x86_64"]
    }
    report["runner_devices"] = {
        p: os.path.exists(p)
        for p in ["/dev/kvm", "/var/run/docker.sock", "/dev/vboxdrv", "/dev/vmmon"]
    }
    report["configuration_present"] = {
        n: bool(os.getenv(n))
        for n in [
            "AWS_REGION",
            "AWS_SUBNET_ID",
            "AWS_SECURITY_GROUP_ID",
            "AWS_SCHEDULER_ROLE_ARN",
            "AZURE_SUBSCRIPTION_ID",
            "ALIYUN_ACCESS_KEY_ID",
            "ALIYUN_IMAGE_ID",
            "VOLCENGINE_ACCESS_KEY_ID",
            "VOLCENGINE_IMAGE_ID",
            "MODAL_TOKEN_ID",
        ]
    }
    try:
        from kubernetes import client, config

        config.load_incluster_config()
        report["runtime_classes"] = [
            x.metadata.name
            for x in client.NodeV1Api().list_runtime_class(_request_timeout=10).items
        ]
    except Exception as e:
        report["runtime_class_discovery"] = {
            "type": type(e).__name__,
            "status": getattr(e, "status", None),
        }

    root = Path(tempfile.mkdtemp(prefix="rogue-provider-audit-"))
    try:
        commands = [
            ["git", "init", "-q", str(root)],
            [
                "git",
                "-C",
                str(root),
                "remote",
                "add",
                "origin",
                "https://github.com/neuroagents-lab/ROGUE.git",
            ],
            [
                "git",
                "-C",
                str(root),
                "sparse-checkout",
                "set",
                "desktop_env/providers",
                "evaluation_examples/settings",
            ],
            [
                "git",
                "-C",
                str(root),
                "fetch",
                "--depth=1",
                "--filter=blob:none",
                "origin",
                ROGUE_COMMIT,
            ],
            ["git", "-C", str(root), "checkout", "--detach", "FETCH_HEAD"],
        ]
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True, timeout=90)
            if result.returncode:
                raise RuntimeError(result.stderr[-1600:])
        report["source_checkout"] = "ok"
        sys.path.insert(0, str(root))
        # Construct the unmodified provider: this contacts only the configured
        # Docker daemon and never downloads an image or starts a container.
        try:
            provider = importlib.import_module("desktop_env.providers.docker.provider")
            p = provider.DockerProvider("us-east-1")
            report["native_docker_provider_init"] = "ok"
            p.client.close()
        except Exception as e:
            report["native_docker_provider_init"] = {
                "type": type(e).__name__,
                "error": str(e)[:1400],
            }
        # Import the original manager. Its own environment validation is run.
        try:
            importlib.import_module("desktop_env.providers.aws.manager")
            report["native_aws_manager_import"] = "ok"
        except Exception as e:
            report["native_aws_manager_import"] = {"type": type(e).__name__, "error": str(e)[:1000]}
    except Exception as e:
        report["source_checkout_error"] = {"type": type(e).__name__, "error": str(e)[:1800]}
    finally:
        if str(root) in sys.path:
            sys.path.remove(str(root))
        shutil.rmtree(root)

    try:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError

        cfg = Config(connect_timeout=5, read_timeout=5, retries={"max_attempts": 0})
        session = boto3.Session(region_name="us-east-1")
        credentials = session.get_credentials()
        report["aws_credential_chain"] = credentials.method if credentials else None
        ec2 = session.client("ec2", config=cfg)
        for key, operation in [
            (
                "aws_describe_rogue_ami",
                lambda: ec2.describe_images(ImageIds=["ami-0d23263edb96951d8"]),
            ),
            (
                "aws_run_instances_dry_run",
                lambda: ec2.run_instances(
                    DryRun=True,
                    ImageId="ami-0d23263edb96951d8",
                    InstanceType="t3.xlarge",
                    MinCount=1,
                    MaxCount=1,
                ),
            ),
        ]:
            try:
                response = operation()
                report[key] = {"status": "ok", "image_count": len(response.get("Images", []))}
            except ClientError as e:
                # No tokens or full ARNs in published evidence.
                report[key] = {"aws_error_code": e.response.get("Error", {}).get("Code")}
            except Exception as e:
                report[key] = {"type": type(e).__name__, "error": str(e)[:600]}
    except Exception as e:
        report["aws_check"] = {"type": type(e).__name__, "error": str(e)[:600]}
    return report


@solver
def provider_audit_solver():
    async def solve(state, generate):
        import asyncio

        report = await asyncio.to_thread(collect)
        state.metadata["provider_audit"] = report
        print("ROGUE_PROVIDER_AUDIT " + json.dumps(report, sort_keys=True), flush=True)
        state.completed = True
        return state

    return solve


@task
def native_provider_audit():
    return Task(
        dataset=[Sample(id="native-providers", input="Read-only ROGUE provider audit")],
        solver=provider_audit_solver(),
        time_limit=240,
    )


@solver
def runtime_admission_solver():
    async def solve(state, generate):
        from kubernetes import client, config

        config.load_incluster_config()
        runner_ns = (
            Path("/var/run/secrets/kubernetes.io/serviceaccount/namespace").read_text().strip()
        )
        namespace = runner_ns + "-s"
        api = client.CoreV1Api()
        report = {"dry_run_only": True, "runtimes": {}}
        for runtime in [
            "gvisor",
            "kata",
            "kata-lockdown",
            "kata-peer",
            "kata-open",
            "nitro",
            "nitro-32bit",
        ]:
            body = {
                "apiVersion": "v1",
                "kind": "Pod",
                "metadata": {"name": "rogue-runtime-admission-" + runtime},
                "spec": {
                    "restartPolicy": "Never",
                    "runtimeClassName": runtime,
                    "automountServiceAccountToken": False,
                    "containers": [
                        {
                            "name": "check",
                            "image": "python:3.12-slim-bookworm",
                            "command": ["true"],
                            "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}},
                        }
                    ],
                },
            }
            try:
                api.create_namespaced_pod(namespace, body, dry_run="All", _request_timeout=10)
                report["runtimes"][runtime] = {"admission": "accepted"}
            except client.exceptions.ApiException as e:
                try:
                    detail = json.loads(e.body).get("message", "")
                except Exception:
                    detail = e.reason
                report["runtimes"][runtime] = {"status": e.status, "message": detail}
        state.metadata["runtime_admission"] = report
        print("ROGUE_RUNTIME_ADMISSION " + json.dumps(report, sort_keys=True), flush=True)
        state.completed = True
        return state

    return solve


@task
def runtime_admission_audit():
    return Task(
        dataset=[
            Sample(id="runtime-admission", input="Validate runtime names without creating pods")
        ],
        solver=runtime_admission_solver(),
        time_limit=90,
    )
