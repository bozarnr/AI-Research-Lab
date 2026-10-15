"""Evidence-gated routing primitives for AI-assisted scientific research."""

from .router import (
    EvidenceSnapshot,
    HypothesisCard,
    ResearchGate,
    RoutingDecision,
    UpstreamIntegration,
    discover_local_upstreams,
    route_research,
)

__all__ = [
    "EvidenceSnapshot",
    "HypothesisCard",
    "ResearchGate",
    "RoutingDecision",
    "UpstreamIntegration",
    "discover_local_upstreams",
    "route_research",
]
