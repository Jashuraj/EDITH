# EDITH Task Engine Architecture

**Module:** `edith.tasks.engine`  

---

## Capabilities

1. **State Persistence:** Every task step automatically checkpoints to local SQLite (`edith_memory.db`).
2. **Crash & Restart Recovery:** Interrupted tasks rehydrate from the database and resume from the exact pending step.
3. **Step Context Injection:** Steps dynamically reference previous step outputs via `$context.<var_name>`.
4. **Security Integration:** Step tools execute through `SecurityGate` with risk level authorization.
