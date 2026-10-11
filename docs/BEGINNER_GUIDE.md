# EDITH beginner guide (plain English)

**What EDITH does:** answers questions, runs safe PC actions, reminds you of things, shows Indian holidays and birthdays, and lets your phone see and control your PC.
**What it can't do:** reach a PC that is off/asleep/offline, unlock Windows for you, or run risky actions without asking.

1. **Install** Node.js (nodejs.org, LTS), PostgreSQL (postgresql.org — remember the password; create database `app_db`), Python (python.org — tick "Add to PATH").
2. **Start EDITH:** open the EDITH folder → right-click → *Open in Terminal* → run `copy .env.example .env`, edit `.env` in Notepad so `DATABASE_URL` has your Postgres password, then `npm install`, `npx drizzle-kit push`, `npm run build`, `npm run start -- -p 3000 -H 0.0.0.0`.
3. **Open** `http://localhost:3000` in Edge/Chrome. Choose a passphrase (8+ characters). The **Getting Started** panel opens — every step can be skipped.
4. **Profile:** in Getting Started fill state, city, timezone (`Asia/Kolkata`), RAM profile and quiet hours → *Save profile*.
5. **Link this PC:** left rail → *Devices & Remote* → *Link this PC* → copy the 6 digits → in a terminal run `host-agent\start_host_agent.bat --gateway http://127.0.0.1:3000 --code 123456`. The status pill changes to **PC LINKED**.
6. **Phone:** uninstall any old EDITH app, copy `dist\EDITH.apk` to the phone, allow "install unknown apps", install. On the HUD press *Generate pairing code*. In the app: *Settings* → URL `http://<your-PC-IP>:3000` (find it with `ipconfig`) → pairing code → *Connect to Host*.
7. **Try it:** type `remind me to drink water in 2 minutes`. After two minutes the HUD shows a toast and beeps, the phone shows an alert, Windows shows a notification.
8. **Remote control:** in the phone app tap *Remote*. You'll see your real screen; tap to click, use the keyboard button to type. A red "REMOTE SESSION ACTIVE" banner appears on the PC — press *Disconnect* there any time.
9. **Local AI (optional):** install Ollama (ollama.com) and run `ollama pull hermes3:3b` (about 2 GB). Pick it in the Command Center model selector.
10. **Away from home:** install Tailscale on both devices (same account) and use the PC's Tailscale address in the phone app.
11. **Safety:** red **E-STOP** stops everything; approvals for risky actions appear in *System Activity*; revoke a lost phone in *Devices & Remote*.
12. **Backup:** System Activity → *Export my data*; Today → *Export JSON*; Calendar → *Export .ics*.
