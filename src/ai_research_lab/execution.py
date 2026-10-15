"""Thin, fail-closed adapter to the shared isolated science executor.

This module deliberately does not offer a host-Python fallback. Approved code
is delegated to the shared AI-Scientist-v2 Interpreter, whose ``run`` method
performs Codex review and fixed-image, network-denied container execution.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


DEFAULT_SHARED_KERNEL = Path(
    r"C:\Users\Administrator\Documents\Codex\2026-09-21\w-zh\outputs\codex-science-workflow"
)


def shared_executor_ready(root: Path = DEFAULT_SHARED_KERNEL) -> bool:
    """Check whether the verified shared executor is present, without running it."""
    return all(
        path.is_file()
        for path in (
            root / "vendor" / "AI-Scientist-v2" / "container_executor.py",
            root / "vendor" / "AI-Scientist-v2" / "codex_gate.py",
            root / "vendor" / "AI-Scientist-v2" / "ai_scientist" / "treesearch" / "interpreter.py",
        )
    )


def run_approved_code(
    code: str,
    *,
    workspace: Path,
    audit_root: Path,
    timeout_seconds: int = 300,
    shared_kernel: Path = DEFAULT_SHARED_KERNEL,
):
    """Execute only through the shared gated container runtime.

    The shared interpreter itself refuses generated code that fails the Codex
    gate and passes accepted snippets only to the pinned, network-denied
    Docker runtime. Windows is intentionally preparation-only.
    """
    if os.name != "posix":
        raise RuntimeError("direct execution is disabled on Windows; use the isolated Ubuntu shared executor")
    if not shared_executor_ready(shared_kernel):
        raise FileNotFoundError("shared isolated executor is incomplete")
    if not workspace.is_dir() or not audit_root.is_dir():
        raise ValueError("workspace and audit_root must already exist")
    if not 1 <= timeout_seconds <= 300:
        raise ValueError("timeout_seconds must be between 1 and 300")

    integration = shared_kernel / "integration"
    vendor = shared_kernel / "vendor" / "AI-Scientist-v2"
    sys.path[:0] = [str(integration), str(vendor)]
    os.environ["SCIENCE_AUDIT_ROOT"] = str(audit_root.resolve())
    from ai_scientist.treesearch.interpreter import Interpreter

    return Interpreter(workspace, timeout=timeout_seconds).run(code)
