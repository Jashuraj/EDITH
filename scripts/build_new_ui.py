"""Builder script to generate the complete Stark Holographic Tactical HUD UI for EDITH.
Replaces the existing UI with the Stitch Spider-AI EV / Stark HUD design while preserving
all native integrations (Three.js, MediaPipe gestures, Web Speech, telemetry, chat, modals).
"""

import sys
from pathlib import Path

HTML_CONTENT = r'''<!DOCTYPE html>
<html class="dark" lang="en">
<head>
  <meta charset="utf-8">
  <meta content="width=device-width, initial-scale=1.0" name="viewport">
  <title>E.D.I.T.H. Mark II // Stark Industries Tactical HUD OS</title>

  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>

  <!-- Google Fonts: Michroma, Chakra Petch, Oxanium, JetBrains Mono, Inter -->
  <link href="https://fonts.googleapis.com" rel="preconnect">
  <link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect">
  <link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Michroma&family=Oxanium:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">

  <!-- Lucide Icons -->
  <script src="https://unpkg.com/lucide@latest"></script>

  <!-- Three.js r128 -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>

  <!-- Tailwind Theme Configuration -->
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            'os-black': '#06090e',
            'os-dark': '#090e17',
            'os-panel': '#0c131f',
            'os-card': '#101826',
            'os-border': '#182639',
            'os-border-glow': '#274163',
            'os-amber': '#ffa800',
            'os-amber-glow': '#ffbe28',
            'os-gold': '#ffb014',
            'os-cyan': '#00f0ff',
            'os-cyan-glow': '#38bdf8',
            'os-red': '#ef4444',
          },
          fontFamily: {
            hud: ['Michroma', 'sans-serif'],
            michroma: ['Michroma', 'sans-serif'],
            chakra: ['"Chakra Petch"', 'sans-serif'],
            oxanium: ['Oxanium', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'monospace'],
            sans: ['Inter', 'sans-serif'],
            telemetry: ['"JetBrains Mono"', 'monospace'],
          },
          animation: {
            'pulse-fast': 'pulse 1.2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            'spin-slow': 'spin 32s linear infinite',
            'spin-reverse': 'spin-rev 40s linear infinite',
            'arc-pulse': 'arc-pulse 3s ease-in-out infinite',
          },
          keyframes: {
            'spin-rev': {
              '0%': { transform: 'rotate(0deg)' },
              '100%': { transform: 'rotate(-360deg)' },
            },
            'arc-pulse': {
              '0%, 100%': { opacity: '0.4', transform: 'scale(0.98)' },
              '50%': { opacity: '0.9', transform: 'scale(1.03)' }
            }
          }
        }
      }
    }
  </script>

  <!-- Tactical HUD Stylesheet -->
  <style data-purpose="hud-effects">
    /* Tactical CRT Scanlines */
    .scanlines {
      background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.35) 50%), linear-gradient(90deg, rgba(255, 168, 0, 0.02), rgba(0, 240, 255, 0.015), rgba(255, 168, 0, 0.02));
      background-size: 100% 3px, 6px 100%;
      pointer-events: none;
    }

    /* Scrollbars */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: #06090e; }
    ::-webkit-scrollbar-thumb { background: #1e3048; border-radius: 1px; }
    ::-webkit-scrollbar-thumb:hover { background: #ffa800; }

    /* Tactical Neon Glows */
    .glow-amber-sm { box-shadow: 0 0 10px rgba(255, 168, 0, 0.38), inset 0 0 8px rgba(255, 168, 0, 0.1); }
    .glow-amber-lg { box-shadow: 0 0 30px rgba(255, 168, 0, 0.55), 0 0 12px rgba(255, 190, 40, 0.35); }
    .glow-cyan-sm { box-shadow: 0 0 10px rgba(0, 240, 255, 0.4), inset 0 0 8px rgba(0, 240, 255, 0.1); }
    .text-glow-amber { text-shadow: 0 0 10px rgba(255, 168, 0, 0.75), 0 0 20px rgba(255, 190, 40, 0.4); }
    .text-glow-cyan { text-shadow: 0 0 8px rgba(0, 240, 255, 0.7); }

    /* Tactical Chamfered Cards with Corner Brackets */
    .stark-card {
      position: relative;
      background: linear-gradient(135deg, rgba(12, 19, 31, 0.94) 0%, rgba(8, 13, 21, 0.97) 100%);
      border: 1px solid rgba(30, 48, 72, 0.85);
      clip-path: polygon(
        0 8px, 8px 0,
        calc(100% - 8px) 0, 100% 8px,
        100% calc(100% - 8px), calc(100% - 8px) 100%,
        8px 100%, 0 calc(100% - 8px)
      );
    }
    .stark-card::before {
      content: '';
      position: absolute;
      top: 0; left: 0; width: 6px; height: 6px;
      border-top: 2px solid #ffa800;
      border-left: 2px solid #ffa800;
      pointer-events: none;
    }
    .stark-card::after {
      content: '';
      position: absolute;
      bottom: 0; right: 0; width: 6px; height: 6px;
      border-bottom: 2px solid #00f0ff;
      border-right: 2px solid #00f0ff;
      pointer-events: none;
    }

    /* Reticle Corner Brackets */
    .reticle-bracket-tl {
      position: absolute; top: 4px; left: 4px; width: 8px; height: 8px;
      border-top: 1.5px solid #ffa800; border-left: 1.5px solid #ffa800; pointer-events: none;
    }
    .reticle-bracket-tr {
      position: absolute; top: 4px; right: 4px; width: 8px; height: 8px;
      border-top: 1.5px solid #ffa800; border-right: 1.5px solid #ffa800; pointer-events: none;
    }
    .reticle-bracket-bl {
      position: absolute; bottom: 4px; left: 4px; width: 8px; height: 8px;
      border-bottom: 1.5px solid #00f0ff; border-left: 1.5px solid #00f0ff; pointer-events: none;
    }
    .reticle-bracket-br {
      position: absolute; bottom: 4px; right: 4px; width: 8px; height: 8px;
      border-bottom: 1.5px solid #00f0ff; border-right: 1.5px solid #00f0ff; pointer-events: none;
    }

    /* Equalizer LED Segment wave bars */
    .eq-bar {
      transition: height 0.08s ease;
      transform-origin: bottom;
    }
    .tactical-grid-bg {
      background-image: 
        linear-gradient(to right, rgba(24, 38, 57, 0.45) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(24, 38, 57, 0.45) 1px, transparent 1px);
      background-size: 28px 28px;
    }

    /* Dialog Modals Overlay */
    .dialog-backdrop {
      position: fixed; inset: 0; z-index: 100;
      background: rgba(4, 7, 14, 0.88);
      backdrop-filter: blur(14px);
      display: flex; align-items: center; justify-content: center;
      padding: 16px;
    }
    .dialog-modal {
      width: 100%; max-width: 640px; max-height: 88vh;
      overflow-y: auto;
      background: #090e18;
      border: 1px solid rgba(255, 168, 0, 0.6);
      box-shadow: 0 0 35px rgba(255, 168, 0, 0.25), inset 0 0 15px rgba(0, 240, 255, 0.08);
      border-radius: 8px;
      padding: 20px;
      color: #e2e8f0;
      position: relative;
    }
    .dialog-wide { max-width: 920px; }

    /* PiP Webcam Container */
    #webcam-box {
      position: absolute;
      top: 14px;
      right: 14px;
      width: 220px;
      height: 165px;
      border: 1.5px solid #00f0ff;
      border-radius: 6px;
      background: #000;
      overflow: hidden;
      box-shadow: 0 0 16px rgba(0, 240, 255, 0.45);
      z-index: 40;
      display: none;
      flex-direction: column;
    }
    #webcam-pip { width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }
    #webcam-overlay { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; transform: scaleX(-1); }
  </style>
</head>

<body class="bg-[#05080e] text-slate-200 font-oxanium antialiased overflow-hidden select-none h-screen w-screen flex flex-col justify-between relative tracking-wider">

  <!-- Background Scanlines & Tech Grid -->
  <div class="fixed inset-0 scanlines opacity-60 z-50 pointer-events-none"></div>
  <div class="fixed inset-0 tactical-grid-bg opacity-30 pointer-events-none"></div>

  <!-- Decorative Top HUD Light Strip -->
  <div class="fixed top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-os-amber to-transparent z-50 opacity-80" id="hud-light-strip"></div>

  <!-- ── Top Global Header ── -->
  <header class="h-14 border-b border-os-border/90 bg-[#070b13]/95 backdrop-blur-md px-4 flex items-center justify-between z-40 shrink-0 relative">
    
    <!-- Left: E.D.I.T.H. Mark II Stark Tactical Branding -->
    <div class="flex items-center space-x-3">
      <div class="w-9 h-9 flex items-center justify-center text-os-amber relative">
        <svg class="w-7 h-7 text-os-amber" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <polygon points="12 2 22 7.5 22 16.5 12 22 2 16.5 2 7.5 12 2"></polygon>
          <polygon points="12 6 18 9.5 18 14.5 12 18 6 14.5 6 9.5 12 6" stroke-dasharray="1 2"></polygon>
          <circle cx="12" cy="12" r="2" fill="currentColor"></circle>
        </svg>
      </div>
      <div>
        <div class="flex items-center space-x-2">
          <span class="font-michroma tracking-[0.25em] text-white font-bold text-xs">E.D.I.T.H.</span>
          <span class="text-[9px] font-bold px-1.5 py-0.2 rounded bg-os-amber text-os-black uppercase tracking-[0.14em] font-chakra">MARK II</span>
          <span class="text-xs text-os-border-glow font-mono px-1">//</span>
        </div>
        <p class="text-[9px] text-slate-400 font-mono tracking-[0.15em] uppercase">EVEN DEAD, I'M THE HERO | LOCAL-FIRST AUTONOMOUS AI OS</p>
      </div>
    </div>

    <!-- Center: Persona Switcher Selector Tabs -->
    <nav aria-label="AI Personas" class="flex items-center bg-[#05080e]/95 p-1 rounded-md border border-os-border/90 space-x-1 font-chakra font-bold tracking-[0.12em]">
      <button class="persona-tab px-2.5 py-0.5 text-[10px] rounded tracking-[0.14em] text-slate-400 hover:text-white transition" data-persona="EDITH">EDITH</button>
      <button class="persona-tab px-3 py-0.5 text-[10px] rounded-full tracking-[0.14em] bg-transparent text-os-amber border border-os-amber/80 flex items-center space-x-1.5 transition glow-amber-sm" data-persona="JARVIS">
        <span class="w-1.5 h-1.5 rounded-full bg-os-amber"></span><span>JARVIS</span>
      </button>
      <button class="persona-tab px-2.5 py-0.5 text-[10px] rounded tracking-[0.14em] text-slate-400 hover:text-white transition" data-persona="FRIDAY">FRIDAY</button>
      <button class="persona-tab px-2.5 py-0.5 text-[10px] rounded tracking-[0.14em] text-slate-400 hover:text-white transition" data-persona="KAREN">KAREN</button>
      <button class="persona-tab px-2.5 py-0.5 text-[10px] rounded tracking-[0.14em] text-slate-400 hover:text-white transition" data-persona="SPIDEY">SPIDEY</button>
      <button class="persona-tab px-2.5 py-0.5 text-[10px] rounded tracking-[0.14em] text-slate-400 hover:text-red-400 transition" data-persona="ULTRON">ULTRON</button>
    </nav>

    <!-- Right: Telemetry, Clock, E-Stop -->
    <div class="flex items-center space-x-3 text-xs">
      <button class="hidden md:flex items-center space-x-1 px-2 py-0.5 rounded border border-os-border text-[9px] uppercase font-mono text-slate-400 hover:text-white" id="btn-mode-toggle" onclick="cycleMode()" title="Cycle Runtime Mode: Auto, Online, Offline">
        <span class="text-slate-400">MODE:</span>
        <span class="text-slate-200 font-chakra font-bold" id="val-mode-text">AUTO</span>
      </button>
      
      <div class="hidden lg:flex items-center space-x-1.5 text-[9px] font-mono text-slate-400">
        <span class="w-1.5 h-1.5 rounded-full bg-os-amber" id="host-status-dot"></span>
        <span id="host-status-text">PC LINKED</span>
        <span class="text-slate-600">·</span>
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
        <span class="text-slate-300">ONLINE (AUTO)</span>
      </div>

      <div class="text-right hidden sm:block border-l border-os-border/90 pl-3">
        <div class="text-xs font-mono font-bold tracking-[0.18em] text-slate-100" id="live-clock">--:--:--</div>
        <div class="text-[9px] text-slate-400 font-mono uppercase tracking-[0.12em]" id="live-date">OCT 11, 2026 · <span id="w-temp">--°C</span></div>
      </div>

      <button class="px-2.5 py-0.5 rounded-full bg-red-950/40 border border-red-500/80 hover:bg-red-600 text-red-400 hover:text-white font-bold text-[9px] tracking-[0.16em] uppercase flex items-center space-x-1.5 transition font-chakra" id="estop-btn" onclick="toggleEmergencyStop()" title="Emergency Stop all active operations">
        <svg class="w-3 h-3 text-red-400" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"></circle><line x1="12" y1="8" x2="12" y2="12"></line></svg>
        <span>E-STOP</span>
      </button>

      <div class="flex items-center space-x-2 border-l border-os-border/90 pl-3 text-slate-400">
        <div class="flex items-center space-x-1 text-[9px] uppercase font-mono text-slate-300">
          <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
          <span class="hidden xl:inline text-[10px] font-chakra font-medium tracking-[0.16em] text-slate-400">PRIVATE SECURE CORE</span>
        </div>
        <button class="p-1 hover:text-white hover:bg-os-card rounded transition" onclick="toggleFullscreen()" title="Toggle Fullscreen">
          <svg class="w-3.5 h-3.5 text-slate-400 hover:text-white" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><polyline points="15 3 21 3 21 9"></polyline><polyline points="9 21 3 21 3 15"></polyline><line x1="21" y1="3" x2="14" y2="10"></line><line x1="3" y1="21" x2="10" y2="14"></line></svg>
        </button>
      </div>
    </div>
  </header>

  <!-- ── Main 3-Column HUD Shell ── -->
  <main class="flex-1 flex overflow-hidden p-2 gap-2 relative z-30">

    <!-- LEFT HUD SLOCK DOCK -->
    <aside class="w-12 bg-[#090f19] border border-os-border/90 rounded-lg flex flex-col items-center py-3 justify-between shrink-0 shadow-lg relative">
      <div class="flex flex-col space-y-3 items-center">
        <button class="w-8 h-8 rounded text-os-amber flex items-center justify-center hover:scale-105 transition" title="Arc Reactor / Home" onclick="openNav(null)">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><polygon points="12 2 22 7.5 22 16.5 12 22 2 16.5 2 7.5 12 2"></polygon><circle cx="12" cy="12" r="3"></circle></svg>
        </button>
        <button class="w-8 h-8 rounded text-slate-400 hover:text-white flex items-center justify-center transition" title="Intelligence & APIs" onclick="openDialog('settings')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
        </button>
        <button class="w-8 h-8 rounded text-slate-400 hover:text-white flex items-center justify-center transition" title="Remote Desktop" onclick="openDialog('remote')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
        </button>
        <button class="w-8 h-8 rounded text-slate-400 hover:text-white flex items-center justify-center transition" title="Face Sentinel" onclick="openDialog('sentinel')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
        </button>
        <button class="w-8 h-8 rounded text-slate-400 hover:text-white flex items-center justify-center transition" title="Command Guide" onclick="openDialog('guide')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>
        </button>
        <button class="w-8 h-8 rounded text-slate-400 hover:text-white flex items-center justify-center transition" title="Audio Mixer" onclick="openDialog('mixer')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>
        </button>
        <button class="w-8 h-8 rounded text-slate-400 hover:text-white flex items-center justify-center transition" title="Activity Logs" onclick="openDialog('activity')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
        </button>
        <button class="w-8 h-8 rounded text-slate-400 hover:text-white flex items-center justify-center transition" title="Virtual Gamepad" onclick="openDialog('gamepad')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
        </button>
      </div>

      <div class="flex flex-col space-y-3 items-center">
        <button class="w-8 h-8 rounded text-slate-400 hover:text-white flex items-center justify-center transition" title="Preferences" onclick="openDialog('settings')">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
        </button>
        <div class="w-7 h-7 rounded border border-os-amber/50 bg-[#0e1624] text-os-amber font-mono font-bold flex items-center justify-center text-xs cursor-pointer hover:border-os-amber" onclick="openDialog('about')">E</div>
      </div>
    </aside>

    <!-- COLUMN 1: LEFT TELEMETRY & SYSTEM MODULES -->
    <section aria-label="System Metrics and Control Panels" class="w-80 2xl:w-96 flex flex-col gap-2 overflow-y-auto pr-1 shrink-0">
      
      <!-- Command Center Card -->
      <div class="p-2.5 stark-card rounded-lg relative overflow-hidden">
        <div class="flex items-center justify-between mb-1">
          <div class="flex items-center space-x-1.5">
            <span class="text-os-amber text-xs font-bold font-michroma tracking-[0.16em]">+ Command center</span>
            <span class="text-[8px] uppercase px-1 py-0.2 rounded border border-os-amber/50 text-os-amber font-mono">LIVE HYBRID AI</span>
          </div>
          <div class="flex items-center space-x-1 text-slate-500 text-[9px] font-mono">
            <svg class="w-3 h-3 text-slate-500" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
            <span class="hidden xl:inline">PRIVATE SECURE CORE</span>
          </div>
        </div>
        <p class="text-[10px] text-slate-400 font-mono tracking-normal leading-tight">Direct reflex execution. Autonomous task planning. Full laptop &amp; mobile control.</p>
      </div>

      <!-- System Status Card -->
      <div class="p-2.5 stark-card rounded-lg text-xs space-y-2 relative">
        <div class="flex items-center justify-between border-b border-os-border/80 pb-1.5">
          <div class="flex items-center space-x-2">
            <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><rect x="4" y="4" width="16" height="16" rx="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="2" x2="9" y2="4"></line><line x1="15" y1="2" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="22"></line><line x1="15" y1="20" x2="15" y2="22"></line></svg>
            <span class="text-[9px] font-bold tracking-[0.16em] uppercase text-slate-300 font-mono">SYSTEM STATUS</span>
          </div>
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        </div>

        <div class="p-2 rounded bg-os-card/60 border border-os-border/70 flex items-start space-x-2.5">
          <div class="p-1 rounded text-os-amber">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><polygon points="12 2 19 8 19 16 12 22 5 16 5 8"></polygon></svg>
          </div>
          <div>
            <div class="text-[11px] font-medium text-slate-200 font-oxanium" id="lbl-system-state">All systems operational</div>
            <div class="text-[9px] text-slate-400 font-mono">Reflex engine &lt;15ms · Ready for input</div>
          </div>
        </div>

        <div class="space-y-1.5 text-[10px] pt-1 font-mono">
          <div class="flex justify-between items-center text-slate-400">
            <span class="uppercase tracking-wider text-[9px]">Core Engine</span>
            <span class="text-os-amber font-mono font-medium flex items-center space-x-1"><span>●</span><span>Reflex L0</span></span>
          </div>
          <div class="flex justify-between items-center text-slate-400">
            <span class="uppercase tracking-wider text-[9px]">AI Model</span>
            <div class="flex items-center space-x-1 px-1.5 py-0.5 rounded bg-os-card text-os-amber text-[9px] border border-os-border cursor-pointer hover:border-os-amber" onclick="openDialog('settings')">
              <span id="active-model-badge">hermes3:3b</span>
              <svg class="w-3 h-3 text-os-amber" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"></polyline></svg>
            </div>
          </div>
          <div class="flex justify-between items-center text-slate-400">
            <span class="uppercase tracking-wider text-[9px]">Voice Persona</span>
            <div class="flex items-center space-x-1 px-1.5 py-0.5 rounded bg-os-card text-os-amber text-[9px] border border-os-border" id="active-voice-badge">
              <span>JARVIS</span>
            </div>
          </div>
          <div class="flex justify-between items-center text-slate-400">
            <span class="uppercase tracking-wider text-[9px]">Cloud Tunnel</span>
            <span class="text-os-amber text-[9px] font-mono font-medium" id="val-tunnel-status">HOST ONLINE</span>
          </div>
        </div>
      </div>

      <!-- Performance & Vitals Card -->
      <div class="p-2.5 stark-card rounded-lg text-xs space-y-1.5 relative">
        <div class="flex items-center justify-between border-b border-os-border/80 pb-1">
          <div class="flex items-center space-x-2">
            <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
            <span class="text-[9px] font-bold tracking-[0.16em] uppercase text-slate-300 font-mono">PERFORMANCE &amp; VITALS</span>
          </div>
        </div>

        <div class="flex items-baseline justify-between pt-1 font-mono">
          <span class="text-[9px] text-slate-400 uppercase">API LATENCY</span>
          <span class="text-xs font-mono text-os-amber flex items-center space-x-1"><span>●</span><span class="text-slate-300">LIVE</span></span>
        </div>
        <div class="text-xs font-mono text-slate-300"><span id="val-ping-latency">12</span> <span class="text-[10px]">ms</span></div>

        <!-- Latency SVG Wave -->
        <div class="h-8 w-full overflow-hidden relative">
          <svg class="w-full h-full" preserveAspectRatio="none" viewBox="0 0 200 40">
            <path id="latency-svg-path" d="M0,25 Q40,30 80,24 T140,20 T200,28" fill="none" stroke="#ffa800" stroke-linecap="round" stroke-width="1.8"></path>
          </svg>
        </div>

        <div class="space-y-1.5 pt-1 text-[10px] font-mono text-slate-400">
          <div class="flex justify-between items-center">
            <span class="text-[9px]">CPU Load</span>
            <span class="text-slate-300 font-mono" id="val-cpu">--%</span>
          </div>
          <div class="w-full bg-slate-900 h-1 rounded overflow-hidden"><div class="bg-os-amber h-full transition-all duration-300" id="bar-cpu" style="width: 15%;"></div></div>

          <div class="flex justify-between items-center">
            <span class="text-[9px]">RAM Usage</span>
            <span class="text-slate-300 font-mono" id="val-ram">--%</span>
          </div>
          <div class="w-full bg-slate-900 h-1 rounded overflow-hidden"><div class="bg-os-cyan h-full transition-all duration-300" id="bar-ram" style="width: 35%;"></div></div>

          <div class="flex justify-between items-center">
            <span class="text-[9px]">Storage (C:)</span>
            <span class="text-slate-300 font-mono" id="val-disk">--%</span>
          </div>
          <div class="w-full bg-slate-900 h-1 rounded overflow-hidden"><div class="bg-emerald-400 h-full transition-all duration-300" id="bar-disk" style="width: 50%;"></div></div>

          <div class="flex justify-between items-center">
            <span class="text-[9px]">Battery / Power</span>
            <span class="text-slate-300 font-mono" id="val-battery">--%</span>
          </div>
        </div>
      </div>

      <!-- Quick Protocols Card -->
      <div class="p-2.5 stark-card rounded-lg text-xs space-y-1.5 relative">
        <div class="flex items-center space-x-2 border-b border-os-border/80 pb-1">
          <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
          <span class="text-[9px] font-bold tracking-[0.16em] uppercase text-slate-300 font-mono">QUICK PROTOCOLS</span>
        </div>

        <div class="space-y-1">
          <button class="w-full text-left p-1.5 rounded bg-os-card/50 hover:bg-os-card border border-os-border/60 flex items-center space-x-2 transition" onclick="submitTextCommand('Give me my daily briefing')">
            <div class="p-1 rounded bg-os-amber/10 text-os-amber">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41m14.14-14.14l-1.41 1.41"></path></svg>
            </div>
            <div>
              <div class="text-[10px] font-medium text-slate-200 font-mono">Daily Briefing</div>
              <div class="text-[8px] text-slate-500 font-mono uppercase">Status, schedule &amp; weather</div>
            </div>
          </button>

          <button class="w-full text-left p-1.5 rounded bg-os-card/50 hover:bg-os-card border border-os-border/60 flex items-center space-x-2 transition" onclick="openDialog('settings')">
            <div class="p-1 rounded bg-os-amber/10 text-os-amber">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
            </div>
            <div>
              <div class="text-[10px] font-medium text-slate-200 font-mono">Intelligence &amp; APIs</div>
              <div class="text-[8px] text-slate-500 font-mono uppercase">Multi-model cloud &amp; local</div>
            </div>
          </button>

          <button class="w-full text-left p-1.5 rounded bg-os-card/50 hover:bg-os-card border border-os-border/60 flex items-center space-x-2 transition" onclick="openDialog('sentinel')">
            <div class="p-1 rounded bg-os-cyan/10 text-os-cyan">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
            </div>
            <div>
              <div class="text-[10px] font-medium text-slate-200 font-mono">Face Sentinel</div>
              <div class="text-[8px] text-slate-500 font-mono uppercase">Biometric security scanner</div>
            </div>
          </button>

          <button class="w-full text-left p-1.5 rounded bg-os-card/50 hover:bg-os-card border border-os-border/60 flex items-center space-x-2 transition" onclick="submitTextCommand('look at my screen')">
            <div class="p-1 rounded bg-emerald-500/10 text-emerald-400">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"></circle><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"></path></svg>
            </div>
            <div>
              <div class="text-[10px] font-medium text-slate-200 font-mono">See Screen</div>
              <div class="text-[8px] text-slate-500 font-mono uppercase">AI screen vision inspection</div>
            </div>
          </button>

          <button class="w-full text-left p-1.5 rounded bg-os-card/50 hover:bg-os-card border border-os-border/60 flex items-center space-x-2 transition" onclick="submitTextCommand('lock screen')">
            <div class="p-1 rounded bg-red-500/10 text-red-400">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
            </div>
            <div>
              <div class="text-[10px] font-medium text-slate-200 font-mono">Lock PC</div>
              <div class="text-[8px] text-slate-500 font-mono uppercase">Lock desktop workstation</div>
            </div>
          </button>
        </div>
      </div>

      <!-- Mobile Link Card -->
      <div class="p-2.5 stark-card rounded-lg text-xs space-y-1.5 relative">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect><line x1="12" y1="18" x2="12.01" y2="18"></line></svg>
            <span class="text-[9px] font-bold tracking-[0.16em] uppercase text-slate-300 font-mono">MOBILE LINK</span>
          </div>
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        </div>
        <p class="text-[10px] text-os-amber font-mono truncate" id="hud-cloud-url">http://localhost:3000</p>
        <div class="grid grid-cols-2 gap-2 pt-1 font-mono">
          <button class="px-2 py-0.5 bg-os-card hover:bg-slate-800 border border-os-border rounded text-[9px] text-slate-300 uppercase transition text-center" onclick="copyCloudLink()">Copy Link</button>
          <button class="px-2 py-0.5 bg-os-card hover:bg-slate-800 border border-os-border rounded text-[9px] text-slate-300 uppercase transition text-center" onclick="syncClipboard()">Sync Clip</button>
        </div>
      </div>

    </section>

    <!-- COLUMN 2: CENTERSTAGE HOLOGRAPHIC SPHERE & AI REFLEX CORE -->
    <section aria-label="Centerstage AI Interactive Core" class="flex-1 flex flex-col justify-between rounded-lg border border-os-border/90 bg-[#060a12]/95 relative overflow-hidden p-4 shadow-2xl">
      <div class="absolute inset-0 bg-[radial-gradient(circle_at_50%_46%,rgba(255,168,0,0.18),transparent_65%)] pointer-events-none" id="core-glow-bg"></div>

      <!-- Headline Intro -->
      <div class="text-center z-10 pt-1 pointer-events-none">
        <span class="text-[9px] font-mono tracking-[0.25em] uppercase text-os-amber font-medium">YOUR PERSONAL AUTONOMOUS AI OS</span>
        <h1 class="text-2xl 2xl:text-3xl font-sans font-bold text-white tracking-wide mt-1" id="core-headline">At your service.</h1>
        <p class="text-[11px] text-slate-400 font-sans font-normal tracking-wide mt-0.5" id="core-subcaption">Your commands. My attention. Let's make things happen.</p>
      </div>

      <!-- HUD Telemetry Corner Tags -->
      <div class="absolute top-16 left-5 z-20 text-[8px] text-slate-400 font-mono space-y-0.5 border-l border-os-border/80 pl-2 pointer-events-none uppercase">
        <div class="text-slate-500 tracking-[0.14em]">NEURAL INTERFACE</div>
        <div class="text-slate-300 font-mono">EDITH // 01</div>
      </div>
      <div class="absolute top-16 right-5 z-20 text-[8px] text-slate-400 font-mono text-right space-y-0.5 border-r border-os-border/80 pr-2 pointer-events-none uppercase">
        <div class="text-slate-500 tracking-[0.14em]">INTERACTIVE CORE</div>
        <div class="text-slate-300 font-mono">DRAG TO ROTATE</div>
      </div>
      <div class="absolute bottom-44 left-5 z-20 text-[8px] text-slate-400 font-mono space-y-0.5 border-l border-os-border/80 pl-2 pointer-events-none uppercase">
        <div class="text-slate-500 tracking-[0.14em]">INPUT SIGNAL</div>
        <div class="text-slate-300 font-mono font-bold" id="val-input-signal">STANDBY</div>
      </div>
      <div class="absolute bottom-44 right-5 z-20 text-[8px] text-slate-400 font-mono text-right space-y-0.5 border-r border-os-border/80 pr-2 pointer-events-none uppercase">
        <div class="text-slate-500 tracking-[0.14em]">RENDER ENGINE</div>
        <div class="text-slate-300 font-mono font-bold" id="val-render-fps">60 FPS</div>
      </div>

      <!-- Center Three.js Globe Container -->
      <div class="flex-1 flex items-center justify-center relative min-h-[340px] my-1">
        <div class="absolute inset-0 w-full h-full z-10 cursor-grab" id="threejs-globe-container"></div>
        
        <!-- Reticle Crosshairs -->
        <div class="absolute inset-0 flex items-center justify-center pointer-events-none z-15">
          <div class="w-72 h-72 2xl:w-84 2xl:h-84 rounded-full border border-os-amber/20 border-dashed pointer-events-none"></div>
          <div class="w-full h-px bg-gradient-to-r from-transparent via-os-amber/30 to-transparent absolute pointer-events-none"></div>
          <div class="h-full w-px bg-gradient-to-b from-transparent via-os-amber/30 to-transparent absolute pointer-events-none"></div>
        </div>

        <!-- PiP Webcam Box for Hand Gesture Tracking -->
        <div id="webcam-box">
          <div class="flex items-center justify-between px-2 py-1 bg-slate-900 border-b border-os-cyan text-[8px] font-mono text-os-cyan">
            <span id="gesture-tag">VISION: CALIBRATING</span>
            <button class="hover:text-white" onclick="toggleGestures()" title="Close Camera">✕</button>
          </div>
          <div class="relative flex-1 bg-black">
            <video id="webcam-pip" autoplay playsinline muted></video>
            <canvas id="webcam-overlay"></canvas>
          </div>
          <div class="p-1 bg-slate-950 flex justify-between items-center text-[8px] font-mono">
            <button id="btn-os-mouse" class="px-1.5 py-0.5 rounded bg-os-card border border-os-border text-slate-300" onclick="toggleOsMouse()">OS MOUSE: OFF</button>
            <span id="lbl-gesture-state" class="text-slate-400">Tracking Live</span>
          </div>
        </div>

        <div class="absolute bottom-2 z-20 flex items-center space-x-1.5 text-[9px] tracking-[0.2em] uppercase font-mono text-os-amber pointer-events-none">
          <span class="w-1.5 h-1.5 rounded-full bg-os-amber"></span>
          <span id="lbl-core-ready">AWAITING YOUR COMMAND</span>
        </div>
      </div>

      <!-- Mic & Waveform Console -->
      <div class="flex flex-col items-center justify-center space-y-2 z-20 my-1">
        <div class="flex items-center space-x-3 sm:space-x-4">
          <button class="w-9 h-9 rounded-full bg-[#0a101a] border border-os-border text-slate-400 hover:text-white flex items-center justify-center transition" id="speaker-btn" onclick="toggleTts()" title="Toggle Voice Output">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>
          </button>

          <div class="hidden sm:flex items-center space-x-1 h-6 px-1" id="waveform-left">
            <span class="eq-bar w-1 bg-os-amber/60 rounded-full h-2"></span>
            <span class="eq-bar w-1 bg-os-amber/80 rounded-full h-3"></span>
            <span class="eq-bar w-1 bg-os-amber rounded-full h-5"></span>
            <span class="eq-bar w-1 bg-os-amber/70 rounded-full h-3"></span>
          </div>

          <!-- Main Pulsing Mic Trigger -->
          <button class="w-14 h-14 rounded-full bg-transparent p-0.5 border border-os-amber/80 flex items-center justify-center transition group relative hover:scale-105 active:scale-95 shadow-[0_0_14px_rgba(255,168,0,0.6)]" id="mic-trigger-btn" onclick="toggleVoice()" title="Tap to Speak (Space)">
            <div class="w-full h-full rounded-full bg-[#080d16] flex items-center justify-center border border-os-amber">
              <svg class="w-6 h-6 text-os-amber" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
            </div>
          </button>

          <div class="hidden sm:flex items-center space-x-1 h-6 px-1" id="waveform-right">
            <span class="eq-bar w-1 bg-os-amber/70 rounded-full h-3"></span>
            <span class="eq-bar w-1 bg-os-amber rounded-full h-5"></span>
            <span class="eq-bar w-1 bg-os-amber/80 rounded-full h-3"></span>
            <span class="eq-bar w-1 bg-os-amber/60 rounded-full h-2"></span>
          </div>

          <button class="w-9 h-9 rounded-full bg-[#0a101a] border border-os-border text-slate-400 hover:text-white flex items-center justify-center transition" id="btn-toggle-continuous-mic" onclick="toggleContinuousMic()" title="Always-Listening Continuous Mic">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
          </button>

          <button class="w-9 h-9 rounded-full bg-[#0a101a] border border-os-border text-slate-400 hover:text-white flex items-center justify-center transition" id="reset-stream-btn" onclick="resetReflexStream()" title="Reset Neural Stream">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path></svg>
          </button>
        </div>

        <div class="text-[9px] text-slate-400 font-mono tracking-wider" id="voice-caption-text">
          Tap to speak or press <kbd class="px-1.5 py-0.2 rounded bg-os-card border border-os-border text-os-amber text-[8px] font-mono">Space</kbd>
        </div>
      </div>

      <!-- Five Tactical Toggles -->
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-2 bg-[#090f19] p-2 rounded-lg border border-os-border/70 z-20 text-xs font-mono">
        
        <!-- Toggle 1: Always-On Mic -->
        <div class="flex items-center justify-between p-1.5 rounded bg-[#0b121e] border border-os-border/50">
          <div class="flex items-center space-x-1.5">
            <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path></svg>
            <div>
              <div class="text-[9px] font-bold text-slate-200">Always-On Mic</div>
              <div class="text-[8px] text-slate-500" id="lbl-continuous-mic-state">Continuous Off</div>
            </div>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input class="sr-only peer" type="checkbox" id="chk-continuous-mic" onchange="toggleContinuousMic()">
            <div class="w-6 h-3 bg-slate-800 rounded-full peer peer-checked:bg-os-amber after:content-[''] after:absolute after:top-[1px] after:left-[1px] after:bg-white after:rounded-full after:h-2.5 after:w-2.5 after:transition-all peer-checked:after:translate-x-3"></div>
          </label>
        </div>

        <!-- Toggle 2: Voice Output -->
        <div class="flex items-center justify-between p-1.5 rounded bg-[#0b121e] border border-os-border/50">
          <div class="flex items-center space-x-1.5">
            <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon></svg>
            <div>
              <div class="text-[9px] font-bold text-slate-200">Voice Output</div>
              <div class="text-[8px] text-slate-500" id="lbl-tts-state">Speech Enabled</div>
            </div>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input class="sr-only peer" type="checkbox" id="tgl-voice-out" checked onchange="toggleTts()">
            <div class="w-6 h-3 bg-slate-800 rounded-full peer peer-checked:bg-os-amber after:content-[''] after:absolute after:top-[1px] after:left-[1px] after:bg-white after:rounded-full after:h-2.5 after:w-2.5 after:transition-all peer-checked:after:translate-x-3"></div>
          </label>
        </div>

        <!-- Toggle 3: Hand Tracking -->
        <div class="flex items-center justify-between p-1.5 rounded bg-[#0b121e] border border-os-border/50">
          <div class="flex items-center space-x-1.5">
            <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M18 11V6a2 2 0 0 0-4 0v5"></path><path d="M14 10V4a2 2 0 0 0-4 0v7"></path></svg>
            <div>
              <div class="text-[9px] font-bold text-slate-200">Hand Tracking</div>
              <div class="text-[8px] text-slate-500" id="lbl-gesture-state-mini">Camera Ready</div>
            </div>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input class="sr-only peer" type="checkbox" id="btn-gestures" onchange="toggleGestures()">
            <div class="w-6 h-3 bg-slate-800 rounded-full peer peer-checked:bg-os-cyan after:content-[''] after:absolute after:top-[1px] after:left-[1px] after:bg-white after:rounded-full after:h-2.5 after:w-2.5 after:transition-all peer-checked:after:translate-x-3"></div>
          </label>
        </div>

        <!-- Toggle 4: Clap to Wake -->
        <div class="flex items-center justify-between p-1.5 rounded bg-[#0b121e] border border-os-border/50">
          <div class="flex items-center space-x-1.5">
            <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="2"></circle><path d="M16.24 7.76a6 6 0 0 1 0 8.49m-8.48-.01a6 6 0 0 1 0-8.49"></path></svg>
            <div>
              <div class="text-[9px] font-bold text-slate-200">Clap to Wake</div>
              <div class="text-[8px] text-slate-500" id="lbl-clap-state">Acoustic Guard</div>
            </div>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input class="sr-only peer" type="checkbox" id="tgl-clap" onchange="toggleClap()">
            <div class="w-6 h-3 bg-slate-800 rounded-full peer peer-checked:bg-os-amber after:content-[''] after:absolute after:top-[1px] after:left-[1px] after:bg-white after:rounded-full after:h-2.5 after:w-2.5 after:transition-all peer-checked:after:translate-x-3"></div>
          </label>
        </div>

        <!-- Toggle 5: Face Sentinel -->
        <div class="flex items-center justify-between p-1.5 rounded bg-[#0b121e] border border-os-border/50">
          <div class="flex items-center space-x-1.5">
            <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
            <div>
              <div class="text-[9px] font-bold text-slate-200">Face Sentinel</div>
              <div class="text-[8px] text-slate-500" id="lbl-sentinel-state">Biometric Lock</div>
            </div>
          </div>
          <label class="relative inline-flex items-center cursor-pointer">
            <input class="sr-only peer" type="checkbox" id="tgl-sentinel" onchange="toggleFaceSentinel()">
            <div class="w-6 h-3 bg-slate-800 rounded-full peer peer-checked:bg-emerald-500 after:content-[''] after:absolute after:top-[1px] after:left-[1px] after:bg-white after:rounded-full after:h-2.5 after:w-2.5 after:transition-all peer-checked:after:translate-x-3"></div>
          </label>
        </div>

      </div>

      <!-- Live Activity Stream Footer inside Center -->
      <div class="mt-2 p-2 stark-card rounded-lg text-xs z-20 relative">
        <div class="flex items-center justify-between border-b border-os-border/70 pb-1 mb-1">
          <div class="flex items-center space-x-2">
            <span class="w-1.5 h-1.5 rounded-full bg-os-amber"></span>
            <span class="text-[9px] font-bold uppercase text-slate-300 font-mono">ACTIVITY STREAM</span>
          </div>
          <a class="text-[9px] text-slate-400 hover:text-white font-mono" href="javascript:void(0)" onclick="openDialog('activity')">View all →</a>
        </div>
        <div class="font-mono text-[9px] space-y-1 max-h-16 overflow-y-auto text-slate-300" id="activity-logs">
          <div class="flex items-center space-x-2">
            <span class="text-slate-500">22:43:14</span>
            <span class="w-1 h-1 bg-emerald-400 rounded-full"></span>
            <span class="text-slate-300">EDITH Autonomous OS online · Reflex engine ready.</span>
          </div>
        </div>
      </div>

    </section>

    <!-- COLUMN 3: RIGHT PANEL - ASSISTANT CHAT & REASONING -->
    <section aria-label="Assistant Dialog and Reasoning Panel" class="w-80 2xl:w-96 flex flex-col justify-between stark-card rounded-lg overflow-hidden shrink-0 relative">
      
      <!-- Heading -->
      <div class="p-2.5 border-b border-os-border/80 flex items-center justify-between bg-[#0a101a]">
        <div class="flex items-center space-x-2">
          <div class="p-1 rounded text-os-amber">
            <svg class="w-4 h-4 text-os-amber" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
          </div>
          <div>
            <div class="flex items-center space-x-1.5">
              <span class="text-[11px] font-bold text-white font-sans">Assistant</span>
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            </div>
            <div class="text-[8px] text-slate-400 font-mono">Reflex tools, AI reasoning, OS orders.</div>
          </div>
        </div>
        <button class="p-1 rounded text-slate-400 hover:text-white transition" onclick="clearConversation()" title="New Chat">
          <span class="text-sm font-mono">+</span>
        </button>
      </div>

      <!-- Tab Buttons: Conversation vs Command Guide -->
      <div class="flex border-b border-os-border/80 bg-[#070c14] text-[9px] px-2 pt-1 font-mono">
        <button class="py-1.5 px-3 border-b-2 border-os-amber text-slate-200 transition" id="tab-conv" onclick="switchRightTab('conv')">Conversation</button>
        <button class="py-1.5 px-3 border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition" id="tab-guide" onclick="switchRightTab('guide')">Command Guide</button>
      </div>

      <!-- Tab Content: Conversation -->
      <div class="flex-1 overflow-y-auto p-3 space-y-3 font-sans text-xs" id="chat-messages-container">
        <div class="text-center text-[8px] text-slate-500 font-mono uppercase tracking-widest my-1">TODAY</div>
        
        <div class="flex items-start space-x-2">
          <div class="w-5 h-5 rounded bg-emerald-950/60 border border-emerald-500/40 text-emerald-400 text-[9px] font-bold flex items-center justify-center shrink-0 font-mono">E</div>
          <div class="flex-1">
            <div class="flex items-center justify-between text-[8px] font-mono mb-1">
              <span class="text-os-amber font-bold" id="chat-welcome-char">EDITH</span>
              <span class="text-slate-500" id="chat-welcome-time">--:--</span>
            </div>
            <div class="text-[11px] text-slate-300 leading-relaxed font-sans">
              Good to have you here, boss. Workstation controls, MediaPipe gesture tracking, VNC screen streaming, and neural reflex tools are fully active. What shall we work on today?
            </div>
          </div>
        </div>

        <!-- Starters -->
        <div class="pt-2 space-y-1.5" id="chat-suggestions">
          <div class="text-[8px] font-mono uppercase text-slate-500 tracking-wider">A FEW PLACES TO START</div>
          <button class="w-full text-left p-1.5 rounded bg-os-card/50 hover:bg-os-card border border-os-border/70 text-[10px] text-slate-300 font-mono flex items-center space-x-2 transition" onclick="submitTextCommand('open youtube and play brand new day trailer')">
            <span class="text-slate-400">▶</span><span>Play Brand New Day Trailer</span>
          </button>
          <button class="w-full text-left p-1.5 rounded bg-os-card/50 hover:bg-os-card border border-os-border/70 text-[10px] text-slate-300 font-mono flex items-center space-x-2 transition" onclick="submitTextCommand('look at my screen')">
            <span class="text-slate-400">👁</span><span>Analyze Active Desktop Screen</span>
          </button>
          <button class="w-full text-left p-1.5 rounded bg-os-card/50 hover:bg-os-card border border-os-border/70 text-[10px] text-slate-300 font-mono flex items-center space-x-2 transition" onclick="submitTextCommand('Give me my daily briefing')">
            <span class="text-slate-400">☀️</span><span>Daily Briefing &amp; Vitals</span>
          </button>
        </div>

        <!-- In-HUD Media Player Embed Dock -->
        <div id="hud-media-dock" class="hidden p-2 bg-black border border-os-cyan rounded-lg my-2">
          <div class="flex justify-between items-center text-[9px] font-mono text-os-cyan mb-1">
            <span id="hud-media-title">▶ Media Player</span>
            <button class="hover:text-white" onclick="closeHudMedia()">✕</button>
          </div>
          <iframe id="hud-media-iframe" class="w-full h-36 rounded" allow="autoplay; encrypted-media" allowfullscreen></iframe>
        </div>
      </div>

      <!-- Tab Content: Command Guide (Hidden by default) -->
      <div class="flex-1 overflow-y-auto p-3 space-y-3 font-mono text-xs hidden" id="guide-tab-container">
        <input type="text" id="guide-filter-input" placeholder="Search commands..." class="w-full bg-[#0c1320] border border-os-border/90 rounded px-2 py-1 text-[10px] text-slate-200 placeholder-slate-500 mb-2" oninput="filterGuideChips(this.value)">
        <div class="space-y-3" id="guide-chips-list">
          <div>
            <div class="text-[9px] text-os-amber font-bold mb-1">▶ MEDIA &amp; SEARCH</div>
            <div class="space-y-1">
              <button class="w-full text-left p-1 rounded bg-os-card/60 hover:bg-os-card border border-os-border/50 text-[9px] text-slate-300" onclick="submitTextCommand(this.innerText)">open youtube and play brand new day trailer</button>
              <button class="w-full text-left p-1 rounded bg-os-card/60 hover:bg-os-card border border-os-border/50 text-[9px] text-slate-300" onclick="submitTextCommand(this.innerText)">play lofi beats on youtube</button>
              <button class="w-full text-left p-1 rounded bg-os-card/60 hover:bg-os-card border border-os-border/50 text-[9px] text-slate-300" onclick="submitTextCommand(this.innerText)">pause music</button>
            </div>
          </div>
          <div>
            <div class="text-[9px] text-os-cyan font-bold mb-1">💻 SYSTEM &amp; APPS</div>
            <div class="space-y-1">
              <button class="w-full text-left p-1 rounded bg-os-card/60 hover:bg-os-card border border-os-border/50 text-[9px] text-slate-300" onclick="submitTextCommand(this.innerText)">open chrome</button>
              <button class="w-full text-left p-1 rounded bg-os-card/60 hover:bg-os-card border border-os-border/50 text-[9px] text-slate-300" onclick="submitTextCommand(this.innerText)">open notepad</button>
              <button class="w-full text-left p-1 rounded bg-os-card/60 hover:bg-os-card border border-os-border/50 text-[9px] text-slate-300" onclick="submitTextCommand(this.innerText)">lock screen</button>
              <button class="w-full text-left p-1 rounded bg-os-card/60 hover:bg-os-card border border-os-border/50 text-[9px] text-slate-300" onclick="submitTextCommand(this.innerText)">take screenshot</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Composer Input -->
      <div class="p-2 border-t border-os-border/80 bg-[#070c14] space-y-1.5">
        <div class="flex items-center justify-between text-[8px] font-mono px-1">
          <span class="flex items-center space-x-1 text-slate-400">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span>Reflex &amp; Hybrid Router</span>
          </span>
          <span class="text-slate-400 font-mono" id="active-char-label">CHAR: JARVIS</span>
        </div>

        <div class="relative bg-[#0c1320] border border-os-border/90 rounded-lg p-1.5">
          <textarea
            class="w-full bg-transparent border-none text-[11px] text-slate-200 placeholder-slate-500 focus:ring-0 focus:outline-none resize-none font-sans"
            id="command-input"
            placeholder="Ask EDITH or give order... (e.g. 'open youtube and play trailer', 'lock pc')"
            rows="2"
            onkeydown="if(event.key==='Enter' && !event.shiftKey){event.preventDefault(); sendUserCommand();}"
          ></textarea>

          <div class="flex items-center justify-between pt-1 border-t border-os-border/40">
            <div class="flex items-center space-x-2 text-slate-400">
              <button class="hover:text-white" onclick="triggerFileUpload()" title="Attach file">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
              </button>
              <button class="hover:text-white" onclick="toggleVoice()" title="Dictate voice">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path></svg>
              </button>
            </div>
            <div class="flex items-center space-x-1">
              <span class="text-[8px] text-slate-500 font-mono">↵ to send</span>
              <button class="px-2 py-1 bg-os-amber hover:bg-amber-400 text-os-black font-bold rounded flex items-center space-x-1 text-[9px] transition" id="send-cmd-btn" onclick="sendUserCommand()">
                <svg class="w-3 h-3 text-os-black" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
              </button>
            </div>
          </div>
        </div>
        <input type="file" id="file-uploader" class="hidden" onchange="handleFileAttached(event)">
      </div>

    </section>

  </main>

  <!-- ── Bottom Global Footer ── -->
  <footer class="h-7 border-t border-os-border/80 bg-[#090f19] px-4 flex items-center justify-between text-[10px] font-mono text-slate-400 z-40 shrink-0">
    <div class="flex items-center space-x-2">
      <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
      <span class="text-slate-400 font-mono tracking-wider text-[9px]">EDITH OS / HYBRID AI v3.0</span>
      <span class="text-slate-600">·</span>
      <span class="text-[9px] tracking-wider text-slate-400">CREATOR: <span class="text-slate-300 font-mono">JASHWANTH RAJ</span></span>
    </div>
    <div class="flex items-center space-x-4 text-[9px]">
      <div>SESSION <span class="text-slate-300 font-mono" id="val-session-time">00:00:00</span></div>
      <div class="hidden sm:inline">SHORTCUT: <kbd class="px-1 py-0.2 bg-[#05080e] border border-os-border text-os-amber rounded font-mono">Ctrl+K</kbd></div>
    </div>
  </footer>

  <!-- ════════════════════════════════════════════════════════════
       STARK TACTICAL MODALS & DIALOGS
       ════════════════════════════════════════════════════════════ -->

  <!-- ── 1. Settings / Intelligence & APIs Modal ── -->
  <div class="dialog-backdrop" id="modal-settings" style="display: none;" onmousedown="closeDialogOnBackdrop(event, 'settings')">
    <div class="dialog-modal dialog-wide">
      <div class="flex justify-between items-center border-b border-os-border/80 pb-2 mb-3">
        <div>
          <span class="text-[9px] font-mono text-os-amber tracking-widest uppercase">INTELLIGENCE &amp; APIS</span>
          <h2 class="text-base font-bold text-white font-chakra">Multi-Model &amp; Security Settings</h2>
        </div>
        <button class="text-slate-400 hover:text-white font-mono text-base" onclick="closeDialog('settings')">✕</button>
      </div>

      <div class="space-y-4 text-xs font-mono">
        <div>
          <label class="text-slate-300 text-[10px] block mb-1">LOCAL MODEL (Ollama)</label>
          <select id="select-active-model" class="w-full bg-[#0c1320] border border-os-border/90 rounded px-2 py-1.5 text-os-amber" onchange="switchModel(this.value)">
            <option value="hermes3:3b">hermes3:3b (Recommended)</option>
            <option value="tinydolphin:1.1b">tinydolphin:1.1b (Ultra Fast)</option>
            <option value="qwen3-vl:2b">qwen3-vl:2b (Vision)</option>
          </select>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label class="text-slate-300 text-[10px] block mb-1">GOOGLE GEMINI API KEY</label>
            <input type="password" id="api-key-gemini" placeholder="AIzaSy..." class="w-full bg-[#0c1320] border border-os-border/90 rounded px-2 py-1 text-slate-200">
          </div>
          <div>
            <label class="text-slate-300 text-[10px] block mb-1">GROQ API KEY</label>
            <input type="password" id="api-key-groq" placeholder="gsk_..." class="w-full bg-[#0c1320] border border-os-border/90 rounded px-2 py-1 text-slate-200">
          </div>
          <div>
            <label class="text-slate-300 text-[10px] block mb-1">OPENROUTER API KEY</label>
            <input type="password" id="api-key-openrouter" placeholder="sk-or-..." class="w-full bg-[#0c1320] border border-os-border/90 rounded px-2 py-1 text-slate-200">
          </div>
          <div>
            <label class="text-slate-300 text-[10px] block mb-1">STATIC CLOUD TUNNEL URL</label>
            <input type="text" id="settings-cloud-url" placeholder="https://..." class="w-full bg-[#0c1320] border border-os-border/90 rounded px-2 py-1 text-slate-200">
          </div>
        </div>

        <div class="flex justify-end space-x-2 pt-2 border-t border-os-border/80">
          <button class="px-3 py-1 bg-os-card hover:bg-slate-800 border border-os-border rounded text-slate-300" onclick="closeDialog('settings')">Cancel</button>
          <button class="px-4 py-1 bg-os-amber hover:bg-amber-400 text-os-black font-bold rounded" onclick="saveSettings()">Save Configuration</button>
        </div>
      </div>
    </div>
  </div>

  <!-- ── 2. Remote Desktop & VNC Streaming Modal ── -->
  <div class="dialog-backdrop" id="modal-remote" style="display: none;" onmousedown="closeDialogOnBackdrop(event, 'remote')">
    <div class="dialog-modal dialog-wide">
      <div class="flex justify-between items-center border-b border-os-border/80 pb-2 mb-3">
        <div>
          <span class="text-[9px] font-mono text-os-cyan tracking-widest uppercase">REMOTE WORKSTATION VIEW</span>
          <h2 class="text-base font-bold text-white font-chakra">Live Windows Screen Stream</h2>
        </div>
        <button class="text-slate-400 hover:text-white font-mono text-base" onclick="closeDialog('remote')">✕</button>
      </div>

      <div class="space-y-2">
        <div class="flex items-center justify-between text-[10px] font-mono">
          <span class="text-emerald-400 flex items-center space-x-1"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span><span>STREAM ACTIVE</span></span>
          <div class="flex space-x-1.5">
            <button class="px-2 py-0.5 rounded bg-os-card border border-os-border text-slate-300 hover:text-white" onclick="zoomRemote(1.2)">🔍+ Zoom</button>
            <button class="px-2 py-0.5 rounded bg-os-card border border-os-border text-slate-300 hover:text-white" onclick="zoomRemote(0.8)">🔍- Out</button>
            <button class="px-2 py-0.5 rounded bg-os-card border border-os-border text-slate-300 hover:text-white" onclick="resetRemoteZoom()">Fit</button>
            <button class="px-2 py-0.5 rounded bg-os-amber text-os-black font-bold" onclick="refreshRemoteStream()">🔄 Refresh</button>
          </div>
        </div>

        <div class="w-full h-96 bg-black rounded border border-os-border flex items-center justify-center overflow-hidden relative" id="remote-stage">
          <img id="remote-stream-img" src="" alt="Live Desktop View" class="max-w-full max-h-full cursor-crosshair transition-transform" onclick="handleRemoteDesktopClick(event)">
        </div>
      </div>
    </div>
  </div>

  <!-- ── 3. Face Sentinel Modal ── -->
  <div class="dialog-backdrop" id="modal-sentinel" style="display: none;" onmousedown="closeDialogOnBackdrop(event, 'sentinel')">
    <div class="dialog-modal">
      <div class="flex justify-between items-center border-b border-os-border/80 pb-2 mb-3">
        <div>
          <span class="text-[9px] font-mono text-os-cyan tracking-widest uppercase">BIOMETRIC SECURITY</span>
          <h2 class="text-base font-bold text-white font-chakra">Face Sentinel Scanner</h2>
        </div>
        <button class="text-slate-400 hover:text-white font-mono text-base" onclick="closeDialog('sentinel')">✕</button>
      </div>

      <div class="space-y-3 text-xs font-mono">
        <div class="w-full h-56 bg-black rounded border border-os-border flex items-center justify-center relative overflow-hidden">
          <video id="sentinel-video" class="w-full h-full object-cover transform -scale-x-100" autoplay playsinline muted></video>
          <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div class="w-36 h-44 border-2 border-dashed border-os-cyan/60 rounded-full animate-pulse"></div>
          </div>
        </div>
        <div class="flex justify-between items-center">
          <span class="text-slate-400 text-[10px]" id="sentinel-diag-status">Scanner Ready</span>
          <button class="px-3 py-1 bg-os-cyan text-os-black font-bold rounded" onclick="enrollFaceBiometrics()">Enroll Face Profile</button>
        </div>
      </div>
    </div>
  </div>

  <!-- ── 4. Virtual Gamepad Modal ── -->
  <div class="dialog-backdrop" id="modal-gamepad" style="display: none;" onmousedown="closeDialogOnBackdrop(event, 'gamepad')">
    <div class="dialog-modal dialog-wide">
      <div class="flex justify-between items-center border-b border-os-border/80 pb-2 mb-3">
        <div>
          <span class="text-[9px] font-mono text-os-amber tracking-widest uppercase">TACTICAL GAMEPAD</span>
          <h2 class="text-base font-bold text-white font-chakra">Landscape Virtual Controller</h2>
        </div>
        <button class="text-slate-400 hover:text-white font-mono text-base" onclick="closeDialog('gamepad')">✕</button>
      </div>

      <div class="flex items-center justify-between p-4 bg-slate-950 rounded border border-os-border">
        <!-- Thumbstick -->
        <div class="relative w-36 h-36 rounded-full border border-os-border bg-[#0a101b] flex items-center justify-center" id="stick-base">
          <span class="absolute top-2 text-[9px] font-mono text-slate-500">W</span>
          <span class="absolute bottom-2 text-[9px] font-mono text-slate-500">S</span>
          <span class="absolute left-2 text-[9px] font-mono text-slate-500">A</span>
          <span class="absolute right-2 text-[9px] font-mono text-slate-500">D</span>
          <div class="w-14 h-14 rounded-full bg-os-amber/80 border border-os-amber shadow-lg cursor-grab" id="stick-nub"></div>
        </div>

        <!-- Trackpad -->
        <div class="flex-1 max-w-xs h-36 border border-os-border bg-[#080d15] rounded mx-4 flex items-center justify-center text-[10px] font-mono text-slate-500">
          🎯 3D LOOK TRACKPAD
        </div>

        <!-- Action Buttons -->
        <div class="grid grid-cols-3 gap-2 w-36 h-36 items-center justify-items-center">
          <span></span>
          <button class="w-10 h-10 rounded-full bg-os-card border border-os-amber text-os-amber font-bold text-xs" onmousedown="dispatchKey('r','down')" onmouseup="dispatchKey('r','up')">Y</button>
          <span></span>
          <button class="w-10 h-10 rounded-full bg-os-card border border-os-cyan text-os-cyan font-bold text-xs" onmousedown="dispatchKey('e','down')" onmouseup="dispatchKey('e','up')">X</button>
          <span></span>
          <button class="w-10 h-10 rounded-full bg-os-card border border-red-500 text-red-400 font-bold text-xs" onmousedown="dispatchKey('c','down')" onmouseup="dispatchKey('c','up')">B</button>
          <span></span>
          <button class="w-10 h-10 rounded-full bg-os-card border border-emerald-500 text-emerald-400 font-bold text-xs" onmousedown="dispatchKey('space','down')" onmouseup="dispatchKey('space','up')">A</button>
          <span></span>
        </div>
      </div>
    </div>
  </div>

  <!-- ── 5. Audio Mixer Modal ── -->
  <div class="dialog-backdrop" id="modal-mixer" style="display: none;" onmousedown="closeDialogOnBackdrop(event, 'mixer')">
    <div class="dialog-modal">
      <div class="flex justify-between items-center border-b border-os-border/80 pb-2 mb-3">
        <div>
          <span class="text-[9px] font-mono text-os-amber tracking-widest uppercase">AUDIO CONTROL</span>
          <h2 class="text-base font-bold text-white font-chakra">Windows Session Mixer</h2>
        </div>
        <button class="text-slate-400 hover:text-white font-mono text-base" onclick="closeDialog('mixer')">✕</button>
      </div>

      <div class="space-y-3 font-mono text-xs">
        <div>
          <label class="text-[10px] text-slate-400 block mb-1">MASTER OUTPUT VOLUME</label>
          <input type="range" min="0" max="100" value="75" class="w-full accent-os-amber" oninput="setMasterVolume(this.value)">
        </div>
        <div id="mixer-apps-container" class="space-y-2 pt-2 border-t border-os-border/80">
          <p class="text-[10px] text-slate-500">Active Audio Sessions: System, Chrome, Media Player</p>
        </div>
      </div>
    </div>
  </div>

  <!-- ── 6. Activity Logs Modal ── -->
  <div class="dialog-backdrop" id="modal-activity" style="display: none;" onmousedown="closeDialogOnBackdrop(event, 'activity')">
    <div class="dialog-modal dialog-wide">
      <div class="flex justify-between items-center border-b border-os-border/80 pb-2 mb-3">
        <div>
          <span class="text-[9px] font-mono text-os-amber tracking-widest uppercase">SYSTEM AUDIT TRAIL</span>
          <h2 class="text-base font-bold text-white font-chakra">Complete Event Log</h2>
        </div>
        <button class="text-slate-400 hover:text-white font-mono text-base" onclick="closeDialog('activity')">✕</button>
      </div>
      <div class="h-80 overflow-y-auto space-y-1 font-mono text-[10px]" id="modal-activity-lines"></div>
    </div>
  </div>

  <!-- ── 7. About EDITH Modal ── -->
  <div class="dialog-backdrop" id="modal-about" style="display: none;" onmousedown="closeDialogOnBackdrop(event, 'about')">
    <div class="dialog-modal">
      <div class="flex justify-between items-center border-b border-os-border/80 pb-2 mb-3">
        <div>
          <span class="text-[9px] font-mono text-os-amber tracking-widest uppercase">SYSTEM ARCHITECTURE</span>
          <h2 class="text-base font-bold text-white font-chakra">E.D.I.T.H. Mark II OS</h2>
        </div>
        <button class="text-slate-400 hover:text-white font-mono text-base" onclick="closeDialog('about')">✕</button>
      </div>
      <div class="space-y-2 text-xs font-mono text-slate-300">
        <p><strong class="text-os-amber">Creator:</strong> Jashwanth Raj</p>
        <p><strong class="text-os-cyan">Version:</strong> 3.0.0 (Local-First Autonomous AI OS)</p>
        <p><strong class="text-emerald-400">Features:</strong> Level 0 Reflexes, Three.js Holographic Core, MediaPipe Dual-Hand Gestures, Low-Latency Remote Desktop, Biometric Sentinel, Mobile LAN Gateway.</p>
      </div>
    </div>
  </div>

  <!-- ════════════════════════════════════════════════════════════
       SCRIPTS: THREE.JS FIBONACCI ORB, SPEECH, GESTURES & CONTROLS
       ════════════════════════════════════════════════════════════ -->
  <script src="gestures.js?v=3.0.0"></script>
  <script src="edith-gateway.js?v=1"></script>

  <script data-purpose="edith-system-logic">
    // State management
    let globeGroup, wireMat, pMat, ring1Mesh, ring2Mesh, ringEquatorMesh, auraMat, innerNode;
    let isDragging = false, prevMousePos = { x: 0, y: 0 }, velocityX = 0, velocityY = 0;
    let ttsEnabled = true;
    let isListening = false;
    let isContinuousMic = false;
    let recognition = null;
    let activeCharacter = 'jarvis';
    let isExecutingCommand = false;
    let sessionSeconds = 0;

    const PERSONA_COLORS = {
      'EDITH': 0x00f0ff,
      'JARVIS': 0xffa800,
      'FRIDAY': 0x38bdf8,
      'KAREN': 0x34d399,
      'SPIDEY': 0xf87171,
      'ULTRON': 0xef4444
    };

    document.addEventListener("DOMContentLoaded", () => {
      if (window.lucide) lucide.createIcons();

      // Start live clock & session timer
      updateClock();
      setInterval(updateClock, 1000);
      setInterval(() => {
        sessionSeconds++;
        const hrs = String(Math.floor(sessionSeconds / 3600)).padStart(2, '0');
        const mins = String(Math.floor((sessionSeconds % 3600) / 60)).padStart(2, '0');
        const secs = String(sessionSeconds % 60).padStart(2, '0');
        const el = document.getElementById('val-session-time');
        if (el) el.textContent = `${hrs}:${mins}:${secs}`;
      }, 1000);

      // Mount Three.js Holographic Globe with Golden Fibonacci Sphere
      initThreeJsGlobe();

      // Dynamic Equalizer visualizer
      initAudioEqualizer();

      // Persona tabs
      setupPersonaSwitcher();

      // Poll telemetry
      fetchTelemetry();
      setInterval(fetchTelemetry, 2000);

      // Load active models & cloud config
      loadActiveModels();
      loadMobileConfig();

      // Spacebar to talk
      window.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && document.activeElement.tagName !== 'TEXTAREA' && document.activeElement.tagName !== 'INPUT') {
          e.preventDefault();
          window.userSpeakingLevel = 0.9;
          if (!isListening) toggleVoice();
        }
        if (e.ctrlKey && e.key.toLowerCase() === 'k') {
          e.preventDefault();
          document.getElementById('command-input')?.focus();
        }
      });
      window.addEventListener('keyup', (e) => {
        if (e.code === 'Space' && !isContinuousMic && isListening) {
          toggleVoice();
        }
      });

      logActivity("EDITH Autonomous OS online · Reflex engine ready.");
    });

    function updateClock() {
      const clockEl = document.getElementById("live-clock");
      if (clockEl) {
        const now = new Date();
        const hrs = String(now.getHours()).padStart(2, '0');
        const mins = String(now.getMinutes()).padStart(2, '0');
        const secs = String(now.getSeconds()).padStart(2, '0');
        clockEl.textContent = `${hrs}:${mins}:${secs}`;
      }
    }

    // ── Three.js Holographic Fibonacci Sphere ──
    function initThreeJsGlobe() {
      const container = document.getElementById('threejs-globe-container');
      if (!container || !window.THREE) return;

      const width = container.clientWidth || 600;
      const height = container.clientHeight || 450;

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
      camera.position.z = 21;

      const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      container.appendChild(renderer.domElement);

      globeGroup = new THREE.Group();
      scene.add(globeGroup);

      // Palette
      const primaryAmber = 0xffa800;
      const brightGold = 0xffbe28;
      const warmGlow = 0xff8c00;
      const hotCore = 0xffea78;

      // 1. Fibonacci Sphere Point Cloud (3,800 points)
      const pointCount = 3800;
      const pGeo = new THREE.BufferGeometry();
      const pPos = new Float32Array(pointCount * 3);
      const pColors = new Float32Array(pointCount * 3);
      const color1 = new THREE.Color(primaryAmber);
      const color2 = new THREE.Color(hotCore);
      const goldenRatio = (1 + Math.sqrt(5)) / 2;
      const radius = 6.2;

      for (let i = 0; i < pointCount; i++) {
        const theta = (2 * Math.PI * i) / goldenRatio;
        const phi = Math.acos(1 - (2 * (i + 0.5)) / pointCount);
        const r = radius + (Math.random() - 0.5) * 0.15;
        const x = r * Math.sin(phi) * Math.cos(theta);
        const y = r * Math.sin(phi) * Math.sin(theta);
        const z = r * Math.cos(phi);

        pPos[i * 3] = x;
        pPos[i * 3 + 1] = y;
        pPos[i * 3 + 2] = z;

        const mixedColor = color1.clone().lerp(color2, Math.random() * 0.4);
        pColors[i * 3] = mixedColor.r;
        pColors[i * 3 + 1] = mixedColor.g;
        pColors[i * 3 + 2] = mixedColor.b;
      }

      pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
      pGeo.setAttribute('color', new THREE.BufferAttribute(pColors, 3));

      pMat = new THREE.PointsMaterial({
        size: 0.16,
        vertexColors: true,
        transparent: true,
        opacity: 0.95,
        blending: THREE.AdditiveBlending
      });
      const pointCloud = new THREE.Points(pGeo, pMat);
      globeGroup.add(pointCloud);

      // 2. Latitude & Longitude Wireframe Sphere
      const wireGeo = new THREE.SphereGeometry(6.25, 52, 36);
      wireMat = new THREE.MeshBasicMaterial({
        color: primaryAmber,
        wireframe: true,
        transparent: true,
        opacity: 0.38,
        blending: THREE.AdditiveBlending
      });
      const wireSphere = new THREE.Mesh(wireGeo, wireMat);
      globeGroup.add(wireSphere);

      // 3. Tactical Gimbal Rings
      function createTacticalRing(r, tube, rotX, rotY, rotZ, opacity) {
        const geo = new THREE.TorusGeometry(r, tube, 6, 120);
        const mat = new THREE.MeshBasicMaterial({
          color: brightGold,
          transparent: true,
          opacity: opacity,
          blending: THREE.AdditiveBlending
        });
        const ring = new THREE.Mesh(geo, mat);
        ring.rotation.set(rotX, rotY, rotZ);
        globeGroup.add(ring);
        return ring;
      }

      ring1Mesh = createTacticalRing(8.2, 0.032, Math.PI / 3.2, 0.3, 0, 0.65);
      ring2Mesh = createTacticalRing(9.4, 0.026, -Math.PI / 3.8, -0.4, 0.2, 0.5);
      ringEquatorMesh = createTacticalRing(6.8, 0.035, Math.PI / 2, 0, 0, 0.4);

      // 4. Inner Octahedron Singularity
      const innerGeo = new THREE.OctahedronGeometry(2.0, 1);
      const innerMat = new THREE.MeshBasicMaterial({
        color: hotCore,
        wireframe: true,
        transparent: true,
        opacity: 0.75,
        blending: THREE.AdditiveBlending
      });
      innerNode = new THREE.Mesh(innerGeo, innerMat);
      globeGroup.add(innerNode);

      // 5. Speaking Aura
      const auraGeo = new THREE.IcosahedronGeometry(7.4, 3);
      auraMat = new THREE.MeshBasicMaterial({
        color: warmGlow,
        wireframe: true,
        transparent: true,
        opacity: 0.15,
        blending: THREE.AdditiveBlending
      });
      const auraMesh = new THREE.Mesh(auraGeo, auraMat);
      globeGroup.add(auraMesh);

      // 6. Orbiting Satellite Beacon
      const satGeo = new THREE.SphereGeometry(0.18, 12, 12);
      const satMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
      const satBeacon = new THREE.Mesh(satGeo, satMat);
      globeGroup.add(satBeacon);

      // Gesture & API attachments
      window.rotateOrb = function (dx, dy) {
        if (globeGroup) {
          globeGroup.rotation.y += dx;
          globeGroup.rotation.x += dy;
        }
      };
      window.scaleOrb = function (factor) {
        if (globeGroup) {
          const s = Math.max(0.6, Math.min(2.5, globeGroup.scale.x * (1 + factor)));
          globeGroup.scale.set(s, s, s);
        }
      };
      window.setCoreState = function (state) {
        if (state === 'speaking') {
          window.edithSpeaking = true;
        } else if (state === 'idle') {
          window.edithSpeaking = false;
        }
      };

      // Mouse drag controls
      renderer.domElement.addEventListener('mousedown', (e) => {
        isDragging = true;
        renderer.domElement.style.cursor = 'grabbing';
        prevMousePos = { x: e.clientX, y: e.clientY };
      });
      window.addEventListener('mouseup', () => {
        if (isDragging) {
          isDragging = false;
          renderer.domElement.style.cursor = 'grab';
        }
      });
      window.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        const deltaX = e.clientX - prevMousePos.x;
        const deltaY = e.clientY - prevMousePos.y;
        globeGroup.rotation.y += deltaX * 0.007;
        globeGroup.rotation.x += deltaY * 0.007;
        velocityX = deltaX * 0.0035;
        velocityY = deltaY * 0.0035;
        prevMousePos = { x: e.clientX, y: e.clientY };
      });

      // Touch controls
      renderer.domElement.addEventListener('touchstart', (e) => {
        if (e.touches.length > 0) {
          isDragging = true;
          prevMousePos = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        }
      }, { passive: true });
      window.addEventListener('touchend', () => { isDragging = false; });
      renderer.domElement.addEventListener('touchmove', (e) => {
        if (isDragging && e.touches.length > 0) {
          const deltaX = e.touches[0].clientX - prevMousePos.x;
          const deltaY = e.touches[0].clientY - prevMousePos.y;
          globeGroup.rotation.y += deltaX * 0.007;
          globeGroup.rotation.x += deltaY * 0.007;
          prevMousePos = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        }
      }, { passive: true });

      const clock = new THREE.Clock();

      function animate() {
        requestAnimationFrame(animate);
        const time = clock.getElapsedTime();

        if (!isDragging) {
          velocityX *= 0.94;
          velocityY *= 0.94;
          globeGroup.rotation.y += 0.0028 + velocityX;
          globeGroup.rotation.x += velocityY;
        }

        pointCloud.rotation.y = time * 0.06;
        wireSphere.rotation.y = -time * 0.04;
        innerNode.rotation.x = time * 0.45;
        innerNode.rotation.y = time * 0.55;

        ring1Mesh.rotation.z = time * 0.18;
        ring2Mesh.rotation.z = -time * 0.14;
        ringEquatorMesh.rotation.z = time * 0.1;

        const satAngle = time * 1.25;
        satBeacon.position.set(
          Math.cos(satAngle) * 8.6,
          Math.sin(satAngle * 0.8) * 3.8,
          Math.sin(satAngle) * 8.6
        );

        // Speaking aura reactions
        const isSpeaking = window.edithSpeaking === true;
        const userVol = window.userSpeakingLevel || 0;

        if (isSpeaking) {
          const auraPulse = 1.0 + Math.sin(time * 8.0) * 0.22 + Math.cos(time * 13.0) * 0.08;
          auraMesh.scale.set(auraPulse, auraPulse, auraPulse);
          auraMat.opacity = 0.42 + Math.sin(time * 9.0) * 0.25;
          innerNode.scale.set(1.45, 1.45, 1.45);
          wireSphere.scale.set(1.05, 1.05, 1.05);
        } else if (userVol > 0.05) {
          const waveScale = 1.0 + userVol * 0.26;
          auraMesh.scale.set(waveScale, waveScale, waveScale);
          auraMat.opacity = 0.22 + userVol * 0.45;
          wireSphere.scale.set(1.0 + userVol * 0.08, 1.0 + userVol * 0.08, 1.0 + userVol * 0.08);
        } else {
          const breath = 1.0 + Math.sin(time * 2.0) * 0.025;
          auraMesh.scale.set(breath, breath, breath);
          auraMat.opacity = 0.14 + Math.sin(time * 2.0) * 0.06;
          wireSphere.scale.set(1.0, 1.0, 1.0);
          innerNode.scale.set(1.0, 1.0, 1.0);
        }

        renderer.render(scene, camera);
      }
      animate();

      window.addEventListener('resize', () => {
        const w = container.clientWidth || 600;
        const h = container.clientHeight || 450;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
      });
    }

    // ── Equalizer LED Wave Bars Loop ──
    function initAudioEqualizer() {
      const bars = document.querySelectorAll('.eq-bar');
      setInterval(() => {
        const isUserSpeaking = (window.userSpeakingLevel || 0) > 0.1;
        const isEdithSpeaking = window.edithSpeaking === true;

        bars.forEach((bar) => {
          let h = 4;
          if (isUserSpeaking) h = Math.floor(Math.random() * 24) + 6;
          else if (isEdithSpeaking) h = Math.floor(Math.random() * 28) + 8;
          else h = Math.floor(Math.random() * 8) + 3;
          bar.style.height = `${h}px`;
        });
      }, 90);
    }

    // ── Persona Switcher ──
    function setupPersonaSwitcher() {
      const tabs = document.querySelectorAll('.persona-tab');
      tabs.forEach(tab => {
        tab.addEventListener('click', () => {
          const persona = tab.dataset.persona;
          switchPersona(persona);
        });
      });
    }

    function switchPersona(persona) {
      activeCharacter = persona.toLowerCase();
      const tabs = document.querySelectorAll('.persona-tab');
      tabs.forEach(t => {
        if (t.dataset.persona === persona) {
          t.className = 'persona-tab px-3 py-0.5 text-[10px] rounded-full tracking-[0.14em] bg-transparent text-os-amber border border-os-amber/80 flex items-center space-x-1.5 transition glow-amber-sm';
          t.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-os-amber"></span><span>${persona}</span>`;
        } else {
          t.className = 'persona-tab px-2.5 py-0.5 text-[10px] rounded tracking-[0.14em] text-slate-400 hover:text-white transition';
          t.textContent = t.dataset.persona;
        }
      });

      const charLabel = document.getElementById('active-char-label');
      if (charLabel) charLabel.textContent = `CHAR: ${persona}`;
      const badge = document.getElementById('active-voice-badge');
      if (badge) badge.innerHTML = `<span>${persona}</span>`;

      // Update Three.js globe color
      const hex = PERSONA_COLORS[persona] || 0xffa800;
      if (wireMat) wireMat.color.setHex(hex);
      if (pMat) pMat.color.setHex(hex);
      if (ring1Mesh) ring1Mesh.material.color.setHex(hex);
      if (ring2Mesh) ring2Mesh.material.color.setHex(hex);
      if (ringEquatorMesh) ringEquatorMesh.material.color.setHex(hex);
      if (auraMat) auraMat.color.setHex(hex);

      // Notify backend
      fetch('/voice/character', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ character: activeCharacter })
      }).catch(() => {});

      logActivity(`Persona shifted to ${persona}. Voice & theme synchronized.`);
    }

    // ── Voice Input & Web Speech API ──
    function toggleVoice() {
      if (isListening) stopVoiceListening();
      else startVoiceListening();
    }

    function startVoiceListening() {
      const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRec) {
        logActivity("WebSpeech recognition unavailable in browser.");
        return;
      }
      try {
        recognition = new SpeechRec();
        recognition.continuous = isContinuousMic;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
          isListening = true;
          window.userSpeakingLevel = 0.85;
          document.getElementById('mic-trigger-btn')?.classList.add('ring-4', 'ring-os-amber/80');
          document.getElementById('val-input-signal').textContent = 'RECEIVING';
          document.getElementById('val-input-signal').className = 'text-os-cyan font-mono font-bold';
          document.getElementById('voice-caption-text').textContent = isContinuousMic ? 'Always listening... Speak anytime' : 'Listening... Speak naturally';
          logActivity("Voice channel active - listening for orders...");
        };

        recognition.onresult = (e) => {
          let transcript = '';
          for (let i = e.resultIndex; i < e.results.length; i++) {
            transcript += e.results[i][0].transcript;
          }
          document.getElementById('voice-caption-text').textContent = `“${transcript}”`;
          if (e.results[e.results.length - 1].isFinal) {
            submitTextCommand(transcript);
          }
        };

        recognition.onerror = () => { stopVoiceListening(); };
        recognition.onend = () => {
          stopVoiceListening();
          if (isContinuousMic) setTimeout(startVoiceListening, 300);
        };

        recognition.start();
      } catch (err) {
        console.warn("Speech recognition warning:", err);
      }
    }

    function stopVoiceListening() {
      isListening = false;
      window.userSpeakingLevel = 0;
      if (recognition) { try { recognition.stop(); } catch (_) {} }
      document.getElementById('mic-trigger-btn')?.classList.remove('ring-4', 'ring-os-amber/80');
      document.getElementById('val-input-signal').textContent = 'STANDBY';
      document.getElementById('val-input-signal').className = 'text-slate-300 font-mono font-bold';
      document.getElementById('voice-caption-text').innerHTML = isContinuousMic
        ? 'Always-Listening active // Speak anytime'
        : 'Tap to speak or press <kbd class="px-1.5 py-0.2 rounded bg-os-card border border-os-border text-os-amber text-[8px] font-mono">Space</kbd>';
    }

    function toggleContinuousMic() {
      isContinuousMic = !isContinuousMic;
      const chk = document.getElementById('chk-continuous-mic');
      if (chk) chk.checked = isContinuousMic;
      const btn = document.getElementById('btn-toggle-continuous-mic');
      if (btn) btn.classList.toggle('text-os-amber', isContinuousMic);
      const lbl = document.getElementById('lbl-continuous-mic-state');
      if (lbl) lbl.textContent = isContinuousMic ? 'Always Active' : 'Continuous Off';

      if (isContinuousMic && !isListening) startVoiceListening();
      else if (!isContinuousMic && isListening) stopVoiceListening();

      logActivity(`Continuous mic ${isContinuousMic ? 'activated' : 'deactivated'}.`);
    }

    function toggleTts() {
      ttsEnabled = !ttsEnabled;
      const tgl = document.getElementById('tgl-voice-out');
      if (tgl) tgl.checked = ttsEnabled;
      const lbl = document.getElementById('lbl-tts-state');
      if (lbl) lbl.textContent = ttsEnabled ? 'Speech Enabled' : 'Muted';
      logActivity(`Voice speech synthesis ${ttsEnabled ? 'enabled' : 'muted'}.`);
    }

    function speakText(text) {
      if (!ttsEnabled || !text) return;
      window.edithSpeaking = true;
      try {
        const audio = new Audio(`/voice/tts?text=${encodeURIComponent(text)}&char=${activeCharacter}`);
        audio.onended = () => { window.edithSpeaking = false; };
        audio.onerror = () => {
          if (window.speechSynthesis) {
            const utter = new SpeechSynthesisUtterance(text);
            utter.onend = () => { window.edithSpeaking = false; };
            window.speechSynthesis.speak(utter);
          } else {
            window.edithSpeaking = false;
          }
        };
        audio.play().catch(() => {
          if (window.speechSynthesis) {
            const utter = new SpeechSynthesisUtterance(text);
            utter.onend = () => { window.edithSpeaking = false; };
            window.speechSynthesis.speak(utter);
          } else {
            window.edithSpeaking = false;
          }
        });
      } catch (_) {
        window.edithSpeaking = false;
      }
    }

    // ── Command Submission ──
    async function submitTextCommand(cmdText) {
      const text = (cmdText || '').trim();
      if (!text || isExecutingCommand) return;
      isExecutingCommand = true;

      appendChatMessage('user', text);
      logActivity(`Order dispatched: ${text}`);

      const headline = document.getElementById('core-headline');
      if (headline) headline.textContent = 'Executing order...';

      const start = performance.now();
      try {
        const res = await fetch('/cmd', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: text, request_id: String(Date.now()) })
        });
        const latency = Math.round(performance.now() - start);
        document.getElementById('val-ping-latency').textContent = latency;

        const data = await res.json();
        const reply = data.result || 'Command acknowledged.';
        appendChatMessage('assistant', reply);

        logActivity(`Order complete (${latency}ms): ${text.slice(0, 32)}`);

        if (ttsEnabled && !data.server_spoken) speakText(reply);

        if (data.embed_url) playInHudMedia(data.embed_url, text);
      } catch (err) {
        appendChatMessage('assistant', `Execution error: ${err.message}`);
        logActivity(`Execution failed: ${err.message}`);
      } finally {
        isExecutingCommand = false;
        if (headline) headline.textContent = 'At your service.';
      }
    }

    function sendUserCommand() {
      const input = document.getElementById('command-input');
      if (!input || !input.value.trim()) return;
      const val = input.value.trim();
      input.value = '';
      submitTextCommand(val);
    }

    function appendChatMessage(sender, text) {
      const container = document.getElementById('chat-messages-container');
      if (!container) return;

      const wrapper = document.createElement('div');
      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

      if (sender === 'user') {
        wrapper.className = 'flex flex-col items-end space-y-1';
        wrapper.innerHTML = `
          <div class="flex items-center space-x-1.5 text-[9px] text-slate-400 font-mono">
            <span class="text-os-cyan font-bold tracking-wider">YOU</span>
            <span>${timeStr}</span>
          </div>
          <div class="bg-os-card border border-os-border text-slate-200 px-3 py-2 rounded-lg max-w-[90%] text-xs font-normal tracking-wide">
            ${escapeHtml(text)}
          </div>
        `;
      } else {
        wrapper.className = 'flex flex-col items-start space-y-1';
        wrapper.innerHTML = `
          <div class="flex items-center space-x-1.5 text-[9px] text-slate-400 font-mono">
            <span class="text-os-amber font-bold font-chakra tracking-wider">${activeCharacter.toUpperCase()}</span>
            <span>${timeStr}</span>
          </div>
          <div class="bg-[#0f1726] border border-os-amber/50 text-slate-200 px-3 py-2 rounded-lg max-w-[95%] leading-relaxed text-[12px] relative glow-amber-sm font-normal tracking-wide">
            ${escapeHtml(text)}
          </div>
        `;
      }

      container.appendChild(wrapper);
      container.scrollTop = container.scrollHeight;
    }

    function clearConversation() {
      const container = document.getElementById('chat-messages-container');
      if (container) {
        container.innerHTML = `
          <div class="flex items-center justify-center py-2 text-[10px] text-slate-400 font-mono uppercase tracking-widest">
            -- SESSION RESET -- READY FOR INPUT --
          </div>
        `;
      }
      logActivity("Conversation session cleared.");
    }

    function switchRightTab(tab) {
      const btnConv = document.getElementById('tab-conv');
      const btnGuide = document.getElementById('tab-guide');
      const chatCont = document.getElementById('chat-messages-container');
      const guideCont = document.getElementById('guide-tab-container');

      if (tab === 'conv') {
        btnConv.className = 'py-1.5 px-3 border-b-2 border-os-amber text-slate-200 transition';
        btnGuide.className = 'py-1.5 px-3 border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition';
        chatCont.classList.remove('hidden');
        guideCont.classList.add('hidden');
      } else {
        btnGuide.className = 'py-1.5 px-3 border-b-2 border-os-amber text-slate-200 transition';
        btnConv.className = 'py-1.5 px-3 border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition';
        guideCont.classList.remove('hidden');
        chatCont.classList.add('hidden');
      }
    }

    function filterGuideChips(q) {
      const query = (q || '').toLowerCase();
      document.querySelectorAll('#guide-chips-list button').forEach(btn => {
        btn.style.display = btn.innerText.toLowerCase().includes(query) ? '' : 'none';
      });
    }

    // ── Telemetry Polling ──
    async function fetchTelemetry() {
      try {
        const res = await fetch('/api/metrics');
        if (!res.ok) return;
        const data = await res.json();

        const cpu = data.cpu_percent || 0;
        const ram = data.ram_percent || 0;
        const disk = data.disk_percent || 0;
        const bat = data.battery_percent ?? 100;

        document.getElementById('val-cpu').textContent = `${Math.round(cpu)}%`;
        document.getElementById('bar-cpu').style.width = `${Math.min(100, Math.round(cpu))}%`;

        document.getElementById('val-ram').textContent = `${Math.round(ram)}% (${data.ram_used_mb || 0}MB)`;
        document.getElementById('bar-ram').style.width = `${Math.min(100, Math.round(ram))}%`;

        document.getElementById('val-disk').textContent = `${Math.round(disk)}%`;
        document.getElementById('bar-disk').style.width = `${Math.min(100, Math.round(disk))}%`;

        document.getElementById('val-battery').textContent = `${Math.round(bat)}%${data.power_plugged ? ' ⚡' : ''}`;

        const hostEl = document.getElementById('host-status-text');
        const hostDot = document.getElementById('host-status-dot');
        if (hostEl && hostDot) {
          hostEl.textContent = data.host_online ? 'PC LINKED' : 'HOST OFFLINE';
          hostDot.className = data.host_online ? 'w-1.5 h-1.5 rounded-full bg-emerald-400' : 'w-1.5 h-1.5 rounded-full bg-os-amber';
        }
      } catch (_) {}
    }

    // ── Dialog & Modals ──
    function openDialog(name) {
      const el = document.getElementById(`modal-${name}`);
      if (el) el.style.display = 'flex';
      if (name === 'remote') refreshRemoteStream();
    }

    function closeDialog(name) {
      const el = document.getElementById(`modal-${name}`);
      if (el) el.style.display = 'none';
    }

    function closeDialogOnBackdrop(e, name) {
      if (e.target.id === `modal-${name}`) closeDialog(name);
    }

    function openNav(name) {
      if (name) openDialog(name);
    }

    // ── Remote Desktop Controls ──
    let remoteZoom = 1.0;
    function refreshRemoteStream() {
      const img = document.getElementById('remote-stream-img');
      if (img) img.src = `/stream/screen?t=${Date.now()}`;
    }
    function zoomRemote(f) {
      remoteZoom = Math.max(0.5, Math.min(3.0, remoteZoom * f));
      const img = document.getElementById('remote-stream-img');
      if (img) img.style.transform = `scale(${remoteZoom})`;
    }
    function resetRemoteZoom() {
      remoteZoom = 1.0;
      const img = document.getElementById('remote-stream-img');
      if (img) img.style.transform = 'scale(1.0)';
    }
    function handleRemoteDesktopClick(e) {
      const rect = e.target.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = (e.clientY - rect.top) / rect.height;
      fetch('/api/remote/click', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ x: Math.max(0, Math.min(1, x)), y: Math.max(0, Math.min(1, y)), button: 'left' })
      });
    }

    // ── Virtual Gamepad Key Dispatcher ──
    function dispatchKey(keyName, action) {
      fetch(`/api/remote/key_${action === 'down' ? 'down' : 'up'}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: keyName })
      }).catch(() => {});
    }

    // ── In-HUD Media Player ──
    function playInHudMedia(url, title) {
      const dock = document.getElementById('hud-media-dock');
      const frame = document.getElementById('hud-media-iframe');
      const titleEl = document.getElementById('hud-media-title');
      if (!dock || !frame) return;
      frame.src = url;
      if (titleEl) titleEl.textContent = `▶ ${title.slice(0, 30)}`;
      dock.classList.remove('hidden');
    }
    function closeHudMedia() {
      const dock = document.getElementById('hud-media-dock');
      const frame = document.getElementById('hud-media-iframe');
      if (dock) dock.classList.add('hidden');
      if (frame) frame.src = '';
    }

    // ── Handlers & Toggles ──
    function toggleClap() {
      fetch('/voice/toggle_clap', { method: 'POST' });
      logActivity("Clap detector state toggled.");
    }

    function toggleFaceSentinel() {
      fetch('/api/sentinel/toggle', { method: 'POST' });
      logActivity("Face Sentinel state toggled.");
    }

    function toggleEmergencyStop() {
      fetch('/api/emergency_stop', { method: 'POST' });
      logActivity("EMERGENCY STOP TRIGGERED BY OPERATOR.");
      alert("EMERGENCY STOP TRIGGERED: All autonomous operations halted.");
    }

    function toggleFullscreen() {
      if (!document.fullscreenElement) document.documentElement.requestFullscreen().catch(() => {});
      else document.exitFullscreen().catch(() => {});
    }

    function cycleMode() {
      fetch('/api/mode', { method: 'POST' }).then(r => r.json()).then(d => {
        const txt = document.getElementById('val-mode-text');
        if (txt) txt.textContent = (d.mode || 'auto').toUpperCase();
        logActivity(`Mode shifted to ${(d.mode || 'auto').toUpperCase()}`);
      }).catch(() => {});
    }

    function resetReflexStream() {
      window.edithSpeaking = false;
      window.userSpeakingLevel = 0;
      logActivity("Reflex core refreshed. Neural latency re-synced.");
    }

    async function loadActiveModels() {
      try {
        const res = await fetch('/models');
        if (!res.ok) return;
        const d = await res.json();
        const sel = document.getElementById('select-active-model');
        const badge = document.getElementById('active-model-badge');
        if (sel && d.models) {
          sel.innerHTML = '';
          d.models.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m;
            opt.textContent = m;
            if (m === d.active_model) opt.selected = true;
            sel.appendChild(opt);
          });
        }
        if (badge && d.active_model) badge.textContent = d.active_model;
      } catch (_) {}
    }

    async function switchModel(model) {
      await fetch('/models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model })
      });
      const badge = document.getElementById('active-model-badge');
      if (badge) badge.textContent = model;
      logActivity(`Switched active local model: ${model}`);
    }

    async function loadMobileConfig() {
      try {
        const res = await fetch('/mobile/config');
        if (!res.ok) return;
        const d = await res.json();
        const url = d.cloud_url || location.origin;
        const el = document.getElementById('hud-cloud-url');
        if (el) el.textContent = url;
        const setEl = document.getElementById('settings-cloud-url');
        if (setEl) setEl.value = url;
      } catch (_) {}
    }

    function copyCloudLink() {
      const url = document.getElementById('hud-cloud-url')?.textContent.trim() || location.origin;
      navigator.clipboard.writeText(url);
      logActivity(`Gateway URL copied to clipboard: ${url}`);
    }

    function syncClipboard() {
      navigator.clipboard.readText().then(txt => {
        fetch('/api/clipboard/sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: txt })
        });
        logActivity("Host clipboard synchronized.");
      }).catch(() => {});
    }

    function triggerFileUpload() {
      document.getElementById('file-uploader')?.click();
    }

    function handleFileAttached(e) {
      const file = e.target.files[0];
      if (!file) return;
      logActivity(`File attached: ${file.name} (${Math.round(file.size / 1024)} KB)`);
      submitTextCommand(`analyze file ${file.name}`);
    }

    function logActivity(text) {
      const box = document.getElementById('activity-logs');
      if (box) {
        const now = new Date();
        const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
        const row = document.createElement('div');
        row.className = 'flex items-center space-x-2';
        row.innerHTML = `<span class="text-slate-500">${timeStr}</span><span class="w-1 h-1 bg-os-amber rounded-full"></span><span class="text-slate-300 uppercase">${escapeHtml(text)}</span>`;
        box.insertBefore(row, box.firstChild);
      }

      const modalBox = document.getElementById('modal-activity-lines');
      if (modalBox) {
        const now = new Date();
        const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
        const r = document.createElement('div');
        r.className = 'p-1 border-b border-slate-800 text-slate-300';
        r.innerHTML = `<span class="text-os-amber">[${timeStr}]</span> ${escapeHtml(text)}`;
        modalBox.insertBefore(r, modalBox.firstChild);
      }
    }
    window.addLog = logActivity;

    function escapeHtml(s) {
      return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }
  </script>

</body>
</html>
'''

def main():
    root = Path(__file__).resolve().parent.parent
    targets = [
        root / "public" / "index.html",
        root / "desktop" / "edith" / "ui" / "public" / "index.html",
        root / "edith" / "ui" / "public" / "index.html",
    ]

    for p in targets:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(HTML_CONTENT, encoding="utf-8")
        print(f"Updated {p}")

if __name__ == "__main__":
    main()
