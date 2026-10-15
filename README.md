# AI Research Lab

An auditable routing core for AI-assisted scientific research. The project treats a research idea as a sequence of evidence-gated decisions, not as a prompt that should automatically become an experiment or a paper.

## Current capability

`ai_research_lab` reads the existing OpenAlex/SQLite literature store without copying it, summarizes direct precursors and mechanism evidence, and routes work through explicit stages:

```text
literature retrieval → novelty review → hypothesis formalization
                     → computational experiment → independent replication
```

The router does **not** claim to discover new science by itself. It blocks a candidate from entering an experiment when evidence is too thin, a direct precursor has not been answered, or the hypothesis lacks a falsifiable prediction and a failure condition.

## Run locally

```powershell
python -m pip install -e .
python -m ai_research_lab.demo
python -m ai_research_lab.demo --literature-db "C:\path\to\ai-auto-science-literature\literature.db"
python -m unittest discover -s tests -v
```

The no-argument invocation is deterministic and needs no credential. The second invocation attaches the router to the existing literature database created by the project's OpenAlex collector.

## Research method

Each hypothesis is represented as a four-part **Hypothesis Card**:

1. a mechanism statement;
2. an executable-model direction;
3. one or more falsifiable predictions;
4. explicit observations that would count against the hypothesis.

Candidate promotion uses fixed gates rather than language-model self-evaluation alone: minimum evidence coverage, a required novelty response when direct precursors are present, an executable direction, and a falsifier. The next route is recorded with its rationale, so a rejected or deferred idea remains inspectable rather than disappearing from the workflow.

The first research application studies representation failure in AI-assisted science: whether abstraction can hide scientifically meaningful anomalies, and whether an AI system can recognize when its own representation is inadequate.

## Upstream integrations

This repository keeps its public core lightweight and does not vendor third-party source code.

- [Future-House Robin](https://github.com/Future-House/robin) — Apache-2.0. Its multi-agent hypothesis, ranking and assay-generation workflow informs the optional external-executor boundary. Robin requires Python 3.12+, an LLM provider configuration, and some functions require Edison platform access.
- [ToolUniverse](https://github.com/mims-harvard/ToolUniverse) — Apache-2.0. Its scientific-tool registry and MCP design informs the optional tool-adapter boundary for literature search, data retrieval and experimental design.
- [The AI Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) — cited as a research reference only. Its source license has additional distribution restrictions, so it is not vendored or made a dependency here.

The local core exposes `discover_local_upstreams(root)` to make these optional checkouts visible without importing or executing them. This is deliberately a discovery boundary: activating either upstream remains an explicit, separately configured step, so provider credentials and lab/tool side effects cannot be triggered by the routing loop.

## Evidence and disclosure boundary

The repository contains an earlier, finance-focused prototype under `src/ai_alpha_lab/`, plus its associated synthetic fixtures and rejection reports. They are retained as historical evidence for the promotion-gate pattern; they are not evidence for scientific-discovery results.

The current public claim is limited to an implemented, tested evidence-to-routing core and locally configured upstream source checkouts. It does not include private data, API keys, paid-platform access, physical-lab execution, or claims of a validated scientific discovery. See [DISCLOSURE.md](DISCLOSURE.md) and [research_state.json](research_state.json).

## Layout

```text
src/ai_research_lab/   current scientific-routing core
src/ai_alpha_lab/      retained legacy prototype
tests/                 regression tests for both cores
```
