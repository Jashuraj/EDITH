# EDITH Mobile Gateway Protocol

**Port:** 8795  
**Module:** `edith.phone.gateway`  

---

## Endpoints

- `POST /pair`: Generates 48-char cryptographic token for mobile client.
- `POST /cmd`: Enqueues authenticated phone command for execution.
- `GET /status`: Returns live system telemetry and state.
- `POST /emergency_stop`: Remote kill-switch halting all computer actions.
