# EDITH Tool Registry & Action Packs

**Module:** `edith.tools.registry`  

---

## Active Action Packs

### WINDOWS_PACK
- `get_system_stats`: CPU, RAM, disk, battery metrics.
- `battery_status`: Current battery charge and AC power state.
- `launch_app`: Launch permitted Windows apps (`chrome`, `wt`, `code`, `notepad`).
- `close_app`: Terminate applications (HIGH risk).
- `screenshot`: Capture current display to PNG.
- `set_volume`: Adjust volume or mute audio.
- `lock_workstation`: Lock Windows workstation.

### FILES_PACK
- `read_file`: Jailed read access with offset/limit.
- `write_file`: Jailed write access with path traversal protection.
- `list_dir`: Jailed directory listing.
- `delete_file`: Jailed file deletion (HIGH risk).
