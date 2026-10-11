/**
 * EDITH Holographic Hand Gesture & Vision Control Layer
 * Engineered based on Ultron (Sagar Tamang) and Barehands (Jared Rhodenizer).
 * 
 * Features:
 * - MediaPipe Hand Landmarker with GPU + CPU fallback
 * - Severe lag fix: zero canvas fillrate overhead when camera background is off
 * - Full-Screen OS Mouse Control via native Win32 User32 C API:
 *   • Smooth index finger cursor positioning across entire desktop with zero lag batching
 *   • Index + Thumb pinch for Left Click / Drag-and-Drop / Double Click
 *   • Middle finger + Thumb pinch for Right Click
 *   • Two-finger vertical swipe for Mouse Wheel Scrolling
 *   • Pinky + Thumb pinch for System Volume Control
 *   • Five-finger downward swipe for Show Desktop / Window Minimize
 *   • Horizontal palm wave for Alt+Tab / Switch Window
 *   • Closed fist hold for Media Play / Pause toggle
 * - High-visibility cybernetic skeleton rendering on HUD overlay
 * - Seamless dual-mode: 3D Orb manipulation OR Full-Screen Desktop Mouse Control
 */

// Global tracking state
let videoElement = null;
let overlayCanvas = null;
let overlayCtx = null;
let bgVideoElement = null;
let bgOverlayCanvas = null;
let bgOverlayCtx = null;
let arContainer = null;
let cursorElement = null;
let statusTag = null;
let gesturesActive = false;
let arBackgroundActive = false;
let osMouseActive = false;
let handLandmarker = null;
let animationFrameId = null;
let lastVideoTime = -1;
let lastDetectTime = 0;

// Landmark indices
const WRIST = 0;
const THUMB_TIP = 4;
const INDEX_MCP = 5;
const INDEX_TIP = 8;
const MIDDLE_MCP = 9;
const MIDDLE_TIP = 12;
const RING_MCP = 13;
const RING_TIP = 16;
const PINKY_MCP = 17;
const PINKY_TIP = 20;

// Gesture tuning thresholds
const PINCH_ON = 0.44;
const PINCH_OFF = 0.58;
const ROTATE_SPEED = 7.0;
const ZOOM_SPEED = 35.0;
const SMOOTHING = 0.85;

// Persistent tracking states per hand (indexed 0 and 1)
const handStates = [
  { isPinching: false, isMiddlePinching: false, isPinkyPinching: false, pinchDist: 1.0, grabX: 0.5, grabY: 0.5, prevGrabX: null, prevGrabY: null },
  { isPinching: false, isMiddlePinching: false, isPinkyPinching: false, pinchDist: 1.0, grabX: 0.5, grabY: 0.5, prevGrabX: null, prevGrabY: null }
];

let prevTwoHandDist = null;

// OS Mouse state tracking
let smoothMouseX = 0.5;
let smoothMouseY = 0.5;
let lastMouseSendTime = 0;
let lastSentNormX = -1;
let lastSentNormY = -1;
let pinchStartTime = 0;
let isDraggingMouse = false;
let lastClickTime = 0;
let lastScrollTime = 0;
let lastRightClickTime = 0;
let lastVolumeTime = 0;
let lastDesktopTime = 0;
let lastSwitchTime = 0;
let lastMediaTime = 0;
let prevScrollY = null;
let prevSwipeX = null;
let prevSwipeY = null;

// Non-blocking in-flight HTTP request manager
let isSendingMouse = false;
let pendingMouseMove = null;

// MediaPipe 21 Landmark skeleton connections
const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],       // Thumb
  [0, 5], [5, 6], [6, 7], [7, 8],       // Index
  [0, 9], [9, 10], [10, 11], [11, 12],  // Middle
  [0, 13], [13, 14], [14, 15], [15, 16],// Ring
  [0, 17], [17, 18], [18, 19], [19, 20],// Pinky
  [5, 9], [9, 13], [13, 17], [0, 17]    // Palm perimeter
];

/**
 * Initialize MediaPipe HandLandmarker with robust fallback.
 */
async function initLandmarker() {
  if (handLandmarker) return handLandmarker;

  const { HandLandmarker, FilesetResolver } = await import(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/vision_bundle.mjs"
  );

  const vision = await FilesetResolver.forVisionTasks(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/wasm"
  );

  const baseConfig = {
    modelAssetPath: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
  };

  try {
    handLandmarker = await HandLandmarker.createFromOptions(vision, {
      baseOptions: { ...baseConfig, delegate: "GPU" },
      runningMode: "VIDEO",
      numHands: 2,
      minHandDetectionConfidence: 0.35,
      minHandPresenceConfidence: 0.35,
      minTrackingConfidence: 0.4
    });
    console.log("[EDITH Vision] GPU HandLandmarker initialized.");
  } catch (gpuErr) {
    console.warn("[EDITH Vision] GPU delegate unavailable. Falling back to CPU:", gpuErr);
    handLandmarker = await HandLandmarker.createFromOptions(vision, {
      baseOptions: { ...baseConfig, delegate: "CPU" },
      runningMode: "VIDEO",
      numHands: 2,
      minHandDetectionConfidence: 0.35,
      minHandPresenceConfidence: 0.35,
      minTrackingConfidence: 0.4
    });
    console.log("[EDITH Vision] CPU HandLandmarker initialized.");
  }

  return handLandmarker;
}

/**
 * Zero-latency non-blocking dispatcher with in-flight queue coalescing.
 * Eliminates HTTP socket pileup and guarantees sub-frame responsiveness.
 */
async function sendMouseAction(action, params = {}) {
  if (action === "move") {
    pendingMouseMove = params;
    if (isSendingMouse) return;
    flushPendingMove();
    return;
  }

  // Immediate discrete actions (click, scroll, key shortcuts)
  try {
    const payload = JSON.stringify({ action, ...params });
    await fetch("/api/mouse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload
    });
  } catch (_) {}
}

async function flushPendingMove() {
  if (isSendingMouse || !pendingMouseMove) return;
  const p = pendingMouseMove;
  pendingMouseMove = null;
  isSendingMouse = true;
  try {
    await fetch("/api/mouse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "move", ...p })
    });
  } catch (_) {}
  isSendingMouse = false;
  if (pendingMouseMove) {
    flushPendingMove();
  }
}

/**
 * Toggle Full-Screen OS Mouse Control.
 */
function toggleOsMouse() {
  osMouseActive = !osMouseActive;
  const btn = document.getElementById("btn-os-mouse");
  if (btn) {
    btn.innerText = osMouseActive ? "OS MOUSE: ON" : "OS MOUSE: OFF";
    btn.classList.toggle("active", osMouseActive);
    btn.style.color = osMouseActive ? "var(--cyan-glow)" : "";
  }
  if (statusTag) {
    statusTag.innerText = osMouseActive
      ? "OS MOUSE ONLINE: PINCH TO CLICK, 2-FINGERS SCROLL"
      : "GESTURE MODE: CONTROLLING HOLOGRAPHIC ORB";
  }
  if (window.logEntry) {
    window.logEntry(
      osMouseActive
        ? "Full-Screen OS Mouse Control engaged. Point index finger to navigate desktop."
        : "OS Mouse Control disengaged. Returned to 3D Orb rotation.",
      "system"
    );
  }
}
window.toggleOsMouse = toggleOsMouse;

function ensureWebcamDom() {
  let box = document.getElementById('webcam-box');
  if (!box) {
    box = document.createElement('div');
    box.id = 'webcam-box';
    box.className = 'webcam-hud-box';
    box.style.display = 'none';
    box.innerHTML = `
      <div class="webcam-hud-header">
        <div class="webcam-hud-title">
          <span class="status-dot green"></span>
          <span>NEURAL HAND VISION</span>
        </div>
        <span id="gesture-tag" class="webcam-hud-tag">READY</span>
        <button class="webcam-hud-close" onclick="toggleGestures()" title="Close Camera">&times;</button>
      </div>
      <div class="webcam-hud-viewport">
        <video id="webcam-pip" autoplay playsinline muted></video>
        <canvas id="webcam-overlay"></canvas>
        <div class="stage-corner top-left"></div>
        <div class="stage-corner top-right"></div>
        <div class="stage-corner bottom-left"></div>
        <div class="stage-corner bottom-right"></div>
      </div>
      <div class="webcam-hud-footer">
        <div class="gesture-hints">
          <span>🖐️ 1-Hand Pinch: Rotate</span>
          <span>👐 2-Hands Pinch: Scale</span>
        </div>
        <button id="btn-os-mouse" class="hud-mini-btn" onclick="toggleOsMouse()">OS MOUSE: OFF</button>
      </div>
    `;
    document.body.appendChild(box);
  }
  return box;
}

/**
 * Toggle webcam and gesture tracking pipeline.
 */
async function toggleGestures() {
  ensureWebcamDom();

  const btn = document.getElementById('tgl-gestures') || document.getElementById('btn-gestures');
  const lblState = document.getElementById('lbl-gesture-state');
  const webcamBox = document.getElementById('webcam-box');
  videoElement = document.getElementById('webcam-pip');
  overlayCanvas = document.getElementById('webcam-overlay');
  bgVideoElement = document.getElementById('bg-camera');
  bgOverlayCanvas = document.getElementById('bg-overlay');
  arContainer = document.getElementById('ar-camera-container');
  cursorElement = document.getElementById('hand-cursor');
  statusTag = document.getElementById('gesture-tag');

  if (gesturesActive) {
    // Shutdown tracking
    gesturesActive = false;
    arBackgroundActive = false;
    osMouseActive = false;
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId);
      animationFrameId = null;
    }
    if (btn) {
      btn.classList.remove('active', 'is-on');
      if (!btn.classList.contains('toggle')) {
        btn.innerText = 'GESTURE: OFF';
        btn.style.color = '';
      }
    }
    if (lblState) lblState.textContent = 'Camera Ready';
    if (statusTag) statusTag.innerText = 'STANDBY';

    const mouseBtn = document.getElementById('btn-os-mouse');
    if (mouseBtn) {
      mouseBtn.innerText = 'OS MOUSE: OFF';
      mouseBtn.classList.remove('active');
      mouseBtn.style.color = '';
    }
    document.body.classList.remove('ar-active');
    if (webcamBox) webcamBox.style.display = 'none';
    if (arContainer) arContainer.style.display = 'none';
    if (cursorElement) cursorElement.style.display = 'none';
    window.isUserPinching = false;
    const arBtn = document.getElementById('btn-ar-bg');
    if (arBtn) {
      arBtn.innerText = 'CAM BG: OFF';
      arBtn.classList.remove('active');
    }

    if (videoElement && videoElement.srcObject) {
      videoElement.srcObject.getTracks().forEach(t => t.stop());
      videoElement.srcObject = null;
    }
    if (bgVideoElement) {
      try { bgVideoElement.pause(); } catch (_) {}
      bgVideoElement.srcObject = null;
    }
    if (window.addLog) window.addLog('Hand tracking paused // Camera stream closed', 'info');
    return;
  }

  // Activating tracking
  if (btn) {
    btn.classList.add('active', 'is-on');
    if (!btn.classList.contains('toggle')) {
      btn.innerText = 'CALIBRATING...';
      btn.style.color = 'var(--amber)';
    }
  }
  if (lblState) lblState.textContent = 'Requesting Camera...';
  if (webcamBox) webcamBox.style.display = 'flex';
  if (statusTag) statusTag.innerText = 'STARTING CAMERA...';
  if (window.addLog) window.addLog('Requesting webcam access for gesture vision...', 'info');

  try {
    // 1. Acquire video stream directly
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 640 },
        height: { ideal: 480 },
        facingMode: "user"
      },
      audio: false
    });

    if (videoElement) {
      videoElement.srcObject = stream;
      await videoElement.play();
    }

    if (overlayCanvas && videoElement) {
      overlayCanvas.width = videoElement.videoWidth || 640;
      overlayCanvas.height = videoElement.videoHeight || 480;
      overlayCtx = overlayCanvas.getContext('2d', { alpha: true });
    }

    if (bgOverlayCanvas) {
      bgOverlayCanvas.width = window.innerWidth;
      bgOverlayCanvas.height = window.innerHeight;
      bgOverlayCtx = bgOverlayCanvas.getContext('2d', { alpha: true });
    }

    if (statusTag) statusTag.innerText = 'INITIALIZING MEDIAPIPE AI...';
    if (lblState) lblState.textContent = 'Loading AI...';

    // 2. Load MediaPipe HandLandmarker
    await initLandmarker();

    gesturesActive = true;
    if (btn && !btn.classList.contains('toggle')) {
      btn.innerText = 'GESTURE: ACTIVE';
      btn.style.color = 'var(--cyan-glow)';
    }
    if (lblState) lblState.textContent = 'Tracking Live';
    if (statusTag) statusTag.innerText = 'VISION ONLINE: SHOW HANDS';
    if (window.addLog) window.addLog('Neural vision online // Camera & MediaPipe active', 'success');

    // Keep OS Mouse off by default so 3D Orb interaction is active
    osMouseActive = false;
    const mouseBtn = document.getElementById('btn-os-mouse');
    if (mouseBtn) {
      mouseBtn.innerText = 'OS MOUSE: OFF';
      mouseBtn.classList.remove('active');
      mouseBtn.style.color = '';
    }

    // Reset tracking states
    handStates[0].prevGrabX = null;
    handStates[0].prevGrabY = null;
    handStates[1].prevGrabX = null;
    handStates[1].prevGrabY = null;
    prevTwoHandDist = null;

    renderGestureLoop();
  } catch (err) {
    console.error("[EDITH Vision] Failed to activate gestures:", err);
    gesturesActive = false;
    if (btn) btn.classList.remove('active', 'is-on');
    if (lblState) lblState.textContent = 'Camera Error';
    if (statusTag) statusTag.innerText = 'CAMERA / AI FAILED';
    if (videoElement && videoElement.srcObject) {
      videoElement.srcObject.getTracks().forEach(t => t.stop());
      videoElement.srcObject = null;
    }
    if (webcamBox) {
      setTimeout(() => { if (!gesturesActive) webcamBox.style.display = 'none'; }, 2500);
    }
    if (window.addLog) window.addLog(`Camera initialization notice: ${err.message}`, 'error');
  }
}

/**
 * Continuous high-performance frame rendering loop.
 * Throttles inference to ~30 FPS to eliminate main thread lockup.
 */
function renderGestureLoop() {
  if (!gesturesActive) return;

  try {
    const now = performance.now();
    if (videoElement && videoElement.readyState >= 2 && handLandmarker) {
      if (videoElement.currentTime !== lastVideoTime && (now - lastDetectTime >= 32)) {
        lastVideoTime = videoElement.currentTime;
        lastDetectTime = now;

        const results = handLandmarker.detectForVideo(videoElement, now);

        if (overlayCtx && overlayCanvas) {
          overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
        }

        // Severe lag fix: Only clear and render background canvas if camera background is ON
        if (arBackgroundActive && bgOverlayCtx && bgOverlayCanvas) {
          bgOverlayCtx.clearRect(0, 0, bgOverlayCanvas.width, bgOverlayCanvas.height);
        }

        if (results && results.landmarks && results.landmarks.length > 0) {
          drawCyberneticSkeleton(results.landmarks, overlayCtx, overlayCanvas);
          if (arBackgroundActive && bgOverlayCtx && bgOverlayCanvas) {
            drawCyberneticSkeleton(results.landmarks, bgOverlayCtx, bgOverlayCanvas);
          }
          processUltronGestures(results.landmarks);
        } else {
          // No hands in frame
          if (cursorElement) cursorElement.style.display = 'none';
          handStates[0].prevGrabX = null;
          handStates[0].prevGrabY = null;
          handStates[1].prevGrabX = null;
          handStates[1].prevGrabY = null;
          prevTwoHandDist = null;
          prevScrollY = null;
          prevSwipeX = null;
          prevSwipeY = null;
          statusTag.innerText = 'LOOKING FOR HANDS...';
        }
      }
    }
  } catch (err) {
    console.warn("[EDITH Vision] Gesture frame error:", err);
  }

  animationFrameId = requestAnimationFrame(renderGestureLoop);
}

/**
 * Calculate aspect-ratio cropping transform matching object-fit: cover.
 */
function getVideoMapping(canvas) {
  if (!videoElement || !videoElement.videoWidth || !canvas) {
    return { scaleX: canvas ? canvas.width : window.innerWidth, scaleY: canvas ? canvas.height : window.innerHeight, offsetX: 0, offsetY: 0 };
  }
  const vRatio = videoElement.videoWidth / videoElement.videoHeight;
  const sRatio = canvas.width / canvas.height;
  let renderW, renderH, offsetX, offsetY;

  if (sRatio > vRatio) {
    renderW = canvas.width;
    renderH = canvas.width / vRatio;
    offsetX = 0;
    offsetY = (canvas.height - renderH) / 2;
  } else {
    renderH = canvas.height;
    renderW = canvas.height * vRatio;
    offsetX = (canvas.width - renderW) / 2;
    offsetY = 0;
  }
  return { scaleX: renderW, scaleY: renderH, offsetX, offsetY };
}

/**
 * Render Iron Man / Ultron cybernetic skeleton over the canvas.
 */
function drawCyberneticSkeleton(landmarksList, ctx, canvas) {
  if (!ctx || !canvas) return;
  const isBg = canvas === bgOverlayCanvas;
  const map = isBg
    ? getVideoMapping(canvas)
    : { scaleX: canvas.width, scaleY: canvas.height, offsetX: 0, offsetY: 0 };

  ctx.shadowBlur = 0;

  // 1. Draw individual cybernetic hand skeletons
  for (let hIdx = 0; hIdx < landmarksList.length; hIdx++) {
    const lm = landmarksList[hIdx];
    const isPinching = handStates[hIdx] ? handStates[hIdx].isPinching : false;

    ctx.lineWidth = isBg ? 2.5 : 2.0;
    ctx.strokeStyle = isPinching ? 'rgba(255, 183, 0, 0.95)' : (hIdx === 0 ? 'rgba(0, 229, 255, 0.85)' : 'rgba(168, 85, 247, 0.85)');

    for (const [startIdx, endIdx] of HAND_CONNECTIONS) {
      const p1 = lm[startIdx];
      const p2 = lm[endIdx];
      ctx.beginPath();
      ctx.moveTo(map.offsetX + p1.x * map.scaleX, map.offsetY + p1.y * map.scaleY);
      ctx.lineTo(map.offsetX + p2.x * map.scaleX, map.offsetY + p2.y * map.scaleY);
      ctx.stroke();
    }

    for (let i = 0; i < lm.length; i++) {
      const p = lm[i];
      const jx = map.offsetX + p.x * map.scaleX;
      const jy = map.offsetY + p.y * map.scaleY;
      ctx.beginPath();
      if (i === THUMB_TIP || i === INDEX_TIP) {
        ctx.fillStyle = isPinching ? '#ff0055' : (hIdx === 0 ? '#00e5ff' : '#c084fc');
        ctx.arc(jx, jy, isBg ? 6 : 4, 0, 2 * Math.PI);
      } else {
        ctx.fillStyle = '#10b981';
        ctx.arc(jx, jy, isBg ? 3 : 2, 0, 2 * Math.PI);
      }
      ctx.fill();
    }

    if (isPinching) {
      const thumb = lm[THUMB_TIP];
      const index = lm[INDEX_TIP];
      const midX = map.offsetX + ((thumb.x + index.x) / 2) * map.scaleX;
      const midY = map.offsetY + ((thumb.y + index.y) / 2) * map.scaleY;

      ctx.strokeStyle = '#ffb700';
      ctx.lineWidth = 3.0;
      ctx.beginPath();
      ctx.arc(midX, midY, isBg ? 18 : 10, 0, 2 * Math.PI);
      ctx.stroke();
    }
  }

  // 2. Holographic energy laser bridge when 2 hands are detected
  if (landmarksList.length >= 2) {
    const lm0 = landmarksList[0];
    const lm1 = landmarksList[1];
    const p0 = lm0[INDEX_TIP];
    const p1 = lm1[INDEX_TIP];
    const x0 = map.offsetX + p0.x * map.scaleX;
    const y0 = map.offsetY + p0.y * map.scaleY;
    const x1 = map.offsetX + p1.x * map.scaleX;
    const y1 = map.offsetY + p1.y * map.scaleY;

    const bothPinching = handStates[0].isPinching && handStates[1].isPinching;

    ctx.save();
    ctx.strokeStyle = bothPinching ? 'rgba(255, 0, 85, 0.90)' : 'rgba(0, 229, 255, 0.45)';
    ctx.lineWidth = bothPinching ? 3.5 : 1.5;
    ctx.setLineDash([8, 6]);
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x1, y1);
    ctx.stroke();

    // Central energy convergence node
    const mx = (x0 + x1) / 2;
    const my = (y0 + y1) / 2;
    ctx.setLineDash([]);
    ctx.fillStyle = bothPinching ? '#ff0055' : '#00e5ff';
    ctx.beginPath();
    ctx.arc(mx, my, bothPinching ? 8 : 4, 0, 2 * Math.PI);
    ctx.fill();
    ctx.restore();
  }
}

/**
 * Ultron Gesture Processor with Dual-Mode (Holographic Orb vs Full-Screen Desktop Mouse).
 * Full two-hand support for dual-pinch maximize/minimize, pitch, and orb manipulation.
 */
function processUltronGestures(landmarksList) {
  const numHands = Math.min(landmarksList.length, 2);
  const now = performance.now();

  // Process metrics for ALL visible hands (Hand 0 and Hand 1)
  const metrics = [];
  for (let h = 0; h < numHands; h++) {
    const hand = landmarksList[h];
    const wrist = hand[WRIST];
    const thumb = hand[THUMB_TIP];
    const index = hand[INDEX_TIP];
    const middle = hand[MIDDLE_TIP];
    const ring = hand[RING_TIP];
    const pinky = hand[PINKY_TIP];
    const indexMcp = hand[INDEX_MCP];
    const middleMcp = hand[MIDDLE_MCP];
    const ringMcp = hand[RING_MCP];
    const pinkyMcp = hand[PINKY_MCP];

    const handSpan = Math.hypot(wrist.x - middleMcp.x, wrist.y - middleMcp.y) || 0.2;
    const pinchDist = Math.hypot(thumb.x - index.x, thumb.y - index.y) / handSpan;
    const middlePinchDist = Math.hypot(thumb.x - middle.x, thumb.y - middle.y) / handSpan;
    const pinkyPinchDist = Math.hypot(thumb.x - pinky.x, thumb.y - pinky.y) / handSpan;

    // Hysteresis pinch tracking
    const state = handStates[h];
    state.pinchDist = pinchDist;
    if (state.isPinching) {
      if (pinchDist > PINCH_OFF) state.isPinching = false;
    } else {
      if (pinchDist < PINCH_ON) state.isPinching = true;
    }

    state.isMiddlePinching = middlePinchDist < PINCH_ON && pinchDist >= PINCH_ON;
    state.isPinkyPinching = pinkyPinchDist < PINCH_ON && pinchDist >= PINCH_ON;

    // Mirrored normalized coordinates for natural human interaction
    state.grabX = 1.0 - index.x;
    state.grabY = index.y;
    state.palmX = 1.0 - (wrist.x + middleMcp.x) / 2;
    state.palmY = (wrist.y + middleMcp.y) / 2;

    const isFiveFingersOpen = (
      index.y < indexMcp.y &&
      middle.y < middleMcp.y &&
      ring.y < ringMcp.y &&
      pinky.y < pinkyMcp.y
    );

    const isClosedFist = (
      index.y > indexMcp.y &&
      middle.y > middleMcp.y &&
      ring.y > ringMcp.y &&
      pinky.y > pinkyMcp.y
    );

    metrics.push({
      hand, wrist, thumb, index, middle, ring, pinky,
      indexMcp, middleMcp, ringMcp, pinkyMcp,
      handSpan, pinchDist, middlePinchDist, pinkyPinchDist,
      isFiveFingersOpen, isClosedFist
    });
  }

  // Clear states for missing hands
  for (let h = numHands; h < 2; h++) {
    handStates[h].isPinching = false;
    handStates[h].isMiddlePinching = false;
    handStates[h].isPinkyPinching = false;
    handStates[h].prevGrabX = null;
    handStates[h].prevGrabY = null;
  }

  // Primary cursor coordinates
  const primaryMetric = metrics[0];
  const rawTargetX = Math.min(1.0, Math.max(0.0, (1.0 - primaryMetric.index.x - 0.15) / 0.70));
  const rawTargetY = Math.min(1.0, Math.max(0.0, (primaryMetric.index.y - 0.15) / 0.70));

  smoothMouseX = smoothMouseX + (rawTargetX - smoothMouseX) * SMOOTHING;
  smoothMouseY = smoothMouseY + (rawTargetY - smoothMouseY) * SMOOTHING;

  const screenX = smoothMouseX * window.innerWidth;
  const screenY = smoothMouseY * window.innerHeight;

  if (cursorElement) {
    cursorElement.style.display = 'block';
    cursorElement.style.left = `${screenX}px`;
    cursorElement.style.top = `${screenY}px`;
  }

  // ==========================================
  // MODE A: FULL SCREEN OS MOUSE CONTROL
  // ==========================================
  if (osMouseActive) {
    const primaryState = handStates[0];
    const wasPinching = primaryState.isPinching;

    // Dual-hand pinch in OS mode -> zoom desktop screen
    if (numHands >= 2 && handStates[0].isPinching && handStates[1].isPinching) {
      const dist = Math.hypot(
        handStates[0].grabX - handStates[1].grabX,
        handStates[0].grabY - handStates[1].grabY
      );
      if (prevTwoHandDist !== null) {
        const delta = dist - prevTwoHandDist;
        if (Math.abs(delta) > 0.015 && (now - lastScrollTime > 120)) {
          sendMouseAction("scroll", { delta: delta > 0 ? 1 : -1 });
          lastScrollTime = now;
        }
      }
      prevTwoHandDist = dist;
      statusTag.innerText = "OS MOUSE: DUAL PINCH ZOOM 🔍";
      return;
    }

    // 1. Closed Fist Hold -> Toggle Media Play/Pause
    if (primaryMetric.isClosedFist && (now - lastMediaTime > 1000)) {
      sendMouseAction("media_toggle");
      lastMediaTime = now;
      statusTag.innerText = "OS GESTURE: MEDIA PLAY / PAUSE ⏯️";
      return;
    }

    // 2. Five-Finger Open Swipe Down -> Show Desktop (Win+D)
    if (primaryMetric.isFiveFingersOpen) {
      if (prevSwipeY !== null && (primaryMetric.wrist.y - prevSwipeY > 0.14) && (now - lastDesktopTime > 1200)) {
        sendMouseAction("desktop");
        lastDesktopTime = now;
        prevSwipeY = null;
        statusTag.innerText = "OS GESTURE: SHOW DESKTOP 🖥️";
        return;
      }
      prevSwipeY = primaryMetric.wrist.y;
    } else {
      prevSwipeY = null;
    }

    // 3. Horizontal Palm Wave -> Switch Window (Alt+Tab)
    if (primaryMetric.isFiveFingersOpen || (primaryMetric.index.y < primaryMetric.indexMcp.y && primaryMetric.middle.y < primaryMetric.middleMcp.y)) {
      if (prevSwipeX !== null && Math.abs(primaryMetric.wrist.x - prevSwipeX) > 0.18 && (now - lastSwitchTime > 900)) {
        sendMouseAction("switch_window");
        lastSwitchTime = now;
        prevSwipeX = null;
        statusTag.innerText = "OS GESTURE: SWITCH WINDOW (ALT+TAB) 🔀";
        return;
      }
      prevSwipeX = primaryMetric.wrist.x;
    } else {
      prevSwipeX = null;
    }

    // 4. Cursor Movement Dispatch
    if (now - lastMouseSendTime > 25) {
      const deltaDist = Math.hypot(smoothMouseX - lastSentNormX, smoothMouseY - lastSentNormY);
      if (deltaDist > 0.0025) {
        sendMouseAction("move", { x: smoothMouseX, y: smoothMouseY });
        lastSentNormX = smoothMouseX;
        lastSentNormY = smoothMouseY;
        lastMouseSendTime = now;
      }
    }

    // 5. Right Click (Middle finger + Thumb pinch)
    if (primaryState.isMiddlePinching && (now - lastRightClickTime > 400)) {
      sendMouseAction("right_click");
      lastRightClickTime = now;
      if (cursorElement) cursorElement.classList.add("right-clicking");
      setTimeout(() => cursorElement && cursorElement.classList.remove("right-clicking"), 200);
      statusTag.innerText = "OS MOUSE: RIGHT CLICK 🖱️";
      return;
    }

    // 6. Two-Finger Scroll
    const isScrollGesture = (
      primaryMetric.index.y < primaryMetric.indexMcp.y &&
      primaryMetric.middle.y < primaryMetric.middleMcp.y &&
      primaryMetric.ring.y > primaryMetric.middleMcp.y &&
      primaryMetric.pinky.y > primaryMetric.pinkyMcp.y &&
      Math.hypot(primaryMetric.index.x - primaryMetric.middle.x, primaryMetric.index.y - primaryMetric.middle.y) < 0.14 &&
      primaryMetric.pinchDist > PINCH_OFF
    );

    if (isScrollGesture) {
      if (prevScrollY !== null) {
        const deltaY = primaryMetric.index.y - prevScrollY;
        if (now - lastScrollTime > 50) {
          if (deltaY < -0.012) {
            sendMouseAction("scroll", { delta: 1 });
            lastScrollTime = now;
            statusTag.innerText = "OS MOUSE: SCROLL UP ↑";
          } else if (deltaY > 0.012) {
            sendMouseAction("scroll", { delta: -1 });
            lastScrollTime = now;
            statusTag.innerText = "OS MOUSE: SCROLL DOWN ↓";
          }
        }
      }
      prevScrollY = primaryMetric.index.y;
      return;
    } else {
      prevScrollY = null;
    }

    // 7. Volume Control (Pinky + Thumb pinch)
    if (primaryState.isPinkyPinching && (now - lastVolumeTime > 220)) {
      const volDelta = primaryMetric.index.y < 0.45 ? 5 : -5;
      sendMouseAction("volume", { delta: volDelta });
      lastVolumeTime = now;
      statusTag.innerText = volDelta > 0 ? "OS MOUSE: VOLUME UP 🔊" : "OS MOUSE: VOLUME DOWN 🔉";
      return;
    }

    // 8. Left Click / Drag & Drop / Double Click
    if (primaryState.isPinching) {
      if (!wasPinching) {
        pinchStartTime = now;
        isDraggingMouse = false;
        if (cursorElement) cursorElement.classList.add("pinching");
      } else {
        if (!isDraggingMouse && (now - pinchStartTime > 260)) {
          isDraggingMouse = true;
          sendMouseAction("drag_start");
          statusTag.innerText = "OS MOUSE: DRAG & DROP ACTIVE ✊";
        }
      }
    } else {
      if (wasPinching) {
        if (cursorElement) cursorElement.classList.remove("pinching");
        if (isDraggingMouse) {
          sendMouseAction("drag_end");
          isDraggingMouse = false;
          statusTag.innerText = "OS MOUSE: RELEASED";
        } else {
          if (now - lastClickTime < 340) {
            sendMouseAction("double_click");
            lastClickTime = 0;
            statusTag.innerText = "OS MOUSE: DOUBLE CLICK ⚡";
          } else {
            sendMouseAction("left_click");
            lastClickTime = now;
            statusTag.innerText = "OS MOUSE: LEFT CLICK 🎯";
          }
        }
      } else {
        statusTag.innerText = "OS MOUSE: INDEX POINTING";
      }
    }
    return;
  }

  // ==========================================
  // MODE B: HOLOGRAPHIC 3D ORB INTERACTION (DEFAULT)
  // ==========================================

  // ----------------------------------------------------
  // TWO-HAND GESTURE 1: DUAL PINCH TO MAXIMIZE / MINIMIZE ORB
  // ----------------------------------------------------
  const isDualPinch = numHands >= 2 && (
    (handStates[0].isPinching && handStates[1].isPinching) ||
    (handStates[0].isPinching && (handStates[1].pinchDist || 1.0) < PINCH_OFF) ||
    (handStates[1].isPinching && (handStates[0].pinchDist || 1.0) < PINCH_OFF)
  );

  if (isDualPinch) {
    window.isUserPinching = true;
    const currentDist = Math.hypot(
      handStates[0].grabX - handStates[1].grabX,
      handStates[0].grabY - handStates[1].grabY
    );

    if (prevTwoHandDist !== null) {
      const deltaDist = currentDist - prevTwoHandDist;
      // Moving hands apart maximizes orb; pushing hands together minimizes orb
      if (window.scaleOrb) {
        window.scaleOrb(deltaDist * 5.2);
      }
      if (window.zoomOrb) {
        window.zoomOrb(-deltaDist * 32.0);
      }
    }
    prevTwoHandDist = currentDist;

    // Holographic tilt based on hand positioning
    if (window.rotateOrb) {
      const midY = (handStates[0].grabY + handStates[1].grabY) / 2;
      window.rotateOrb(0, (midY - 0.5) * 0.06);
    }

    if (cursorElement) cursorElement.style.display = 'none';
    const curScale = window.getOrbScale ? window.getOrbScale() : 100;
    statusTag.innerText = `DUAL PINCH: ORB SCALE ${curScale}% 🌐`;
    return;
  }

  // ----------------------------------------------------
  // TWO-HAND GESTURE 2: TWO OPEN PALMS SPREAD (EXPAND / MAXIMIZE)
  // ----------------------------------------------------
  if (numHands >= 2 && metrics[0].isFiveFingersOpen && metrics[1].isFiveFingersOpen) {
    const palmDist = Math.hypot(
      handStates[0].palmX - handStates[1].palmX,
      handStates[0].palmY - handStates[1].palmY
    );
    if (prevTwoHandDist !== null) {
      const delta = palmDist - prevTwoHandDist;
      if (Math.abs(delta) > 0.008 && window.scaleOrb) {
        window.scaleOrb(delta * 3.2);
      }
    }
    prevTwoHandDist = palmDist;
    const curScale = window.getOrbScale ? window.getOrbScale() : 100;
    statusTag.innerText = `OPEN PALMS SPREAD: ORB SCALE ${curScale}% 🌟`;
    return;
  }

  // ----------------------------------------------------
  // TWO-HAND GESTURE 3: TWO INDEX TIPS AIR TAP (RE-CENTER / RESET)
  // ----------------------------------------------------
  if (numHands >= 2) {
    const indexTipDist = Math.hypot(
      handStates[0].grabX - handStates[1].grabX,
      handStates[0].grabY - handStates[1].grabY
    );
    if (indexTipDist < 0.06 && !handStates[0].isPinching && !handStates[1].isPinching) {
      if (window.resetOrb) window.resetOrb();
      statusTag.innerText = "DUAL INDEX TAP: ORB RE-CENTERED TO DEFAULT 🎯";
      prevTwoHandDist = null;
      return;
    }
  }

  // ----------------------------------------------------
  // TWO-HAND GESTURE 4: TWO CLOSED FISTS (CONTRACT / MINIMIZE)
  // ----------------------------------------------------
  if (numHands >= 2 && metrics[0].isClosedFist && metrics[1].isClosedFist) {
    if (window.scaleOrb) window.scaleOrb(-0.025);
    const curScale = window.getOrbScale ? window.getOrbScale() : 100;
    statusTag.innerText = `TWO FISTS: CONTRACTING ORB (${curScale}%) ✊✊`;
    prevTwoHandDist = null;
    return;
  }

  // Reset two-hand distance tracker when no two-hand gesture is active
  prevTwoHandDist = null;

  // ----------------------------------------------------
  // SINGLE-HAND GESTURE: ROTATE 3D ORB (HAND 0 OR HAND 1)
  // ----------------------------------------------------
  const activePinchingHandIdx = handStates[0].isPinching ? 0 : (numHands >= 2 && handStates[1].isPinching ? 1 : -1);

  if (activePinchingHandIdx !== -1) {
    window.isUserPinching = true;
    if (cursorElement) cursorElement.classList.add('pinching');

    const activeState = handStates[activePinchingHandIdx];
    const posX = activeState.grabX;
    const posY = activeState.grabY;

    if (activeState.prevGrabX !== null && activeState.prevGrabY !== null) {
      const deltaX = (posX - activeState.prevGrabX) * ROTATE_SPEED;
      const deltaY = (posY - activeState.prevGrabY) * ROTATE_SPEED;
      if (window.rotateOrb) window.rotateOrb(deltaX, deltaY);
    }

    activeState.prevGrabX = posX;
    activeState.prevGrabY = posY;
    statusTag.innerText = `HAND ${activePinchingHandIdx + 1} PINCH: ROTATING 3D ORB 🌀`;
  } else {
    window.isUserPinching = false;
    if (cursorElement) cursorElement.classList.remove('pinching');
    handStates[0].prevGrabX = null;
    handStates[0].prevGrabY = null;
    handStates[1].prevGrabX = null;
    handStates[1].prevGrabY = null;

    if (numHands >= 2) {
      statusTag.innerText = "2 HANDS READY: PINCH BOTH TO SCALE/MAXIMIZE ORB 👐";
    } else if (numHands === 1) {
      statusTag.innerText = "1 HAND READY: PINCH TO ROTATE 3D ORB 🖐️";
    } else {
      statusTag.innerText = "LOOKING FOR HANDS... SHOW 1 OR 2 HANDS";
    }
  }
}

// Global exports
window.toggleGestures = toggleGestures;

/**
 * Toggle full-screen AR background camera feed on/off manually.
 */
async function toggleArBackground() {
  if (!gesturesActive || !videoElement || !videoElement.srcObject) {
    if (window.logEntry) {
      window.logEntry('Please activate gesture mode before toggling AR background camera.', 'system');
    }
    return;
  }

  const arBtn = document.getElementById('btn-ar-bg');
  arBackgroundActive = !arBackgroundActive;

  if (arBackgroundActive) {
    if (bgVideoElement) {
      if (!bgVideoElement.srcObject) {
        bgVideoElement.srcObject = typeof videoElement.srcObject.clone === 'function'
          ? videoElement.srcObject.clone()
          : videoElement.srcObject;
      }
      try { await bgVideoElement.play(); } catch (_) {}
    }
    if (arContainer) arContainer.style.display = 'block';
    document.body.classList.add('ar-active');
    if (arBtn) {
      arBtn.innerText = 'CAM BG: ON';
      arBtn.classList.add('active');
    }
  } else {
    if (bgVideoElement) {
      try { bgVideoElement.pause(); } catch (_) {}
    }
    if (arContainer) arContainer.style.display = 'none';
    document.body.classList.remove('ar-active');
    if (arBtn) {
      arBtn.innerText = 'CAM BG: OFF';
      arBtn.classList.remove('active');
    }
    // Cleanly clear background canvas once when turned off
    if (bgOverlayCtx && bgOverlayCanvas) {
      bgOverlayCtx.clearRect(0, 0, bgOverlayCanvas.width, bgOverlayCanvas.height);
    }
  }
}
window.toggleArBackground = toggleArBackground;
