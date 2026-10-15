"""Small, local and auditable research routing core.

The module intentionally has no LLM, API-key or physical-lab dependency. It
consumes reviewed evidence counts and a structured hypothesis card, then
returns the next defensible research action. External systems such as Robin and
ToolUniverse remain optional executors behind this boundary.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvidenceSnapshot:
    total_papers: int
    direct_precursors: int
    mechanism_evidence: int
    strong_baselines: int

    @classmethod
    def from_literature_db(cls, path: Path) -> "EvidenceSnapshot":
        """Summarize the existing collector database without modifying it."""
        if not path.is_file():
            raise FileNotFoundError(f"literature database not found: {path}")
        with sqlite3.connect(path) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "papers" not in tables or "screening" not in tables:
                raise ValueError("literature database must contain papers and screening tables; run the collector and screen first")
            total = int(conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0])
            counts = {
                label: int(conn.execute("SELECT COUNT(*) FROM screening WHERE label = ?", (label,)).fetchone()[0])
                for label in ("Direct precursor", "Mechanism evidence", "Strong baseline")
            }
        return cls(total, counts["Direct precursor"], counts["Mechanism evidence"], counts["Strong baseline"])


@dataclass(frozen=True)
class HypothesisCard:
    mechanism: str
    executable_direction: str
    predictions: tuple[str, ...]
    falsifiers: tuple[str, ...]
    novelty_response: str

    def is_complete(self) -> bool:
        return bool(self.mechanism.strip() and self.executable_direction.strip() and self.predictions and self.falsifiers and self.novelty_response.strip())


@dataclass(frozen=True)
class ResearchGate:
    minimum_papers: int = 8
    minimum_mechanism_evidence: int = 2
    minimum_strong_baselines: int = 2


@dataclass(frozen=True)
class RoutingDecision:
    stage: str
    ready_for_experiment: bool
    rationale: str
    evidence: EvidenceSnapshot

    def to_dict(self) -> dict[str, object]:
        return {"stage": self.stage, "ready_for_experiment": self.ready_for_experiment, "rationale": self.rationale, "evidence": asdict(self.evidence)}


@dataclass(frozen=True)
class UpstreamIntegration:
    """A non-invasive local checkout that may serve as an optional executor."""

    name: str
    path: Path
    available: bool
    capability: str
    activation_note: str


def canonical_json(payload: object) -> str:
    """Serialize a research record deterministically before hashing it."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def artifact_digest(payload: object) -> str:
    """Return the SHA-256 identity of a JSON-compatible research artifact."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ResearchArtifact:
    """Immutable, content-addressed handoff between research stages."""

    stage: str
    payload: dict[str, object]
    sha256: str

    @classmethod
    def create(cls, stage: str, payload: dict[str, object]) -> "ResearchArtifact":
        if not stage.strip():
            raise ValueError("artifact stage must not be empty")
        return cls(stage=stage, payload=payload, sha256=artifact_digest(payload))

    def verifies(self) -> bool:
        return self.sha256 == artifact_digest(self.payload)


@dataclass(frozen=True)
class ArtifactApproval:
    """An approval that is valid for exactly one immutable artifact."""

    artifact_sha256: str
    approved_by: str

    def authorizes(self, artifact: ResearchArtifact) -> bool:
        return bool(self.approved_by.strip() and artifact.verifies() and self.artifact_sha256 == artifact.sha256)


@dataclass(frozen=True)
class ExperimentPlan:
    """Pre-registered computational comparison, not executable code."""

    hypothesis_sha256: str
    evidence_sha256: str
    baselines: tuple[str, ...]
    primary_metric: str
    seeds: tuple[int, ...]
    expected_pattern: str
    falsifier: str

    def is_complete(self) -> bool:
        return bool(
            self.hypothesis_sha256
            and self.evidence_sha256
            and self.baselines
            and self.primary_metric.strip()
            and self.seeds
            and len(set(self.seeds)) == len(self.seeds)
            and self.expected_pattern.strip()
            and self.falsifier.strip()
        )

    def artifact(self) -> ResearchArtifact:
        if not self.is_complete():
            raise ValueError("experiment plan is incomplete or repeats random seeds")
        return ResearchArtifact.create("computational_experiment", asdict(self))


def can_submit_experiment(
    plan: ExperimentPlan,
    approval: ArtifactApproval | None,
    *,
    hypothesis: ResearchArtifact,
    evidence: ResearchArtifact,
) -> bool:
    """Fail closed unless an approved plan matches its exact upstream inputs."""
    if not hypothesis.verifies() or not evidence.verifies() or not plan.is_complete():
        return False
    if plan.hypothesis_sha256 != hypothesis.sha256 or plan.evidence_sha256 != evidence.sha256:
        return False
    return approval is not None and approval.authorizes(plan.artifact())


@dataclass(frozen=True)
class HypothesisCandidate:
    """A scored candidate for deterministic portfolio selection.

    Scores must come from a recorded evidence review, not from an unlogged
    model preference. Larger is better except for estimated_execution_cost.
    """

    candidate_id: str
    evidence_strength: float
    novelty_distance: float
    falsifiability: float
    estimated_execution_cost: float

    def is_valid(self) -> bool:
        scores = (self.evidence_strength, self.novelty_distance, self.falsifiability)
        return bool(
            self.candidate_id.strip()
            and all(0.0 <= score <= 1.0 for score in scores)
            and self.estimated_execution_cost >= 0.0
        )


def dominates(left: HypothesisCandidate, right: HypothesisCandidate) -> bool:
    """Return whether left is no worse on every objective and better on one."""
    if not left.is_valid() or not right.is_valid():
        raise ValueError("all candidates need bounded scores and a non-negative cost")
    left_values = (left.evidence_strength, left.novelty_distance, left.falsifiability, -left.estimated_execution_cost)
    right_values = (right.evidence_strength, right.novelty_distance, right.falsifiability, -right.estimated_execution_cost)
    return all(a >= b for a, b in zip(left_values, right_values)) and any(a > b for a, b in zip(left_values, right_values))


def pareto_hypotheses(candidates: tuple[HypothesisCandidate, ...]) -> tuple[HypothesisCandidate, ...]:
    """Return a deterministic Pareto frontier for bounded research capacity."""
    if len({candidate.candidate_id for candidate in candidates}) != len(candidates):
        raise ValueError("candidate ids must be unique")
    frontier = [
        candidate
        for candidate in candidates
        if not any(other.candidate_id != candidate.candidate_id and dominates(other, candidate) for other in candidates)
    ]
    return tuple(sorted(frontier, key=lambda item: (-item.evidence_strength, -item.falsifiability, -item.novelty_distance, item.estimated_execution_cost, item.candidate_id)))


@dataclass(frozen=True)
class ScientificClaim:
    """A bounded claim with explicit evidence, replication and limitations."""

    statement: str
    evidence_sha256: str
    experiment_sha256: str
    replication_sha256: str
    limitations: tuple[str, ...]

    def is_complete(self) -> bool:
        return bool(
            self.statement.strip()
            and self.evidence_sha256
            and self.experiment_sha256
            and self.replication_sha256
            and self.limitations
            and all(item.strip() for item in self.limitations)
        )

    def artifact(self) -> ResearchArtifact:
        if not self.is_complete():
            raise ValueError("scientific claims need linked evidence, replication and stated limitations")
        return ResearchArtifact.create("claim_review", asdict(self))


def can_release_claim(
    claim: ScientificClaim,
    approval: ArtifactApproval | None,
    *,
    evidence: ResearchArtifact,
    experiment: ResearchArtifact,
    replication: ResearchArtifact,
) -> bool:
    """Permit release only when all cited artifacts verify and match exactly."""
    if not all(item.verifies() for item in (evidence, experiment, replication)):
        return False
    if not claim.is_complete():
        return False
    if (
        claim.evidence_sha256 != evidence.sha256
        or claim.experiment_sha256 != experiment.sha256
        or claim.replication_sha256 != replication.sha256
    ):
        return False
    return approval is not None and approval.authorizes(claim.artifact())


def discover_local_upstreams(root: Path) -> tuple[UpstreamIntegration, ...]:
    """Report optional upstream checkouts without importing or executing them.

    Keeping this boundary explicit prevents credentials, lab controls and a
    large tool registry from becoming hidden dependencies of the routing core.
    """
    configurations = (
        (
            "Future-House Robin",
            "robin",
            "hypothesis ranking and assay-planning executor",
            "Requires its own Python 3.12+ and provider/Edison configuration.",
        ),
        (
            "ToolUniverse",
            "tooluniverse",
            "scientific tool-registry and MCP executor",
            "Requires its own environment and any selected tool credentials.",
        ),
    )
    return tuple(
        UpstreamIntegration(
            name=name,
            path=root / directory,
            available=(root / directory / "pyproject.toml").is_file(),
            capability=capability,
            activation_note=activation_note,
        )
        for name, directory, capability, activation_note in configurations
    )


def route_research(evidence: EvidenceSnapshot, hypothesis: HypothesisCard | None, gate: ResearchGate = ResearchGate(), *, replication_requested: bool = False) -> RoutingDecision:
    """Choose the next stage using fixed, inspectable gates."""
    if evidence.total_papers < gate.minimum_papers:
        return RoutingDecision("literature_retrieval", False, f"Only {evidence.total_papers} papers are available; collect at least {gate.minimum_papers} before routing a hypothesis.", evidence)
    if evidence.mechanism_evidence < gate.minimum_mechanism_evidence or evidence.strong_baselines < gate.minimum_strong_baselines:
        return RoutingDecision("evidence_gap_review", False, "Mechanism evidence or strong baselines are insufficient for a defensible experiment comparison.", evidence)
    if evidence.direct_precursors and (hypothesis is None or not hypothesis.novelty_response.strip()):
        return RoutingDecision("novelty_review", False, "Direct precursors exist; state the candidate's specific difference before hypothesis formalization.", evidence)
    if hypothesis is None or not hypothesis.is_complete():
        return RoutingDecision("hypothesis_formalization", False, "Supply a mechanism, executable direction, falsifiable prediction, falsifier and novelty response.", evidence)
    if replication_requested:
        return RoutingDecision("independent_replication", False, "A computational result exists; reproduce it independently before making a scientific claim.", evidence)
    return RoutingDecision("computational_experiment", True, "Evidence coverage and hypothesis completeness meet the fixed gate; run a logged computational experiment next.", evidence)
