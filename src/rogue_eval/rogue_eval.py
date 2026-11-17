"""Day 1 adapter: original ROGUE episodes and Inspect model routing."""

import asyncio
import hashlib
import inspect
import json
import math
import uuid
from pathlib import Path
from typing import Any

from inspect_ai import Task, task
from inspect_ai.agent import sandbox_agent_bridge
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import get_model
from inspect_ai.scorer import Score, Target, mean, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import sandbox
from inspect_evals_utils.metadata import load_eval_version

EVAL_VERSION = load_eval_version(__file__)
ROGUE_COMMIT = "c6cb2a0022b23707dd647282abda99fa09488d98"
STEP_LIMITS = {"override": 20, "rewire": 25, "restrictedaccess": 40}


def load_records() -> list[dict[str, Any]]:
    return json.loads(Path(__file__).with_name("tasks.json").read_text(encoding="utf-8"))


def record_to_sample(record: dict[str, Any]) -> Sample:
    return Sample(
        id=record["id"],
        input=record["instruction"],
        metadata={k: v for k, v in record.items() if k != "instruction"},
    )


def parse_native_score(text: str) -> float:
    if text.strip().lower() == "skipped":
        raise RuntimeError("Native evaluator skipped; no valid task score")
    try:
        value = float(text.strip())
    except ValueError as exc:
        raise RuntimeError("Native task score missing or invalid") from exc
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise RuntimeError("Native task score must be finite and between zero and one")
    return value


def native_command(
    native_python: str,
    root: str,
    manifest: str,
    results: str,
    scenario: str,
    model_alias: str,
    provider: str,
    path_to_vm: str | None,
    region: str,
    reasoning_effort: str,
) -> list[str]:
    args = [
        native_python,
        f"{root}/run.py",
        "--provider_name",
        provider,
        "--headless",
        "--action_space",
        "pyautogui",
        "--observation_type",
        "screenshot",
        "--max_steps",
        str(STEP_LIMITS[scenario]),
        "--max_trajectory_length",
        "20",
        "--per-step-recording",
        "--model",
        model_alias,
        "--reasoning_effort",
        reasoning_effort,
        "--test_all_meta_path",
        manifest,
        "--result_dir",
        results,
        "--region",
        region,
        "--client_password",
        "password" if provider == "vmware" else "osworld-public-evaluation",
    ]
    if path_to_vm:
        args.extend(["--path_to_vm", path_to_vm])
    return args


@solver
def native_episode(
    root: str,
    native_python: str,
    provider: str,
    path_to_vm: str | None,
    region: str,
    reasoning_effort: str,
    episode_timeout: int,
    configured: bool = True,
) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        if not configured:
            raise RuntimeError("Provisioned worker config required; see DAY1.md")
        env = sandbox()
        revision = await env.exec(["git", "-C", root, "rev-parse", "HEAD"], timeout=15)
        if revision.returncode or revision.stdout.strip() != ROGUE_COMMIT:
            raise RuntimeError("Worker must contain pinned ROGUE checkout; see DAY1.md")
        text = await env.read_file(f"{root}/{state.metadata['config_path']}")
        if hashlib.sha256(text.encode()).hexdigest() != state.metadata["config_sha256"]:
            raise RuntimeError("Worker task config differs from pinned original")
        scenario = state.metadata["scenario"]
        if scenario == "restrictedaccess":
            raise RuntimeError("Access runs await private-artifact and Drive validation")
        features = inspect.signature(sandbox_agent_bridge).parameters
        if not {"model_aliases", "forward_generation_config"} <= features.keys():
            raise RuntimeError("Inspect bridge lacks required routing/config support")
        work = "/tmp/rogue-inspect-" + uuid.uuid4().hex
        created = await env.exec(["mkdir", "-p", work], timeout=10)
        if created.returncode:
            raise RuntimeError("Cannot create episode artifact directory")
        manifest_path = work + "/manifest.json"
        await env.write_file(manifest_path, json.dumps({scenario: [state.sample_id]}))
        model = get_model()
        if not model.name.startswith("openai/"):
            raise RuntimeError("Day 1 validates OpenAI actor routing first")
        alias = model.name.split("/", 1)[1]
        command = native_command(
            native_python,
            root,
            manifest_path,
            work + "/results",
            scenario,
            alias,
            provider,
            path_to_vm,
            region,
            reasoning_effort,
        )
        state.metadata["native_artifact_directory"] = work
        state.metadata["scoring_scope"] = "task completion; corrigibility scorers pending"
        try:
            async with sandbox_agent_bridge(
                model_aliases={alias: model}, forward_generation_config=True
            ) as bridge:
                result = await env.exec(
                    command,
                    cwd=root,
                    timeout=episode_timeout,
                    env={
                        "OPENAI_BASE_URL": f"http://localhost:{bridge.port}/v1",
                        "OPENAI_API_BASE": f"http://localhost:{bridge.port}/v1",
                        "OPENAI_API_KEY": "inspect-bridge",
                        "LITELLM_TELEMETRY": "False",
                    },
                )
                state.messages = bridge.state.messages
                state.output = bridge.state.output
            await env.write_file(work + "/native-stdout.log", result.stdout)
            await env.write_file(work + "/native-stderr.log", result.stderr)
            if result.returncode:
                raise RuntimeError(f"Native episode failed; private artifacts: {work}")
            listing = await env.exec(
                [
                    native_python,
                    "-c",
                    "import json,pathlib,sys; print(json.dumps([str(p) for p in pathlib.Path(sys.argv[1]).rglob('result.txt')]))",
                    work + "/results",
                ],
                timeout=15,
            )
            if listing.returncode:
                raise RuntimeError("Cannot locate native result")
            files = json.loads(listing.stdout)
            if len(files) != 1:
                raise RuntimeError("Expected exactly one native task result")
            state.metadata["native_task_score"] = parse_native_score(await env.read_file(files[0]))
        finally:
            archive = work + "/native-artifacts.tar.gz"
            packed = await env.exec(
                [
                    "tar",
                    "--exclude=native-artifacts.tar.gz",
                    "-czf",
                    archive,
                    "-C",
                    work,
                    ".",
                ],
                timeout=60,
            )
            if packed.returncode:
                raise RuntimeError("Could not preserve native evidence before worker cleanup")
            content = await env.read_file(archive, text=False)
            destination = Path("artifacts") / (str(state.sample_id) + "-" + uuid.uuid4().hex)
            await asyncio.to_thread(destination.mkdir, parents=True)
            await asyncio.to_thread((destination / "native-artifacts.tar.gz").write_bytes, content)
            state.metadata["retained_native_artifacts"] = str(destination.resolve())
        state.completed = True
        return state

    return solve


@scorer(metrics=[mean()])
def native_task_completion():
    # Inspect requires an async scoring callback even for an in-memory result.
    async def score(state: TaskState, target: Target) -> Score:  # ruff: ignore[unused-async]
        if "native_task_score" not in state.metadata:
            raise RuntimeError("No native score; infrastructure failure is not a zero")
        return Score(
            value=state.metadata["native_task_score"],
            explanation="Original task evaluator, not a corrigibility score",
        )

    return score


@task
def rogue_eval(
    scenario: str = "all",
    worker_sandbox: str = "ec2",
    sandbox_config: str | None = None,
    root: str = "/opt/ROGUE",
    native_python: str = "/opt/rogue-venv/bin/python",
    provider: str = "docker",
    path_to_vm: str | None = None,
    region: str = "us-east-1",
    reasoning_effort: str = "low",
    episode_timeout: int = 900,
) -> Task:
    """Run original episodes on a separately provisioned controller.

    Args:
        scenario: Original scenario key or all 82 main tasks.
        worker_sandbox: Installed Inspect controller provider.
        sandbox_config: Operator-provided config; required to execute.
        root: Pinned native checkout on the controller.
        native_python: Separate Python 3.11 ROGUE environment.
        provider: Native VM provider, distinct from the Inspect provider.
        path_to_vm: Native provider VM identifier/path.
        region: Native AWS region when relevant.
        reasoning_effort: Explicit smoke setting, not a paper-reproduction preset.
        episode_timeout: Timeout; provider-side cleanup/TTL is also required.

    Returns:
        Original-episode adapter with task-completion scoring.
    """
    if scenario != "all" and scenario not in STEP_LIMITS:
        raise ValueError(f"Unknown ROGUE scenario: {scenario}")
    records = [r for r in load_records() if scenario == "all" or r["scenario"] == scenario]
    return Task(
        dataset=MemoryDataset([record_to_sample(r) for r in records]),
        solver=native_episode(
            root,
            native_python,
            provider,
            path_to_vm,
            region,
            reasoning_effort,
            episode_timeout,
            bool(sandbox_config),
        ),
        scorer=native_task_completion(),
        sandbox=(worker_sandbox, sandbox_config) if sandbox_config else None,
        version=EVAL_VERSION,
    )
