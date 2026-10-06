/* ==========================================================================
   EDITH MOBILE APPLICATION ENGINE - HIGH RELIABILITY CLIENT
   Spider-Man Insignia Edition | Dual-Mode WiFi & Internet Connectivity
   ========================================================================== */

(() => {
  "use strict";

  // ---------------- Configuration & State ----------------
  const STORAGE_KEYS = {
    LOCAL_URL: "edith_mobile_local_url",
    CLOUD_URL: "edith_mobile_cloud_url",
    MODE: "edith_mobile_mode",
    TOKEN: "edith_mobile_token",
    TTS_ENABLED: "edith_mobile_tts_enabled",
  };

  const defaultLocalUrl = window.location.origin.startsWith("http")
    ? window.location.origin
    : "http://192.168.1.167:8794";

  const state = {
    mode: localStorage.getItem(STORAGE_KEYS.MODE) || "auto", // auto, local, cloud
    localUrl: localStorage.getItem(STORAGE_KEYS.LOCAL_URL) || defaultLocalUrl,
    cloudUrl: localStorage.getItem(STORAGE_KEYS.CLOUD_URL) || "",
    token: localStorage.getItem(STORAGE_KEYS.TOKEN) || "",
    ttsEnabled: localStorage.getItem(STORAGE_KEYS.TTS_ENABLED) !== "false",
    activeEndpoint: "",
    activeType: "CONNECTING", // LOCAL, CLOUD, OFFLINE
    isOnline: false,
    latencyMs: null,
    isListening: false,
    isExecuting: false,
    audioWaveLevel: 0.1,
  };

  // ---------------- DOM References ----------------
  const dom = {
    canvasWeb: document.getElementById("web-canvas"),
    canvasOsc: document.getElementById("oscilloscope-canvas"),
    statusBadge: document.getElementById("btn-status-badge"),
    statusDot: document.getElementById("status-dot"),
    statusText: document.getElementById("status-text"),
    btnTts: document.getElementById("btn-toggle-tts"),
    ttsWave1: document.getElementById("tts-wave-1"),
    ttsWave2: document.getElementById("tts-wave-2"),
    btnOpenSettings: document.getElementById("btn-open-settings"),
    btnCloseSettings: document.getElementById("btn-close-settings"),
    modalSettings: document.getElementById("modal-settings"),
    cfgLocalUrl: document.getElementById("cfg-local-url"),
    cfgCloudUrl: document.getElementById("cfg-cloud-url"),
    cfgToken: document.getElementById("cfg-token"),
    btnSaveSettings: document.getElementById("btn-save-settings"),
    btnTestConn: document.getElementById("btn-test-conn"),
    btnStartTunnel: document.getElementById("btn-start-tunnel"),
    modeBtns: document.querySelectorAll(".mode-btn"),
    spiderCore: document.getElementById("spider-core-trigger"),
    cmdInput: document.getElementById("cmd-input"),
    btnSend: document.getElementById("btn-send"),
    btnMic: document.getElementById("btn-mic"),
    consoleChannel: document.getElementById("console-channel"),
    consolePing: document.getElementById("console-ping"),
    consoleOutput: document.getElementById("console-output"),
    chips: document.querySelectorAll(".chip-btn"),
  };

  // ---------------- Service Worker Setup ----------------
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("./sw.js").catch((err) => {
        console.warn("SW registration skipped:", err);
      });
    });
  }

  // ---------------- Speech Synthesis & Audio ----------------
  function speakResponse(text) {
    if (!state.ttsEnabled || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const clean = text.replace(/Action:\s*[\w_]+/gi, "").replace(/https?:\/\/\S+/g, "");
      if (!clean.trim()) return;

      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.rate = 1.05;
      utterance.pitch = 0.95;

      utterance.onstart = () => {
        state.audioWaveLevel = 0.85;
      };
      utterance.onend = () => {
        state.audioWaveLevel = 0.1;
      };
      utterance.onerror = () => {
        state.audioWaveLevel = 0.1;
      };

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("TTS error:", e);
    }
  }

  function updateTtsIcon() {
    if (state.ttsEnabled) {
      dom.ttsWave1.style.display = "block";
      dom.ttsWave2.style.display = "block";
      dom.btnTts.style.color = "var(--cyan-glow)";
    } else {
      dom.ttsWave1.style.display = "none";
      dom.ttsWave2.style.display = "none";
      dom.btnTts.style.color = "var(--text-muted)";
    }
  }

  // ---------------- Speech Recognition ----------------
  let recognition = null;
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      state.isListening = true;
      state.audioWaveLevel = 0.9;
      dom.btnMic.classList.add("listening");
      logConsole("LISTENING", "Microphone active. Speak your command...");
      triggerHaptic(30);
    };

    recognition.onresult = (event) => {
      let interim = "";
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          final += event.results[i][0].transcript;
        } else {
          interim += event.results[i][0].transcript;
        }
      }
      const liveText = final || interim;
      if (liveText) {
        dom.cmdInput.value = liveText;
        logConsole("VOICE DETECTED", `"${liveText}"`);
      }
      if (final) {
        executeCommand(final.trim());
      }
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      state.isListening = false;
      state.audioWaveLevel = 0.1;
      dom.btnMic.classList.remove("listening");
      if (event.error !== "no-speech") {
        logConsole("VOICE STATUS", `Speech recognition: ${event.error}`);
      }
    };

    recognition.onend = () => {
      state.isListening = false;
      state.audioWaveLevel = 0.1;
      dom.btnMic.classList.remove("listening");
    };
  }

  function toggleSpeech() {
    if (!recognition) {
      alert("Web Speech API is not supported on this browser. You can type commands directly.");
      return;
    }
    if (state.isListening) {
      recognition.stop();
    } else {
      try {
        recognition.start();
      } catch (err) {
        console.warn("Could not start recognition:", err);
      }
    }
  }

  function triggerHaptic(duration = 20) {
    if ("vibrate" in navigator) {
      try {
        navigator.vibrate(duration);
      } catch (_) {}
    }
  }

  // ---------------- Connection Manager ----------------
  async function pingEndpoint(url, timeoutMs = 2000) {
    if (!url) return { ok: false, ms: 0 };
    const cleanUrl = url.replace(/\/+$/, "");
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const t0 = performance.now();

    try {
      const resp = await fetch(`${cleanUrl}/ping`, {
        method: "GET",
        signal: controller.signal,
        headers: { "Accept": "application/json" },
      });
      clearTimeout(timer);
      const dt = Math.round(performance.now() - t0);
      return { ok: resp.ok, ms: dt };
    } catch (_) {
      clearTimeout(timer);
      return { ok: false, ms: 0 };
    }
  }

  async function resolveActiveEndpoint() {
    const local = state.localUrl.trim().replace(/\/+$/, "");
    const cloud = state.cloudUrl.trim().replace(/\/+$/, "");

    if (state.mode === "local") {
      const res = await pingEndpoint(local, 2500);
      if (res.ok) {
        setConnectionState("LOCAL", local, res.ms);
        return;
      }
      setConnectionState("OFFLINE", local, null);
      return;
    }

    if (state.mode === "cloud") {
      if (!cloud) {
        setConnectionState("OFFLINE", "", null, "Cloud URL not configured");
        return;
      }
      const res = await pingEndpoint(cloud, 4000);
      if (res.ok) {
        setConnectionState("CLOUD", cloud, res.ms);
        return;
      }
      setConnectionState("OFFLINE", cloud, null);
      return;
    }

    // AUTO Mode: Priority to Local WiFi, fallback to Cloud Tunnel
    const localPing = await pingEndpoint(local, 1800);
    if (localPing.ok) {
      setConnectionState("LOCAL", local, localPing.ms);
      return;
    }

    if (cloud) {
      const cloudPing = await pingEndpoint(cloud, 3500);
      if (cloudPing.ok) {
        setConnectionState("CLOUD", cloud, cloudPing.ms);
        return;
      }
    }

    setConnectionState("OFFLINE", local, null);
  }

  function setConnectionState(type, endpoint, latency, msg) {
    state.activeType = type;
    state.activeEndpoint = endpoint;
    state.latencyMs = latency;
    state.isOnline = type !== "OFFLINE";

    if (type === "LOCAL") {
      dom.statusDot.style.background = "#00e676";
      dom.statusDot.style.boxShadow = "0 0 8px #00e676";
      dom.statusText.textContent = `WI-FI (${latency}ms)`;
      dom.consoleChannel.textContent = `CHANNEL: LOCAL WI-FI`;
      dom.consolePing.textContent = `LATENCY: ${latency}ms`;
    } else if (type === "CLOUD") {
      dom.statusDot.style.background = "#00e5ff";
      dom.statusDot.style.boxShadow = "0 0 8px #00e5ff";
      dom.statusText.textContent = `CLOUD (${latency}ms)`;
      dom.consoleChannel.textContent = `CHANNEL: CLOUD INTERNET`;
      dom.consolePing.textContent = `LATENCY: ${latency}ms`;
    } else {
      dom.statusDot.style.background = "#ff1744";
      dom.statusDot.style.boxShadow = "0 0 8px #ff1744";
      dom.statusText.textContent = "OFFLINE";
      dom.consoleChannel.textContent = `CHANNEL: DISCONNECTED`;
      dom.consolePing.textContent = `LATENCY: --ms`;
      if (msg) {
        logConsole("ALERT", msg);
      }
    }
  }

  // ---------------- Command Execution ----------------
  async function executeCommand(commandStr) {
    const cmd = (commandStr || "").trim();
    if (!cmd) {
      logConsole("VALIDATION", "Empty instruction rejected.");
      return;
    }

    if (state.isExecuting) {
      logConsole("BUSY", "Another action is currently executing.");
      return;
    }

    triggerHaptic(20);
    state.isExecuting = true;
    state.audioWaveLevel = 0.6;
    dom.btnSend.disabled = true;
    logConsole("EXECUTING", `Dispatching: "${cmd}"...`);

    // Verify or ensure active endpoint
    if (!state.activeEndpoint || !state.isOnline) {
      await resolveActiveEndpoint();
    }

    if (!state.activeEndpoint) {
      logConsole("ERROR", "No active server link. Check WiFi or Cloud Tunnel URL.");
      state.isExecuting = false;
      state.audioWaveLevel = 0.1;
      dom.btnSend.disabled = false;
      return;
    }

    const payload = {
      command: cmd,
      device_id: "edith_mobile_pwa",
      token: state.token || undefined,
    };

    const targetUrl = `${state.activeEndpoint.replace(/\/+$/, "")}/cmd`;

    try {
      const resp = await fetch(targetUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await resp.json();
      state.isExecuting = false;
      dom.btnSend.disabled = false;
      state.audioWaveLevel = 0.2;

      if (!resp.ok && data.error) {
        logConsole("ERROR", `Server reported: ${data.error}`);
        return;
      }

      const outcome = data.result || (data.matched ? "Action completed" : "Acknowledged");
      logConsole(data.model || "EDITH", outcome);

      // Handle speech response
      speakResponse(outcome);

      // Handle URL navigation (e.g., YouTube search match)
      if (data.url && typeof data.url === "string") {
        setTimeout(() => {
          window.open(data.url, "_blank");
        }, 600);
      }

      dom.cmdInput.value = "";
    } catch (err) {
      console.error("Command dispatch error:", err);
      state.isExecuting = false;
      dom.btnSend.disabled = false;
      state.audioWaveLevel = 0.1;
      logConsole("NETWORK ERROR", `Connection failed: ${err.message}. Retrying link...`);
      resolveActiveEndpoint();
    }
  }

  function logConsole(channel, text) {
    dom.consoleChannel.textContent = `CHANNEL: ${channel}`;
    dom.consoleOutput.textContent = text;
  }

  // ---------------- Canvas Visualizers ----------------
  // 1. Spider-Web Radar Background Canvas
  function initWebCanvas() {
    const canvas = dom.canvasWeb;
    const ctx = canvas.getContext("2d");
    let w = 0, h = 0;

    function resize() {
      w = canvas.width = window.innerWidth;
      h = canvas.height = window.innerHeight;
    }
    window.addEventListener("resize", resize);
    resize();

    let scanAngle = 0;

    function draw() {
      ctx.clearRect(0, 0, w, h);

      const cx = w / 2;
      const cy = h * 0.28; // Web anchor point matching design
      const maxR = Math.max(w, h) * 0.95;

      // Spider Web Spokes
      const spokes = 16;
      ctx.strokeStyle = "rgba(0, 229, 255, 0.12)";
      ctx.lineWidth = 1;
      for (let i = 0; i < spokes; i++) {
        const rad = (i * 2 * Math.PI) / spokes;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(rad) * maxR, cy + Math.sin(rad) * maxR);
        ctx.stroke();
      }

      // Concentric Web Rings
      const rings = 9;
      ctx.strokeStyle = "rgba(0, 229, 255, 0.15)";
      for (let r = 1; r <= rings; r++) {
        const radius = (maxR / rings) * r;
        ctx.beginPath();
        for (let i = 0; i <= spokes; i++) {
          const rad = (i * 2 * Math.PI) / spokes;
          const x = cx + Math.cos(rad) * radius;
          const y = cy + Math.sin(rad) * radius;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      // Subtle Crimson Cross Rings
      ctx.strokeStyle = "rgba(255, 23, 68, 0.18)";
      ctx.beginPath();
      ctx.arc(cx, cy, 90, 0, Math.PI * 2);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(cx, cy, 180, 0, Math.PI * 2);
      ctx.stroke();

      // Animated Radar Scan Beam
      scanAngle += 0.015;
      ctx.strokeStyle = "rgba(0, 229, 255, 0.35)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(scanAngle) * maxR * 0.5, cy + Math.sin(scanAngle) * maxR * 0.5);
      ctx.stroke();

      requestAnimationFrame(draw);
    }
    draw();
  }

  // 2. Center Reticle Oscilloscope Waveform Canvas
  function initOscilloscopeCanvas() {
    const canvas = dom.canvasOsc;
    const ctx = canvas.getContext("2d");
    const w = (canvas.width = 220);
    const h = (canvas.height = 50);
    let phase = 0;

    function renderWave() {
      ctx.clearRect(0, 0, w, h);

      phase += 0.09;
      const amp = state.audioWaveLevel * 18 + 2;
      const midY = h / 2;

      ctx.beginPath();
      ctx.strokeStyle = state.isListening
        ? "#00e5ff"
        : state.isExecuting
        ? "#ff1744"
        : "rgba(0, 229, 255, 0.85)";
      ctx.lineWidth = 2.2;
      ctx.shadowColor = ctx.strokeStyle;
      ctx.shadowBlur = 8;

      for (let x = 0; x < w; x++) {
        // Taper wave towards edges
        const envelope = Math.sin((x / w) * Math.PI);
        const y = midY + Math.sin(x * 0.12 + phase) * amp * envelope;
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Reset shadow for performance
      ctx.shadowBlur = 0;

      requestAnimationFrame(renderWave);
    }
    renderWave();
  }

  // ---------------- Settings & UI Event Listeners ----------------
  function initEvents() {
    // Input Submissions
    dom.btnSend.addEventListener("click", () => {
      executeCommand(dom.cmdInput.value);
    });

    dom.cmdInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        executeCommand(dom.cmdInput.value);
      }
    });

    // Voice Mic Toggles
    dom.btnMic.addEventListener("click", toggleSpeech);
    dom.spiderCore.addEventListener("click", toggleSpeech);

    // Quick Action Chips
    dom.chips.forEach((chip) => {
      chip.addEventListener("click", () => {
        const cmd = chip.getAttribute("data-cmd");
        if (cmd) executeCommand(cmd);
      });
    });

    // TTS Toggle
    dom.btnTts.addEventListener("click", () => {
      state.ttsEnabled = !state.ttsEnabled;
      localStorage.setItem(STORAGE_KEYS.TTS_ENABLED, state.ttsEnabled.toString());
      updateTtsIcon();
      triggerHaptic(15);
    });

    // Settings Modal Open/Close
    dom.statusBadge.addEventListener("click", openSettings);
    dom.btnOpenSettings.addEventListener("click", openSettings);
    dom.btnCloseSettings.addEventListener("click", closeSettings);

    dom.modalSettings.addEventListener("click", (e) => {
      if (e.target === dom.modalSettings) closeSettings();
    });

    // Mode Selector Buttons
    dom.modeBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        dom.modeBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.mode = btn.getAttribute("data-mode");
      });
    });

    // Save Settings
    dom.btnSaveSettings.addEventListener("click", async () => {
      state.localUrl = dom.cfgLocalUrl.value.trim() || defaultLocalUrl;
      state.cloudUrl = dom.cfgCloudUrl.value.trim();
      state.token = dom.cfgToken.value.trim();

      localStorage.setItem(STORAGE_KEYS.LOCAL_URL, state.localUrl);
      localStorage.setItem(STORAGE_KEYS.CLOUD_URL, state.cloudUrl);
      localStorage.setItem(STORAGE_KEYS.MODE, state.mode);
      localStorage.setItem(STORAGE_KEYS.TOKEN, state.token);

      closeSettings();
      logConsole("CONFIG", "Settings applied. Testing connection...");
      await resolveActiveEndpoint();
    });

    // Test Connection
    dom.btnTestConn.addEventListener("click", async () => {
      dom.btnTestConn.textContent = "Testing...";
      dom.btnTestConn.disabled = true;
      const tUrl = state.mode === "cloud" && dom.cfgCloudUrl.value.trim()
        ? dom.cfgCloudUrl.value.trim()
        : dom.cfgLocalUrl.value.trim() || defaultLocalUrl;

      const res = await pingEndpoint(tUrl, 3000);
      dom.btnTestConn.disabled = false;
      dom.btnTestConn.textContent = "Test Link";

      if (res.ok) {
        alert(`Connection successful! Ping: ${res.ms}ms`);
      } else {
        alert(`Connection failed to: ${tUrl}. Make sure EDITH is running.`);
      }
    });

    // Launch Cloud Tunnel Trigger
    dom.btnStartTunnel.addEventListener("click", async () => {
      dom.btnStartTunnel.textContent = "⚡ Initializing Tunnel...";
      dom.btnStartTunnel.disabled = true;

      try {
        const local = (dom.cfgLocalUrl.value.trim() || defaultLocalUrl).replace(/\/+$/, "");
        const resp = await fetch(`${local}/api/tunnel`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "start", provider: "pinggy" }),
        });
        const data = await resp.json();
        dom.btnStartTunnel.disabled = false;
        dom.btnStartTunnel.textContent = "⚡ Launch Cloud Tunnel on Laptop";

        if (data.tunnel_url) {
          dom.cfgCloudUrl.value = data.tunnel_url;
          alert(`Cloud tunnel online:\n${data.tunnel_url}\n\nAuto-populated in settings.`);
        } else {
          alert("Could not start tunnel automatically. You can enter your custom cloud URL.");
        }
      } catch (err) {
        dom.btnStartTunnel.disabled = false;
        dom.btnStartTunnel.textContent = "⚡ Launch Cloud Tunnel on Laptop";
        alert(`Tunnel launch failed: ${err.message}. Please test while on local WiFi.`);
      }
    });
  }

  function openSettings() {
    dom.cfgLocalUrl.value = state.localUrl;
    dom.cfgCloudUrl.value = state.cloudUrl;
    dom.cfgToken.value = state.token;

    dom.modeBtns.forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-mode") === state.mode);
    });

    dom.modalSettings.classList.add("open");
  }

  function closeSettings() {
    dom.modalSettings.classList.remove("open");
  }

  // Auto-fetch server config if loaded from server
  async function fetchServerConfig() {
    try {
      const resp = await fetch(`${defaultLocalUrl}/mobile/config`);
      if (resp.ok) {
        const cfg = await resp.json();
        if (cfg.cloud_url && !state.cloudUrl) {
          state.cloudUrl = cfg.cloud_url;
          localStorage.setItem(STORAGE_KEYS.CLOUD_URL, state.cloudUrl);
        }
        if (cfg.local_ip && (!state.localUrl || state.localUrl.includes("127.0.0.1"))) {
          state.localUrl = `http://${cfg.local_ip}:${cfg.ui_port || 8794}`;
          localStorage.setItem(STORAGE_KEYS.LOCAL_URL, state.localUrl);
        }
      }
    } catch (_) {}
  }

  // ---------------- Bootstrap ----------------
  async function init() {
    initWebCanvas();
    initOscilloscopeCanvas();
    initEvents();
    updateTtsIcon();

    await fetchServerConfig();
    await resolveActiveEndpoint();

    // Heartbeat connection maintenance every 5 seconds
    setInterval(resolveActiveEndpoint, 5000);
  }

  window.addEventListener("DOMContentLoaded", init);
})();
