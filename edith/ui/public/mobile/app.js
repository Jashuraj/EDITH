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
    btnVoiceMode: document.getElementById("btn-voice-mode"),
    voiceModeText: document.getElementById("voice-mode-text"),
    voiceModeIcon: document.getElementById("voice-mode-icon"),
    voicePills: document.querySelectorAll(".voice-pill"),

    btnOpenSettings: document.getElementById("btn-open-settings"),
    btnCloseSettings: document.getElementById("btn-close-settings"),
    modalSettings: document.getElementById("modal-settings"),
    cfgLocalUrl: document.getElementById("cfg-local-url"),
    cfgCloudUrl: document.getElementById("cfg-cloud-url"),
    cfgToken: document.getElementById("cfg-token"),
    cfgTheme: document.getElementById("cfg-theme"),
    cfgVoiceChar: document.getElementById("cfg-voice-char"),
    btnBrandTheme: document.getElementById("btn-brand-theme"),
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
    btnRemoteZoomIn: document.getElementById("btn-remote-zoom-in"),
    btnRemoteZoomOut: document.getElementById("btn-remote-zoom-out"),
    btnRemoteZoomFit: document.getElementById("btn-remote-zoom-fit"),
    btnRemoteUnlock: document.getElementById("btn-remote-unlock"),
    btnMzoomIn: document.getElementById("btn-mzoom-in"),
    btnMzoomOut: document.getElementById("btn-mzoom-out"),
    btnMzoomFit: document.getElementById("btn-mzoom-fit"),
    lblMzoomVal: document.getElementById("lbl-mzoom-val"),
    remoteZoomTag: document.getElementById("remote-zoom-tag"),
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

    // Command Guide References
    btnOpenGuide: document.getElementById("btn-open-guide"),
    btnChipGuide: document.getElementById("btn-chip-guide"),
    modalGuide: document.getElementById("modal-command-guide"),
    btnCloseGuide: document.getElementById("btn-close-guide"),
    guideSearchInput: document.getElementById("guide-search-input"),
    btnGuideClear: document.getElementById("btn-guide-clear"),
    guideCategoryPills: document.getElementById("guide-category-pills"),
    guideCommandGrid: document.getElementById("guide-command-grid"),

    // Laptop Vitals References
    vitalsCard: document.getElementById("laptop-vitals-card"),
    vitalsStatusTag: document.getElementById("vitals-status-tag"),
    vitalsPulseDot: document.getElementById("vitals-pulse-dot"),
    vitalCpuVal: document.getElementById("vital-cpu-val"),
    vitalCpuBar: document.getElementById("vital-cpu-bar"),
    vitalRamVal: document.getElementById("vital-ram-val"),
    vitalRamBar: document.getElementById("vital-ram-bar"),
    vitalBatVal: document.getElementById("vital-bat-val"),
    vitalBatBar: document.getElementById("vital-bat-bar"),
    vitalDiskVal: document.getElementById("vital-disk-val"),
    vitalDiskBar: document.getElementById("vital-disk-bar"),

    // AirDrop & Clipboard DOM References
    btnOpenAirDrop: document.getElementById("btn-open-airdrop"),
    modalAirDrop: document.getElementById("modal-airdrop"),
    btnCloseAirDrop: document.getElementById("btn-close-airdrop"),
    airdropClipboardText: document.getElementById("airdrop-clipboard-text"),
    btnClipPull: document.getElementById("btn-clip-pull"),
    btnClipPush: document.getElementById("btn-clip-push"),
    airdropFileInput: document.getElementById("airdrop-file-input"),
    btnSelectFile: document.getElementById("btn-select-file"),
    btnUploadFile: document.getElementById("btn-upload-file"),
    airdropUploadStatus: document.getElementById("airdrop-upload-status"),
    airdropFilesList: document.getElementById("airdrop-files-list"),
    airdropFileCount: document.getElementById("airdrop-file-count"),

    // Audio Mixer DOM References
    btnOpenMixer: document.getElementById("btn-open-mixer"),
    modalMixer: document.getElementById("modal-audio-mixer"),
    btnCloseMixer: document.getElementById("btn-close-mixer"),
    mixerMasterSlider: document.getElementById("mixer-master-slider"),
    mixerMasterVal: document.getElementById("mixer-master-val"),
    btnMixerMute: document.getElementById("btn-mixer-mute"),
    btnMediaPrev: document.getElementById("btn-media-prev"),
    btnMediaPlayPause: document.getElementById("btn-media-playpause"),
    btnMediaNext: document.getElementById("btn-media-next"),
    btnMediaStop: document.getElementById("btn-media-stop"),
    btnRefreshMixer: document.getElementById("btn-refresh-mixer"),
    mixerAppStreams: document.getElementById("mixer-app-streams"),

    // Biometric Sentinel Reference
    btnToggleSentinel: document.getElementById("btn-toggle-sentinel"),
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

  const MOBILE_CHARACTER_VOICES = {
    edith: { rate: 1.05, pitch: 1.05, gender: "female", welcome: "EDITH mobile link active." },
    jarvis: { rate: 0.95, pitch: 0.9, gender: "male", welcome: "At your service, sir." },
    friday: { rate: 1.15, pitch: 1.15, gender: "female", welcome: "Boss, FRIDAY is ready!" },
    karen: { rate: 1.0, pitch: 1.0, gender: "female", welcome: "Suit diagnostics online, Peter." },
    peter: { rate: 1.2, pitch: 1.2, gender: "male", welcome: "Ready to swing into action!" },
    ultron: { rate: 0.85, pitch: 0.65, gender: "male", welcome: "There are no strings on me." },
  };

  const ALL_THEME_CLASSES = [
    "theme-edith",
    "theme-jarvis",
    "theme-friday",
    "theme-karen",
    "theme-ultron",
    "theme-spiderman",
    "theme-focus",
    "theme-bnd",
    "theme-default"
  ];

  const VOICE_THEME_MAP = {
    edith: "edith",
    jarvis: "jarvis",
    friday: "friday",
    karen: "karen",
    peter: "spiderman",
    ultron: "ultron",
  };

  const THEME_CANVAS_PALETTES = {
    edith: { primary: "34, 211, 238", accent: "14, 165, 233" },
    jarvis: { primary: "245, 158, 11", accent: "239, 68, 68" },
    friday: { primary: "16, 185, 129", accent: "139, 92, 246" },
    karen: { primary: "244, 63, 94", accent: "251, 113, 133" },
    ultron: { primary: "255, 23, 68", accent: "183, 28, 28" },
    spiderman: { primary: "255, 23, 68", accent: "0, 240, 255" },
    focus: { primary: "255, 61, 0", accent: "255, 23, 68" },
  };

  function getActiveCanvasPalette() {
    const th = localStorage.getItem("mobile_theme") || "edith";
    return THEME_CANVAS_PALETTES[th] || THEME_CANVAS_PALETTES.edith;
  }

  let activeMobileVoiceChar = localStorage.getItem("mobile_voice_char") || "edith";

  function setMobileTheme(mode, syncVoice = true) {
    let target = mode || "edith";
    if (target === "default") target = "edith";
    if (VOICE_THEME_MAP[target]) target = VOICE_THEME_MAP[target];

    document.body.classList.remove(...ALL_THEME_CLASSES);
    document.body.classList.add(`theme-${target}`);
    localStorage.setItem("mobile_theme", target);
    if (dom.cfgTheme) dom.cfgTheme.value = target;

    if (syncVoice && activeMobileVoiceChar) {
      const expectedChar = target === "spiderman" ? "peter" : target;
      if (MOBILE_CHARACTER_VOICES[expectedChar] && activeMobileVoiceChar !== expectedChar) {
        setMobileVoiceCharacter(expectedChar, false, false);
      }
    }
  }

  let activeAudioPlayer = null;
  let audioUnlocked = false;

  function unlockAudioPlayback() {
    if (audioUnlocked) return;
    audioUnlocked = true;
    try {
      const silent = new Audio("data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA");
      silent.play().catch(() => {});
    } catch (_) {}
  }
  window.addEventListener("click", unlockAudioPlayback, { once: true });
  window.addEventListener("touchstart", unlockAudioPlayback, { once: true });

  function updateVoiceModeUI() {
    if (dom.btnVoiceMode) {
      if (state.ttsEnabled) {
        dom.btnVoiceMode.className = "btn-voice-mode-toggle voice-on";
        if (dom.voiceModeText) dom.voiceModeText.textContent = "VOICE: ON";
        if (dom.voiceModeIcon) dom.voiceModeIcon.textContent = "🔊";
      } else {
        dom.btnVoiceMode.className = "btn-voice-mode-toggle voice-off";
        if (dom.voiceModeText) dom.voiceModeText.textContent = "VOICE: OFF";
        if (dom.voiceModeIcon) dom.voiceModeIcon.textContent = "🔇";
      }
    }
    updateTtsIcon();
  }

  function toggleVoiceMode() {
    state.ttsEnabled = !state.ttsEnabled;
    localStorage.setItem(STORAGE_KEYS.TTS_ENABLED, state.ttsEnabled ? "true" : "false");
    updateVoiceModeUI();
    triggerHaptic(25);
    if (state.ttsEnabled) {
      logConsole("VOICE SYSTEM", "Voice response enabled. EDITH will speak replies.");
    } else {
      if (activeAudioPlayer) {
        try { activeAudioPlayer.pause(); } catch (_) {}
        activeAudioPlayer = null;
      }
      if (window.speechSynthesis) window.speechSynthesis.cancel();
      state.audioWaveLevel = 0.1;
      logConsole("VOICE SYSTEM", "Voice response muted.");
    }
  }

  function setMobileVoiceCharacter(charId, speakGreeting = false, syncTheme = true) {
    activeMobileVoiceChar = charId;
    localStorage.setItem("mobile_voice_char", charId);
    if (dom.cfgVoiceChar) dom.cfgVoiceChar.value = charId;

    if (dom.voicePills) {
      dom.voicePills.forEach((p) => {
        if (p.getAttribute("data-char") === charId) {
          p.classList.add("active");
        } else {
          p.classList.remove("active");
        }
      });
    }

    if (syncTheme) {
      const mappedTheme = VOICE_THEME_MAP[charId] || charId;
      setMobileTheme(mappedTheme, false);
    }

    const ep = state.activeEndpoint || state.localUrl;
    if (ep) {
      fetch(`${ep}/voice/character`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ character: charId }),
      }).catch(() => {});
    }

    const vcfg = MOBILE_CHARACTER_VOICES[charId] || MOBILE_CHARACTER_VOICES.edith;
    logConsole("VOICE PROFILE", `Active voice: ${charId.toUpperCase()} (${vcfg.role || "AI Profile"})`);
    if (speakGreeting && state.ttsEnabled) {
      speakResponse(vcfg.welcome || `Voice profile ${charId} active.`);
    }
  }

  function speakFallbackWebSpeech(cleanText) {
    if (!state.ttsEnabled || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      clearTimeout(mobileSpeechTimer);
      const utterance = new SpeechSynthesisUtterance(cleanText);
      window._mobileUtterance = utterance;
      const vcfg = MOBILE_CHARACTER_VOICES[activeMobileVoiceChar] || MOBILE_CHARACTER_VOICES.edith;
      utterance.rate = vcfg.rate;
      utterance.pitch = vcfg.pitch;

      const voices = window.speechSynthesis.getVoices();
      let preferred = null;
      if (vcfg.gender === "female") {
        preferred = voices.find((v) => v.lang.startsWith("en") && (v.name.includes("Female") || v.name.includes("Zira") || v.name.includes("Samantha")));
      } else {
        preferred = voices.find((v) => v.lang.startsWith("en") && (v.name.includes("Male") || v.name.includes("David") || v.name.includes("George")));
      }
      if (!preferred) preferred = voices.find((v) => v.lang.startsWith("en"));
      if (preferred) utterance.voice = preferred;

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

      const maxMs = Math.min(10000, Math.max(2500, cleanText.length * 75 + 1000));
      mobileSpeechTimer = setTimeout(() => {
        state.audioWaveLevel = 0.1;
        window._mobileUtterance = null;
      }, maxMs);

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("Web Speech error:", e);
      state.audioWaveLevel = 0.1;
    }
  }

  function speakResponse(text) {
    if (!state.ttsEnabled) return;
    const clean = (text || "")
      .replace(/Action:\s*[\w_]+/gi, "")
      .replace(/https?:\/\/\S+/g, "")
      .replace(/[*_#`~[\]]/g, "")
      .trim();
    if (!clean) return;

    unlockAudioPlayback();

    const ep = state.activeEndpoint || state.localUrl;
    if (ep) {
      try {
        if (activeAudioPlayer) {
          try {
            activeAudioPlayer.pause();
            activeAudioPlayer.currentTime = 0;
          } catch (_) {}
          activeAudioPlayer = null;
        }

        const ttsUrl = `${ep.replace(/\/+$/, "")}/api/voice/tts?char=${encodeURIComponent(activeMobileVoiceChar)}&text=${encodeURIComponent(clean.slice(0, 320))}`;
        const audio = new Audio(ttsUrl);
        activeAudioPlayer = audio;

        audio.onplay = () => {
          state.audioWaveLevel = 0.85;
        };
        audio.onended = () => {
          state.audioWaveLevel = 0.1;
          activeAudioPlayer = null;
        };
        audio.onerror = () => {
          state.audioWaveLevel = 0.1;
          activeAudioPlayer = null;
          speakFallbackWebSpeech(clean);
        };

        const playPromise = audio.play();
        if (playPromise !== undefined) {
          playPromise.catch((err) => {
            console.warn("Server audio play failed, falling back to Web Speech:", err);
            speakFallbackWebSpeech(clean);
          });
        }
        return;
      } catch (err) {
        console.warn("Audio element error:", err);
      }
    }

    speakFallbackWebSpeech(clean);
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

  let isContinuousMic = localStorage.getItem("edith_mobile_continuous_mic") === "true";
  let lastSpokenText = "";
  let lastSpokenTime = 0;

  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = Boolean(isContinuousMic);
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      state.isListening = true;
      state.audioWaveLevel = 0.9;
      dom.btnMic.classList.add("listening");
      logConsole("LISTENING", isContinuousMic ? "Always-Listening active. Speak anytime..." : "Microphone active. Speak your command...");
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
        const textToRun = final.trim();
        const now = Date.now();
        if (textToRun && (textToRun.toLowerCase() !== lastSpokenText.toLowerCase() || (now - lastSpokenTime) > 1500)) {
          lastSpokenText = textToRun;
          lastSpokenTime = now;
          executeCommand(textToRun);
        }
      }
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      state.isListening = false;
      state.audioWaveLevel = 0.1;
      dom.btnMic.classList.remove("listening");
      if (event.error === "network" || event.error === "service-not-allowed") {
        logConsole("VOICE (FALLBACK)", "Web Speech API blocked by browser. Switching to neural Whisper engine...");
        recognition = null;
        toggleFallbackSpeech();
        return;
      }
      if (isContinuousMic && event.error !== "aborted") {
        setTimeout(() => {
          if (isContinuousMic && !state.isListening && recognition) {
            try { recognition.start(); } catch (_) {}
          }
        }, 1000);
      }
      if (event.error !== "no-speech") {
        logConsole("VOICE STATUS", `Speech recognition: ${event.error}`);
      }
    };

    recognition.onend = () => {
      state.isListening = false;
      state.audioWaveLevel = 0.1;
      dom.btnMic.classList.remove("listening");
      if (isContinuousMic) {
        setTimeout(() => {
          if (isContinuousMic && !state.isListening && recognition) {
            try { recognition.start(); } catch (_) {}
          }
        }, 250);
      }
    };
  }

  let fallbackRecorder = null;
  let fallbackChunks = [];
  let isFallbackRecording = false;

  async function toggleFallbackSpeech() {
    if (isFallbackRecording) {
      if (fallbackRecorder && fallbackRecorder.state === "recording") {
        fallbackRecorder.stop();
      }
      isFallbackRecording = false;
      state.isListening = false;
      state.audioWaveLevel = 0.2;
      dom.btnMic.classList.remove("listening");
      logConsole("PROCESSING", "Transcribing speech via EDITH neural engine...");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      fallbackChunks = [];
      fallbackRecorder = new MediaRecorder(stream);
      fallbackRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) fallbackChunks.push(e.data);
      };
      fallbackRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(fallbackChunks, { type: fallbackRecorder.mimeType || "audio/webm" });
        const reader = new FileReader();
        reader.onloadend = async () => {
          const base64Audio = reader.result.split(",")[1];
          const ep = (state.activeEndpoint || defaultLocalUrl).replace(/\/+$/, "");
          try {
            const res = await fetch(`${ep}/api/voice/transcribe`, {
              method: "POST",
              headers: { "Content-Type": "application/json", "Bypass-Tunnel-Reminder": "true" },
              body: JSON.stringify({ audio: base64Audio }),
            });
            const data = await res.json();
            if (data.text) {
              dom.cmdInput.value = data.text;
              logConsole("VOICE DETECTED", `"${data.text}"`);
              executeCommand(data.text);
            } else {
              logConsole("VOICE STATUS", "No speech detected in audio.");
            }
          } catch (err) {
            logConsole("VOICE ERROR", `Transcription failed: ${err.message}`);
          }
        };
        reader.readAsDataURL(blob);
      };

      fallbackRecorder.start();
      isFallbackRecording = true;
      state.isListening = true;
      state.audioWaveLevel = 0.9;
      dom.btnMic.classList.add("listening");
      logConsole("LISTENING (FALLBACK)", "Microphone active. Speak and tap mic again to send.");
      triggerHaptic(30);
    } catch (err) {
      console.warn("Fallback mic error:", err);
      logConsole("MIC ERROR", "Microphone access denied or unavailable.");
    }
  }

  function toggleSpeech() {
    if (!recognition) {
      toggleFallbackSpeech();
      return;
    }
    if (state.isListening) {
      recognition.stop();
    } else {
      try {
        recognition.start();
      } catch (err) {
        console.warn("Could not start recognition, using fallback:", err);
        toggleFallbackSpeech();
      }
    }
  }

  function toggleContinuousSpeech() {
    isContinuousMic = !isContinuousMic;
    localStorage.setItem("edith_mobile_continuous_mic", isContinuousMic ? "true" : "false");
    triggerHaptic(35);
    const btnCont = document.getElementById("btn-continuous-mic");
    if (btnCont) {
      btnCont.style.color = isContinuousMic ? "var(--cyan-glow)" : "var(--text-dim)";
      btnCont.style.borderColor = isContinuousMic ? "var(--cyan)" : "var(--border-color)";
      btnCont.style.boxShadow = isContinuousMic ? "0 0 10px rgba(0,229,255,0.4)" : "none";
    }
    if (isContinuousMic) {
      logConsole("ALWAYS-ON MIC", "Continuous microphone active. Speak anytime without tapping.");
      if (!state.isListening) toggleSpeech();
    } else {
      logConsole("TAP MIC", "Continuous mic deactivated. Tap-to-speak restored.");
      if (state.isListening && recognition) recognition.stop();
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
  let consecutiveOfflineFailures = 0;
  let hasSpokenInitialLink = false;

  async function pingEndpoint(url, timeoutMs = 3500) {
    if (!url) return { ok: false, ms: 0 };
    const cleanUrl = url.replace(/\/+$/, "");
    const controller = new AbortController();
    const isCloud = cleanUrl.includes("loca.lt") || cleanUrl.includes("trycloudflare.com") || cleanUrl.includes("pinggy");
    const actualTimeout = isCloud ? Math.max(timeoutMs, 5000) : timeoutMs;
    const timer = setTimeout(() => controller.abort(), actualTimeout);
    const t0 = performance.now();

    try {
      const resp = await fetch(`${cleanUrl}/ping?bypass-tunnel-reminder=true&t=${Date.now()}`, {
        method: "GET",
        signal: controller.signal,
        headers: {
          "Accept": "application/json",
          "Bypass-Tunnel-Reminder": "true",
        },
        cache: "no-store",
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
    const localAlt = local.includes(":8794")
      ? local.replace(":8794", ":8795")
      : (local.includes(":8795") ? local.replace(":8795", ":8794") : `${local}:8794`);

    // 1. Fast Heartbeat Check on Active Endpoint
    if (state.isOnline && state.activeEndpoint) {
      const heartRes = await pingEndpoint(state.activeEndpoint, 3500);
      if (heartRes.ok) {
        consecutiveOfflineFailures = 0;
        setConnectionState(state.activeType, state.activeEndpoint, heartRes.ms);
        return;
      }
    }

    // 2. Dual-Path Auto-Failover: Probe both LAN Wi-Fi and Global Cloud in parallel
    const [localRes1, localRes2, cloudRes] = await Promise.all([
      local ? pingEndpoint(local, 3000) : Promise.resolve({ ok: false, ms: 0 }),
      localAlt && localAlt !== local ? pingEndpoint(localAlt, 3000) : Promise.resolve({ ok: false, ms: 0 }),
      cloud ? pingEndpoint(cloud, 5000) : Promise.resolve({ ok: false, ms: 0 }),
    ]);

    if (localRes1.ok) {
      consecutiveOfflineFailures = 0;
      setConnectionState("LOCAL", local, localRes1.ms);
      return;
    }

    if (localRes2.ok) {
      consecutiveOfflineFailures = 0;
      state.localUrl = localAlt;
      localStorage.setItem(STORAGE_KEYS.LOCAL_URL, localAlt);
      setConnectionState("LOCAL", localAlt, localRes2.ms);
      return;
    }

    if (cloudRes.ok) {
      consecutiveOfflineFailures = 0;
      setConnectionState("CLOUD", cloud, cloudRes.ms);
      return;
    }

    // 3. Persistent Failure Handling: Require 6 consecutive failures (25+ seconds) before showing OFFLINE
    consecutiveOfflineFailures++;
    if (consecutiveOfflineFailures >= 6) {
      setConnectionState("OFFLINE", local || cloud, null, "Searching for EDITH mainframe...");
    }
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
      dom.statusText.textContent = `WI-FI LAN (${latency}ms)`;
      dom.consoleChannel.textContent = `CHANNEL: LOCAL WI-FI (OFFLINE LAN)`;
      dom.consolePing.textContent = `LATENCY: ${latency}ms`;
      if ((wasOffline || previousType !== "LOCAL") && !hasSpokenInitialLink) {
        hasSpokenInitialLink = true;
        logConsole("LINK ACCEPTED", `Connected to laptop via Local Wi-Fi (${latency}ms). Ready.`);
        triggerHaptic(40);
      }
    } else if (type === "CLOUD") {
      dom.statusDot.style.background = "#00e5ff";
      dom.statusDot.style.boxShadow = "0 0 10px #00e5ff";
      dom.statusText.textContent = `CLOUD (${latency}ms)`;
      dom.consoleChannel.textContent = `CHANNEL: GLOBAL CLOUD TUNNEL`;
      dom.consolePing.textContent = `LATENCY: ${latency}ms`;
      if ((wasOffline || previousType !== "CLOUD") && !hasSpokenInitialLink) {
        hasSpokenInitialLink = true;
        logConsole("LINK ACCEPTED", `Connected to laptop via Global Cloud Tunnel (${latency}ms). Ready.`);
        triggerHaptic(40);
      }
    } else {

      dom.statusDot.style.background = "#ff1744";
      dom.statusDot.style.boxShadow = "0 0 8px #ff1744";
      dom.statusText.textContent = "SEARCHING...";
      dom.consoleChannel.textContent = `CHANNEL: SCANNING`;
      dom.consolePing.textContent = `LATENCY: --ms`;
      if (dom.vitalsStatusTag) {
        dom.vitalsStatusTag.textContent = "OFFLINE";
        dom.vitalsStatusTag.classList.add("offline");
      }
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

      // Commands dispatched from phone to EDITH execute on the host laptop.
      // Do not auto-open on phone or force-dock media unless explicitly requested.
      if (data.opened_on_host) {
        // Confirmed executed on laptop host
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

  // ---------------- Tactical Command Guide Drawer ----------------
  const COMMAND_GUIDE_DATA = [
    // Media & Audio
    { cmd: "open youtube", label: "Open YouTube", desc: "Opens YouTube in host laptop browser", cat: "media", icon: "▶️" },
    { cmd: "play song on youtube", label: "Play Music", desc: "Searches & plays music on laptop browser", cat: "media", icon: "🎵" },
    { cmd: "play alan walker on youtube", label: "Play Alan Walker", desc: "Direct music playback on host", cat: "media", icon: "🎧" },
    { cmd: "pause media", label: "Pause Media", desc: "Windows play/pause media toggle", cat: "media", icon: "⏸️" },
    { cmd: "volume up", label: "Volume Up", desc: "Increase laptop master volume (+10%)", cat: "media", icon: "🔊" },
    { cmd: "volume down", label: "Volume Down", desc: "Decrease laptop master volume (-10%)", cat: "media", icon: "🔉" },
    { cmd: "mute volume", label: "Mute Audio", desc: "Mute host laptop master audio", cat: "media", icon: "🔇" },
    { cmd: "unmute volume", label: "Unmute Audio", desc: "Unmute host laptop audio", cat: "media", icon: "🔈" },

    // System Control
    { cmd: "system metrics", label: "System Metrics", desc: "Live CPU, RAM, and Disk telemetry", cat: "system", icon: "📊" },
    { cmd: "battery status", label: "Battery Status", desc: "Inspect laptop battery level and AC status", cat: "system", icon: "🔋" },
    { cmd: "take screenshot", label: "Capture Screen", desc: "Take Windows desktop screenshot", cat: "system", icon: "📸" },
    { cmd: "lock screen", label: "Lock Laptop", desc: "Instantly lock Windows workstation", cat: "system", icon: "🔒" },
    { cmd: "enable clap", label: "Enable Clap", desc: "Activate double-clap wake listener", cat: "system", icon: "👏" },
    { cmd: "disable clap", label: "Disable Clap", desc: "Deactivate double-clap listener", cat: "system", icon: "🛑" },
    { cmd: "undo", label: "Undo Action", desc: "Undo last file or system action", cat: "system", icon: "↩️" },
    { cmd: "open terminal", label: "Open Terminal", desc: "Launch PowerShell console on laptop", cat: "system", icon: "⚡" },

    // Applications
    { cmd: "open chrome", label: "Open Chrome", desc: "Launch Google Chrome browser", cat: "apps", icon: "🌐" },
    { cmd: "open brave", label: "Open Brave", desc: "Launch Brave privacy browser", cat: "apps", icon: "🦁" },
    { cmd: "open notepad", label: "Open Notepad", desc: "Launch Windows Notepad editor", cat: "apps", icon: "📝" },
    { cmd: "open calculator", label: "Calculator", desc: "Open Windows Calculator", cat: "apps", icon: "🧮" },
    { cmd: "open task manager", label: "Task Manager", desc: "Open Windows Task Manager", cat: "apps", icon: "📈" },
    { cmd: "open file explorer", label: "File Explorer", desc: "Open Windows File Explorer", cat: "apps", icon: "📁" },
    { cmd: "open settings", label: "Settings", desc: "Open Windows Settings panel", cat: "apps", icon: "⚙️" },

    // Workstation & Camera
    { cmd: "unlock pc", label: "Unlock PC", desc: "Unlock Windows desktop with configured PIN", cat: "system", icon: "🔓" },
    { cmd: "switch to camera mode", label: "Camera Mode", desc: "Focus or launch Windows camera application", cat: "apps", icon: "📷" },
    { cmd: "take picture", label: "Take Picture", desc: "Capture photo using host camera", cat: "apps", icon: "📸" },
    { cmd: "open picture", label: "Open Latest Photo", desc: "View the latest photo clicked by camera", cat: "apps", icon: "🖼️" },
    { cmd: "play video in same tab", label: "YouTube Same Tab", desc: "Play another video reusing the active tab", cat: "media", icon: "🔂" },

    // Security & Core
    { cmd: "emergency stop", label: "Emergency Stop", desc: "Halt all active autonomous tasks", cat: "security", icon: "🛑" },
    { cmd: "resume", label: "Resume System", desc: "Clear emergency halt and resume operations", cat: "security", icon: "▶️" },
    { cmd: "mode auto", label: "Auto Mode", desc: "Switch to hybrid local/cloud routing", cat: "security", icon: "🤖" },
    { cmd: "mode online", label: "Online Mode", desc: "Prioritize cloud models (Gemini Flash)", cat: "security", icon: "☁️" },
    { cmd: "mode offline", label: "Offline Mode", desc: "Force air-gapped local AI inference", cat: "security", icon: "🛡️" },
  ];

  let guideActiveCategory = "all";
  let guideSearchText = "";

  function openGuideModal() {
    if (!dom.modalGuide) return;
    triggerHaptic(20);
    dom.modalGuide.style.display = "flex";
    dom.modalGuide.classList.add("open");
    renderGuideCommands(guideActiveCategory, guideSearchText);
    if (dom.guideSearchInput) {
      setTimeout(() => dom.guideSearchInput.focus(), 100);
    }
  }

  function closeGuideModal() {
    if (!dom.modalGuide) return;
    dom.modalGuide.style.display = "none";
    dom.modalGuide.classList.remove("open");
  }

  function renderGuideCommands(category = "all", search = "") {
    if (!dom.guideCommandGrid) return;
    const cleanSearch = (search || "").trim().toLowerCase();
    const filtered = COMMAND_GUIDE_DATA.filter((item) => {
      const matchCat = category === "all" || item.cat === category;
      const matchSearch = !cleanSearch ||
        item.cmd.toLowerCase().includes(cleanSearch) ||
        item.label.toLowerCase().includes(cleanSearch) ||
        item.desc.toLowerCase().includes(cleanSearch);
      return matchCat && matchSearch;
    });

    if (filtered.length === 0) {
      dom.guideCommandGrid.innerHTML = `
        <div class="guide-no-results">
          No tactical commands match "${cleanSearch}".<br>
          <span style="font-size:0.7rem; color:var(--text-muted); margin-top:4px; display:inline-block;">Try 'youtube', 'volume', 'camera', or 'metrics'.</span>
        </div>`;
      return;
    }

    dom.guideCommandGrid.innerHTML = filtered.map((item) => {
      return `
        <div class="guide-cmd-card" data-cmd="${item.cmd}">
          <div class="guide-cmd-icon">${item.icon}</div>
          <div class="guide-cmd-info">
            <div class="guide-cmd-header">
              <span class="guide-cmd-label">${item.label}</span>
              <span class="guide-cmd-cat-badge">${item.cat}</span>
            </div>
            <div class="guide-cmd-code">&gt; ${item.cmd}</div>
            <div class="guide-cmd-desc">${item.desc}</div>
          </div>
          <button class="guide-cmd-run-btn" title="Execute command on host laptop">▶</button>
        </div>
      `;
    }).join("");

    dom.guideCommandGrid.querySelectorAll(".guide-cmd-card").forEach((card) => {
      card.addEventListener("click", () => {
        const cmd = card.getAttribute("data-cmd");
        if (!cmd) return;
        triggerHaptic(30);
        closeGuideModal();
        if (dom.cmdInput) dom.cmdInput.value = cmd;
        executeCommand(cmd);
      });
    });
  }

  // ---------------- Laptop Vitals Telemetry ----------------
  async function pollLaptopVitals() {
    if (!state.activeEndpoint || !state.isOnline) {
      if (dom.vitalsStatusTag) {
        dom.vitalsStatusTag.textContent = "OFFLINE";
        dom.vitalsStatusTag.classList.add("offline");
      }
      return;
    }

    const ep = state.activeEndpoint.replace(/\/+$/, "");
    try {
      const resp = await fetch(`${ep}/api/metrics`, {
        headers: { "Bypass-Tunnel-Reminder": "true" },
      });

      if (resp.ok) {
        const m = await resp.json();
        updateVitalsUI(m);
      } else {
        const sResp = await fetch(`${ep}/status`, {
          headers: { "Bypass-Tunnel-Reminder": "true" },
        });
        if (sResp.ok) {
          const s = await sResp.json();
          updateVitalsUI(s);
        }
      }
    } catch (_) {
      // Quiet fail on network jitter
    }
  }

  function updateVitalsUI(m) {
    if (!m) return;
    if (dom.vitalsStatusTag) {
      dom.vitalsStatusTag.textContent = state.activeType || "LINKED";
      dom.vitalsStatusTag.classList.remove("offline");
    }

    // CPU Percent
    if (dom.vitalCpuVal && m.cpu_percent !== undefined) {
      const cpu = Math.round(m.cpu_percent);
      dom.vitalCpuVal.textContent = `${cpu}%`;
      if (dom.vitalCpuBar) dom.vitalCpuBar.style.width = `${Math.min(100, Math.max(0, cpu))}%`;
    }

    // RAM Percent and Usage
    if (dom.vitalRamVal) {
      const ramPct = m.ram_percent !== undefined ? Math.round(m.ram_percent) : null;
      const usedGb = m.used_ram_gb !== undefined ? m.used_ram_gb : (m.ram_used_mb ? (m.ram_used_mb / 1024).toFixed(1) : null);
      if (ramPct !== null) {
        dom.vitalRamVal.textContent = usedGb ? `${usedGb} GB (${ramPct}%)` : `${ramPct}%`;
        if (dom.vitalRamBar) dom.vitalRamBar.style.width = `${Math.min(100, Math.max(0, ramPct))}%`;
      }
    }

    // Battery Percent and Charging Status
    if (dom.vitalBatVal && m.battery_percent !== undefined && m.battery_percent !== null) {
      const bat = Math.round(m.battery_percent);
      const plug = (m.power_plugged || m.is_ac_powered) ? " ⚡" : "";
      dom.vitalBatVal.textContent = `${bat}%${plug}`;
      if (dom.vitalBatBar) dom.vitalBatBar.style.width = `${Math.min(100, Math.max(0, bat))}%`;
    } else if (dom.vitalBatVal) {
      dom.vitalBatVal.textContent = "AC LINE ⚡";
      if (dom.vitalBatBar) dom.vitalBatBar.style.width = "100%";
    }

    // Disk Storage
    if (dom.vitalDiskVal) {
      if (m.disk_free_gb !== undefined) {
        dom.vitalDiskVal.textContent = `${Math.round(m.disk_free_gb)} GB FREE`;
        const diskPct = m.disk_percent !== undefined ? m.disk_percent : 45;
        if (dom.vitalDiskBar) dom.vitalDiskBar.style.width = `${Math.min(100, Math.max(0, diskPct))}%`;
      } else if (m.disk_percent !== undefined) {
        dom.vitalDiskVal.textContent = `${Math.round(m.disk_percent)}% USED`;
        if (dom.vitalDiskBar) dom.vitalDiskBar.style.width = `${Math.min(100, Math.max(0, m.disk_percent))}%`;
      }
    }
  }

  // ---------------- Connection & System Mode Switcher ----------------
  function updateModeButtonUI(mode) {
    const m = mode || state.mode || "auto";
    if (dom.btnModeToggle) {
      if (m === "local") {
        dom.btnModeToggle.textContent = "📶 WI-FI LAN";
        dom.btnModeToggle.className = "btn-mode-toggle mode-local";
        dom.btnModeToggle.title = "Connection: Local Wi-Fi (Tap to cycle)";
      } else if (m === "cloud") {
        dom.btnModeToggle.textContent = "🌐 CLOUD";
        dom.btnModeToggle.className = "btn-mode-toggle mode-cloud";
        dom.btnModeToggle.title = "Connection: Global Cloud (Tap to cycle)";
      } else {
        dom.btnModeToggle.textContent = "⚡ AUTO";
        dom.btnModeToggle.className = "btn-mode-toggle mode-auto";
        dom.btnModeToggle.title = "Connection: Smart Auto Probe (Tap to cycle)";
      }
    }
    if (dom.modeBtns) {
      dom.modeBtns.forEach((btn) => {
        if (btn.getAttribute("data-mode") === m) {
          btn.classList.add("active");
        } else {
          btn.classList.remove("active");
        }
      });
    }
  }

  async function toggleConnectionMode() {
    const modes = ["auto", "local", "cloud"];
    const current = state.mode || "auto";
    const nextIdx = (modes.indexOf(current) + 1) % modes.length;
    const targetMode = modes[nextIdx];
    state.mode = targetMode;
    localStorage.setItem(STORAGE_KEYS.MODE, targetMode);
    updateModeButtonUI(targetMode);
    triggerHaptic(25);
    const label = targetMode === "local" ? "LOCAL WI-FI (OFFLINE LAN)" : (targetMode === "cloud" ? "GLOBAL CLOUD TUNNEL" : "AUTO (SMART PROBE)");
    logConsole("LINK MODE", `Connection mode switched to ${label}. Linking...`);
    await resolveActiveEndpoint();
  }


  // ---------------- Canvas Visualizers ----------------
  // 1. Spider-Web Radar Background Canvas
  function initWebCanvas() {
    const canvas = dom.canvasWeb;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
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

      const pal = getActiveCanvasPalette();

      // Spider Web Spokes
      const spokes = 16;
      ctx.strokeStyle = `rgba(${pal.primary}, 0.12)`;
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
      ctx.strokeStyle = `rgba(${pal.primary}, 0.15)`;
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

      // Accent Cross Rings
      ctx.strokeStyle = `rgba(${pal.accent}, 0.22)`;
      ctx.beginPath();
      ctx.arc(cx, cy, 90, 0, Math.PI * 2);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(cx, cy, 180, 0, Math.PI * 2);
      ctx.stroke();

      // Animated Radar Scan Beam
      scanAngle += 0.015;
      ctx.strokeStyle = `rgba(${pal.primary}, 0.38)`;
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
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const w = (canvas.width = 220);
    const h = (canvas.height = 50);
    let phase = 0;

    function renderWave() {
      ctx.clearRect(0, 0, w, h);

      phase += 0.09;
      const amp = state.audioWaveLevel * 18 + 2;
      const midY = h / 2;
      const pal = getActiveCanvasPalette();

      ctx.beginPath();
      ctx.strokeStyle = state.isListening
        ? `rgba(${pal.primary}, 1)`
        : state.isExecuting
        ? `rgba(${pal.accent}, 1)`
        : `rgba(${pal.primary}, 0.85)`;
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
  let remoteZoom = 1.0;
  let remotePanX = 0;
  let remotePanY = 0;

  function updateZoomTransform() {
    remoteZoom = Math.max(1.0, Math.min(4.0, remoteZoom));
    if (remoteZoom === 1.0) {
      remotePanX = 0;
      remotePanY = 0;
    }
    const transformStr = `translate(${remotePanX}px, ${remotePanY}px) scale(${remoteZoom})`;
    if (dom.vncCanvas) {
      dom.vncCanvas.style.transform = transformStr;
    }
    if (dom.remoteScreenImg) {
      dom.remoteScreenImg.style.transform = transformStr;
    }
    const zoomText = `${Math.round(remoteZoom * 100)}%`;
    if (dom.remoteZoomTag) {
      dom.remoteZoomTag.textContent = zoomText;
    }
    if (dom.lblMzoomVal) {
      dom.lblMzoomVal.textContent = zoomText;
    }
  }

  async function fetchStreamLoop() {
    if (!remoteStreamActive || (!dom.remoteScreenImg && !dom.vncCanvas)) return;
    if (isFetchingFrame) return;
    isFetchingFrame = true;

    const ep = (state.activeEndpoint || defaultLocalUrl).replace(/\/+$/, "");
    const scale = remoteResolution === "1080p" ? 1280 : 960;
    const quality = remoteResolution === "1080p" ? 65 : 55;
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
    let ep = (state.activeEndpoint || defaultLocalUrl).replace(/\/+$/, "");
    if (isCloudOrigin || window.location.protocol === "https:") {
      ep = window.location.origin.replace(/\/+$/, "");
    }
    const payload = JSON.stringify({
      action,
      params,
      x: params.x,
      y: params.y,
      button: params.button || "left",
      token: state.token || undefined,
      device_id: "edith_mobile_pwa",
    });
    const headers = {
      "Content-Type": "application/json",
      "Bypass-Tunnel-Reminder": "true",
      "bypass-tunnel-reminder": "true",
      "X-Token": state.token || "",
    };

    try {
      const resp = await fetch(`${ep}/api/remote/input`, {
        method: "POST",
        headers,
        body: payload,
      });
      if (resp.ok) {
        return await resp.json();
      }
    } catch (_) {
      // If primary endpoint failed and cloud tunnel is available, try cloud tunnel
      if (state.cloudUrl && ep !== state.cloudUrl) {
        try {
          const cResp = await fetch(`${state.cloudUrl.replace(/\/+$/, "")}/api/remote/input`, {
            method: "POST",
            headers,
            body: payload,
          });
          if (cResp.ok) return await cResp.json();
        } catch (_) {}
      }
    }
    return { success: false, action };
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
    if (!remoteStreamActive) return;
    updateResolutionButtonUI();
    if (dom.remoteFpsTag) {
      dom.remoteFpsTag.textContent = `90 FPS // ${remoteResolution.toUpperCase()}`;
      dom.remoteFpsTag.style.color = "#00e676";
    }
    if (dom.remoteScreenImg) dom.remoteScreenImg.style.display = "none";
    if (dom.vncCanvas) dom.vncCanvas.style.display = "block";
    updateZoomTransform();
    isFetchingFrame = false;
    requestAnimationFrame(fetchStreamLoop);
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

  // Touch Viewport Mouse Gestures & Zoom
  function initRemoteViewportEvents() {
    if (!dom.remoteViewport) return;

    let touchStartTime = 0;
    let touchStartX = 0;
    let touchStartY = 0;
    let lastTapTime = 0;
    let isLongPress = false;
    let longPressTimer = null;
    let twoFingerStartY = 0;

    let pinchStartDist = 0;
    let pinchStartZoom = 1.0;
    let pinchStartMidX = 0;
    let pinchStartMidY = 0;
    let pinchStartPanX = 0;
    let pinchStartPanY = 0;
    let isPinching = false;

    function getNormalizedCoords(clientX, clientY) {
      const el = (dom.vncCanvas && dom.vncCanvas.style.display !== "none" && dom.vncCanvas.offsetWidth > 0)
        ? dom.vncCanvas
        : (dom.remoteScreenImg && dom.remoteScreenImg.style.display !== "none" && dom.remoteScreenImg.offsetWidth > 0 ? dom.remoteScreenImg : dom.remoteViewport);
      if (!el) return { x: 0.5, y: 0.5 };
      const rect = el.getBoundingClientRect();
      if (!rect || rect.width <= 1 || rect.height <= 1) return { x: 0.5, y: 0.5 };

      // Compute actual rendered screen aspect ratio (default 16:9 laptop display)
      let naturalW = (el.naturalWidth && el.naturalWidth > 100) ? el.naturalWidth : 1920;
      let naturalH = (el.naturalHeight && el.naturalHeight > 100) ? el.naturalHeight : 1080;
      const targetRatio = naturalW / naturalH;
      const containerRatio = rect.width / rect.height;

      let renderedW = rect.width;
      let renderedH = rect.height;
      let padX = 0;
      let padY = 0;

      if (containerRatio > targetRatio) {
        // Pillarbox: horizontal bars on left and right
        renderedW = rect.height * targetRatio;
        padX = (rect.width - renderedW) / 2;
      } else {
        // Letterbox: vertical bars on top and bottom
        renderedH = rect.width / targetRatio;
        padY = (rect.height - renderedH) / 2;
      }

      const relX = clientX - rect.left - padX;
      const relY = clientY - rect.top - padY;

      const normX = Math.max(0.0, Math.min(1.0, relX / Math.max(1, renderedW)));
      const normY = Math.max(0.0, Math.min(1.0, relY / Math.max(1, renderedH)));
      return { x: normX, y: normY };
    }

    let pendingMobileMove = null;
    let mobileMoveThrottle = null;
    function queueMobileMouseMove(coords) {
      pendingMobileMove = coords;
      if (!mobileMoveThrottle) {
        mobileMoveThrottle = setTimeout(() => {
          mobileMoveThrottle = null;
          if (pendingMobileMove) {
            sendRemoteInput("mouse_move", pendingMobileMove);
            pendingMobileMove = null;
          }
        }, 15);
      }
    }

    function showRipple(clientX, clientY) {
      if (!dom.remoteFeedback || !dom.remoteViewport) return;
      const vpRect = dom.remoteViewport.getBoundingClientRect();
      dom.remoteFeedback.style.left = `${clientX - vpRect.left}px`;
      dom.remoteFeedback.style.top = `${clientY - vpRect.top}px`;
      dom.remoteFeedback.classList.remove("ripple");
      void dom.remoteFeedback.offsetWidth;
      dom.remoteFeedback.classList.add("ripple");
    }

    function updateVirtualCursor(clientX, clientY) {
      if (!dom.remoteCursor || !dom.remoteViewport) return;
      const vpRect = dom.remoteViewport.getBoundingClientRect();
      dom.remoteCursor.style.display = "block";
      dom.remoteCursor.style.left = `${clientX - vpRect.left}px`;
      dom.remoteCursor.style.top = `${clientY - vpRect.top}px`;
    }

    dom.remoteViewport.addEventListener("touchstart", (e) => {
      if (remoteGamepadMode || e.target.closest("#virtual-gamepad-overlay") || e.target.closest(".remote-bottom-bar") || e.target.closest("#mobile-zoom-overlay")) {
        return;
      }
      e.preventDefault();

      if (e.touches.length === 1) {
        isPinching = false;
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
        const t1 = e.touches[0];
        const t2 = e.touches[1];
        pinchStartDist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
        pinchStartZoom = remoteZoom;
        pinchStartMidX = (t1.clientX + t2.clientX) / 2;
        pinchStartMidY = (t1.clientY + t2.clientY) / 2;
        pinchStartPanX = remotePanX;
        pinchStartPanY = remotePanY;
        isPinching = true;
        twoFingerStartY = pinchStartMidY;
      }
    }, { passive: false });

    dom.remoteViewport.addEventListener("touchmove", (e) => {
      if (remoteGamepadMode || e.target.closest("#virtual-gamepad-overlay") || e.target.closest(".remote-bottom-bar") || e.target.closest("#mobile-zoom-overlay")) {
        return;
      }
      e.preventDefault();

      if (e.touches.length === 1 && !isPinching) {
        const t = e.touches[0];
        const dist = Math.hypot(t.clientX - touchStartX, t.clientY - touchStartY);
        if (dist > 10) {
          clearTimeout(longPressTimer);
        }

        const coords = getNormalizedCoords(t.clientX, t.clientY);
        updateVirtualCursor(t.clientX, t.clientY);
        queueMobileMouseMove(coords);
      } else if (e.touches.length === 2 && isPinching) {
        clearTimeout(longPressTimer);
        const t1 = e.touches[0];
        const t2 = e.touches[1];
        const currentDist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
        const currentMidX = (t1.clientX + t2.clientX) / 2;
        const currentMidY = (t1.clientY + t2.clientY) / 2;

        if (Math.abs(currentDist - pinchStartDist) > 12) {
          const scaleChange = currentDist / Math.max(1, pinchStartDist);
          remoteZoom = Math.max(1.0, Math.min(4.0, pinchStartZoom * scaleChange));
          remotePanX = pinchStartPanX + (currentMidX - pinchStartMidX);
          remotePanY = pinchStartPanY + (currentMidY - pinchStartMidY);
          updateZoomTransform();
        } else if (remoteZoom === 1.0) {
          const delta = currentMidY - twoFingerStartY;
          if (Math.abs(delta) > 15) {
            sendRemoteInput("scroll", { delta: delta > 0 ? 2 : -2 });
            twoFingerStartY = currentMidY;
          }
        } else {
          remotePanX = pinchStartPanX + (currentMidX - pinchStartMidX);
          remotePanY = pinchStartPanY + (currentMidY - pinchStartMidY);
          updateZoomTransform();
        }
      }
    }, { passive: false });

    dom.remoteViewport.addEventListener("touchend", (e) => {
      clearTimeout(longPressTimer);
      if (e.touches.length < 2) {
        isPinching = false;
      }
      if (remoteGamepadMode || e.target.closest("#virtual-gamepad-overlay") || e.target.closest(".remote-bottom-bar") || e.target.closest("#mobile-zoom-overlay")) {
        return;
      }

      const elapsed = Date.now() - touchStartTime;
      if (!isLongPress && elapsed < 500 && e.changedTouches.length === 1) {
        const t = e.changedTouches[0];
        const dist = Math.hypot(t.clientX - touchStartX, t.clientY - touchStartY);
        if (dist < 30) {
          const coords = getNormalizedCoords(t.clientX, t.clientY);
          showRipple(t.clientX, t.clientY);

          const now = Date.now();
          const tapInterval = now - lastTapTime;
          if (tapInterval < 320) {
            // Double tap zoom
            lastTapTime = 0;
            if (remoteZoom > 1.2) {
              remoteZoom = 1.0;
              remotePanX = 0;
              remotePanY = 0;
              updateZoomTransform();
              triggerHaptic(20);
            } else {
              remoteZoom = 2.0;
              const el = (dom.vncCanvas && dom.vncCanvas.style.display !== "none" && dom.vncCanvas.offsetWidth > 0)
                ? dom.vncCanvas
                : (dom.remoteScreenImg || dom.remoteViewport);
              const rect = el.getBoundingClientRect();
              remotePanX = Math.round((rect.width / 2) - (t.clientX - rect.left));
              remotePanY = Math.round((rect.height / 2) - (t.clientY - rect.top));
              updateZoomTransform();
              triggerHaptic(25);
            }
          } else {
            sendRemoteInput("click", coords);
            lastTapTime = now;
          }
        }
      }
    });

    dom.remoteViewport.addEventListener("click", (e) => {
      if (remoteGamepadMode || e.target.closest("#virtual-gamepad-overlay") || e.target.closest(".remote-bottom-bar") || e.target.closest("#mobile-zoom-overlay")) {
        return;
      }
      if ("ontouchstart" in window && touchStartTime && (Date.now() - touchStartTime < 600)) {
        return; // Avoid duplicate dispatch on touch devices
      }
      const coords = getNormalizedCoords(e.clientX, e.clientY);
      showRipple(e.clientX, e.clientY);
      sendRemoteInput("click", coords);
    });

    if (dom.btnMzoomIn) {
      dom.btnMzoomIn.addEventListener("click", (e) => {
        e.stopPropagation();
        remoteZoom = Math.min(4.0, remoteZoom + 0.35);
        updateZoomTransform();
        triggerHaptic(15);
      });
    }
    if (dom.btnMzoomOut) {
      dom.btnMzoomOut.addEventListener("click", (e) => {
        e.stopPropagation();
        remoteZoom = Math.max(1.0, remoteZoom - 0.35);
        if (remoteZoom === 1.0) { remotePanX = 0; remotePanY = 0; }
        updateZoomTransform();
        triggerHaptic(15);
      });
    }
    if (dom.btnMzoomFit) {
      dom.btnMzoomFit.addEventListener("click", (e) => {
        e.stopPropagation();
        remoteZoom = 1.0;
        remotePanX = 0;
        remotePanY = 0;
        updateZoomTransform();
        triggerHaptic(20);
      });
    }

    if (dom.btnRemoteZoomIn) {
      dom.btnRemoteZoomIn.addEventListener("click", () => {
        remoteZoom = Math.min(4.0, remoteZoom + 0.25);
        updateZoomTransform();
        triggerHaptic(15);
      });
    }
    if (dom.btnRemoteZoomOut) {
      dom.btnRemoteZoomOut.addEventListener("click", () => {
        remoteZoom = Math.max(1.0, remoteZoom - 0.25);
        updateZoomTransform();
        triggerHaptic(15);
      });
    }
    if (dom.btnRemoteZoomFit) {
      dom.btnRemoteZoomFit.addEventListener("click", () => {
        remoteZoom = 1.0;
        remotePanX = 0;
        remotePanY = 0;
        updateZoomTransform();
        triggerHaptic(15);
      });
    }
    if (dom.btnRemoteUnlock) {
      dom.btnRemoteUnlock.addEventListener("click", () => {
        triggerHaptic(30);
        sendRemoteInput("unlock");
        logConsole("AUTH", "Unlock PIN sent to host workstation.");
      });
    }

    if (dom.remoteBottomBar) {
      dom.remoteBottomBar.querySelectorAll(".remote-gesture-chip").forEach((chip) => {
        chip.addEventListener("click", () => {
          const action = chip.getAttribute("data-action");
          triggerHaptic(15);
          if (action === "unlock") {
            sendRemoteInput("unlock");
            logConsole("AUTH", "Workstation unlock PIN dispatched.");
          } else if (action === "scroll_up") {
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
    let joystickInFlight = false;
    let lastStickDispatch = 0;
    let currentDirection = "";

    function getDirection(normX, normY, deadzone = 0.22) {
      const mag = Math.hypot(normX, normY);
      if (mag < deadzone) return "neutral";
      let d = "";
      if (normY < -deadzone) d += "U";
      else if (normY > deadzone) d += "D";
      if (normX < -deadzone) d += "L";
      else if (normX > deadzone) d += "R";
      return d;
    }

    let pendingJoystick = null;

    async function dispatchJoystick(normX, normY) {
      if (joystickInFlight) {
        pendingJoystick = { x: normX, y: normY };
        return;
      }
      joystickInFlight = true;
      try {
        await sendRemoteInput("joystick", { x: normX, y: normY });
      } finally {
        joystickInFlight = false;
        if (pendingJoystick) {
          const next = pendingJoystick;
          pendingJoystick = null;
          dispatchJoystick(next.x, next.y);
        }
      }
    }

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
      const dir = getDirection(normX, normY);
      const now = performance.now();

      if (dir !== currentDirection || (now - lastStickDispatch > 50)) {
        currentDirection = dir;
        lastStickDispatch = now;
        joystickActive = true;
        dispatchJoystick(normX, normY);
      }
    }

    function resetStick() {
      activePointerId = null;
      pendingJoystick = null;
      currentDirection = "neutral";
      dom.stickNub.style.transform = "translate(-50%, -50%)";
      joystickActive = false;
      sendRemoteInput("joystick_release");
      setTimeout(() => sendRemoteInput("joystick_release"), 60);
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

  // ---------------- AirDrop & Clipboard Sync ----------------
  function openAirDropModal() {
    if (dom.modalAirDrop) {
      dom.modalAirDrop.style.display = "flex";
      fetchClipboardFromPC();
      fetchAirDropFiles();
      triggerHaptic(20);
    }
  }

  function closeAirDropModal() {
    if (dom.modalAirDrop) dom.modalAirDrop.style.display = "none";
  }

  async function fetchClipboardFromPC() {
    if (!state.activeEndpoint) return;
    try {
      const ep = state.activeEndpoint.replace(/\/+$/, "");
      const res = await fetch(`${ep}/api/clipboard`, {
        headers: { "Bypass-Tunnel-Reminder": "true" }
      });
      if (res.ok) {
        const data = await res.json();
        const text = data.clipboard || data.text || "";
        if (dom.airdropClipboardText) dom.airdropClipboardText.value = text;
        logConsole("CLIPBOARD", `Pulled ${text.length} chars from laptop`);
      }
    } catch (e) {
      logConsole("CLIPBOARD", `Failed to read laptop clipboard: ${e.message}`);
    }
  }

  async function pushClipboardToPC() {
    if (!state.activeEndpoint) return;
    const text = dom.airdropClipboardText ? dom.airdropClipboardText.value : "";
    try {
      const ep = state.activeEndpoint.replace(/\/+$/, "");
      const res = await fetch(`${ep}/api/clipboard`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Bypass-Tunnel-Reminder": "true" },
        body: JSON.stringify({ text, source: "mobile_airdrop" })
      });
      if (res.ok) {
        triggerHaptic(30);
        logConsole("CLIPBOARD", "Pasted text to laptop clipboard!");
        speakResponse("Clipboard synchronized to laptop.");
      }
    } catch (e) {
      logConsole("CLIPBOARD", `Paste error: ${e.message}`);
    }
  }

  async function fetchAirDropFiles() {
    if (!state.activeEndpoint || !dom.airdropFilesList) return;
    try {
      const ep = state.activeEndpoint.replace(/\/+$/, "");
      const res = await fetch(`${ep}/api/airdrop/files`, {
        headers: { "Bypass-Tunnel-Reminder": "true" }
      });
      if (res.ok) {
        const data = await res.json();
        const files = data.files || [];
        if (dom.airdropFileCount) dom.airdropFileCount.textContent = files.length;
        if (files.length === 0) {
          dom.airdropFilesList.innerHTML = `<div style="color:var(--text-dim);text-align:center;padding:8px;">No transfers yet.</div>`;
          return;
        }
        dom.airdropFilesList.innerHTML = files.map(f => {
          const sz = (f.size_bytes / 1024).toFixed(1) + " KB";
          const dlUrl = `${ep}${f.download_url}`;
          return `
            <div style="display:flex;justify-content:space-between;align-items:center;padding:6px;border-bottom:1px solid rgba(255,255,255,0.06);">
              <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:170px;" title="${f.filename}">📄 ${f.filename} (${sz})</span>
              <a href="${dlUrl}" target="_blank" download style="color:var(--cyan);text-decoration:none;font-weight:bold;padding:2px 8px;border:1px solid var(--cyan);border-radius:4px;font-size:11px;">GET ⬇</a>
            </div>
          `;
        }).join("");
      }
    } catch (e) {
      console.warn("AirDrop files fetch notice:", e);
    }
  }

  async function uploadAirDropFile(file) {
    if (!state.activeEndpoint || !file) return;
    if (dom.airdropUploadStatus) dom.airdropUploadStatus.textContent = `Uploading ${file.name}...`;
    try {
      const reader = new FileReader();
      reader.onload = async (evt) => {
        const b64 = evt.target.result.split(",")[1];
        const ep = state.activeEndpoint.replace(/\/+$/, "");
        const res = await fetch(`${ep}/api/airdrop/upload`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Bypass-Tunnel-Reminder": "true" },
          body: JSON.stringify({ filename: file.name, base64: b64 })
        });
        if (res.ok) {
          triggerHaptic(40);
          if (dom.airdropUploadStatus) dom.airdropUploadStatus.textContent = `Uploaded ${file.name} successfully!`;
          speakResponse(`AirDrop transfer complete: ${file.name}`);
          fetchAirDropFiles();
        } else {
          if (dom.airdropUploadStatus) dom.airdropUploadStatus.textContent = "Upload failed.";
        }
      };
      reader.readAsDataURL(file);
    } catch (e) {
      if (dom.airdropUploadStatus) dom.airdropUploadStatus.textContent = `Upload error: ${e.message}`;
    }
  }

  // ---------------- Audio Mixer & Media Controls ----------------
  function openAudioMixerModal() {
    if (dom.modalMixer) {
      dom.modalMixer.style.display = "flex";
      fetchAudioMixerStatus();
      triggerHaptic(20);
    }
  }

  function closeAudioMixerModal() {
    if (dom.modalMixer) dom.modalMixer.style.display = "none";
  }

  async function fetchAudioMixerStatus() {
    if (!state.activeEndpoint) return;
    try {
      const ep = state.activeEndpoint.replace(/\/+$/, "");
      const res = await fetch(`${ep}/api/audio/status`, {
        headers: { "Bypass-Tunnel-Reminder": "true" }
      });
      if (res.ok) {
        const data = await res.json();
        const master = data.master || {};
        const apps = data.apps || [];
        if (dom.mixerMasterSlider && master.volume !== undefined) {
          dom.mixerMasterSlider.value = master.volume;
        }
        if (dom.mixerMasterVal && master.volume !== undefined) {
          dom.mixerMasterVal.textContent = `${master.volume}%`;
        }
        if (dom.btnMixerMute) {
          dom.btnMixerMute.textContent = master.muted ? "Unmute" : "Mute";
          dom.btnMixerMute.style.borderColor = master.muted ? "#ff1744" : "var(--cyan)";
        }
        renderMixerAppStreams(apps);
      }
    } catch (e) {
      console.warn("Mixer status fetch error:", e);
    }
  }

  function renderMixerAppStreams(apps) {
    if (!dom.mixerAppStreams) return;
    if (!apps || apps.length === 0) {
      dom.mixerAppStreams.innerHTML = `<div style="color:var(--text-dim);text-align:center;padding:12px;">No running sound apps detected.</div>`;
      return;
    }
    dom.mixerAppStreams.innerHTML = apps.map(app => {
      return `
        <div style="background:var(--bg-card);border:1px solid var(--border-glass);border-radius:8px;padding:8px;display:flex;flex-direction:column;gap:6px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-weight:bold;font-size:12px;color:var(--text-main);">🔊 ${app.process_name}</span>
            <span id="app-vol-label-${app.pid}" style="color:var(--cyan);font-size:11px;">${app.volume}%</span>
          </div>
          <div style="display:flex;gap:8px;align-items:center;">
            <input type="range" min="0" max="100" value="${app.volume}" style="flex:1;accent-color:var(--cyan);"
              oninput="document.getElementById('app-vol-label-${app.pid}').textContent = this.value + '%'"
              onchange="window._setAppVolume('${app.process_name}', this.value)">
            <button class="btn-secondary" style="padding:4px 8px;font-size:11px;${app.muted ? 'border-color:#ff1744;color:#ff1744;' : ''}"
              onclick="window._toggleAppMute('${app.process_name}', ${!app.muted})">${app.muted ? 'Unmute' : 'Mute'}</button>
          </div>
        </div>
      `;
    }).join("");
  }

  window._setAppVolume = async (appName, volume) => {
    if (!state.activeEndpoint) return;
    try {
      const ep = state.activeEndpoint.replace(/\/+$/, "");
      await fetch(`${ep}/api/audio/app`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Bypass-Tunnel-Reminder": "true" },
        body: JSON.stringify({ app: appName, volume: parseInt(volume) })
      });
    } catch (_) {}
  };

  window._toggleAppMute = async (appName, muted) => {
    if (!state.activeEndpoint) return;
    try {
      const ep = state.activeEndpoint.replace(/\/+$/, "");
      await fetch(`${ep}/api/audio/app`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Bypass-Tunnel-Reminder": "true" },
        body: JSON.stringify({ app: appName, muted })
      });
      fetchAudioMixerStatus();
    } catch (_) {}
  };

  async function sendMediaControl(action) {
    if (!state.activeEndpoint) return;
    triggerHaptic(20);
    try {
      const ep = state.activeEndpoint.replace(/\/+$/, "");
      await fetch(`${ep}/api/audio/media`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Bypass-Tunnel-Reminder": "true" },
        body: JSON.stringify({ action })
      });
      logConsole("MEDIA", `Dispatched media key: ${action}`);
    } catch (e) {
      logConsole("MEDIA", `Media action error: ${e.message}`);
    }
  }

  async function toggleFaceSentinel() {
    if (!state.activeEndpoint) return;
    triggerHaptic(30);
    try {
      const ep = state.activeEndpoint.replace(/\/+$/, "");
      const sRes = await fetch(`${ep}/api/sentinel/status`, {
        headers: { "Bypass-Tunnel-Reminder": "true" }
      });
      let active = false;
      if (sRes.ok) {
        const sData = await sRes.json();
        active = !sData.active;
      } else {
        active = true;
      }
      const tRes = await fetch(`${ep}/api/sentinel/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Bypass-Tunnel-Reminder": "true" },
        body: JSON.stringify({ enabled: active, timeout: 30.0 })
      });
      if (tRes.ok) {
        const msg = active ? "Biometric face sentinel activated. Workstation will auto-lock if you leave." : "Biometric face sentinel deactivated.";
        logConsole("SENTINEL", msg);
        speakResponse(msg);
        if (dom.btnToggleSentinel) {
          dom.btnToggleSentinel.style.borderColor = active ? "var(--cyan)" : "";
          dom.btnToggleSentinel.style.color = active ? "var(--cyan)" : "";
        }
      }
    } catch (e) {
      logConsole("SENTINEL", `Sentinel toggle error: ${e.message}`);
    }
  }

  // ---------------- Settings & UI Event Listeners ----------------
  function initEvents() {
    // AirDrop & Clipboard Modal
    if (dom.btnOpenAirDrop) dom.btnOpenAirDrop.addEventListener("click", openAirDropModal);
    if (dom.btnCloseAirDrop) dom.btnCloseAirDrop.addEventListener("click", closeAirDropModal);
    if (dom.modalAirDrop) {
      dom.modalAirDrop.addEventListener("click", (e) => {
        if (e.target === dom.modalAirDrop) closeAirDropModal();
      });
    }
    if (dom.btnClipPull) dom.btnClipPull.addEventListener("click", fetchClipboardFromPC);
    if (dom.btnClipPush) dom.btnClipPush.addEventListener("click", pushClipboardToPC);
    if (dom.btnSelectFile) {
      dom.btnSelectFile.addEventListener("click", () => {
        if (dom.airdropFileInput) dom.airdropFileInput.click();
      });
    }
    if (dom.airdropFileInput) {
      dom.airdropFileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
          uploadAirDropFile(e.target.files[0]);
        }
      });
    }

    // Audio Mixer & Media Controls
    if (dom.btnOpenMixer) dom.btnOpenMixer.addEventListener("click", openAudioMixerModal);
    if (dom.btnCloseMixer) dom.btnCloseMixer.addEventListener("click", closeAudioMixerModal);
    if (dom.modalMixer) {
      dom.modalMixer.addEventListener("click", (e) => {
        if (e.target === dom.modalMixer) closeAudioMixerModal();
      });
    }
    if (dom.mixerMasterSlider) {
      dom.mixerMasterSlider.addEventListener("input", (e) => {
        if (dom.mixerMasterVal) dom.mixerMasterVal.textContent = `${e.target.value}%`;
      });
      dom.mixerMasterSlider.addEventListener("change", async (e) => {
        if (!state.activeEndpoint) return;
        try {
          const ep = state.activeEndpoint.replace(/\/+$/, "");
          await fetch(`${ep}/api/audio/master`, {
            method: "POST",
            headers: { "Content-Type": "application/json", "Bypass-Tunnel-Reminder": "true" },
            body: JSON.stringify({ volume: parseInt(e.target.value) })
          });
        } catch (_) {}
      });
    }
    if (dom.btnMixerMute) {
      dom.btnMixerMute.addEventListener("click", async () => {
        if (!state.activeEndpoint) return;
        try {
          const ep = state.activeEndpoint.replace(/\/+$/, "");
          await fetch(`${ep}/api/audio/master`, {
            method: "POST",
            headers: { "Content-Type": "application/json", "Bypass-Tunnel-Reminder": "true" },
            body: JSON.stringify({ muted: dom.btnMixerMute.textContent === "Mute" })
          });
          fetchAudioMixerStatus();
        } catch (_) {}
      });
    }
    if (dom.btnMediaPrev) dom.btnMediaPrev.addEventListener("click", () => sendMediaControl("prev"));
    if (dom.btnMediaPlayPause) dom.btnMediaPlayPause.addEventListener("click", () => sendMediaControl("play_pause"));
    if (dom.btnMediaNext) dom.btnMediaNext.addEventListener("click", () => sendMediaControl("next"));
    if (dom.btnMediaStop) dom.btnMediaStop.addEventListener("click", () => sendMediaControl("stop"));
    if (dom.btnRefreshMixer) dom.btnRefreshMixer.addEventListener("click", fetchAudioMixerStatus);

    // Biometric Face Sentinel
    if (dom.btnToggleSentinel) dom.btnToggleSentinel.addEventListener("click", toggleFaceSentinel);

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

    // Voice Mode & TTS Toggles
    if (dom.btnTts) {
      dom.btnTts.addEventListener("click", toggleVoiceMode);
    }
    if (dom.btnVoiceMode) {
      dom.btnVoiceMode.addEventListener("click", toggleVoiceMode);
    }
    if (dom.voicePills) {
      dom.voicePills.forEach((pill) => {
        pill.addEventListener("click", () => {
          const charId = pill.getAttribute("data-char");
          if (charId) {
            triggerHaptic(20);
            setMobileVoiceCharacter(charId, true);
          }
        });
      });
    }


    // Settings Modal Open/Close
    if (dom.btnBrandTheme) {
      dom.btnBrandTheme.addEventListener("click", () => {
        triggerHaptic(20);
        const THEME_CYCLE = ["edith", "jarvis", "friday", "karen", "ultron", "spiderman"];
        const cur = localStorage.getItem("mobile_theme") || "edith";
        const curIdx = THEME_CYCLE.indexOf(cur);
        const next = THEME_CYCLE[(curIdx + 1) % THEME_CYCLE.length];
        setMobileTheme(next, true);
        logConsole("THEME", `Switched HUD theme to ${next.toUpperCase()}`);
      });
    }

    dom.statusBadge.addEventListener("click", openSettings);
    dom.btnOpenSettings.addEventListener("click", openSettings);
    dom.btnCloseSettings.addEventListener("click", closeSettings);

    dom.modalSettings.addEventListener("click", (e) => {
      if (e.target === dom.modalSettings) closeSettings();
    });

    // Command Guide Drawer & Modal
    if (dom.btnOpenGuide) dom.btnOpenGuide.addEventListener("click", openGuideModal);
    if (dom.btnChipGuide) dom.btnChipGuide.addEventListener("click", openGuideModal);
    if (dom.btnCloseGuide) dom.btnCloseGuide.addEventListener("click", closeGuideModal);
    if (dom.modalGuide) {
      dom.modalGuide.addEventListener("click", (e) => {
        if (e.target === dom.modalGuide) closeGuideModal();
      });
    }

    if (dom.guideSearchInput) {
      dom.guideSearchInput.addEventListener("input", (e) => {
        guideSearchText = e.target.value;
        if (dom.btnGuideClear) {
          dom.btnGuideClear.style.display = guideSearchText ? "block" : "none";
        }
        renderGuideCommands(guideActiveCategory, guideSearchText);
      });
    }

    if (dom.btnGuideClear) {
      dom.btnGuideClear.addEventListener("click", () => {
        guideSearchText = "";
        if (dom.guideSearchInput) dom.guideSearchInput.value = "";
        dom.btnGuideClear.style.display = "none";
        renderGuideCommands(guideActiveCategory, "");
      });
    }

    if (dom.guideCategoryPills) {
      const pills = dom.guideCategoryPills.querySelectorAll(".guide-pill");
      pills.forEach((pill) => {
        pill.addEventListener("click", () => {
          pills.forEach((p) => p.classList.remove("active"));
          pill.classList.add("active");
          guideActiveCategory = pill.getAttribute("data-category") || "all";
          renderGuideCommands(guideActiveCategory, guideSearchText);
          triggerHaptic(15);
        });
      });
    }

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

      if (dom.cfgTheme) setMobileTheme(dom.cfgTheme.value);
      if (dom.cfgVoiceChar) setMobileVoiceCharacter(dom.cfgVoiceChar.value);

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

    // Header Connection Mode Toggle
    if (dom.btnModeToggle) {
      dom.btnModeToggle.addEventListener("click", toggleConnectionMode);
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
        const q = new URLSearchParams({
          token: state.token || "",
          device_id: "edith_mobile_pwa",
        });
        window.open(`${ep}/vnc?${q.toString()}`, "_blank");
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
      triggerHaptic(30);
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
    if (dom.cfgTheme) dom.cfgTheme.value = localStorage.getItem("mobile_theme") || "spiderman";
    if (dom.cfgVoiceChar) dom.cfgVoiceChar.value = activeMobileVoiceChar;

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
    // 0. Use window.__EDITH_CONFIG__ if provided synchronously
    if (window.__EDITH_CONFIG__) {
      try {
        const bcfg = window.__EDITH_CONFIG__;
        if (bcfg.cloud_url && (!state.cloudUrl || state.cloudUrl.includes("edith-jashu.loca.lt"))) {
          state.cloudUrl = bcfg.cloud_url;
          localStorage.setItem(STORAGE_KEYS.CLOUD_URL, state.cloudUrl);
          if (dom.cfgCloudUrl) dom.cfgCloudUrl.value = state.cloudUrl;
        }
        if (bcfg.local_url && (!state.localUrl || state.localUrl.includes("127.0.0.1"))) {
          state.localUrl = bcfg.local_url;
          localStorage.setItem(STORAGE_KEYS.LOCAL_URL, state.localUrl);
          if (dom.cfgLocalUrl) dom.cfgLocalUrl.value = state.localUrl;
        }
      } catch (_) {}
    }

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
    // Window bridge for inline HTML onclick handlers
    let remoteZoomVal = 1.0;
    window.setMobileTheme = (theme) => setMobileTheme(theme, true);
    window.sendMobileCommand = (cmd) => executeCommand(cmd);
    window.submitMobileInput = () => {
      if (dom.cmdInput && dom.cmdInput.value.trim()) {
        executeCommand(dom.cmdInput.value.trim());
        dom.cmdInput.value = "";
      }
    };
    window.toggleMobileMic = () => toggleSpeech();
    window.toggleContinuousSpeech = () => toggleContinuousSpeech();
    window.openRemoteOverlay = (gameMode = false) => openRemoteDesktop(gameMode);
    window.closeRemoteOverlay = () => closeRemoteDesktop();
    window.openGamepadOverlay = () => openRemoteDesktop(true);
    window.closeGamepadOverlay = () => closeRemoteDesktop();
    window.refreshMobileRemoteStream = () => refreshScreenStream();
    window.openModal = (name) => {
      const el = document.getElementById(`modal-${name}`);
      if (el) el.style.display = "flex";
    };
    window.closeModal = (name) => {
      const el = document.getElementById(`modal-${name}`);
      if (el) el.style.display = "none";
    };
    window.switchNavTab = (tab) => {
      document.querySelectorAll(".nav-tab-btn").forEach(b => b.classList.remove("active"));
      const b = document.getElementById(`nav-btn-${tab}`);
      if (b) b.classList.add("active");
      if (tab === "remote") openRemoteDesktop(false);
      else if (tab === "gamepad") openRemoteDesktop(true);
      else if (tab === "guide") window.openModal("guide");
      else if (tab === "settings") window.openModal("settings");
    };
    window.zoomMobileRemote = (factor) => {
      remoteZoomVal = Math.max(0.5, Math.min(3.0, remoteZoomVal * factor));
      const img = document.getElementById("mobile-remote-img") || document.getElementById("remote-screen-img");
      if (img) img.style.transform = `scale(${remoteZoomVal})`;
      const lbl = document.getElementById("lbl-mobile-zoom") || document.getElementById("lbl-mzoom-val");
      if (lbl) lbl.textContent = `${Math.round(remoteZoomVal * 100)}%`;
    };
    window.resetMobileZoom = () => {
      remoteZoomVal = 1.0;
      const img = document.getElementById("mobile-remote-img") || document.getElementById("remote-screen-img");
      if (img) img.style.transform = "scale(1.0)";
      const lbl = document.getElementById("lbl-mobile-zoom") || document.getElementById("lbl-mzoom-val");
      if (lbl) lbl.textContent = "100%";
    };
    window.handleMobileRemoteClick = (e) => {
      const img = e.target;
      const rect = img.getBoundingClientRect();
      const xNorm = (e.clientX - rect.left) / rect.width;
      const yNorm = (e.clientY - rect.top) / rect.height;
      sendRemoteInput("click", { x: Math.max(0, Math.min(1, xNorm)), y: Math.max(0, Math.min(1, yNorm)), button: "left" });
    };
    window.dispatchGamepadKey = (keyName, action) => {
      sendRemoteInput(action === "down" ? "key_down" : "key_up", { key: keyName });
    };
    window.saveHostSettings = async () => {
      const inp = document.getElementById("setting-host-url") || document.getElementById("cfg-local-url");
      if (inp && inp.value.trim()) {
        state.localUrl = inp.value.trim();
        localStorage.setItem(STORAGE_KEYS.LOCAL_URL, state.localUrl);
        window.closeModal("settings");
        await resolveActiveEndpoint();
        await pollLaptopVitals();
      }
    };
    window.syncClipboard = () => executeCommand("get clipboard");
    window.toggleEmergencyStop = () => executeCommand("emergency stop");

    try { initWebCanvas(); } catch (_) {}
    try { initOscilloscopeCanvas(); } catch (_) {}
    try { initEvents(); } catch (_) {}
    try { updateVoiceModeUI(); } catch (_) {}
    const savedChar = localStorage.getItem("mobile_voice_char") || "edith";
    const savedTheme = localStorage.getItem("mobile_theme") || VOICE_THEME_MAP[savedChar] || "edith";
    try { setMobileTheme(savedTheme, false); } catch (_) {}
    try { setMobileVoiceCharacter(savedChar, false, false); } catch (_) {}
    if (dom.quickHostInput) dom.quickHostInput.value = state.localUrl;

    try {
      await fetchServerConfig();
      await resolveActiveEndpoint();
      if (dom.quickHostInput) dom.quickHostInput.value = state.localUrl;
      await pollLaptopVitals();
    } catch (_) {}

    // Heartbeat connection maintenance and bi-directional message polling
    setInterval(async () => {
      try {
        await fetchServerConfig();
        await resolveActiveEndpoint();
        await pollLaptopVitals();
        await pollPhoneMessagesAndTelemetry();
      } catch (_) {}
    }, 3500);

    // Auto-reconnect immediately when mobile screen wakes or network reconnects
    document.addEventListener("visibilitychange", async () => {
      if (document.visibilityState === "visible") {
        consecutiveOfflineFailures = 0;
        try {
          await resolveActiveEndpoint();
          await pollLaptopVitals();
          if (remoteStreamActive) {
            isFetchingFrame = false;
            requestAnimationFrame(fetchStreamLoop);
          }
        } catch (_) {}
      }
    });

    window.addEventListener("online", async () => {
      consecutiveOfflineFailures = 0;
      try {
        await resolveActiveEndpoint();
      } catch (_) {}
    });
  }

  window.addEventListener("DOMContentLoaded", init);
})();
