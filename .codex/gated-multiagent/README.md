# Gated multi-agent adapter

This directory is a thin contract; the gate/routing kernel remains shared.

```powershell
python .codex/gated-multiagent/invoke.py validate
python .codex/gated-multiagent/invoke.py status
python .codex/gated-multiagent/invoke.py backfill --changed implementation
```

Before marking implementation complete, replace any code-executing stage with an adapter that calls the shared `Interpreter.run()` and add `may_execute_code`, `execution_adapter`, `codex-review`, and `container-execution` to that stage.
