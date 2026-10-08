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

  const DEFAULT_CLOUD_URL = "https://edith-jashu.loca.lt";
  const isCloudOrigin = window.location.origin.includes("loca.lt") ||
    window.location.origin.includes("trycloudflare.com") ||
    window.location.origin.includes("pinggy");

  const defaultLocalUrl = window.location.origin.startsWith("http") && !isCloudOrigin
    ? window.location.origin
    : "http://192.168.1.167:8794";

  let savedCloud = localStorage.getItem(STORAGE_KEYS.CLOUD_URL) || DEFAULT_CLOUD_URL;
  if (!savedCloud || savedCloud.includes("edith-core-jashu.loca.lt")) {
    savedCloud = DEFAULT_CLOUD_URL;
  }
  if (!savedCloud && isCloudOrigin) {
    savedCloud = window.location.origin;
  }

  const state = {
    mode: localStorage.getItem(STORAGE_KEYS.MODE) || "auto", // auto, local, cloud
    localUrl: localStorage.getItem(STORAGE_KEYS.LOCAL_URL) || defaultLocalUrl,
    cloudUrl: savedCloud,
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
    btnModeToggle: document.getElementById("btn-mode-toggle"),
    hudMediaDock: document.getElementById("hud-media-dock"),
    hudMediaFrame: document.getElementById("hud-media-iframe"),
    hudMediaTitle: document.getElementById("hud-media-title"),
    btnMediaPopout: document.getElementById("btn-media-popout"),
    btnMediaMin: document.getElementById("btn-media-min"),
    btnMediaClose: document.getElementById("btn-media-close"),
    consoleChannel: document.getElementById("console-channel"),
    consolePing: document.getElementById("console-ping"),
    consoleOutput: document.getElementById("console-output"),
    chips: document.querySelectorAll(".chip-btn"),

    // Remote Desktop & Gamepad HUD References
    btnOpenRemote: document.getElementById("btn-open-remote"),
    btnOpenGamepad: document.getElementById("btn-open-gamepad"),
    btnSyncClipboard: document.getElementById("btn-sync-clipboard"),
    remoteOverlay: document.getElementById("remote-desktop-overlay"),
    remoteScreenImg: document.getElementById("remote-screen-img"),
    remoteViewport: document.getElementById("remote-viewport"),
    remoteCursor: document.getElementById("remote-virtual-cursor"),
    remoteFeedback: document.getElementById("remote-touch-feedback"),
    btnCloseRemote: document.getElementById("btn-close-remote"),
    btnToggleGamepad: document.getElementById("btn-toggle-gamepad"),
    btnOpenKb: document.getElementById("btn-open-kb"),
    btnRemoteClip: document.getElementById("btn-remote-clip"),
    btnRemoteRefresh: document.getElementById("btn-remote-refresh"),
    btnRemoteRes: document.getElementById("btn-remote-res"),
    remoteFpsTag: document.getElementById("remote-fps-tag"),
    remoteTitleText: document.getElementById("remote-title-text"),
    gamepadOverlay: document.getElementById("virtual-gamepad-overlay"),
    stickBase: document.getElementById("gamepad-stick-base"),
    stickNub: document.getElementById("gamepad-stick-nub"),
    modalKb: document.getElementById("modal-remote-keyboard"),
    kbTextInput: document.getElementById("kb-text-input"),
    btnKbSendText: document.getElementById("btn-kb-send-text"),
    btnKbEnter: document.getElementById("btn-kb-enter"),
    btnCloseKb: document.getElementById("btn-close-kb"),
    remoteBottomBar: document.getElementById("remote-bottom-bar"),
    vncCanvas: document.getElementById("vnc-canvas"),
    gameLookTrackpad: document.getElementById("game-look-trackpad"),
    quickHostBar: document.getElementById("quick-host-bar"),
    quickHostInput: document.getElementById("quick-host-input"),
    btnQuickConnect: document.getElementById("btn-quick-connect"),
    btnQuickScan: document.getElementById("btn-quick-scan"),
    btnOpenVnc: document.getElementById("btn-open-vnc"),
  };

  // ---------------- Service Worker Setup ----------------
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("./sw.js").catch((err) => {
        console.warn("SW registration skipped:", err);
      });
    });
  }

  let mobileSpeechTimer = null;
  window._mobileUtterance = null;

  // ---------------- Speech Synthesis & Audio ----------------
  function speakResponse(text) {
    if (!state.ttsEnabled || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      clearTimeout(mobileSpeechTimer);
      const clean = text.replace(/Action:\s*[\w_]+/gi, "").replace(/https?:\/\/\S+/g, "");
      if (!clean.trim()) return;

      const utterance = new SpeechSynthesisUtterance(clean);
      window._mobileUtterance = utterance;
      utterance.rate = 1.05;
      utterance.pitch = 0.95;

      utterance.onstart = () => {
        state.audioWaveLevel = 0.85;
      };
      utterance.onend = () => {
        clearTimeout(mobileSpeechTimer);
        state.audioWaveLevel = 0.1;
        window._mobileUtterance = null;
      };
      utterance.onerror = () => {
        clearTimeout(mobileSpeechTimer);
        state.audioWaveLevel = 0.1;
        window._mobileUtterance = null;
      };

      const maxMs = Math.min(10000, Math.max(2500, clean.length * 75 + 1000));
      mobileSpeechTimer = setTimeout(() => {
        state.audioWaveLevel = 0.1;
        window._mobileUtterance = null;
      }, maxMs);

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("TTS error:", e);
      state.audioWaveLevel = 0.1;
      window._mobileUtterance = null;
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
      const resp = await fetch(`${cleanUrl}/ping?bypass-tunnel-reminder=true`, {
        method: "GET",
        signal: controller.signal,
        headers: {
          "Accept": "application/json",
          "Bypass-Tunnel-Reminder": "true",
        },
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
      const res = await pingEndpoint(cloud, 3000);
      if (res.ok) {
        setConnectionState("CLOUD", cloud, res.ms);
        return;
      }
      setConnectionState("OFFLINE", cloud, null);
      return;
    }

    // AUTO Mode: Concurrent probe of local WiFi and global cloud
    const [localRes, cloudRes] = await Promise.all([
      local ? pingEndpoint(local, 1800) : Promise.resolve({ ok: false, ms: 0 }),
      cloud ? pingEndpoint(cloud, 2800) : Promise.resolve({ ok: false, ms: 0 }),
    ]);

    if (localRes.ok) {
      setConnectionState("LOCAL", local, localRes.ms);
      return;
    }

    if (cloudRes.ok) {
      setConnectionState("CLOUD", cloud, cloudRes.ms);
      return;
    }

    setConnectionState("OFFLINE", local || cloud, null, "Searching for EDITH mainframe...");
  }

  let previousType = "INITIAL";

  function setConnectionState(type, endpoint, latency, msg) {
    const wasOffline = !state.isOnline;
    state.activeType = type;
    state.activeEndpoint = endpoint;
    state.latencyMs = latency;
    state.isOnline = type !== "OFFLINE";

    if (type === "LOCAL") {
      dom.statusDot.style.background = "#00e676";
      dom.statusDot.style.boxShadow = "0 0 10px #00e676";
      dom.statusText.textContent = `WI-FI (${latency}ms)`;
      dom.consoleChannel.textContent = `CHANNEL: LOCAL WI-FI`;
      dom.consolePing.textContent = `LATENCY: ${latency}ms`;
      if (wasOffline || previousType !== "LOCAL") {
        logConsole("LINK ACCEPTED", `Connected to laptop via Local Wi-Fi (${latency}ms). Ready.`);
        speakResponse("EDITH system linked on local Wi-Fi, Creator.");
        triggerHaptic(40);
      }
    } else if (type === "CLOUD") {
      dom.statusDot.style.background = "#00e5ff";
      dom.statusDot.style.boxShadow = "0 0 10px #00e5ff";
      dom.statusText.textContent = `CLOUD (${latency}ms)`;
      dom.consoleChannel.textContent = `CHANNEL: GLOBAL INTERNET`;
      dom.consolePing.textContent = `LATENCY: ${latency}ms`;
      if (wasOffline || previousType !== "CLOUD") {
        logConsole("LINK ACCEPTED", `Connected to laptop via Global Cloud Tunnel (${latency}ms). Ready.`);
        speakResponse("EDITH mainframe online via satellite cloud link.");
        triggerHaptic(40);
      }
    } else {
      dom.statusDot.style.background = "#ff1744";
      dom.statusDot.style.boxShadow = "0 0 8px #ff1744";
      dom.statusText.textContent = "SEARCHING...";
      dom.consoleChannel.textContent = `CHANNEL: SCANNING`;
      dom.consolePing.textContent = `LATENCY: --ms`;
      if (msg && previousType !== "OFFLINE") {
        logConsole("STANDBY", "Searching for EDITH on laptop. Launch EDITH.exe to connect.");
      }
    }
    previousType = type;
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
        headers: {
          "Content-Type": "application/json",
          "Bypass-Tunnel-Reminder": "true",
        },
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

      // Handle media playback or external navigation without duplicate tabs
      if (data.embed_url) {
        playInHudMedia(data.embed_url, outcome || "YouTube Media", data.url);
      } else if (data.url && typeof data.url === "string" && !data.opened_on_host) {
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

  // ---------------- In-HUD Media Player ----------------
  let activeMediaUrl = "";
  function playInHudMedia(embedUrl, title, fullUrl) {
    if (!dom.hudMediaDock || !dom.hudMediaFrame) return;
    activeMediaUrl = fullUrl || embedUrl;
    dom.hudMediaFrame.src = embedUrl;
    if (dom.hudMediaTitle) {
      dom.hudMediaTitle.textContent = `▶ ${(title || "MEDIA").slice(0, 24)}`;
    }
    dom.hudMediaDock.style.display = "flex";
    dom.hudMediaDock.classList.remove("minimized");
  }

  function closeHudMedia() {
    if (dom.hudMediaDock) dom.hudMediaDock.style.display = "none";
    if (dom.hudMediaFrame) dom.hudMediaFrame.src = "";
  }

  function toggleMinimizeMedia() {
    if (dom.hudMediaDock) dom.hudMediaDock.classList.toggle("minimized");
  }

  function popoutMedia() {
    if (activeMediaUrl) {
      window.open(activeMediaUrl, "_blank");
      closeHudMedia();
    }
  }

  // ---------------- System Mode Switcher ----------------
  let currentSystemMode = "auto";
  function updateSystemModeUI(mode) {
    currentSystemMode = mode || "auto";
    if (dom.btnModeToggle) {
      dom.btnModeToggle.textContent = currentSystemMode.toUpperCase();
      dom.btnModeToggle.className = `btn-mode-toggle mode-${currentSystemMode}`;
    }
  }

  async function toggleSystemMode() {
    const modes = ["auto", "online", "offline"];
    const nextIdx = (modes.indexOf(currentSystemMode) + 1) % modes.length;
    const targetMode = modes[nextIdx];
    const ep = state.activeEndpoint || window.location.origin;
    try {
      const res = await fetch(`${ep.replace(/\/+$/, "")}/api/mode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: targetMode }),
      });
      if (res.ok) {
        const data = await res.json();
        updateSystemModeUI(data.manual_mode || targetMode);
        logConsole("SYSTEM MODE", `Mode changed: ${(data.manual_mode || targetMode).toUpperCase()}`);
      }
    } catch (e) {
      console.warn("Mode toggle failed:", e);
    }
  }

  async function syncSystemMode() {
    const ep = state.activeEndpoint || window.location.origin;
    try {
      const res = await fetch(`${ep.replace(/\/+$/, "")}/api/mode`);
      if (res.ok) {
        const data = await res.json();
        updateSystemModeUI(data.manual_mode);
      }
    } catch (_) {}
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

  // ==========================================================================
  // REMOTE DESKTOP & VIRTUAL GAMEPAD ENGINE (RAT CLIENT)
  // ==========================================================================

  let remoteStreamActive = false;
  let remoteGamepadMode = false;
  let remoteStreamRetryTimer = null;
  let lastJoystickDispatch = 0;
  let joystickActive = false;
  let remoteResolution = localStorage.getItem("edith_remote_res") || "720p";
  let currentBlobUrl = null;
  let isFetchingFrame = false;
  let frameCount = 0;
  let lastFpsCalcTime = performance.now();
  let currentFps = 0;

  function updateResolutionButtonUI() {
    if (dom.btnRemoteRes) {
      dom.btnRemoteRes.textContent = remoteResolution === "1080p" ? "📺 1080p FHD" : "📺 720p HD";
    }
  }

  function toggleResolution() {
    remoteResolution = remoteResolution === "720p" ? "1080p" : "720p";
    localStorage.setItem("edith_remote_res", remoteResolution);
    updateResolutionButtonUI();
    triggerHaptic(20);
    if (dom.remoteFpsTag) {
      dom.remoteFpsTag.textContent = `SWITCHING TO ${remoteResolution.toUpperCase()}...`;
      dom.remoteFpsTag.style.color = "#00e5ff";
    }
  }

  let vncCtx = null;

  async function fetchStreamLoop() {
    if (!remoteStreamActive || (!dom.remoteScreenImg && !dom.vncCanvas)) return;
    if (isFetchingFrame) return;
    isFetchingFrame = true;

    const ep = (state.activeEndpoint || defaultLocalUrl).replace(/\/+$/, "");
    const scale = remoteResolution === "1080p" ? 1920 : 1280;
    const quality = remoteResolution === "1080p" ? 80 : 75;
    const streamUrl = `${ep}/api/screen/capture?scale=${scale}&quality=${quality}&token=${encodeURIComponent(state.token)}&t=${Date.now()}`;

    try {
      const resp = await fetch(streamUrl, {
        method: "GET",
        headers: {
          "Bypass-Tunnel-Reminder": "true",
          "X-Token": state.token || "",
        },
        cache: "no-store",
      });

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }

      const blob = await resp.blob();
      if (!remoteStreamActive) {
        isFetchingFrame = false;
        return;
      }

      // Fast GPU path via createImageBitmap & HTML5 Canvas
      if (window.createImageBitmap && dom.vncCanvas) {
        try {
          const bitmap = await createImageBitmap(blob);
          if (!remoteStreamActive) {
            bitmap.close();
            isFetchingFrame = false;
            return;
          }
          if (dom.vncCanvas.width !== bitmap.width || dom.vncCanvas.height !== bitmap.height) {
            dom.vncCanvas.width = bitmap.width;
            dom.vncCanvas.height = bitmap.height;
          }
          if (!vncCtx) {
            vncCtx = dom.vncCanvas.getContext("2d", { alpha: false, desynchronized: true });
          }
          vncCtx.drawImage(bitmap, 0, 0);
          bitmap.close();

          frameCount++;
          const now = performance.now();
          if (now - lastFpsCalcTime >= 1000) {
            currentFps = Math.round((frameCount * 1000) / (now - lastFpsCalcTime));
            frameCount = 0;
            lastFpsCalcTime = now;
            if (dom.remoteFpsTag) {
              dom.remoteFpsTag.textContent = `${currentFps} FPS // ${remoteResolution.toUpperCase()}`;
              dom.remoteFpsTag.style.color = currentFps >= 10 ? "#00e676" : "#ff9100";
            }
          }

          isFetchingFrame = false;
          if (remoteStreamActive) {
            requestAnimationFrame(fetchStreamLoop);
          }
          return;
        } catch (bmErr) {
          console.warn("Bitmap decode notice:", bmErr);
        }
      }

      // Fallback Image element swap path
      const newBlobUrl = URL.createObjectURL(blob);
      const nextImg = new Image();
      nextImg.onload = () => {
        if (!remoteStreamActive) {
          URL.revokeObjectURL(newBlobUrl);
          isFetchingFrame = false;
          return;
        }
        if (dom.remoteScreenImg) {
          dom.remoteScreenImg.src = newBlobUrl;
          dom.remoteScreenImg.style.display = "block";
        }
        if (currentBlobUrl) {
          URL.revokeObjectURL(currentBlobUrl);
        }
        currentBlobUrl = newBlobUrl;

        frameCount++;
        const now = performance.now();
        if (now - lastFpsCalcTime >= 1000) {
          currentFps = Math.round((frameCount * 1000) / (now - lastFpsCalcTime));
          frameCount = 0;
          lastFpsCalcTime = now;
          if (dom.remoteFpsTag) {
            dom.remoteFpsTag.textContent = `${currentFps} FPS // ${remoteResolution.toUpperCase()}`;
            dom.remoteFpsTag.style.color = currentFps >= 10 ? "#00e676" : "#ff9100";
          }
        }

        isFetchingFrame = false;
        if (remoteStreamActive) {
          requestAnimationFrame(fetchStreamLoop);
        }
      };

      nextImg.onerror = () => {
        URL.revokeObjectURL(newBlobUrl);
        isFetchingFrame = false;
        if (remoteStreamActive) {
          setTimeout(fetchStreamLoop, 150);
        }
      };
    } catch (ex) {
      isFetchingFrame = false;
      if (dom.remoteFpsTag && remoteStreamActive) {
        dom.remoteFpsTag.textContent = "CONNECTING...";
        dom.remoteFpsTag.style.color = "#ff9100";
      }
      if (remoteStreamActive) {
        setTimeout(fetchStreamLoop, 600);
      }
    }
  }

  async function sendRemoteInput(action, params = {}) {
    const ep = (state.activeEndpoint || defaultLocalUrl).replace(/\/+$/, "");
    try {
      const resp = await fetch(`${ep}/api/remote/input`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Bypass-Tunnel-Reminder": "true",
          "X-Token": state.token,
        },
        body: JSON.stringify({
          action,
          params,
          token: state.token || undefined,
          device_id: "edith_mobile_pwa",
        }),
      });
      return await resp.json();
    } catch (ex) {
      console.warn("Remote input dispatch notice:", ex);
      return { success: false, error: ex.message };
    }
  }

  function openRemoteDesktop(gameMode = false) {
    remoteStreamActive = true;
    remoteGamepadMode = Boolean(gameMode);

    if (dom.remoteOverlay) {
      dom.remoteOverlay.style.display = "flex";
    }
    if (dom.gamepadOverlay) {
      dom.gamepadOverlay.style.display = remoteGamepadMode ? "flex" : "none";
    }
    if (dom.btnToggleGamepad) {
      dom.btnToggleGamepad.textContent = remoteGamepadMode ? "🖱️ Touch Mouse" : "🎮 Gamepad";
    }
    if (dom.remoteTitleText) {
      dom.remoteTitleText.textContent = remoteGamepadMode ? "EDITH CONTROLLER // GAME MODE" : "EDITH HOST VIEW // REMOTE RAT";
    }

    startScreenStream();
    triggerHaptic(30);

    try {
      if (document.documentElement.requestFullscreen && remoteGamepadMode) {
        document.documentElement.requestFullscreen().catch(() => {});
      }
      if (screen.orientation && screen.orientation.lock && remoteGamepadMode) {
        screen.orientation.lock("landscape").catch(() => {});
      }
    } catch (_) {}
  }

  function closeRemoteDesktop() {
    remoteStreamActive = false;
    isFetchingFrame = false;
    clearTimeout(remoteStreamRetryTimer);

    if (currentBlobUrl) {
      URL.revokeObjectURL(currentBlobUrl);
      currentBlobUrl = null;
    }

    if (dom.remoteOverlay) {
      dom.remoteOverlay.style.display = "none";
    }
    if (dom.remoteScreenImg) {
      dom.remoteScreenImg.src = "";
    }
    sendRemoteInput("joystick_release");

    try {
      if (document.exitFullscreen && document.fullscreenElement) {
        document.exitFullscreen().catch(() => {});
      }
      if (screen.orientation && screen.orientation.unlock) {
        screen.orientation.unlock();
      }
    } catch (_) {}
  }

  function startScreenStream() {
    if (!remoteStreamActive || !dom.remoteScreenImg) return;
    updateResolutionButtonUI();
    if (dom.remoteFpsTag) {
      dom.remoteFpsTag.textContent = `LINKING // ${remoteResolution.toUpperCase()}`;
      dom.remoteFpsTag.style.color = "#00e5ff";
    }
    isFetchingFrame = false;
    frameCount = 0;
    lastFpsCalcTime = performance.now();
    fetchStreamLoop();
  }

  function toggleGamepadView() {
    remoteGamepadMode = !remoteGamepadMode;
    if (dom.gamepadOverlay) {
      dom.gamepadOverlay.style.display = remoteGamepadMode ? "flex" : "none";
    }
    if (dom.btnToggleGamepad) {
      dom.btnToggleGamepad.textContent = remoteGamepadMode ? "🖱️ Touch Mouse" : "🎮 Gamepad";
    }
    if (dom.remoteTitleText) {
      dom.remoteTitleText.textContent = remoteGamepadMode ? "EDITH CONTROLLER // GAME MODE" : "EDITH HOST VIEW // REMOTE RAT";
    }
    triggerHaptic(20);
  }

  // Bi-Directional Clipboard Sync
  async function syncClipboardWithLaptop() {
    triggerHaptic(25);
    const ep = (state.activeEndpoint || defaultLocalUrl).replace(/\/+$/, "");
    let textToSend = "";

    try {
      if (navigator.clipboard && navigator.clipboard.readText) {
        textToSend = (await navigator.clipboard.readText()) || "";
      }
    } catch (_) {}

    try {
      const resp = await fetch(`${ep}/api/clipboard/sync`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Bypass-Tunnel-Reminder": "true",
          "X-Token": state.token,
        },
        body: JSON.stringify({
          text: textToSend,
          device_id: "edith_mobile_pwa",
          token: state.token || undefined,
        }),
      });
      const data = await resp.json();

      if (data.laptop_clipboard && navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(data.laptop_clipboard);
        logConsole("CLIPBOARD", `Synced! Copied ${data.laptop_clipboard.length} chars from laptop.`);
        alert(`Clipboard Synced!\nReceived from Laptop: "${data.laptop_clipboard.slice(0, 80)}..."`);
      } else {
        logConsole("CLIPBOARD", "Sent mobile clipboard to laptop.");
        alert("Mobile clipboard synced to laptop.");
      }
    } catch (err) {
      alert(`Clipboard sync notice: ${err.message}`);
    }
  }

  // Touch Viewport Mouse Gestures
  function initRemoteViewportEvents() {
    if (!dom.remoteViewport || !dom.remoteScreenImg) return;

    let touchStartTime = 0;
    let touchStartX = 0;
    let touchStartY = 0;
    let lastTapTime = 0;
    let isLongPress = false;
    let longPressTimer = null;
    let twoFingerStartY = 0;

    function getNormalizedCoords(clientX, clientY) {
      let rect = dom.vncCanvas ? dom.vncCanvas.getBoundingClientRect() : null;
      if (!rect || rect.width <= 10 || rect.height <= 10) {
        rect = dom.remoteScreenImg ? dom.remoteScreenImg.getBoundingClientRect() : null;
      }
      if (!rect || rect.width <= 10 || rect.height <= 10) {
        rect = dom.remoteViewport.getBoundingClientRect();
      }
      if (!rect || rect.width === 0 || rect.height === 0) {
        return { x: 0.5, y: 0.5 };
      }
      const x = Math.max(0.0, Math.min(1.0, (clientX - rect.left) / rect.width));
      const y = Math.max(0.0, Math.min(1.0, (clientY - rect.top) / rect.height));
      return { x, y };
    }

    function showRipple(clientX, clientY) {
      if (!dom.remoteFeedback) return;
      dom.remoteFeedback.style.left = `${clientX}px`;
      dom.remoteFeedback.style.top = `${clientY}px`;
      dom.remoteFeedback.classList.remove("ripple");
      void dom.remoteFeedback.offsetWidth;
      dom.remoteFeedback.classList.add("ripple");
    }

    function updateVirtualCursor(clientX, clientY) {
      if (!dom.remoteCursor) return;
      dom.remoteCursor.style.display = "block";
      dom.remoteCursor.style.left = `${clientX}px`;
      dom.remoteCursor.style.top = `${clientY}px`;
    }

    dom.remoteViewport.addEventListener("touchstart", (e) => {
      if (e.target.closest("#virtual-gamepad-overlay") || e.target.closest(".remote-bottom-bar")) {
        return;
      }

      if (e.touches.length === 1) {
        const t = e.touches[0];
        touchStartTime = Date.now();
        touchStartX = t.clientX;
        touchStartY = t.clientY;
        isLongPress = false;

        const coords = getNormalizedCoords(t.clientX, t.clientY);
        updateVirtualCursor(t.clientX, t.clientY);

        clearTimeout(longPressTimer);
        longPressTimer = setTimeout(() => {
          isLongPress = true;
          triggerHaptic(40);
          showRipple(t.clientX, t.clientY);
          sendRemoteInput("right_click", coords);
        }, 450);
      } else if (e.touches.length === 2) {
        clearTimeout(longPressTimer);
        twoFingerStartY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      }
    }, { passive: false });

    dom.remoteViewport.addEventListener("touchmove", (e) => {
      if (e.target.closest("#virtual-gamepad-overlay") || e.target.closest(".remote-bottom-bar")) {
        return;
      }
      e.preventDefault();

      if (e.touches.length === 1) {
        const t = e.touches[0];
        const dist = Math.hypot(t.clientX - touchStartX, t.clientY - touchStartY);
        if (dist > 10) {
          clearTimeout(longPressTimer);
        }

        const coords = getNormalizedCoords(t.clientX, t.clientY);
        updateVirtualCursor(t.clientX, t.clientY);
        sendRemoteInput("mouse_move", coords);
      } else if (e.touches.length === 2) {
        clearTimeout(longPressTimer);
        const currentTwoY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
        const delta = currentTwoY - twoFingerStartY;
        if (Math.abs(delta) > 15) {
          sendRemoteInput("scroll", { delta: delta > 0 ? 2 : -2 });
          twoFingerStartY = currentTwoY;
        }
      }
    }, { passive: false });

    dom.remoteViewport.addEventListener("touchend", (e) => {
      clearTimeout(longPressTimer);
      if (e.target.closest("#virtual-gamepad-overlay") || e.target.closest(".remote-bottom-bar")) {
        return;
      }

      const elapsed = Date.now() - touchStartTime;
      if (!isLongPress && elapsed < 350 && e.changedTouches.length === 1) {
        const t = e.changedTouches[0];
        const dist = Math.hypot(t.clientX - touchStartX, t.clientY - touchStartY);
        if (dist < 15) {
          const coords = getNormalizedCoords(t.clientX, t.clientY);
          showRipple(t.clientX, t.clientY);

          const now = Date.now();
          if (now - lastTapTime < 300) {
            sendRemoteInput("double_click", coords);
            lastTapTime = 0;
          } else {
            sendRemoteInput("click", coords);
            lastTapTime = now;
          }
        }
      }
    });

    if (dom.remoteBottomBar) {
      dom.remoteBottomBar.querySelectorAll(".remote-gesture-chip").forEach((chip) => {
        chip.addEventListener("click", () => {
          const action = chip.getAttribute("data-action");
          triggerHaptic(15);
          if (action === "scroll_up") {
            sendRemoteInput("scroll", { delta: 3 });
          } else if (action === "scroll_down") {
            sendRemoteInput("scroll", { delta: -3 });
          } else if (action === "switch_window") {
            sendRemoteInput("switch_window");
          } else {
            sendRemoteInput(action);
          }
        });
      });
    }
  }

  // Virtual Joystick Touch & Pointer Controller
  function initJoystickEvents() {
    if (!dom.stickBase || !dom.stickNub) return;

    const maxRadius = 45;
    let activePointerId = null;

    function handleStickMove(clientX, clientY) {
      const rect = dom.stickBase.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      let dx = clientX - centerX;
      let dy = clientY - centerY;
      const dist = Math.hypot(dx, dy);

      if (dist > maxRadius) {
        dx = (dx / dist) * maxRadius;
        dy = (dy / dist) * maxRadius;
      }

      dom.stickNub.style.transform = `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px))`;

      const normX = dx / maxRadius;
      const normY = dy / maxRadius;

      const now = performance.now();
      if (now - lastJoystickDispatch > 30) {
        lastJoystickDispatch = now;
        joystickActive = true;
        sendRemoteInput("joystick", { x: normX, y: normY });
      }
    }

    function resetStick() {
      activePointerId = null;
      dom.stickNub.style.transform = "translate(-50%, -50%)";
      if (joystickActive) {
        joystickActive = false;
        sendRemoteInput("joystick_release");
      }
    }

    if (window.PointerEvent) {
      dom.stickBase.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        e.stopPropagation();
        activePointerId = e.pointerId;
        try { dom.stickBase.setPointerCapture(e.pointerId); } catch (_) {}
        handleStickMove(e.clientX, e.clientY);
      });

      dom.stickBase.addEventListener("pointermove", (e) => {
        if (activePointerId === null || e.pointerId !== activePointerId) return;
        e.preventDefault();
        e.stopPropagation();
        handleStickMove(e.clientX, e.clientY);
      });

      const onPointerEnd = (e) => {
        if (activePointerId !== null && e.pointerId === activePointerId) {
          e.preventDefault();
          e.stopPropagation();
          try { dom.stickBase.releasePointerCapture(e.pointerId); } catch (_) {}
          resetStick();
        }
      };

      dom.stickBase.addEventListener("pointerup", onPointerEnd);
      dom.stickBase.addEventListener("pointercancel", onPointerEnd);
    } else {
      dom.stickBase.addEventListener("touchstart", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const t = e.touches[0];
        handleStickMove(t.clientX, t.clientY);
      }, { passive: false });

      dom.stickBase.addEventListener("touchmove", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const t = e.touches[0];
        handleStickMove(t.clientX, t.clientY);
      }, { passive: false });

      dom.stickBase.addEventListener("touchend", (e) => {
        e.preventDefault();
        e.stopPropagation();
        resetStick();
      }, { passive: false });

      dom.stickBase.addEventListener("touchcancel", (e) => {
        e.preventDefault();
        e.stopPropagation();
        resetStick();
      }, { passive: false });
    }
  }

  // Gamepad Action Buttons
  function initGamepadButtonEvents() {
    const buttons = document.querySelectorAll(".game-btn");
    buttons.forEach((btn) => {
      const btnCode = btn.getAttribute("data-btn");
      if (!btnCode) return;

      const press = (e) => {
        e.preventDefault();
        e.stopPropagation();
        btn.classList.add("pressed");
        triggerHaptic(20);
        sendRemoteInput("game_button", { button: btnCode, pressed: true });
      };

      const release = (e) => {
        e.preventDefault();
        e.stopPropagation();
        btn.classList.remove("pressed");
        sendRemoteInput("game_button", { button: btnCode, pressed: false });
      };

      btn.addEventListener("touchstart", press, { passive: false });
      btn.addEventListener("touchend", release, { passive: false });
      btn.addEventListener("touchcancel", release, { passive: false });
      btn.addEventListener("mousedown", press);
      btn.addEventListener("mouseup", release);
      btn.addEventListener("mouseleave", release);
    });
  }

  // Remote Keyboard Modal Events
  function initRemoteKeyboardEvents() {
    if (!dom.modalKb) return;

    if (dom.btnOpenKb) {
      dom.btnOpenKb.addEventListener("click", () => {
        dom.modalKb.style.display = "flex";
        if (dom.kbTextInput) dom.kbTextInput.focus();
      });
    }

    if (dom.btnCloseKb) {
      dom.btnCloseKb.addEventListener("click", () => {
        dom.modalKb.style.display = "none";
      });
    }

    if (dom.btnKbSendText && dom.kbTextInput) {
      const sendText = () => {
        const txt = dom.kbTextInput.value;
        if (txt) {
          sendRemoteInput("type_text", { text: txt });
          dom.kbTextInput.value = "";
          triggerHaptic(15);
        }
      };
      dom.btnKbSendText.addEventListener("click", sendText);
      dom.kbTextInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendText();
      });
    }

    if (dom.btnKbEnter) {
      dom.btnKbEnter.addEventListener("click", () => {
        triggerHaptic(15);
        sendRemoteInput("key_press", { key: "enter" });
      });
    }

    document.querySelectorAll(".kb-key-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        triggerHaptic(15);
        const singleKey = chip.getAttribute("data-key");
        const hotkeys = chip.getAttribute("data-hotkey");

        if (singleKey) {
          sendRemoteInput("key_press", { key: singleKey });
        } else if (hotkeys) {
          sendRemoteInput("hotkey", { keys: hotkeys.split(",") });
        }
      });
    });
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

    // In-HUD Media Player Listeners
    if (dom.btnMediaPopout) {
      dom.btnMediaPopout.addEventListener("click", popoutMedia);
    }
    if (dom.btnMediaMin) {
      dom.btnMediaMin.addEventListener("click", toggleMinimizeMedia);
    }
    if (dom.btnMediaClose) {
      dom.btnMediaClose.addEventListener("click", closeHudMedia);
    }

    // Header Mode Toggle
    if (dom.btnModeToggle) {
      dom.btnModeToggle.addEventListener("click", toggleSystemMode);
    }

    // Remote Desktop & Virtual Gamepad Listeners
    if (dom.btnOpenRemote) {
      dom.btnOpenRemote.addEventListener("click", () => openRemoteDesktop(false));
    }
    if (dom.btnOpenGamepad) {
      dom.btnOpenGamepad.addEventListener("click", () => openRemoteDesktop(true));
    }
    if (dom.btnSyncClipboard) {
      dom.btnSyncClipboard.addEventListener("click", syncClipboardWithLaptop);
    }
    if (dom.btnCloseRemote) {
      dom.btnCloseRemote.addEventListener("click", closeRemoteDesktop);
    }
    if (dom.btnToggleGamepad) {
      dom.btnToggleGamepad.addEventListener("click", toggleGamepadView);
    }
    if (dom.btnRemoteClip) {
      dom.btnRemoteClip.addEventListener("click", syncClipboardWithLaptop);
    }
    if (dom.btnRemoteRefresh) {
      dom.btnRemoteRefresh.addEventListener("click", startScreenStream);
    }
    if (dom.btnRemoteRes) {
      dom.btnRemoteRes.addEventListener("click", toggleResolution);
    }
    if (dom.btnQuickConnect) {
      dom.btnQuickConnect.addEventListener("click", async () => {
        const val = (dom.quickHostInput ? dom.quickHostInput.value : "").trim();
        if (val) {
          const clean = val.startsWith("http") ? val : `http://${val}`;
          state.localUrl = clean;
          localStorage.setItem("edith_mobile_local_url", clean);
          if (dom.cfgLocalUrl) dom.cfgLocalUrl.value = clean;
          logConsole("MANUAL HOST", `Testing host link: ${clean}`);
          await resolveActiveEndpoint();
        }
      });
    }
    if (dom.btnQuickScan) {
      dom.btnQuickScan.addEventListener("click", () => scanLocalSubnet());
    }
    if (dom.btnOpenVnc) {
      dom.btnOpenVnc.addEventListener("click", () => {
        const ep = (state.activeEndpoint || defaultLocalUrl).replace(/\/+$/, "");
        window.open(`${ep}/vnc`, "_blank");
      });
    }

    initRemoteViewportEvents();
    initJoystickEvents();
    initGamepadButtonEvents();
    initRemoteKeyboardEvents();
    initGameCameraTrackpad();
  }

  function initGameCameraTrackpad() {
    if (!dom.gameLookTrackpad) return;
    let isTracking = false;
    let lastX = 0;
    let lastY = 0;
    let lastDispatch = 0;

    dom.gameLookTrackpad.addEventListener("touchstart", (e) => {
      if (e.touches.length > 0) {
        isTracking = true;
        lastX = e.touches[0].clientX;
        lastY = e.touches[0].clientY;
        triggerHaptic(10);
      }
    }, { passive: false });

    dom.gameLookTrackpad.addEventListener("touchmove", (e) => {
      if (!isTracking || e.touches.length === 0) return;
      e.preventDefault();
      const now = performance.now();
      if (now - lastDispatch < 22) return;

      const t = e.touches[0];
      const dx = Math.round((t.clientX - lastX) * 1.5);
      const dy = Math.round((t.clientY - lastY) * 1.5);
      lastX = t.clientX;
      lastY = t.clientY;
      lastDispatch = now;

      if (dx !== 0 || dy !== 0) {
        sendRemoteInput("camera_look", { dx, dy });
      }
    }, { passive: false });

    const endTrack = () => { isTracking = false; };
    dom.gameLookTrackpad.addEventListener("touchend", endTrack);
    dom.gameLookTrackpad.addEventListener("touchcancel", endTrack);
  }

  async function scanLocalSubnet(baseSubnet = "192.168.1", port = 8794) {
    if (dom.btnQuickScan) {
      dom.btnQuickScan.textContent = "Scanning...";
      dom.btnQuickScan.style.color = "#ff9100";
    }
    logConsole("SCANNER", `Scanning LAN subnet ${baseSubnet}.0/24 for EDITH PC...`);
    triggerHaptic(30);

    const priorityIps = [167, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 2, 3, 4, 5, 10, 20, 50, 150];
    const otherIps = Array.from({ length: 254 }, (_, i) => i + 1).filter(i => !priorityIps.includes(i));
    const allIps = [...priorityIps, ...otherIps];

    const batchSize = 12;
    let foundUrl = null;

    for (let i = 0; i < allIps.length; i += batchSize) {
      const batch = allIps.slice(i, i + batchSize);
      const promises = batch.map(async (hostNum) => {
        const testUrl = `http://${baseSubnet}.${hostNum}:${port}`;
        const res = await pingEndpoint(testUrl, 450);
        if (res.ok) return testUrl;
        return null;
      });
      const results = await Promise.all(promises);
      foundUrl = results.find(Boolean);
      if (foundUrl) break;
    }

    if (foundUrl) {
      logConsole("SCANNER", `Discovered EDITH Host: ${foundUrl}!`);
      state.localUrl = foundUrl;
      localStorage.setItem("edith_mobile_local_url", foundUrl);
      if (dom.cfgLocalUrl) dom.cfgLocalUrl.value = foundUrl;
      if (dom.quickHostInput) dom.quickHostInput.value = foundUrl;
      await resolveActiveEndpoint();
      speakResponse("EDITH mainframe discovered and connected.");
    } else {
      logConsole("SCANNER", "No EDITH host detected on 192.168.1.x. Try entering host IP manually.");
      alert("No EDITH host detected on 192.168.1.x.\\nPlease verify PC is on same Wi-Fi and EDITH is running.");
    }

    if (dom.btnQuickScan) {
      dom.btnQuickScan.textContent = "🔍 Scan";
      dom.btnQuickScan.style.color = "#00e676";
    }
    return foundUrl;
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

  // Auto-fetch server config if loaded from server or disk
  async function fetchServerConfig() {
    // 1. Try bundled server_config.json if running in native APK
    try {
      const bResp = await fetch("./server_config.json");
      if (bResp.ok) {
        const bcfg = await bResp.json();
        if (bcfg.cloud_url) {
          state.cloudUrl = bcfg.cloud_url;
          localStorage.setItem(STORAGE_KEYS.CLOUD_URL, state.cloudUrl);
          if (dom.cfgCloudUrl) dom.cfgCloudUrl.value = state.cloudUrl;
        }
        if (bcfg.local_url && (!state.localUrl || state.localUrl.includes("127.0.0.1"))) {
          state.localUrl = bcfg.local_url;
          localStorage.setItem(STORAGE_KEYS.LOCAL_URL, state.localUrl);
          if (dom.cfgLocalUrl) dom.cfgLocalUrl.value = state.localUrl;
        }
      }
    } catch (_) {}

    // 2. Query running host endpoints for live dynamic config
    const candidates = [state.activeEndpoint, state.localUrl, defaultLocalUrl, state.cloudUrl].filter(Boolean);
    for (const ep of candidates) {
      try {
        const clean = ep.replace(/\/+$/, "");
        const resp = await fetch(`${clean}/mobile/config`, {
          headers: { "Bypass-Tunnel-Reminder": "true" },
        });
        if (resp.ok) {
          const cfg = await resp.json();
          if (cfg.cloud_url && state.cloudUrl !== cfg.cloud_url) {
            state.cloudUrl = cfg.cloud_url;
            localStorage.setItem(STORAGE_KEYS.CLOUD_URL, state.cloudUrl);
            if (dom.cfgCloudUrl) dom.cfgCloudUrl.value = state.cloudUrl;
          }
          if (cfg.local_ip && (!state.localUrl || state.localUrl.includes("127.0.0.1"))) {
            state.localUrl = `http://${cfg.local_ip}:${cfg.ui_port || 8794}`;
            localStorage.setItem(STORAGE_KEYS.LOCAL_URL, state.localUrl);
            if (dom.cfgLocalUrl) dom.cfgLocalUrl.value = state.localUrl;
          }
          break;
        }
      } catch (_) {}
    }
  }

  // ---------------- Bi-Directional Message Polling & Telemetry ----------------
  async function pollPhoneMessagesAndTelemetry() {
    if (!state.activeEndpoint || !state.isOnline) return;

    let batteryPercent = null;
    try {
      if (navigator.getBattery) {
        const b = await navigator.getBattery();
        batteryPercent = Math.round(b.level * 100);
      }
    } catch (_) {}

    let connType = state.activeType || "UNKNOWN";
    try {
      if (navigator.connection && (navigator.connection.effectiveType || navigator.connection.type)) {
        connType = `${state.activeType}:${navigator.connection.effectiveType || navigator.connection.type}`;
      }
    } catch (_) {}

    const ep = state.activeEndpoint.replace(/\/+$/, "");
    const query = new URLSearchParams({
      device_id: "edith_mobile_pwa",
      battery: batteryPercent !== null ? batteryPercent.toString() : "",
      conn: connType,
      token: state.token || "",
    });

    try {
      const resp = await fetch(`${ep}/api/phone/messages?${query.toString()}`, {
        headers: { "Bypass-Tunnel-Reminder": "true" },
      });
      if (resp.ok) {
        const data = await resp.json();
        const msgs = data.messages || [];
        for (const m of msgs) {
          const text = m.text || m.message || JSON.stringify(m);
          logConsole("PC NOTIFICATION", text);
          triggerHaptic(40);
          speakResponse(`Notification from PC: ${text}`);
          if (m.type === "alert") {
            alert(`[EDITH LAPTOP MESSAGE]:\n${text}`);
          }
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
    if (dom.quickHostInput) dom.quickHostInput.value = state.localUrl;

    await fetchServerConfig();
    await resolveActiveEndpoint();
    if (dom.quickHostInput) dom.quickHostInput.value = state.localUrl;
    await syncSystemMode();

    // Heartbeat connection maintenance and bi-directional message polling
    setInterval(async () => {
      await fetchServerConfig();
      await resolveActiveEndpoint();
      await syncSystemMode();
      await pollPhoneMessagesAndTelemetry();
    }, 3500);
  }

  window.addEventListener("DOMContentLoaded", init);
})();
