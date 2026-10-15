# Disclosure Boundary

This repository publishes an auditable AI-assisted scientific-research routing core. It does not publish a claim that an AI system has independently made a validated scientific discovery.

## Included

- Evidence summaries read from a user-supplied local SQLite literature store.
- Deterministic gates for novelty review, hypothesis formalization, computational-experiment readiness and replication routing.
- A small no-credential demonstration and regression tests.
- Explicit references to optional upstream projects, without vendoring their code.
- A thin adapter to the existing gated Docker execution kernel; direct Windows host execution is denied.

## Excluded

- Private research notes, raw literature PDFs, API keys, paid-platform credentials and non-public datasets.
- Physical-laboratory control, unreviewed model-generated hypotheses presented as discoveries, and scientific-performance claims.
- Any assertion that an upstream project has been executed through this repository unless a reproducible run record is added.
- Any scientific claim whose exact evidence, experiment and independent-replication artifacts have not passed hash-bound review.

## Legacy material

The earlier formula-alpha prototype and its synthetic fixtures remain for historical context. They demonstrate the general promotion-gate and rejection-accounting pattern only; they are not part of the current scientific-discovery claim.
