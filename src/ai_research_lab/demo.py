"""Run the local scientific-routing demonstration without external credentials."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .router import EvidenceSnapshot, HypothesisCard, route_research


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--literature-db", type=Path)
    args = parser.parse_args()
    evidence = EvidenceSnapshot.from_literature_db(args.literature_db) if args.literature_db else EvidenceSnapshot(12, 1, 4, 3)
    hypothesis = HypothesisCard(
        mechanism="A coarse representation hides a latent regime and produces clustered residual anomalies.",
        executable_direction="Compare pooled and regime-aware probabilistic models on held-out observations.",
        predictions=("The regime-aware model reduces structured residual clusters without only improving aggregate fit.",),
        falsifiers=("Independent measurements remove the residual clusters without a regime-aware representation.",),
        novelty_response="The target is representation-failure detection and anomaly preservation, not prediction alone.",
    )
    print(json.dumps(route_research(evidence, hypothesis).to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
