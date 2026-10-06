/**
 * EDITH Holographic Hand Gesture & Vision Control Layer
 * Engineered based on Ultron (Sagar Tamang) and Barehands (Jared Rhodenizer).
 * 
 * Features:
 * - MediaPipe Hand Landmarker with GPU + CPU fallback
 * - Pinch hysteresis (PINCH_ON=0.32, PINCH_OFF=0.45) for rock-solid grab stability
 * - Exponential Moving Average (EMA) smoothing for zero-jitter rotation
 * - Dual-hand pinch-to-zoom with distance tracking
 * - High-visibility cybernetic skeleton rendering on HUD video overlay
 * - Full-screen holographic laser cursor following index finger
 */

// Global state
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
let handLandmarker = null;
let animationFrameId = null;
let lastVideoTime = -1;

// Ultron gesture tuning constants
const WRIST = 0;
const THUMB_TIP = 4;
const INDEX_TIP = 8;
const MIDDLE_MCP = 9;

const PINCH_ON = 0.38;   // Enter pinch below this relative distance
const PINCH_OFF = 0.52;  // Exit pinch above this relative distance
const ROTATE_SPEED = 7.0;
const ZOOM_SPEED = 35.0;
const SMOOTHING = 0.88;  // Super-fluid 60FPS instant response without lag

// Persistent tracking states per hand (indexed 0 and 1)
const handStates = [
  { isPinching: false, grabX: 0.5, grabY: 0.5, prevGrabX: null, prevGrabY: null },
  { isPinching: false, grabX: 0.5, grabY: 0.5, prevGrabX: null, prevGrabY: null }
];

let prevTwoHandDist = null;

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
    // Attempt GPU acceleration
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
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId);
      animationFrameId = null;
    }
    btn.innerText = 'GESTURE: OFF';
    btn.style.color = '';
    btn.classList.remove('active');
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
    if (bgVideoElement) bgVideoElement.srcObject = null;
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
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: "user"
      },
      audio: false
    });

    videoElement.srcObject = stream;
    await videoElement.play();

    // Setup background camera element in standby (OFF by default as requested by user)
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
    overlayCtx = overlayCanvas.getContext('2d');

    if (bgOverlayCanvas) {
      bgOverlayCanvas.width = window.innerWidth;
      bgOverlayCanvas.height = window.innerHeight;
      bgOverlayCtx = bgOverlayCanvas.getContext('2d');
    }

    window.addEventListener('resize', () => {
      if (bgOverlayCanvas) {
        bgOverlayCanvas.width = window.innerWidth;
        bgOverlayCanvas.height = window.innerHeight;
      }
    });

    gesturesActive = true;
    btn.innerText = 'GESTURE: ACTIVE';
    btn.style.color = 'var(--amber)';
    btn.classList.add('active');
    statusTag.innerText = 'VISION ONLINE: PINCH TO INTERACT';

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
 * Continuous frame rendering loop.
 */
function renderGestureLoop() {
  if (!gesturesActive) return;

  try {
    const now = performance.now();
    if (videoElement && videoElement.readyState >= 2 && handLandmarker) {
      if (videoElement.currentTime !== lastVideoTime) {
        lastVideoTime = videoElement.currentTime;

        const results = handLandmarker.detectForVideo(videoElement, now);

        if (overlayCtx && overlayCanvas) {
          overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
        }
        if (bgOverlayCtx && bgOverlayCanvas) {
          bgOverlayCtx.clearRect(0, 0, bgOverlayCanvas.width, bgOverlayCanvas.height);
        }

        if (results && results.landmarks && results.landmarks.length > 0) {
          drawCyberneticSkeleton(results.landmarks, overlayCtx, overlayCanvas);
          if (bgOverlayCtx && bgOverlayCanvas) {
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

  ctx.shadowBlur = 0; // Disabled for maximum 60FPS rendering throughput

  for (let hIdx = 0; hIdx < landmarksList.length; hIdx++) {
    const lm = landmarksList[hIdx];
    const isPinching = handStates[hIdx] ? handStates[hIdx].isPinching : false;

    // Draw cybernetic bones
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

    // Draw joints
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

    // Draw glowing pinch ring if pinching
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
 * Ultron Hysteresis & Smoothing Gesture Processor.
 */
function processUltronGestures(landmarksList) {
  const numHands = Math.min(landmarksList.length, 2);

  // Update pinch state & smoothed coordinates for each hand
  for (let i = 0; i < numHands; i++) {
    const hand = landmarksList[i];
    const wrist = hand[WRIST];
    const middleMcp = hand[MIDDLE_MCP];
    const thumb = hand[THUMB_TIP];
    const index = hand[INDEX_TIP];

    // Hand scale normalization
    const handSpan = Math.hypot(wrist.x - middleMcp.x, wrist.y - middleMcp.y) || 0.2;
    const rawPinchDist = Math.hypot(thumb.x - index.x, thumb.y - index.y) / handSpan;

    // Hysteresis logic
    const state = handStates[i];
    if (state.isPinching) {
      if (rawPinchDist > PINCH_OFF) {
        state.isPinching = false;
      }
    } else {
      if (rawPinchDist < PINCH_ON) {
        state.isPinching = true;
      }
    }

    // Mirrored coordinates for intuitive interaction
    const rawMidX = 1.0 - ((thumb.x + index.x) / 2.0);
    const rawMidY = (thumb.y + index.y) / 2.0;

    // Exponential Moving Average (EMA) smoothing
    state.grabX = state.grabX + (rawMidX - state.grabX) * SMOOTHING;
    state.grabY = state.grabY + (rawMidY - state.grabY) * SMOOTHING;
  }

  // --- Two-Hand Mode: Dual Pinch Zoom ---
  if (numHands >= 2 && handStates[0].isPinching && handStates[1].isPinching) {
    const dist = Math.hypot(
      handStates[0].grabX - handStates[1].grabX,
      handStates[0].grabY - handStates[1].grabY
    );

    if (prevTwoHandDist !== null) {
      const deltaDist = dist - prevTwoHandDist;
      if (window.zoomOrb) {
        window.zoomOrb(-deltaDist * ZOOM_SPEED);
      }
    }

    prevTwoHandDist = dist;
    handStates[0].prevGrabX = null;
    handStates[0].prevGrabY = null;
    handStates[1].prevGrabX = null;
    handStates[1].prevGrabY = null;

    if (cursorElement) cursorElement.style.display = 'none';
    statusTag.innerText = 'DUAL PINCH: ZOOMING ORB';
    return;
  }

  prevTwoHandDist = null;

  // --- Single-Hand Mode: Hand 0 Interaction ---
  const primaryHand = landmarksList[0];
  const primaryState = handStates[0];

  // Full-screen holographic cursor follows index fingertip (with aspect-ratio compensation)
  const indexPos = primaryHand[INDEX_TIP];
  const map = getVideoMapping(bgOverlayCanvas || { width: window.innerWidth, height: window.innerHeight });
  const screenX = map.offsetX + (1.0 - indexPos.x) * map.scaleX;
  const screenY = map.offsetY + indexPos.y * map.scaleY;

  if (cursorElement) {
    cursorElement.style.display = 'block';
    cursorElement.style.left = `${screenX}px`;
    cursorElement.style.top = `${screenY}px`;
  }

  if (primaryState.isPinching) {
    window.isUserPinching = true;
    if (cursorElement) cursorElement.classList.add('pinching');

    if (primaryState.prevGrabX !== null && primaryState.prevGrabY !== null) {
      const deltaX = (primaryState.grabX - primaryState.prevGrabX) * ROTATE_SPEED;
      const deltaY = (primaryState.grabY - primaryState.prevGrabY) * ROTATE_SPEED;

      if (window.rotateOrb) {
        window.rotateOrb(deltaX, deltaY);
      }
    }

    primaryState.prevGrabX = primaryState.grabX;
    primaryState.prevGrabY = primaryState.grabY;
    statusTag.innerText = 'PINCH ACTIVE: ROTATING ORB';
  } else {
    window.isUserPinching = false;
    if (cursorElement) cursorElement.classList.remove('pinching');
    primaryState.prevGrabX = null;
    primaryState.prevGrabY = null;
    statusTag.innerText = 'HAND DETECTED: PINCH TO ROTATE';
  }
}

// Expose toggle function globally for DOM buttons
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
    if (arContainer) arContainer.style.display = 'none';
    document.body.classList.remove('ar-active');
    if (arBtn) {
      arBtn.innerText = 'CAM BG: OFF';
      arBtn.classList.remove('active');
    }
  }
}
window.toggleArBackground = toggleArBackground;

