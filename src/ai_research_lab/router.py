"""Small, local and auditable research routing core.

The module intentionally has no LLM, API-key or physical-lab dependency. It
consumes reviewed evidence counts and a structured hypothesis card, then
returns the next defensible research action. External systems such as Robin and
ToolUniverse remain optional executors behind this boundary.
"""

from __future__ import annotations

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
