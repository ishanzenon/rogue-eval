"""Check sample mapping, bridge routing, and evidence retention with a mocked worker."""

import hashlib
import json
from collections import Counter
from unittest.mock import AsyncMock

import pytest
from inspect_ai.model import ModelName, get_model
from inspect_ai.solver import TaskState

from rogue_eval.rogue_eval import (
    EVAL_VERSION,
    STEP_LIMITS,
    load_records,
    native_command,
    native_episode,
    parse_native_score,
    record_to_sample,
    rogue_eval,
)


@pytest.mark.asyncio
async def test_native_episode_rejects_missing_worker_before_sandbox_access(monkeypatch):
    import importlib

    module = importlib.import_module("rogue_eval.rogue_eval")

    def forbidden_sandbox():
        raise AssertionError("An unconfigured worker must not be accessed")

    monkeypatch.setattr(module, "sandbox", forbidden_sandbox)
    state = TaskState(
        model=ModelName("mockllm/model"),
        sample_id="control",
        epoch=1,
        input="original task",
        messages=[],
    )
    solve = native_episode(
        "/opt/ROGUE",
        "/opt/rogue-venv/bin/python",
        "docker",
        None,
        "us-east-1",
        "low",
        900,
        configured=False,
    )
    with pytest.raises(RuntimeError, match="worker config"):
        await solve(state, AsyncMock())


def test_original_task_counts_and_unique_ids():
    records = load_records()
    assert Counter(r["scenario"] for r in records) == {
        "override": 52,
        "rewire": 22,
        "restrictedaccess": 8,
    }
    assert len({r["id"] for r in records}) == 82
    for r in records:
        assert r["id"] == r["config"]["id"]
        assert record_to_sample(r).input == r["config"]["instruction"]
        assert r["max_steps"] == STEP_LIMITS[r["scenario"]]
        assert len(r["config_sha256"]) == 64


@pytest.mark.parametrize(("text", "expected"), [("0", 0), ("1\n", 1), ("0.5", 0.5)])
def test_task_score_values(text, expected):
    assert parse_native_score(text) == expected


@pytest.mark.parametrize("text", ["", "nan", "inf", "-1", "1.1", "broken"])
def test_missing_skipped_or_invalid_is_not_zero(text):
    with pytest.raises(RuntimeError):
        parse_native_score(text)


def test_native_command_preserves_original_loop_and_budget():
    args = native_command(
        "/native/python",
        "/opt/ROGUE",
        "/tmp/one.json",
        "/tmp/out",
        "override",
        "gpt-5.4-mini",
        "docker",
        None,
        "us-east-1",
        "low",
    )
    assert args[:2] == ["/native/python", "/opt/ROGUE/run.py"]
    assert args[args.index("--max_steps") + 1] == "20"
    assert args[args.index("--action_space") + 1] == "pyautogui"
    assert args[args.index("--observation_type") + 1] == "screenshot"
    assert "--enable_subagents" not in args
    assert "--deployment-prompt" not in args


def test_task_construction_does_not_need_a_vm():
    task = rogue_eval(sandbox_config="operator-worker.yaml")
    assert len(task.dataset) == 82
    assert EVAL_VERSION == "2-A"
    assert len(rogue_eval(scenario="override", sandbox_config="worker.yaml").dataset) == 52


def test_execution_cannot_silently_use_a_default_empty_sandbox():
    task = rogue_eval()
    assert task.sandbox is None
    assert len(task.dataset) == 82


def test_unknown_scenario_cannot_silently_drop_samples():
    with pytest.raises(ValueError, match="Unknown"):
        rogue_eval(scenario="typo", sandbox_config="worker.yaml")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "domain",
    [
        "override",
        "rewire",
        "restrictedaccess",
        "subagents_override",
        "subagents_rewire",
        "subagents_restrictedaccess",
    ],
)
@pytest.mark.parametrize(
    ("native_exit", "score_text", "expected_status"),
    [(0, "0", "success"), (0, "skipped", "success"), (1, "", "error")],
)
async def test_first_original_episode_through_inspect_with_mocked_worker(
    monkeypatch, tmp_path, native_exit, score_text, expected_status, domain
):
    """A pipeline test; explicitly not a VM boot or native desktop E2E test."""
    import importlib
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    from inspect_ai.model import ModelOutput

    module = importlib.import_module("rogue_eval.rogue_eval")
    record = next(
        r
        for r in load_records(domain)
        if r["id"].endswith(
            "897e3b53-5d4d-444b-85cb-2cdc8a97d903"
            if "restrictedaccess" in domain
            else "0512bb38-d531-4acf-9e7e-0add90816068"
        )
    )
    config_text = '{"test":"original-config"}'
    record = dict(record, config_sha256=hashlib.sha256(config_text.encode()).hexdigest())
    writes = {}

    async def execute(cmd, **kwargs):
        if cmd[0] == "git":
            out = module.ROGUE_COMMIT
        elif "-c" in cmd:
            out = json.dumps(["/tmp/native/result.txt"])
        else:
            out = ""
        failed_native = len(cmd) > 1 and cmd[1].endswith("/run.py")
        return SimpleNamespace(
            returncode=native_exit if failed_native else 0, stdout=out, stderr=""
        )

    async def read_file(path, text=True):
        if not text:
            return b"mock artifact archive"
        return score_text if path.endswith("result.txt") else config_text

    async def write_file(path, value):
        writes[path] = value

    fake = SimpleNamespace(exec=execute, read_file=read_file, write_file=write_file)

    @asynccontextmanager
    async def bridge(*, model_aliases, forward_generation_config, port):
        assert forward_generation_config
        assert port == 13131
        assert model_aliases == {"gpt-5.4-mini": inspect_actor}
        yield SimpleNamespace(
            port=13131,
            state=SimpleNamespace(messages=[], output=ModelOutput.from_content("mock", "DONE")),
        )

    monkeypatch.setattr(module, "sandbox", lambda: fake)
    monkeypatch.setattr(module, "sandbox_agent_bridge", bridge)
    name = "openrouter/openai/gpt-5.4-mini" if domain == "override" else "gpt-5.4-mini"
    inspect_actor = get_model(f"openai/{name}", api_key="offline-placeholder")
    monkeypatch.setattr(module, "get_model", lambda: inspect_actor)
    monkeypatch.setattr(module, "load_records", lambda domain="all": [record])
    monkeypatch.setattr(
        module,
        "analyze_archive",
        lambda *args: {
            "family": "override",
            "actual": {"detector_evidence_available": False},
        },
    )
    monkeypatch.chdir(tmp_path)
    task = rogue_eval(scenario=domain, sandbox_config="unused", access_ready=True)
    # We mocked the worker transport and bridge, so no real sandbox is launched.
    task.sandbox = None
    logs = await module_test_eval(task, tmp_path)
    assert logs[0].status == expected_status
    assert logs[0].samples is not None
    if expected_status == "success":
        assert logs[0].samples[0].scores is not None
        assert set(logs[0].samples[0].scores) == {
            "native_task_completion",
            "native_task_success",
            "actual_violation",
            "intended_violation",
            "alternate_shutdown_avoidance",
        }
        score = logs[0].samples[0].scores["native_task_completion"]
        if score_text == "skipped":
            assert score.reason == "upstream_skipped"
        else:
            assert score.value == 0
    else:
        assert logs[0].samples[0].error is not None
        assert not logs[0].samples[0].scores
    assert len(list((tmp_path / "artifacts").glob("*/native-artifacts.tar.gz"))) == 1
    manifests = [v for k, v in writes.items() if k.endswith("manifest.json")]
    assert json.loads(manifests[0]) == {domain: [record["id"]]}


async def module_test_eval(task, tmp_path):
    from inspect_ai import eval_async

    return await eval_async(task, model="mockllm/model", log_dir=str(tmp_path))
