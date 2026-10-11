/**
 * EDITH Holographic 3D Orb & Stage
 * Inspired by ULTRON Orb (Sagar Tamang) and barehands (Jared Rhodenizer).
 * Built with Three.js.
 */

let scene, camera, renderer;
let orbGroup, particleSphere, innerRings = [];
let coreMesh, cageMesh, coreMat, cageMat;
let targetColor = new THREE.Color(0x22d3ee); // Default Tactical Cyan
let currentColor = new THREE.Color(0x22d3ee);
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

  // 3. Inner Reactor Core (MAX version Icosahedron Core & Outer Cage)
  coreMat = new THREE.MeshBasicMaterial({
    color: currentColor,
    wireframe: true,
    transparent: true,
    opacity: 0.45,
    blending: THREE.AdditiveBlending
  });
  coreMesh = new THREE.Mesh(new THREE.IcosahedronGeometry(2.6, 2), coreMat);
  orbGroup.add(coreMesh);

  cageMat = new THREE.MeshBasicMaterial({
    color: currentColor,
    wireframe: true,
    transparent: true,
    opacity: 0.18,
    blending: THREE.AdditiveBlending
  });
  cageMesh = new THREE.Mesh(new THREE.IcosahedronGeometry(3.6, 1), cageMat);
  orbGroup.add(cageMesh);

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
  if (particleSphere) particleSphere.material.color = currentColor;
  innerRings.forEach(r => r.material.color = currentColor);
  if (coreMat) coreMat.color = currentColor;
  if (cageMat) cageMat.color = currentColor;

  if (coreMesh && !window.isUserPinching && !isDragging) {
    coreMesh.rotation.y += 0.005 * pulseSpeed;
    coreMesh.rotation.x += 0.003 * pulseSpeed;
  }
  if (cageMesh && !window.isUserPinching && !isDragging) {
    cageMesh.rotation.y -= 0.002 * pulseSpeed;
    cageMesh.rotation.z += 0.002 * pulseSpeed;
  }

  // Smooth scaling with gentle breathing animation
  baseOrbScale += (targetOrbScale - baseOrbScale) * 0.14;
  const breathe = 1.0 + Math.sin(time * 2) * 0.03;
  const currentScale = baseOrbScale * breathe;
  orbGroup.scale.set(currentScale, currentScale, currentScale);

  renderer.render(scene, camera);
}

let currentThemeMode = localStorage.getItem('edith_theme') || 'default';
const THEME_COLORS = {
  default: 0x22d3ee,
  edith: 0x22d3ee,
  jarvis: 0xf59e0b,
  friday: 0x10b981,
  karen: 0xf43f5e,
  peter: 0xe11d48,
  spiderman: 0xe11d48,
  ultron: 0xff1744,
  bnd: 0x85dbe1,
  focus: 0xff3d00,
};

window.setActiveTheme = function(mode) {
  currentThemeMode = mode;
  const hex = THEME_COLORS[mode] !== undefined ? THEME_COLORS[mode] : 0x22d3ee;
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

window.setOrbColor = function(hexColor) {
  targetColor = new THREE.Color(hexColor);
};

window.getCurrentThemeColor = function() {
  return '#' + targetColor.getHexString();
};

window.addEventListener('DOMContentLoaded', () => {
  initThreeScene();
  setInterval(pollState, 800);
  pollState();
});
