"""Thin entry point into the shared gated multi-agent kernel."""
import os
import sys
from pathlib import Path

core = Path(os.environ.get("GATED_MULTIAGENT_CORE", r"C:\Users\Administrator\Documents\Codex\2026-09-21\w-zh\outputs\codex-science-workflow"))
sys.path.insert(0, str(core / "integration"))
from system_factory import project_main

if __name__ == "__main__":
    project_main(Path(__file__).with_name("workflow.contract.json"))
