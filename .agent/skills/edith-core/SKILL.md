---
name: edith-core
description: Master operating invariants, event bus, and core lifecycle of EDITH.
---

# EDITH Core Architecture

## Operating Model
EDITH runs as a local-first autonomous AI operating system on Windows.

## Key Principles
- Local-first execution with offline autonomy.
- Asynchronous event bus via `edith/core/event_bus.py`.
- Strict state management via `edith/core/state_machine.py`.
- Health inspection and auto-repair via `edith/core/doctor.py`.
- Immutable audit logging via `edith/core/logger.py`.
