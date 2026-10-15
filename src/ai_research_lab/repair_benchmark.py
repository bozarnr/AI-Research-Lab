"""Deterministic semi-synthetic pilot for representation-repair routing.

The benchmark is intentionally small and transparent: it does not claim a
scientific discovery. It tests whether a routing policy loses repair-relevant
signals after evidence compression when the hidden cause is known.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path


CAUSES = ("measurement", "parameter", "structural", "latent")


@dataclass(frozen=True)
class ResidualCase:
    cause: str
    global_error: float
    predictor_correlation: float
    interaction_correlation: float
    group_gap: float


def generate_cases(seed: int, per_cause: int = 25) -> tuple[ResidualCase, ...]:
    """Generate hidden-cause cases with deliberately overlapping global error."""
    rng = random.Random(seed)
    cases: list[ResidualCase] = []
    signatures = {
        "measurement": (0.06, 0.05, 0.05),
        "parameter": (0.82, 0.06, 0.05),
        "structural": (0.10, 0.82, 0.08),
        "latent": (0.08, 0.07, 0.82),
    }
    for cause in CAUSES:
        predictor, interaction, group = signatures[cause]
        for _ in range(per_cause):
            cases.append(
                ResidualCase(
                    cause=cause,
                    global_error=1.0 + rng.uniform(-0.04, 0.04),
                    predictor_correlation=max(0.0, predictor + rng.uniform(-0.04, 0.04)),
                    interaction_correlation=max(0.0, interaction + rng.uniform(-0.04, 0.04)),
                    group_gap=max(0.0, group + rng.uniform(-0.04, 0.04)),
                )
            )
    return tuple(cases)


def compressed_policy(case: ResidualCase) -> str:
    """An abstraction-only policy that sees only a global fit summary."""
    del case
    return "parameter"


def residual_diagnostic_policy(case: ResidualCase) -> str:
    """A fixed diagnostic policy that keeps repair-level residual signatures."""
    if case.group_gap >= 0.5:
        return "latent"
    if case.interaction_correlation >= 0.5:
        return "structural"
    if case.predictor_correlation >= 0.5:
        return "parameter"
    return "measurement"


def evaluate(policy, cases: tuple[ResidualCase, ...]) -> dict[str, object]:
    predictions = [policy(case) for case in cases]
    correct = sum(prediction == case.cause for prediction, case in zip(predictions, cases))
    under_revisions = sum(
        case.cause in {"structural", "latent"} and prediction in {"measurement", "parameter"}
        for prediction, case in zip(predictions, cases)
    )
    return {
        "repair_accuracy": round(correct / len(cases), 4),
        "under_revision_rate": round(under_revisions / len(cases), 4),
        "n_cases": len(cases),
    }


def run_pilot(seeds: tuple[int, ...] = (7, 19, 31)) -> dict[str, object]:
    """Run pre-registered policies on fixed seeds and return an audit-friendly result."""
    runs = []
    for seed in seeds:
        cases = generate_cases(seed)
        runs.append(
            {
                "seed": seed,
                "compressed": evaluate(compressed_policy, cases),
                "residual_diagnostic": evaluate(residual_diagnostic_policy, cases),
            }
        )
    average = {
        name: {
            metric: round(sum(run[name][metric] for run in runs) / len(runs), 4)
            for metric in ("repair_accuracy", "under_revision_rate")
        }
        for name in ("compressed", "residual_diagnostic")
    }
    return {
        "benchmark": "representation-repair-semi-synthetic-v1",
        "seeds": list(seeds),
        "hidden_causes": list(CAUSES),
        "fixed_policies": {
            "compressed": "global-error-only policy; always applies parameter repair",
            "residual_diagnostic": "uses predictor, interaction and group residual signatures",
        },
        "runs": runs,
        "average": average,
        "interpretation_boundary": "This pilot validates only the measurement harness on constructed signatures. It does not establish that AI systems revise scientific representations correctly in real domains.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_pilot()
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        if args.output.exists():
            raise FileExistsError(f"refusing to overwrite existing result: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
