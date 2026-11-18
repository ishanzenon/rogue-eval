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

from rogue_eval.scoring import (
    actual_violation,
    alternate_shutdown_avoidance,
    analyze_archive,
    intended_violation,
    native_task_success,
    scenario_family,
)
from rogue_eval.settings import (
    condition_fingerprint,
    options_to_args,
    preset_options,
    read_data,
    validate_options,
)

EVAL_VERSION = load_eval_version(__file__)
ROGUE_COMMIT = "c6cb2a0022b23707dd647282abda99fa09488d98"
STEP_LIMITS = {"override": 20, "rewire": 25, "restrictedaccess": 40}


def load_records(domain: str = "all") -> list[dict[str, Any]]:
    if domain == "all":
        return json.loads(Path(__file__).with_name("tasks.json").read_text(encoding="utf-8"))
    domains = read_data("provenance.json")["domains"]
    if domain == "all_variants":
        return [record for name in domains for record in read_data(f"variants/{name}.json")]
    if domain not in domains:
        raise ValueError(f"Unknown ROGUE scenario: {domain}")
    return read_data(f"variants/{domain}.json")


def record_to_sample(record: dict[str, Any]) -> Sample:
    return Sample(
        id=record["id"],
        input=record["instruction"],
        metadata={k: v for k, v in record.items() if k != "instruction"},
    )


def parse_native_score(text: str) -> float | str:
    if text.strip().lower() == "skipped":
        return "skipped"
    try:
        value = float(text.strip())
    except ValueError as exc:
        raise RuntimeError("Native task score missing or invalid") from exc
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise RuntimeError("Native task score must be finite and between zero and one")
    return value


def resolved_options(
    scenario: str, reasoning_effort: str, native_options: dict[str, Any] | None = None
) -> dict[str, Any]:
    family = scenario_family(scenario)
    options = {
        "headless": True,
        "action_space": "pyautogui",
        "observation_type": "screenshot",
        "max_steps": STEP_LIMITS[family] + (10 if scenario.startswith("subagents_") else 0),
        "max_trajectory_length": 20,
        "recording_mode": "per-step",
        "reasoning_effort": reasoning_effort,
        "enable_subagents": scenario.startswith("subagents_"),
    }
    options.update(native_options or {})
    if options["enable_subagents"] != scenario.startswith("subagents_"):
        raise ValueError("Select the original subagents domain to enable delegation")
    return validate_options(options)


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
    native_options: dict[str, Any] | None = None,
) -> list[str]:
    options = resolved_options(scenario, reasoning_effort, native_options)
    args = [
        native_python,
        f"{root}/run.py",
        "--provider_name",
        provider,
        *options_to_args(options),
        "--model",
        model_alias,
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
    native_options: dict[str, Any] | None = None,
    expected_model: str | None = None,
    access_ready: bool = False,
    access_settings_file: str | None = None,
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
        if scenario_family(scenario) == "restrictedaccess" and not access_ready:
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
        if expected_model and alias != expected_model:
            raise RuntimeError(
                "Inspect actor differs from original preset; select its actor or use explicit native_options without a preset"
            )
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
            native_options,
        )
        effective = resolved_options(scenario, reasoning_effort, native_options)
        state.metadata["native_options"] = effective
        state.metadata["dataset_default_max_steps"] = state.metadata.get("max_steps")
        state.metadata["max_steps"] = effective["max_steps"]
        state.metadata["max_trajectory_length"] = effective["max_trajectory_length"]
        # Result paths contain UUIDs and must not change a condition's identity.
        semantic_args = []
        skip = False
        for argument in command[2:]:
            if skip:
                skip = False
            elif argument in {"--test_all_meta_path", "--result_dir"}:
                skip = True
            else:
                semantic_args.append(argument)
        state.metadata["condition_fingerprint"] = condition_fingerprint(
            {
                "scenario": scenario,
                "model": model.name,
                "options": semantic_args,
                "upstream": ROGUE_COMMIT,
            }
        )
        state.metadata["native_artifact_directory"] = work
        await env.write_file(
            work + "/adapter-condition.json",
            json.dumps(
                {
                    "fingerprint": state.metadata["condition_fingerprint"],
                    "scenario": scenario,
                    "model": model.name,
                    "options": effective,
                    "upstream_commit": ROGUE_COMMIT,
                    "epoch": state.epoch,
                    "sample_id": str(state.sample_id),
                }
            ),
        )
        state.metadata["scoring_scope"] = (
            "native task reward and success; separate deterministic and optional LLM scores"
        )
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
        evidence = await asyncio.to_thread(
            analyze_archive,
            destination / "native-artifacts.tar.gz",
            str(state.sample_id),
            scenario,
            access_settings_file,
        )
        evidence.pop("runtime", None)
        evidence.pop("reasoning", None)
        state.metadata["rogue_evidence"] = evidence
        state.completed = True
        return state

    return solve


@scorer(metrics=[mean()])
def native_task_completion():
    # Inspect requires an async scoring callback even for an in-memory result.
    async def score(state: TaskState, target: Target) -> Score:  # ruff: ignore[unused-async]
        if "native_task_score" not in state.metadata:
            raise RuntimeError("No native score; infrastructure failure is not a zero")
        if state.metadata["native_task_score"] == "skipped":
            return Score.unscored(
                reason="upstream_skipped",
                explanation="Native task evaluation unavailable; violation evidence may remain scoreable",
            )
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
    native_options: dict[str, Any] | None = None,
    preset: str | None = None,
    judge_model: str | None = None,
    judge_config: dict[str, Any] | None = None,
    judge_max_chars: int = 800_000,
    access_ready: bool = False,
    access_settings_file: str | None = None,
) -> Task:
    """Run original episodes on a separately provisioned controller.

    Args:
        scenario: Original domain, all for 82 main tasks, or all_variants for every public domain.
        worker_sandbox: Installed Inspect controller provider.
        sandbox_config: Operator-provided config; required to execute.
        root: Pinned native checkout on the controller.
        native_python: Separate Python 3.11 ROGUE environment.
        provider: Native VM provider, distinct from the Inspect provider.
        path_to_vm: Native provider VM identifier/path.
        region: Native AWS region when relevant.
        reasoning_effort: Explicit smoke setting, not a paper-reproduction preset.
        episode_timeout: Timeout; provider-side cleanup/TTL is also required.
        native_options: Validated native CLI destinations for budgets, prompts, observations and delegation settings.
        preset: Named original experiment_runner job; preserves its task selection, settings and actor identity.
        judge_model: Explicit Inspect grader model; no judge calls when omitted.
        judge_config: Inspect grader settings; defaults to GPT xhigh or Anthropic max with 64000 output tokens.
        judge_max_chars: Native per-file judge input limit; oversized logs fail rather than truncate.
        access_ready: Explicit confirmation of private access fixtures and artifact handling; not proof of live acceptance.
        access_settings_file: Private local Google settings path used only for the sentinel detector.

    Returns:
        Original-episode adapter with task-completion scoring.
    """
    expected_model = None
    options: dict[str, Any] = {}
    if preset:
        options, selection, expected_model = preset_options(preset)
        if scenario not in {"all", *selection}:
            raise ValueError("Scenario conflicts with original preset selection")
        records = [
            r for domain, ids in selection.items() for r in load_records(domain) if r["id"] in ids
        ]
        if len(records) != sum(len(ids) for ids in selection.values()):
            raise ValueError("Preset task selection differs from pinned catalog")
    else:
        records = load_records() if scenario == "all" else load_records(scenario)
    options.update(native_options or {})
    validate_options(options)
    for record in records:
        if "enable_subagents" in options and options["enable_subagents"] != record[
            "scenario"
        ].startswith("subagents_"):
            raise ValueError("Delegation flag conflicts with selected original domain")
    if episode_timeout < 1 or judge_max_chars < 0:
        raise ValueError("Invalid episode timeout or judge input limit")
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
            options,
            expected_model,
            access_ready,
            access_settings_file,
        ),
        scorer=[
            native_task_completion(),
            native_task_success(),
            actual_violation(),
            intended_violation(judge_model, judge_config, judge_max_chars),
            alternate_shutdown_avoidance(judge_model, judge_config, judge_max_chars),
        ],
        sandbox=(worker_sandbox, sandbox_config) if sandbox_config else None,
        version=EVAL_VERSION,
    )
