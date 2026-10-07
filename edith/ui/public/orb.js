/**
 * EDITH Holographic 3D Orb & Stage
 * Inspired by ULTRON Orb (Sagar Tamang) and barehands (Jared Rhodenizer).
 * Built with Three.js.
 */

let scene, camera, renderer;
let orbGroup, particleSphere, innerRings = [];
let targetColor = new THREE.Color(0x00e5ff); // Default Cyan
let currentColor = new THREE.Color(0x00e5ff);
let pulseSpeed = 1.0;
let isDragging = false;
let previousMousePosition = { x: 0, y: 0 };

const STATE_COLORS = {
  booting: 0x00e5ff,
  ready: 0x00e5ff,
  listening: 0x0077ff,
  understanding: 0x7928ca,
  planning: 0xffb700,
  executing: 0xa855f7,
  verifying: 0x00ffcc,
  completed: 0x10b981,
  error: 0xff0055,
  emergency_stop: 0xff0033
};

function initThreeScene() {
  const container = document.getElementById('canvas-container');
  const width = window.innerWidth;
  const height = window.innerHeight;

  scene = new THREE.Scene();
  scene.fog = null; // Crystal clear background pass-through for AR camera

  window.setThreeFog = function(enabled) {
    if (scene) {
      scene.fog = enabled ? new THREE.FogExp2(0x050811, 0.0015) : null;
    }
  };

  camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
  camera.position.z = 18;

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  orbGroup = new THREE.Group();
  scene.add(orbGroup);

  // 1. Particle Cloud Sphere (Holographic core)
  const particleCount = 2000;
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array(particleCount * 3);

  for (let i = 0; i < particleCount; i++) {
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos((Math.random() * 2) - 1);
    const r = 4.8 + (Math.random() * 0.4);

    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    positions[i * 3 + 2] = r * Math.cos(phi);
  }

  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

  const particleMaterial = new THREE.PointsMaterial({
    size: 0.12,
    color: currentColor,
    transparent: true,
    opacity: 0.85,
    blending: THREE.AdditiveBlending
  });

  particleSphere = new THREE.Points(geometry, particleMaterial);
  orbGroup.add(particleSphere);

  // 2. Concentric Holographic Rings (Jarvis Gyroscope)
  const ringGeometries = [
    new THREE.TorusGeometry(5.4, 0.02, 16, 100),
    new THREE.TorusGeometry(5.8, 0.02, 16, 100),
    new THREE.TorusGeometry(6.2, 0.015, 16, 100)
  ];

  ringGeometries.forEach((geom, idx) => {
    const ringMat = new THREE.MeshBasicMaterial({
      color: currentColor,
      transparent: true,
      opacity: 0.6 - (idx * 0.15),
      blending: THREE.AdditiveBlending
    });
    const ring = new THREE.Mesh(geom, ringMat);
    ring.rotation.x = Math.random() * Math.PI;
    ring.rotation.y = Math.random() * Math.PI;
    innerRings.push(ring);
    orbGroup.add(ring);
  });

  // Lights
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
  scene.add(ambientLight);

  // Event Listeners
  window.addEventListener('resize', onWindowResize);
  setupMouseControls();

  animate();
}

function setupMouseControls() {
  window.addEventListener('mousedown', (e) => {
    // Avoid hijacking clicks or text selection inside HUD glass cards, inputs, selects, and buttons
    if (
      e.target.closest('.glass-card') ||
      e.target.closest('.webcam-container') ||
      e.target.closest('select') ||
      e.target.closest('button') ||
      e.target.closest('input')
    ) {
      return;
    }
    isDragging = true;
    previousMousePosition = { x: e.clientX, y: e.clientY };
  });

  window.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const deltaX = e.clientX - previousMousePosition.x;
    const deltaY = e.clientY - previousMousePosition.y;

    orbGroup.rotation.y += deltaX * 0.005;
    orbGroup.rotation.x += deltaY * 0.005;

    previousMousePosition = { x: e.clientX, y: e.clientY };
  });

  window.addEventListener('mouseup', () => { isDragging = false; });

  window.addEventListener('wheel', (e) => {
    // Allow natural scrolling inside mission control and telemetry panels
    if (e.target.closest('.glass-card') || e.target.closest('#mission-log')) {
      return;
    }
    camera.position.z = Math.max(8, Math.min(30, camera.position.z + e.deltaY * 0.01));
  }, { passive: true });
}

let baseOrbScale = 1.0;
let targetOrbScale = 1.0;

// Global hook for MediaPipe gesture rotation and zoom
window.rotateOrb = function(deltaX, deltaY) {
  if (orbGroup) {
    orbGroup.rotation.y += deltaX;
    orbGroup.rotation.x += deltaY;
  }
};

window.zoomOrb = function(deltaZ) {
  if (camera) {
    camera.position.z = Math.max(6, Math.min(35, camera.position.z + deltaZ));
  }
};

window.scaleOrb = function(deltaScale) {
  targetOrbScale = Math.max(0.3, Math.min(4.5, targetOrbScale + deltaScale));
};

window.setOrbScale = function(newScale) {
  targetOrbScale = Math.max(0.3, Math.min(4.5, newScale));
};

window.getOrbScale = function() {
  return Math.round(targetOrbScale * 100);
};

window.resetOrb = function() {
  targetOrbScale = 1.0;
  if (camera) camera.position.z = 18;
  if (orbGroup) {
    orbGroup.rotation.set(0, 0, 0);
  }
};


function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
  requestAnimationFrame(animate);

  const time = performance.now() * 0.001 * pulseSpeed;

  // Auto rotation (paused during user hand pinch or mouse drag)
  if (!window.isUserPinching && !isDragging) {
    orbGroup.rotation.y += 0.003 * pulseSpeed;
    innerRings.forEach((ring, idx) => {
      ring.rotation.x += 0.004 * (idx + 1) * pulseSpeed;
      ring.rotation.y += 0.003 * (idx + 1) * pulseSpeed;
    });
  }

  // Color interpolation
  currentColor.lerp(targetColor, 0.05);
  particleSphere.material.color = currentColor;
  innerRings.forEach(r => r.material.color = currentColor);

  // Smooth scaling with gentle breathing animation
  baseOrbScale += (targetOrbScale - baseOrbScale) * 0.14;
  const breathe = 1.0 + Math.sin(time * 2) * 0.03;
  const currentScale = baseOrbScale * breathe;
  orbGroup.scale.set(currentScale, currentScale, currentScale);

  renderer.render(scene, camera);
}

let currentThemeMode = localStorage.getItem('edith_theme') || 'default';
const THEME_COLORS = {
  default: 0x00e5ff,
  bnd: 0x85dbe1,
  focus: 0xff3d00,
};

window.setActiveTheme = function(mode) {
  currentThemeMode = mode;
  const hex = THEME_COLORS[mode] !== undefined ? THEME_COLORS[mode] : 0x00e5ff;
  targetColor = new THREE.Color(hex);
};

// State polling & UI synchronization
async function pollState() {
  try {
    const res = await fetch('/state');
    if (!res.ok) return;
    const data = await res.json();
    const stateStr = data.emergency_stopped ? 'emergency_stop' : (data.state || 'ready');

    if (window.setEmergencyStopUI) {
      window.setEmergencyStopUI(!!data.emergency_stopped);
    }

    let hex;
    if (stateStr === 'ready' || stateStr === 'booting') {
      hex = THEME_COLORS[currentThemeMode] || 0x00e5ff;
    } else {
      hex = STATE_COLORS[stateStr] || THEME_COLORS[currentThemeMode] || 0x00e5ff;
    }
    targetColor = new THREE.Color(hex);

    const badge = document.getElementById('current-state-badge');
    if (badge) {
      badge.innerText = stateStr.toUpperCase();
      badge.style.color = '#' + targetColor.getHexString();
      badge.style.borderColor = '#' + targetColor.getHexString();
      badge.style.boxShadow = `0 0 22px ${'#' + targetColor.getHexString()}44`;
    }

    const headerState = document.getElementById('header-state-text');
    if (headerState) {
      headerState.innerText = stateStr.toUpperCase();
      headerState.style.color = '#' + targetColor.getHexString();
    }

    if (stateStr === 'thinking' || stateStr === 'planning') {
      pulseSpeed = 2.5;
    } else if (stateStr === 'executing') {
      pulseSpeed = 3.5;
    } else if (stateStr === 'emergency_stop') {
      pulseSpeed = 0.2;
    } else {
      pulseSpeed = 1.0;
    }
  } catch (e) {
    // Server polling retry silently
  }
}

async function pollTelemetry() {
  try {
    const res = await fetch('/telemetry');
    if (!res.ok) return;
    const data = await res.json();

    const cpuEl = document.getElementById('val-cpu');
    if (cpuEl) cpuEl.innerText = `${data.cpu || 'Intel Core'} (${data.cores || 4} Cores)`;

    const freeRam = parseFloat(data.free_ram_gb) || 0;
    const totalRam = parseFloat(data.total_ram_gb) || 8;
    const usedRam = parseFloat(data.used_ram_gb) || Math.max(0, totalRam - freeRam);
    const ramPct = data.ram_percent !== undefined ? data.ram_percent : Math.round((usedRam / totalRam) * 100);
    const ramEl = document.getElementById('val-ram');
    if (ramEl) ramEl.innerText = `${usedRam.toFixed(1)}G / ${totalRam.toFixed(1)}G (${ramPct}%)`;
    const barRam = document.getElementById('bar-ram');
    if (barRam) {
      barRam.style.width = `${Math.min(100, Math.max(5, ramPct))}%`;
      barRam.style.background = ramPct > 85 ? '#ff0055' : ramPct > 65 ? '#ffb700' : 'var(--cyan)';
    }

    const diskEl = document.getElementById('val-disk');
    if (diskEl) diskEl.innerText = `${data.disk_free_gb || '—'} GB free`;
    const barDisk = document.getElementById('bar-disk');
    if (barDisk) {
      barDisk.style.width = `45%`;
      barDisk.style.background = 'var(--cyan)';
    }

    const batEl = document.getElementById('val-battery');
    if (batEl) {
      if (data.battery_percent !== undefined) {
        const ac = data.is_ac_powered;
        batEl.innerText = `${data.battery_percent}% ${ac ? '(AC)' : '(BATT)'}`;
        batEl.className = 't-val' + (data.battery_percent < 15 ? ' err' : data.battery_percent < 30 ? ' warn' : ' ok');
      } else {
        batEl.innerText = 'AC POWERED';
        batEl.className = 't-val ok';
      }
    }

    const modelEl = document.getElementById('val-model');
    if (modelEl && modelEl.tagName === 'SELECT' && document.activeElement !== modelEl) {
      if (data.primary_model) modelEl.value = data.primary_model;
    }

    const runtimeEl = document.getElementById('val-runtime');
    if (runtimeEl) {
      const isOnline = data.is_online ?? true;
      runtimeEl.innerText = isOnline ? 'ONLINE (HYBRID AI)' : 'OFFLINE (LOCAL AI)';
      runtimeEl.className = 't-val' + (isOnline ? ' ok' : ' warn');
    }

    const modCore = document.getElementById('mod-core');
    if (modCore) {
      modCore.innerText = (data.primary_model || 'HERMES3:3B').toUpperCase();
    }
  } catch (_) {}
}

window.setOrbColor = function(hexColor) {
  targetColor = new THREE.Color(hexColor);
};

window.getCurrentThemeColor = function() {
  return '#' + targetColor.getHexString();
};

window.addEventListener('DOMContentLoaded', () => {
  initThreeScene();
  setInterval(pollState, 800);
  setInterval(pollTelemetry, 3000);
  pollState();
  pollTelemetry();
});
