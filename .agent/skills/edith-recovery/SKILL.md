---
name: edith-recovery
description: Failure recovery, error diagnosis, and state rollback mechanisms.
---

# EDITH Recovery

## Recovery Protocol
- Revert broken changes with `edith/core/undo.py`.
- Run health checks via `edith/core/doctor.py`.
- Preserve operational state across interruptions.
- Resume interrupted multi-step tasks without starting over.
