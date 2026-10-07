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
const PINCH_ON = 0.38;
const PINCH_OFF = 0.52;
const ROTATE_SPEED = 7.0;
const ZOOM_SPEED = 35.0;
const SMOOTHING = 0.85;

// Persistent tracking states per hand (indexed 0 and 1)
const handStates = [
  { isPinching: false, isMiddlePinching: false, isPinkyPinching: false, grabX: 0.5, grabY: 0.5, prevGrabX: null, prevGrabY: null },
  { isPinching: false, isMiddlePinching: false, isPinkyPinching: false, grabX: 0.5, grabY: 0.5, prevGrabX: null, prevGrabY: null }
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
      minHandDetectionConfidence: 0.55,
      minHandPresenceConfidence: 0.55,
      minTrackingConfidence: 0.55
    });
    console.log("[EDITH Vision] GPU HandLandmarker initialized.");
  } catch (gpuErr) {
    console.warn("[EDITH Vision] GPU delegate unavailable. Falling back to CPU:", gpuErr);
    handLandmarker = await HandLandmarker.createFromOptions(vision, {
      baseOptions: { ...baseConfig, delegate: "CPU" },
      runningMode: "VIDEO",
      numHands: 2,
      minHandDetectionConfidence: 0.5,
      minHandPresenceConfidence: 0.5,
      minTrackingConfidence: 0.5
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

/**
 * Toggle webcam and gesture tracking pipeline.
 */
async function toggleGestures() {
  const btn = document.getElementById('btn-gestures');
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
    btn.innerText = 'GESTURE: OFF';
    btn.style.color = '';
    btn.classList.remove('active');
    const mouseBtn = document.getElementById('btn-os-mouse');
    if (mouseBtn) {
      mouseBtn.innerText = 'OS MOUSE: OFF';
      mouseBtn.classList.remove('active');
      mouseBtn.style.color = '';
    }
    document.body.classList.remove('ar-active');
    webcamBox.style.display = 'none';
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
    return;
  }

  // Activating tracking
  btn.innerText = 'CALIBRATING...';
  btn.style.color = 'var(--amber)';
  webcamBox.style.display = 'block';
  statusTag.innerText = 'STARTING CAMERA & AI VISION...';

  try {
    await initLandmarker();

    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 640 },
        height: { ideal: 480 },
        facingMode: "user"
      },
      audio: false
    });

    videoElement.srcObject = stream;
    await videoElement.play();

    arBackgroundActive = false;
    if (arContainer) arContainer.style.display = 'none';
    document.body.classList.remove('ar-active');
    const arBtn = document.getElementById('btn-ar-bg');
    if (arBtn) {
      arBtn.innerText = 'CAM BG: OFF';
      arBtn.classList.remove('active');
    }

    overlayCanvas.width = videoElement.videoWidth || 640;
    overlayCanvas.height = videoElement.videoHeight || 480;
    overlayCtx = overlayCanvas.getContext('2d', { alpha: true });

    if (bgOverlayCanvas) {
      bgOverlayCanvas.width = window.innerWidth;
      bgOverlayCanvas.height = window.innerHeight;
      bgOverlayCtx = bgOverlayCanvas.getContext('2d', { alpha: true });
    }

    window.addEventListener('resize', () => {
      if (bgOverlayCanvas && arBackgroundActive) {
        bgOverlayCanvas.width = window.innerWidth;
        bgOverlayCanvas.height = window.innerHeight;
      }
    });

    gesturesActive = true;
    btn.innerText = 'GESTURE: ACTIVE';
    btn.style.color = 'var(--amber)';
    btn.classList.add('active');
    statusTag.innerText = 'VISION ONLINE: PINCH TO INTERACT';

    // Auto-enable OS mouse control mode
    toggleOsMouse();

    // Reset tracking states
    handStates[0].prevGrabX = null;
    handStates[0].prevGrabY = null;
    handStates[1].prevGrabX = null;
    handStates[1].prevGrabY = null;
    prevTwoHandDist = null;

    renderGestureLoop();
  } catch (err) {
    console.error("[EDITH Vision] Failed to activate gestures:", err);
    btn.innerText = 'GESTURE: ERROR';
    btn.style.color = 'var(--red)';
    statusTag.innerText = 'CAMERA / VISION INITIALIZATION FAILED';
    alert("Camera or MediaPipe initialization error: " + err.message);
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

  for (let hIdx = 0; hIdx < landmarksList.length; hIdx++) {
    const lm = landmarksList[hIdx];
    const isPinching = handStates[hIdx] ? handStates[hIdx].isPinching : false;

    ctx.lineWidth = isBg ? 2.5 : 2.0;
    ctx.strokeStyle = isPinching ? 'rgba(255, 183, 0, 0.95)' : 'rgba(0, 229, 255, 0.85)';

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
        ctx.fillStyle = isPinching ? '#ff0055' : '#00e5ff';
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
}

/**
 * Ultron Gesture Processor with Dual-Mode (Orb vs Full-Screen Desktop Mouse).
 */
function processUltronGestures(landmarksList) {
  const numHands = Math.min(landmarksList.length, 2);
  const now = performance.now();

  // Primary hand analysis
  const primaryHand = landmarksList[0];
  const wrist = primaryHand[WRIST];
  const thumb = primaryHand[THUMB_TIP];
  const index = primaryHand[INDEX_TIP];
  const middle = primaryHand[MIDDLE_TIP];
  const ring = primaryHand[RING_TIP];
  const pinky = primaryHand[PINKY_TIP];
  const indexMcp = primaryHand[INDEX_MCP];
  const middleMcp = primaryHand[MIDDLE_MCP];
  const ringMcp = primaryHand[RING_MCP];
  const pinkyMcp = primaryHand[PINKY_MCP];

  // Scale normalization based on hand size
  const handSpan = Math.hypot(wrist.x - middleMcp.x, wrist.y - middleMcp.y) || 0.2;
  const pinchDist = Math.hypot(thumb.x - index.x, thumb.y - index.y) / handSpan;
  const middlePinchDist = Math.hypot(thumb.x - middle.x, thumb.y - middle.y) / handSpan;
  const pinkyPinchDist = Math.hypot(thumb.x - pinky.x, thumb.y - pinky.y) / handSpan;

  // Normalized cursor coordinate with margin calibrated to comfortable hand zone
  const rawTargetX = Math.min(1.0, Math.max(0.0, (1.0 - index.x - 0.15) / 0.70));
  const rawTargetY = Math.min(1.0, Math.max(0.0, (index.y - 0.15) / 0.70));

  // Exponential moving average smoothing
  smoothMouseX = smoothMouseX + (rawTargetX - smoothMouseX) * SMOOTHING;
  smoothMouseY = smoothMouseY + (rawTargetY - smoothMouseY) * SMOOTHING;

  // Visual screen cursor on HUD
  const screenX = smoothMouseX * window.innerWidth;
  const screenY = smoothMouseY * window.innerHeight;

  if (cursorElement) {
    cursorElement.style.display = 'block';
    cursorElement.style.left = `${screenX}px`;
    cursorElement.style.top = `${screenY}px`;
  }

  // Check pinch states with hysteresis
  const primaryState = handStates[0];
  const wasPinching = primaryState.isPinching;
  if (primaryState.isPinching) {
    if (pinchDist > PINCH_OFF) primaryState.isPinching = false;
  } else {
    if (pinchDist < PINCH_ON) primaryState.isPinching = true;
  }

  // Check middle finger right-click pinch
  const isRightPinch = middlePinchDist < PINCH_ON && pinchDist >= PINCH_ON;

  // Check pinky pinch for volume
  const isPinkyPinch = pinkyPinchDist < PINCH_ON && pinchDist >= PINCH_ON;

  // Two fingers pointing up (scroll mode): index & middle extended, ring & pinky folded
  const isScrollGesture = (
    index.y < indexMcp.y &&
    middle.y < middleMcp.y &&
    ring.y > middleMcp.y &&
    pinky.y > pinkyMcp.y &&
    Math.hypot(index.x - middle.x, index.y - middle.y) < 0.14 &&
    pinchDist > PINCH_OFF
  );

  // Five fingers open wide (extended)
  const isFiveFingersOpen = (
    index.y < indexMcp.y &&
    middle.y < middleMcp.y &&
    ring.y < ringMcp.y &&
    pinky.y < pinkyMcp.y
  );

  // Closed Fist: all 4 fingers folded below MCPs
  const isClosedFist = (
    index.y > indexMcp.y &&
    middle.y > middleMcp.y &&
    ring.y > ringMcp.y &&
    pinky.y > pinkyMcp.y
  );

  // ==========================================
  // MODE A: FULL SCREEN OS MOUSE CONTROL
  // ==========================================
  if (osMouseActive) {
    // 1. Closed Fist Hold -> Toggle Media Play/Pause
    if (isClosedFist && (now - lastMediaTime > 1000)) {
      sendMouseAction("media_toggle");
      lastMediaTime = now;
      statusTag.innerText = "OS GESTURE: MEDIA PLAY / PAUSE ⏯️";
      return;
    }

    // 2. Five-Finger Open Swipe Down -> Show Desktop (Win+D)
    if (isFiveFingersOpen) {
      if (prevSwipeY !== null && (wrist.y - prevSwipeY > 0.14) && (now - lastDesktopTime > 1200)) {
        sendMouseAction("desktop");
        lastDesktopTime = now;
        prevSwipeY = null;
        statusTag.innerText = "OS GESTURE: SHOW DESKTOP 🖥️";
        return;
      }
      prevSwipeY = wrist.y;
    } else {
      prevSwipeY = null;
    }

    // 3. Horizontal Palm Wave -> Switch Window (Alt+Tab)
    if (isFiveFingersOpen || (index.y < indexMcp.y && middle.y < middleMcp.y)) {
      if (prevSwipeX !== null && Math.abs(wrist.x - prevSwipeX) > 0.18 && (now - lastSwitchTime > 900)) {
        sendMouseAction("switch_window");
        lastSwitchTime = now;
        prevSwipeX = null;
        statusTag.innerText = "OS GESTURE: SWITCH WINDOW (ALT+TAB) 🔀";
        return;
      }
      prevSwipeX = wrist.x;
    } else {
      prevSwipeX = null;
    }

    // 4. Cursor Movement Dispatch
    if (now - lastMouseSendTime > 25) { // ~40 Hz throttle
      const deltaDist = Math.hypot(smoothMouseX - lastSentNormX, smoothMouseY - lastSentNormY);
      if (deltaDist > 0.0025) {
        sendMouseAction("move", { x: smoothMouseX, y: smoothMouseY });
        lastSentNormX = smoothMouseX;
        lastSentNormY = smoothMouseY;
        lastMouseSendTime = now;
      }
    }

    // 5. Right Click (Middle finger + Thumb pinch)
    if (isRightPinch && (now - lastRightClickTime > 400)) {
      sendMouseAction("right_click");
      lastRightClickTime = now;
      if (cursorElement) cursorElement.classList.add("right-clicking");
      setTimeout(() => cursorElement && cursorElement.classList.remove("right-clicking"), 200);
      statusTag.innerText = "OS MOUSE: RIGHT CLICK 🖱️";
      return;
    }

    // 6. Two-Finger Scroll
    if (isScrollGesture) {
      if (prevScrollY !== null) {
        const deltaY = index.y - prevScrollY;
        if (now - lastScrollTime > 50) {
          if (deltaY < -0.012) {
            sendMouseAction("scroll", { delta: 1 }); // Scroll up
            lastScrollTime = now;
            statusTag.innerText = "OS MOUSE: SCROLL UP ↑";
          } else if (deltaY > 0.012) {
            sendMouseAction("scroll", { delta: -1 }); // Scroll down
            lastScrollTime = now;
            statusTag.innerText = "OS MOUSE: SCROLL DOWN ↓";
          }
        }
      }
      prevScrollY = index.y;
      return;
    } else {
      prevScrollY = null;
    }

    // 7. Volume Control (Pinky + Thumb pinch)
    if (isPinkyPinch && (now - lastVolumeTime > 220)) {
      const volDelta = index.y < 0.45 ? 5 : -5;
      sendMouseAction("volume", { delta: volDelta });
      lastVolumeTime = now;
      statusTag.innerText = volDelta > 0 ? "OS MOUSE: VOLUME UP 🔊" : "OS MOUSE: VOLUME DOWN 🔉";
      return;
    }

    // 8. Left Click / Drag & Drop / Double Click
    if (primaryState.isPinching) {
      if (!wasPinching) {
        // Pinch started
        pinchStartTime = now;
        isDraggingMouse = false;
        if (cursorElement) cursorElement.classList.add("pinching");
      } else {
        // Pinch held > 260ms -> enter Drag & Drop mode
        if (!isDraggingMouse && (now - pinchStartTime > 260)) {
          isDraggingMouse = true;
          sendMouseAction("drag_start");
          statusTag.innerText = "OS MOUSE: DRAG & DROP ACTIVE ✊";
        }
      }
    } else {
      if (wasPinching) {
        // Pinch released
        if (cursorElement) cursorElement.classList.remove("pinching");
        if (isDraggingMouse) {
          sendMouseAction("drag_end");
          isDraggingMouse = false;
          statusTag.innerText = "OS MOUSE: RELEASED";
        } else {
          // Quick tap release (< 260ms) -> Click or Double Click
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
  // MODE B: HOLOGRAPHIC 3D ORB INTERACTION
  // ==========================================
  // Two-Hand Mode: Dual Pinch Zoom
  if (numHands >= 2 && handStates[0].isPinching && handStates[1].isPinching) {
    const dist = Math.hypot(
      handStates[0].grabX - handStates[1].grabX,
      handStates[0].grabY - handStates[1].grabY
    );
    if (prevTwoHandDist !== null) {
      const deltaDist = dist - prevTwoHandDist;
      if (window.zoomOrb) window.zoomOrb(-deltaDist * ZOOM_SPEED);
    }
    prevTwoHandDist = dist;
    if (cursorElement) cursorElement.style.display = 'none';
    statusTag.innerText = 'DUAL PINCH: ZOOMING ORB';
    return;
  }
  prevTwoHandDist = null;

  // Single-Hand Mode: Rotate Orb
  if (primaryState.isPinching) {
    window.isUserPinching = true;
    if (cursorElement) cursorElement.classList.add('pinching');

    if (primaryState.prevGrabX !== null && primaryState.prevGrabY !== null) {
      const deltaX = (smoothMouseX - primaryState.prevGrabX) * ROTATE_SPEED;
      const deltaY = (smoothMouseY - primaryState.prevGrabY) * ROTATE_SPEED;
      if (window.rotateOrb) window.rotateOrb(deltaX, deltaY);
    }

    primaryState.prevGrabX = smoothMouseX;
    primaryState.prevGrabY = smoothMouseY;
    statusTag.innerText = 'PINCH ACTIVE: ROTATING ORB';
  } else {
    window.isUserPinching = false;
    if (cursorElement) cursorElement.classList.remove('pinching');
    primaryState.prevGrabX = null;
    primaryState.prevGrabY = null;
    statusTag.innerText = 'GESTURE READY: PINCH ORB (OR TOGGLE OS MOUSE)';
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
