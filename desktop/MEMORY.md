# EDITH Local Memory & SQLite Schema

**File:** `edith/data/edith_memory.db`  

---

## Tables

1. `preferences`: Key-value storage for user configurations and runtime flags.
2. `conversations`: Chronological log of user interactions and assistant responses.
3. `audit_log`: Immutable audit log recording every tool invocation, parameters, and status.
4. `task_checkpoints`: Serialized execution state for ongoing multi-step missions.
