/**
 * EDITH Holographic 3D Interactive Core
 * Adopted from ASTRA 6 design architecture (Three.js WebGL).
 * Implements Fibonacci particle cloud, orbital gyroscope rings,
 * wireframe shells, custom shader glow, pointer inertia, zoom,
 * and dynamic voice-persona theme synchronization.
 */

(function () {
  'use strict';

  let scene, camera, renderer, composer, bloom;
  let rootGroup, globeGroup, dotsMesh, shellMesh, innerMesh, glowMesh;
  let orbitGroup1, orbitGroup2, nodeMesh, dustPoints;
  let animFrameId = null;

  let pointerX = 0, pointerY = 0, pointerDown = false, lastX = 0, lastY = 0;
  let zoom = 1.0;
  let lastFrame = 0, frames = 0, fpsAt = 0;
  let currentFps = 60;

  // Active Core State
  let coreState = 'idle'; // 'idle', 'listening', 'thinking', 'speaking'
  let gestureData = { x: 0, y: 0, scale: 1 };

  // Theme Colors
  const THEME_PALETTES = {
    edith: { pale: '#37dce9', rim: '#128395' },
    jarvis: { pale: '#fbbf24', rim: '#b45309' },
    friday: { pale: '#34d399', rim: '#047857' },
    karen: { pale: '#fb7185', rim: '#be123c' },
    spiderman: { pale: '#38bdf8', rim: '#e11d48' },
    ultron: { pale: '#ff5252', rim: '#990000' }
  };
  let currentPalette = THEME_PALETTES.edith;

  function initOrb() {
    const host = document.getElementById('orb-canvas-container') || document.getElementById('canvas-container');
    if (!host || !window.THREE) return;

    host.innerHTML = '';

    const width = host.clientWidth || window.innerWidth;
    const height = host.clientHeight || window.innerHeight;

    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    } catch (e) {
      console.warn('WebGL initialization fallback:', e);
      return;
    }

    renderer.setClearColor(0x000000, 0);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
    renderer.setSize(width, height);
    if (renderer.outputColorSpace) renderer.outputColorSpace = THREE.SRGBColorSpace;
    host.appendChild(renderer.domElement);

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(44, width / height, 0.1, 100);
    camera.position.z = width / height < 1.1 ? 6.1 : 5.0;

    rootGroup = new THREE.Group();
    globeGroup = new THREE.Group();
    globeGroup.scale.setScalar(1.06);
    rootGroup.add(globeGroup);
    scene.add(rootGroup);

    // 1. Fibonacci Spherical Particle Cloud (11,000 points)
    const paleColor = new THREE.Color(currentPalette.pale);
    const rimColor = new THREE.Color(currentPalette.rim);
    const count = 11000;
    const positions = [];
    const colors = [];

    for (let i = 0; i < count; i++) {
      const y = 1 - (i / (count - 1)) * 2;
      const angle = i * Math.PI * (3 - Math.sqrt(5));
      const circle = Math.sqrt(Math.max(0, 1 - y * y));
      const band = Math.sin(y * 32 + Math.sin(angle * 4) * 0.4);
      const radius = 1.29 + Math.sin(angle * 7 + y * 22) * 0.033;

      positions.push(Math.cos(angle) * circle * radius, y * radius, Math.sin(angle) * circle * radius);
      const c = rimColor.clone().lerp(paleColor, Math.max(0, band) * 0.8 + 0.1);
      colors.push(c.r, c.g, c.b);
    }

    const dotsGeo = new THREE.BufferGeometry();
    dotsGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    dotsGeo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    const dotsMat = new THREE.PointsMaterial({
      size: 0.009,
      vertexColors: true,
      transparent: true,
      opacity: 0.72,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    dotsMesh = new THREE.Points(dotsGeo, dotsMat);
    globeGroup.add(dotsMesh);

    // 2. Outer Wireframe Sphere
    const shellGeo = new THREE.SphereGeometry(1.285, 60, 35);
    const shellMat = new THREE.MeshBasicMaterial({
      color: rimColor,
      wireframe: true,
      transparent: true,
      opacity: 0.22,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    shellMesh = new THREE.Mesh(shellGeo, shellMat);
    globeGroup.add(shellMesh);

    // 3. Inner Wireframe Icosahedron
    const innerGeo = new THREE.IcosahedronGeometry(0.96, 2);
    const innerMat = new THREE.MeshBasicMaterial({
      color: paleColor,
      wireframe: true,
      transparent: true,
      opacity: 0.075,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    innerMesh = new THREE.Mesh(innerGeo, innerMat);
    globeGroup.add(innerMesh);

    // 4. Custom Shader Rim Glow
    const glowMat = new THREE.ShaderMaterial({
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      vertexShader: `
        varying vec3 vNormal;
        varying vec3 vPosition;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          vec4 p = modelViewMatrix * vec4(position, 1.0);
          vPosition = p.xyz;
          gl_Position = projectionMatrix * p;
        }
      `,
      fragmentShader: `
        varying vec3 vNormal;
        varying vec3 vPosition;
        void main() {
          float rim = pow(1.0 - abs(dot(normalize(vNormal), normalize(-vPosition))), 2.8);
          gl_FragColor = vec4(0.05, 0.68, 0.8, rim * 0.12);
        }
      `
    });
    glowMesh = new THREE.Mesh(new THREE.SphereGeometry(1.3, 64, 48), glowMat);
    globeGroup.add(glowMesh);

    // 5. Orbital Concentric Rings
    function createRing(radius, start, length, opacity, parent = rootGroup) {
      const pts = [];
      for (let i = 0; i <= 180; i++) {
        const t = start + (i / 180) * length;
        pts.push(new THREE.Vector3(Math.cos(t) * radius, Math.sin(t) * radius, 0));
      }
      const ringGeo = new THREE.BufferGeometry().setFromPoints(pts);
      const ringMat = new THREE.LineBasicMaterial({
        color: paleColor,
        transparent: true,
        opacity: opacity,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      });
      const line = new THREE.Line(ringGeo, ringMat);
      parent.add(line);
      return line;
    }

    orbitGroup1 = new THREE.Group();
    orbitGroup1.rotation.set(0.76, -0.31, -0.35);
    rootGroup.add(orbitGroup1);
    createRing(1.66, 0, Math.PI * 2, 0.42, orbitGroup1);
    createRing(1.7, 0.2, Math.PI * 1.24, 0.16, orbitGroup1);

    orbitGroup2 = new THREE.Group();
    orbitGroup2.rotation.set(-0.72, 0.48, 0.83);
    rootGroup.add(orbitGroup2);
    createRing(1.53, 0, Math.PI * 2, 0.22, orbitGroup2);
    createRing(1.87, -0.08, Math.PI * 0.45, 0.55, rootGroup);
    createRing(1.87, Math.PI * 0.68, Math.PI * 0.38, 0.3, rootGroup);
    createRing(1.87, Math.PI * 1.37, Math.PI * 0.32, 0.28, rootGroup);
    createRing(1.96, 0, Math.PI * 2, 0.08, rootGroup);

    // 6. Ring Ticks
    const ticks = [];
    for (let i = 0; i < 160; i++) {
      const t = (i / 160) * Math.PI * 2;
      const r1 = i % 10 === 0 ? 1.84 : 1.88;
      const r2 = 1.91;
      ticks.push(Math.cos(t) * r1, Math.sin(t) * r1, 0, Math.cos(t) * r2, Math.sin(t) * r2, 0);
    }
    const tickGeo = new THREE.BufferGeometry();
    tickGeo.setAttribute('position', new THREE.Float32BufferAttribute(ticks, 3));
    rootGroup.add(new THREE.LineSegments(tickGeo, new THREE.LineBasicMaterial({ color: paleColor, opacity: 0.35, transparent: true })));

    // 7. Star Dust Cloud
    const stars = [];
    for (let i = 0; i < 320; i++) {
      stars.push((Math.random() - 0.5) * 9, (Math.random() - 0.5) * 5.5, (Math.random() - 0.5) * 3 - 2);
    }
    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute('position', new THREE.Float32BufferAttribute(stars, 3));
    dustPoints = new THREE.Points(starGeo, new THREE.PointsMaterial({
      size: 0.012,
      color: paleColor,
      transparent: true,
      opacity: 0.38,
      blending: THREE.AdditiveBlending
    }));
    scene.add(dustPoints);

    // 8. Orbiting Satellite Node
    nodeMesh = new THREE.Mesh(new THREE.SphereGeometry(0.024, 10, 10), new THREE.MeshBasicMaterial({ color: 0xffffff }));
    orbitGroup1.add(nodeMesh);

    // Interaction Listeners
    const down = (e) => {
      pointerDown = true;
      lastX = e.clientX;
      lastY = e.clientY;
      if (host.setPointerCapture) host.setPointerCapture(e.pointerId);
    };
    const move = (e) => {
      if (!pointerDown) return;
      pointerX += (e.clientX - lastX) * 0.006;
      pointerY += (e.clientY - lastY) * 0.006;
      lastX = e.clientX;
      lastY = e.clientY;
    };
    const up = () => { pointerDown = false; };
    const wheel = (e) => {
      e.preventDefault();
      zoom = Math.max(0.72, Math.min(1.35, zoom - e.deltaY * 0.0007));
    };

    host.addEventListener('pointerdown', down);
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
    host.addEventListener('wheel', wheel, { passive: false });

    // Resize Observer
    const onResize = () => {
      const w = host.clientWidth || window.innerWidth;
      const h = host.clientHeight || window.innerHeight;
      if (!w || !h) return;
      camera.aspect = w / h;
      camera.position.z = camera.aspect < 1.1 ? 6.1 : 5.0;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', onResize);

    // Animation Loop
    function animate(time) {
      animFrameId = requestAnimationFrame(animate);
      if (document.hidden) return;

      const delta = Math.min((time - lastFrame) / 1000, 0.05);
      lastFrame = time;
      frames++;
      if (time - fpsAt >= 1200) {
        currentFps = Math.round((frames * 1000) / (time - fpsAt));
        frames = 0;
        fpsAt = time;
        const fpsEl = document.getElementById('val-render-fps');
        if (fpsEl) fpsEl.textContent = `${currentFps} FPS`;
      }

      const active = coreState !== 'idle';
      globeGroup.rotation.y += delta * (active ? 0.22 : 0.075);
      innerMesh.rotation.y -= delta * 0.17;
      orbitGroup1.rotation.z += delta * 0.015;
      dustPoints.rotation.z += delta * 0.002;

      rootGroup.rotation.y += (pointerX + gestureData.x - rootGroup.rotation.y) * 0.055;
      rootGroup.rotation.x += (pointerY + gestureData.y - rootGroup.rotation.x) * 0.055;

      const targetScale = zoom * (gestureData.scale || 1.0) * (active ? 1 + Math.sin(time * 0.004) * 0.02 : 1.0);
      rootGroup.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.055);

      nodeMesh.position.set(Math.cos(time * 0.00022) * 1.66, Math.sin(time * 0.00022) * 1.66, 0);

      renderer.render(scene, camera);
    }

    animFrameId = requestAnimationFrame(animate);
  }

  // Public Interface for Core State & Themes
  window.setCoreState = function (state) {
    coreState = state || 'idle';
  };

  window.setGestureControl = function (x, y, scale) {
    gestureData.x = (x || 0) * 0.8;
    gestureData.y = (y || 0) * 0.8;
    gestureData.scale = scale || 1.0;
  };

  window.resetOrbView = function () {
    pointerX = 0;
    pointerY = 0;
    zoom = 1.0;
    gestureData = { x: 0, y: 0, scale: 1.0 };
  };

  window.rotateOrb = function (dx, dy) {
    pointerX += (dx || 0) * 0.015;
    pointerY += (dy || 0) * 0.015;
  };

  window.scaleOrb = function (delta) {
    zoom = Math.max(0.4, Math.min(3.0, zoom + (delta || 0)));
  };

  window.resetOrb = function () {
    window.resetOrbView();
  };

  window.getOrbScale = function () {
    return Math.round(zoom * 100);
  };

  window.setActiveTheme = function (themeName) {
    const key = (themeName || 'edith').toLowerCase();
    if (THEME_PALETTES[key]) {
      currentPalette = THEME_PALETTES[key];
      if (scene) {
        initOrb(); // Rebuild with new theme colors
      }
    }
  };

  // Auto-boot on load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initOrb);
  } else {
    initOrb();
  }
})();
