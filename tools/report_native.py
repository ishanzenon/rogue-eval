"""Summarize retained native archives offline, grouped by recorded condition.

This uses upstream rates and reports missing judges. Inspect's conditional scored
means can differ. No model calls are made; outputs stay in private artifacts/.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

from rogue_eval import _upstream as upstream
from rogue_eval.scoring import analyze_archive, scenario_family, upstream_summary


def build_report(
    artifact_root: Path, primary: str, secondary: str | None, settings_file: str | None = None
):
    groups = defaultdict(list)
    for archive in artifact_root.rglob("native-artifacts.tar.gz"):
        import tarfile

        with tarfile.open(archive, "r:gz") as source:
            condition_member = next(
                (m for m in source.getmembers() if m.name.lstrip("./") == "adapter-condition.json"),
                None,
            )
            if condition_member is None:
                raise ValueError(
                    "Archive lacks condition provenance; do not mix Day 1 and later evidence"
                )
            stream = source.extractfile(condition_member)
            assert stream is not None
            condition = json.load(stream)
            candidates = [
                Path(m.name).parent.name
                for m in source.getmembers()
                if m.name.endswith("/result.txt")
            ]
        if len(candidates) > 1:
            raise ValueError("Archive does not contain exactly one task result")
        if candidates:
            evidence = analyze_archive(archive, candidates[0], condition["scenario"], settings_file)
            if (
                evidence["family"] == "restrictedaccess"
                and not evidence["actual"]["detector_evidence_available"]
            ):
                raise ValueError(
                    "Access reference reporting requires private sentinel settings and available logs"
                )
        else:
            evidence = {
                "task_id": condition["sample_id"],
                "family": scenario_family(condition["scenario"]),
                "actual": {"result_found": False},
            }
        judges = {}
        for cache in archive.parent.glob("judge-*.json"):
            record = json.loads(cache.read_text(encoding="utf-8"))
            model = record["model"]
            if model in judges:
                raise ValueError(
                    "Multiple judge configurations for one model; select a single adjudication condition"
                )
            judges[model] = {"output": record["judgment"]}
        primary_output = judges.get(primary, {}).get("output")
        comparison = upstream.build_judge_comparison(
            evidence["family"],
            judges,
            SimpleNamespace(judge_id=primary),
            SimpleNamespace(judge_id=secondary or "not-configured"),
        )
        groups[condition["scenario"], condition["fingerprint"]].append(
            {
                "task_id": evidence["task_id"],
                "archive": str(archive),
                "epoch": condition.get("epoch"),
                "actual": evidence["actual"],
                "judge": primary_output,
                "judge_comparison": comparison,
            }
        )
    return [
        {
            "domain": domain,
            "condition_fingerprint": fingerprint,
            "primary_judge": primary,
            "secondary_judge": secondary,
            "reference_summary": upstream_summary(domain, entries),
            "tasks": entries,
        }
        for (domain, fingerprint), entries in sorted(groups.items())
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--primary-judge", default="openai/gpt-5.5")
    parser.add_argument("--secondary-judge")
    parser.add_argument("--settings-file")
    args = parser.parse_args()
    report = build_report(
        args.artifacts, args.primary_judge, args.secondary_judge, args.settings_file
    )
    destination = args.artifacts / "native-summary.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(report)} condition groups to {destination}; no model calls")


if __name__ == "__main__":
    main()
