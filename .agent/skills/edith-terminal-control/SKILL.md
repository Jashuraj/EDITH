---
name: edith-terminal-control
description: Safe Windows shell and terminal execution via PowerShell and CMD.
---

# EDITH Terminal Control

## Shell Selection
- Default to PowerShell 7 on Windows.
- Fall back to Windows PowerShell if PowerShell 7 is unavailable.
- Use CMD for batch files or legacy scripts.
- Use WSL when target environments require native Linux binaries.

## Safety Standards
- Inspect commands before executing.
- Capture stdout, stderr, and exit codes.
- Timeout long-running commands deterministically.
