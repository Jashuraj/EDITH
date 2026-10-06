# EDITH Mission Engine Specification

**Module:** `edith.tasks.mission`  

---

## Autonomous Goal Execution Loop

```text
User Goal: "Prepare this project for release"
  1. Inspect environment & inputs
  2. Synthesize multi-step plan
  3. Execute steps via TaskEngine
  4. Verify outcomes against success criteria
  5. Generate final MissionReport with verified artifacts (Section 190)
```

## Autonomy Levels

- **Level 1 (Assisted):** Prompts user before every step.
- **Level 2 (Supervised):** Auto-runs LOW and MEDIUM tools; blocks on HIGH and CRITICAL tools.
- **Level 3 (Autonomous):** Auto-runs non-destructive tools; only prompts on CRITICAL tools or when genuinely blocked.
