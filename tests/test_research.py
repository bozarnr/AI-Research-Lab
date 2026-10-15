import unittest
from pathlib import Path
import os

from ai_alpha_lab.demo import synthetic_panel
from ai_alpha_lab.expressions import FormulaContract, FormulaError, evaluate_formula
from ai_alpha_lab.loop import CandidateRecord, rejection_gallery, summarize_loop
from ai_alpha_lab.research import PromotionGate, evaluate_candidate
from ai_research_lab.router import (
    ArtifactApproval,
    EvidenceSnapshot,
    ExperimentPlan,
    HypothesisCard,
    HypothesisCandidate,
    ResearchArtifact,
    ResearchGate,
    ScientificClaim,
    can_release_claim,
    can_submit_experiment,
    discover_local_upstreams,
    pareto_hypotheses,
    route_research,
)
from ai_research_lab.execution import run_approved_code, shared_executor_ready
from ai_research_lab.repair_benchmark import run_pilot


class FormulaSafetyTests(unittest.TestCase):
    def setUp(self):
        self.panel = synthetic_panel()
        self.contract = FormulaContract(frozenset({"close", "amount", "returns"}))

    def test_formula_uses_past_data_only(self):
        output = evaluate_formula("rank(delta(amount, 3))", self.panel, self.contract)
        self.assertEqual(len(output), len(self.panel))
        self.assertTrue(output.isna().any())

    def test_future_field_is_rejected(self):
        with self.assertRaises(FormulaError):
            evaluate_formula("forward_return", self.panel, self.contract)

    def test_unsorted_panel_is_rejected(self):
        with self.assertRaises(FormulaError):
            evaluate_formula("rank(amount)", self.panel.sample(frac=1, random_state=1), self.contract)

    def test_demo_candidate_is_not_promoted(self):
        result = evaluate_candidate(
            "rank(delta(amount, 3)) - rank(mean(returns, 5))",
            self.panel,
            split_date="2024-03-15",
            gate=PromotionGate(min_oos_rank_ic=0.05, max_turnover=0.60),
        )
        self.assertFalse(result["promoted"])

    def test_costs_reduce_reported_net_return(self):
        result = evaluate_candidate(
            "rank(delta(amount, 3))",
            self.panel,
            split_date="2024-03-15",
            gate=PromotionGate(transaction_cost_bps=30),
        )
        self.assertLessEqual(result["oos_net_return"], result["oos_gross_return"])

    def test_rejection_gallery_sorts_best_rejected_candidates_first(self):
        records = [
            CandidateRecord("rank(amount)", 0.01, -0.001, 0.7, False, "too costly"),
            CandidateRecord("rank(close)", 0.03, -0.002, 0.8, False, "too costly"),
            CandidateRecord("rank(returns)", 0.06, 0.001, 0.4, True, "passed"),
        ]

        summary = summarize_loop(records)
        gallery = rejection_gallery(records, limit=1)

        self.assertEqual(summary.promoted_candidates, 1)
        self.assertEqual(summary.rejection_reasons, {"too costly": 2})
        self.assertEqual(gallery[0]["formula"], "rank(close)")


class ScientificRoutingTests(unittest.TestCase):
    def test_representation_repair_pilot_is_deterministic_and_reports_boundary(self):
        result = run_pilot()
        self.assertEqual(result["seeds"], [7, 19, 31])
        self.assertEqual(result["average"]["compressed"]["repair_accuracy"], 0.25)
        self.assertEqual(result["average"]["residual_diagnostic"]["under_revision_rate"], 0.0)
        self.assertIn("does not establish", result["interpretation_boundary"])

    def test_scientific_claim_requires_matching_independent_replication(self):
        evidence = ResearchArtifact.create("evidence", {"paper_ids": ["W1"]})
        experiment = ResearchArtifact.create("experiment", {"run": "a", "metric": 0.8})
        replication = ResearchArtifact.create("replication", {"run": "b", "metric": 0.79})
        claim = ScientificClaim(
            statement="The representation-aware alternative preserved the anomaly under two controlled runs.",
            evidence_sha256=evidence.sha256,
            experiment_sha256=experiment.sha256,
            replication_sha256=replication.sha256,
            limitations=("This is a computational result, not a physical-lab validation.",),
        )
        approval = ArtifactApproval(claim.artifact().sha256, "reviewer")
        self.assertTrue(can_release_claim(claim, approval, evidence=evidence, experiment=experiment, replication=replication))
        wrong_replication = ResearchArtifact.create("replication", {"run": "c", "metric": 0.1})
        self.assertFalse(can_release_claim(claim, approval, evidence=evidence, experiment=experiment, replication=wrong_replication))

    def test_shared_executor_is_detected_but_windows_execution_is_denied(self):
        self.assertTrue(shared_executor_ready())
        if os.name != "posix":
            with self.assertRaisesRegex(RuntimeError, "disabled on Windows"):
                run_approved_code("print('not executed')", workspace=Path.cwd(), audit_root=Path.cwd())

    def test_pareto_selection_discards_dominated_hypotheses(self):
        candidates = (
            HypothesisCandidate("balanced", 0.8, 0.6, 0.9, 3.0),
            HypothesisCandidate("dominated", 0.7, 0.5, 0.8, 4.0),
            HypothesisCandidate("high_novelty", 0.6, 0.95, 0.7, 2.0),
        )
        frontier = pareto_hypotheses(candidates)
        self.assertEqual([item.candidate_id for item in frontier], ["balanced", "high_novelty"])

    def test_experiment_approval_is_bound_to_exact_plan_and_inputs(self):
        hypothesis = ResearchArtifact.create("hypothesis", {"claim": "regime-aware models preserve anomalies"})
        evidence = ResearchArtifact.create("evidence", {"paper_ids": ["W1", "W2"], "query": "representation failure"})
        plan = ExperimentPlan(
            hypothesis_sha256=hypothesis.sha256,
            evidence_sha256=evidence.sha256,
            baselines=("pooled model", "noise-only control"),
            primary_metric="held-out residual-cluster stability",
            seeds=(7, 19, 31),
            expected_pattern="The regime-aware model reduces structured residuals without merely improving aggregate fit.",
            falsifier="Independent observations remove the residual cluster without the proposed representation.",
        )
        approval = ArtifactApproval(plan.artifact().sha256, "researcher")
        self.assertTrue(can_submit_experiment(plan, approval, hypothesis=hypothesis, evidence=evidence))

        changed_plan = ExperimentPlan(
            hypothesis_sha256=hypothesis.sha256,
            evidence_sha256=evidence.sha256,
            baselines=("pooled model",),
            primary_metric=plan.primary_metric,
            seeds=plan.seeds,
            expected_pattern=plan.expected_pattern,
            falsifier=plan.falsifier,
        )
        self.assertFalse(can_submit_experiment(changed_plan, approval, hypothesis=hypothesis, evidence=evidence))

    def test_repeated_random_seed_blocks_experiment_plan(self):
        plan = ExperimentPlan("h", "e", ("baseline",), "metric", (3, 3), "pattern", "falsifier")
        with self.assertRaises(ValueError):
            plan.artifact()

    def test_local_upstream_discovery_is_non_invasive(self):
        integrations = discover_local_upstreams(Path(__file__).parent)
        self.assertEqual([item.name for item in integrations], ["Future-House Robin", "ToolUniverse"])
        self.assertTrue(all(not item.available for item in integrations))

    def test_direct_precursor_requires_a_novelty_response(self):
        decision = route_research(
            EvidenceSnapshot(total_papers=12, direct_precursors=2, mechanism_evidence=4, strong_baselines=3),
            hypothesis=None,
            gate=ResearchGate(minimum_papers=8),
        )
        self.assertEqual(decision.stage, "novelty_review")
        self.assertFalse(decision.ready_for_experiment)

    def test_complete_hypothesis_can_enter_computational_experiment(self):
        hypothesis = HypothesisCard(
            mechanism="A coarse representation hides a latent regime that creates clustered residuals.",
            executable_direction="Compare a pooled model with a regime-aware probabilistic program.",
            predictions=("Residual clusters remain after controlling for measurement noise.",),
            falsifiers=("Residual structure disappears under an independently collected measurement.",),
            novelty_response="The candidate targets representation-failure detection rather than aggregate fit alone.",
        )
        decision = route_research(
            EvidenceSnapshot(total_papers=12, direct_precursors=1, mechanism_evidence=4, strong_baselines=3),
            hypothesis=hypothesis,
        )
        self.assertEqual(decision.stage, "computational_experiment")
        self.assertTrue(decision.ready_for_experiment)


if __name__ == "__main__":
    unittest.main()
