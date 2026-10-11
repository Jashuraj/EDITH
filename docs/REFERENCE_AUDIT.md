# Reference audit

**Honest status:** the 15 reference repositories were **not cloned or license-reviewed in this session** (the session prioritised P0 remote access, the broken phone app, security, reminders and packaging). No code from them was copied into the gateway, host agent or APK. Several were already adapted upstream by the EDITH author (see `desktop/THIRD_PARTY_NOTICES.md`); those adaptations remain in the original UI/runtime.

| Reference | Status in this release | Where it lives |
|---|---|---|
| Ultron (Three.js orb/HUD) | Pre-existing upstream adaptation kept unchanged | `public/orb.js` |
| Barehands (MediaPipe gestures) | Pre-existing upstream adaptation kept; optional, local | `public/gestures.js` |
| OpenJarvis / Mark-LV / E.V (Ryanditko, Ouru77) | Not reviewed this session; EDITH-native equivalents built for command routing, reminders, approvals | `src/server/assistant.ts` |
| hectorg2211/jarvis (double clap) | Pre-existing upstream `clap_detector.py` (desktop runtime only) | `desktop/edith/voice/` |
| OmniRoute | Supported as OpenAI-compatible "gateway" provider (no code copied) | `src/server/models.ts` |
| Jarvis Fable / VoiceStudio / Brahma-Echo | Not reviewed; voice remains browser Web Speech + upstream desktop voice | — |
| ECC (Executive Command Center) | Not reviewed; approvals/activity/audit implemented natively | System Activity dialog |
| God's Eye View | Not reviewed; no integration | — |
| addyosmani/agent-skills | Not reviewed this session; upstream `.agent/skills/*` kept in `desktop/` | `desktop/.agent/skills` |

**Next step:** clone each repo, record license and maintenance status here, then integrate only the components that pass review, behind EDITH's existing UI.
