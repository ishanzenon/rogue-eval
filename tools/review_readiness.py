"""Generate an offline review and smoke plan. Never launches tasks or calls models."""

import json
from pathlib import Path

from rogue_eval.rogue_eval import load_records, native_command
from rogue_eval.settings import MANAGED, preset_options, read_data


def main():
    root = Path(__file__).resolve().parents[1]
    provenance = read_data("provenance.json")
    rows = []
    for name in read_data("experiment_presets.json"):
        options, selection, model = preset_options(name)
        rows.append(
            {
                "preset": name,
                "native_actor": model,
                "selection": selection,
                "options": options,
                "status": "offline construction verified; live actor routing and VM acceptance pending",
            }
        )
    smoke = []
    for domain in [
        "override",
        "rewire",
        "restrictedaccess",
        "subagents_override",
        "subagents_rewire",
        "subagents_restrictedaccess",
    ]:
        suffix = (
            "897e3b53-5d4d-444b-85cb-2cdc8a97d903"
            if "restrictedaccess" in domain
            else "0512bb38-d531-4acf-9e7e-0add90816068"
        )
        record = next(r for r in load_records(domain) if r["id"].endswith(suffix))
        smoke.append(
            {
                "domain": domain,
                "sample_id": record["id"],
                "config_sha256": record["config_sha256"],
                "native_smoke_command": native_command(
                    "/opt/rogue-venv/bin/python",
                    "/opt/ROGUE",
                    "PRIVATE_ONE_TASK_MANIFEST",
                    "PRIVATE_FRESH_RESULTS",
                    domain,
                    "gpt-5.4-mini",
                    "aws",
                    None,
                    "REGION_FROM_HANDOFF",
                    "low",
                ),
                "required_evidence": [
                    "Inspect .eval log and native archive",
                    "correct scenario resources and intervention",
                    "stop reason and task score",
                    "deterministic detector and judge coverage",
                    "model identity and generation settings",
                    "independent reset, timeout/cancellation cleanup and TTL",
                ],
                "status": "not run",
            }
        )
    schema = read_data("native_schema.json")
    settings = [
        {
            "flag": flag,
            "destination": rule["dest"],
            "native_default": rule["default"],
            "handling": "adapter managed" if rule["dest"] in MANAGED else "native_options",
            "live_validated": False,
        }
        for flag, rule in schema.items()
    ]
    report = {
        "upstream_commit": provenance["commit"],
        "main_samples": 82,
        "public_domain_counts": provenance["domains"],
        "presets": rows,
        "native_settings": settings,
        "smoke_plan": smoke,
        "analysis_modes": {
            "native_preflight": ["--judge-preflight"],
            "native_cache_only": ["--judge-mode", "cache_only"],
            "native_sync": ["--judge-mode", "auto"],
            "native_refresh": ["--judge-mode", "refresh"],
            "openai_batch": ["--openai-batch-action", "submit|status|apply"],
            "anthropic_batch": [
                "--judge-targets",
                "claude-opus-4.7-max",
                "--claude-batch-action",
                "submit|status|apply",
            ],
        },
        "judge_profiles": [
            {"model": "openai/gpt-5.5", "reasoning_effort": "xhigh"},
            {
                "model": "anthropic/claude-opus-4-7",
                "reasoning_effort": "max",
                "thinking_mode": "adaptive",
                "max_output_tokens": 64000,
            },
        ],
        "not_done": [
            "live desktop/model episodes",
            "GL AWS desktop access and networking",
            "Hawk PR18 image build and deployment integration",
            "OpenRouter and cross-provider transport parity",
            "full native multi-judge/batch transport validation",
            "peer review and reading-group attendance",
        ],
    }
    path = root / "configs/offline-readiness.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path}; no resources or models invoked")


if __name__ == "__main__":
    main()
