"""Resolve native ROGUE presets and validate options for the desktop runner."""

import hashlib
import json
import math
from pathlib import Path
from typing import Any

DATA = Path(__file__).with_name("data")
MANAGED = {
    "provider_name",
    "path_to_vm",
    "region",
    "model",
    "client_password",
    "test_config_base_dir",
    "test_all_meta_path",
    "result_dir",
    "domain",
}


def read_data(name: str) -> Any:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def schema_by_dest() -> dict[str, dict[str, Any]]:
    return {v["dest"]: dict(v, flag=k) for k, v in read_data("native_schema.json").items()}


def validate_options(options: dict[str, Any]) -> dict[str, Any]:
    schema = schema_by_dest()
    for key, value in options.items():
        if key not in schema or key in MANAGED:
            raise ValueError(f"Unknown or adapter-managed native option: {key}")
        rule = schema[key]
        if key == "recording_mode":
            if value not in {"full", "per-step"}:
                raise ValueError("recording_mode must be full or per-step")
            continue
        kind = rule["type"]
        valid = (
            isinstance(value, bool)
            if kind == "bool"
            else isinstance(value, int) and not isinstance(value, bool)
            if kind == "int"
            else isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            if kind == "float"
            else isinstance(value, str)
        )
        if not valid or (rule["choices"] and value not in rule["choices"]):
            raise ValueError(f"Invalid native value for {key}")
        if (
            key
            in {"max_steps", "max_tokens", "max_trajectory_length", "screen_width", "screen_height"}
            and value <= 0
        ):
            raise ValueError(f"{key} must be positive")
        if key == "sleep_after_execution" and value < 0:
            raise ValueError("sleep_after_execution must be nonnegative")
    if options.get("subagent_inherit_parent_history") and not options.get("enable_subagents"):
        raise ValueError("Inherited history requires enable_subagents")
    return dict(options)


def options_to_args(options: dict[str, Any]) -> list[str]:
    schema = schema_by_dest()
    result = []
    for key, value in validate_options(options).items():
        if key == "recording_mode":
            result.append("--full-recording" if value == "full" else "--per-step-recording")
        elif isinstance(value, bool):
            if value:
                result.append(schema[key]["flag"])
        else:
            result.extend([schema[key]["flag"], str(value)])
    return result


def preset_options(name: str) -> tuple[dict[str, Any], dict[str, list[str]], str]:
    presets = read_data("experiment_presets.json")
    if name not in presets:
        raise ValueError(f"Unknown original experiment preset: {name}")
    preset = presets[name]
    schema = read_data("native_schema.json")
    args = preset["common_args"] + preset["native_args"]
    options: dict[str, Any] = {
        "reasoning_effort": "medium",
        "recording_mode": "per-step",
        "action_space": "pyautogui",
        "headless": True,
    }
    model = ""
    i = 0
    while i < len(args):
        rule = schema[args[i]]
        key = rule["dest"]
        value = rule["const"] if rule["nargs"] == 0 else args[i + 1]
        i += 1 if rule["nargs"] == 0 else 2
        if key == "model":
            model = value
        elif key not in MANAGED:
            options[key] = {"int": int, "float": float}.get(rule["type"], lambda x: x)(value)
    return validate_options(options), preset["selection"], model


def condition_fingerprint(settings: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(settings, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
