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
  let spiderLogo3D, coreCrystalMesh;
  let animFrameId = null;

  let pointerX = 0, pointerY = 0, pointerDown = false, lastX = 0, lastY = 0;
  let zoom = 1.0;
  let lastFrame = 0, frames = 0, fpsAt = 0;
  let currentFps = 60;

  // Active Core State
  let coreState = 'idle'; // 'idle', 'listening', 'thinking', 'speaking'
  let gestureData = { x: 0, y: 0, scale: 1 };
  let currentThemeName = 'edith';

  // Theme Colors
  const THEME_PALETTES = {
    edith: { pale: '#37dce9', rim: '#128395' },
    jarvis: { pale: '#fbbf24', rim: '#b45309' },
    friday: { pale: '#34d399', rim: '#047857' },
    karen: { pale: '#fb7185', rim: '#be123c' },
    spiderman: { pale: '#00f0ff', rim: '#ff1744' },
    peter: { pale: '#00f0ff', rim: '#ff1744' },
    peter1: { pale: '#00f0ff', rim: '#ff1744' },
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

    // 9. Procedural 3D Spider Emblem (Stitch Mark II Design System)
    spiderLogo3D = new THREE.Group();
    spiderLogo3D.scale.set(0.24, 0.24, 0.24);
    globeGroup.add(spiderLogo3D);

    const isSpidey = currentThemeName === 'spiderman' || currentThemeName === 'peter' || currentThemeName === 'peter1' || currentThemeName === 'peter 1' || currentThemeName === 'peter one' || currentThemeName === 'edith // peter 1' || currentThemeName === 'spidey';
    spiderLogo3D.visible = isSpidey;
    if (dotsMesh) dotsMesh.visible = !isSpidey;
    if (shellMesh) shellMesh.visible = !isSpidey;
    if (innerMesh) innerMesh.visible = !isSpidey;
    if (glowMesh) glowMesh.visible = !isSpidey;

    const emblemMatWhite = new THREE.MeshPhongMaterial({
      color: 0xffffff,
      emissive: 0x1a202c,
      specular: 0x00f0ff,
      shininess: 80,
      flatShading: false,
      side: THREE.DoubleSide
    });

    const emblemMatRed = new THREE.MeshPhongMaterial({
      color: 0xff1744,
      emissive: 0x4a000e,
      shininess: 90,
      flatShading: false,
      side: THREE.DoubleSide
    });

    function createExtrudedPart(pts, depth, bevel) {
      const shape = new THREE.Shape();
      if (!pts || pts.length < 3) return null;
      shape.moveTo(pts[0][0], pts[0][1]);
      for (let i = 1; i < pts.length; i++) {
        shape.lineTo(pts[i][0], pts[i][1]);
      }
      shape.closePath();

      const extrudeSettings = {
        steps: 1,
        depth: depth || 0.45,
        bevelEnabled: true,
        bevelThickness: bevel || 0.15,
        bevelSize: bevel || 0.12,
        bevelSegments: 3
      };

      const geo = new THREE.ExtrudeGeometry(shape, extrudeSettings);
      geo.center();
      return geo;
    }

    const abdomenPts = [[0, 2.8], [1.4, 1.2], [1.2, -1.8], [0, -4.6], [-1.2, -1.8], [-1.4, 1.2]];
    const abdomenGeo = createExtrudedPart(abdomenPts, 0.55, 0.2);
    if (abdomenGeo) {
      const abdomenMesh = new THREE.Mesh(abdomenGeo, emblemMatWhite);
      abdomenMesh.position.y = -0.5;
      spiderLogo3D.add(abdomenMesh);
    }

    const spinePts = [[0, 2.0], [0.6, 0.8], [0.5, -1.2], [0, -3.8], [-0.5, -1.2], [-0.6, 0.8]];
    const spineGeo = createExtrudedPart(spinePts, 0.65, 0.1);
    if (spineGeo) {
      const spineMesh = new THREE.Mesh(spineGeo, emblemMatRed);
      spineMesh.position.set(0, -0.5, 0.05);
      spiderLogo3D.add(spineMesh);
    }

    const headPts = [[0, 2.2], [0.9, 1.2], [0.5, 0.0], [0, -0.6], [-0.5, 0.0], [-0.9, 1.2]];
    const headGeo = createExtrudedPart(headPts, 0.45, 0.16);
    if (headGeo) {
      const headMesh = new THREE.Mesh(headGeo, emblemMatWhite);
      headMesh.position.y = 3.1;
      spiderLogo3D.add(headMesh);
    }

    const coreCrystalGeo = new THREE.OctahedronGeometry(0.55, 0);
    const coreCrystalMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      wireframe: true,
      transparent: true,
      opacity: 0.95,
      blending: THREE.AdditiveBlending
    });
    coreCrystalMesh = new THREE.Mesh(coreCrystalGeo, coreCrystalMat);
    coreCrystalMesh.position.set(0, 0.5, 0.4);
    spiderLogo3D.add(coreCrystalMesh);

    const legDefinitions = [
      {
        pts: [
          [0.6, 2.0], [2.2, 3.8], [3.8, 5.8], [4.2, 5.4], [2.6, 3.2],
          [1.8, 1.4], [2.4, -1.5], [3.2, -4.8], [2.8, -4.9], [1.6, -1.8], [1.1, 1.2]
        ],
        depth: 0.35, bevel: 0.12
      },
      {
        pts: [
          [0.8, 1.6], [2.8, 3.0], [4.4, 3.8], [4.6, 3.4], [3.0, 2.4],
          [2.5, 0.5], [2.9, -2.8], [2.5, -2.8], [1.9, 0.2], [1.2, 1.1]
        ],
        depth: 0.32, bevel: 0.1
      },
      {
        pts: [
          [0.9, 0.6], [3.2, 1.6], [5.2, 1.4], [5.4, 0.9], [3.4, 0.7],
          [2.8, -1.2], [3.4, -3.9], [3.0, -3.9], [2.2, -1.4], [1.2, 0.1]
        ],
        depth: 0.3, bevel: 0.1
      },
      {
        pts: [
          [0.8, -0.6], [2.6, -0.2], [4.4, -0.8], [4.2, -1.3], [2.8, -1.1],
          [2.2, -2.6], [2.2, -5.6], [1.8, -5.6], [1.6, -2.8], [0.9, -1.4]
        ],
        depth: 0.3, bevel: 0.1
      }
    ];

    legDefinitions.forEach((def) => {
      const geoR = createExtrudedPart(def.pts, def.depth, def.bevel);
      if (geoR) {
        const meshR = new THREE.Mesh(geoR, emblemMatWhite);
        spiderLogo3D.add(meshR);

        const ptsL = def.pts.map(p => [-p[0], p[1]]);
        const geoL = createExtrudedPart(ptsL, def.depth, def.bevel);
        const meshL = new THREE.Mesh(geoL, emblemMatWhite);
        spiderLogo3D.add(meshL);
      }
    });

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.4);
    dirLight1.position.set(4, 6, 8);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x00f0ff, 1.0);
    dirLight2.position.set(-6, -4, 4);
    scene.add(dirLight2);

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

      if (spiderLogo3D && spiderLogo3D.visible) {
        spiderLogo3D.rotation.y = time * 0.00065;
        spiderLogo3D.rotation.z = Math.sin(time * 0.0018) * 0.08;
        spiderLogo3D.position.y = Math.sin(time * 0.0022) * 0.08;
        if (coreCrystalMesh) {
          coreCrystalMesh.rotation.x = time * 0.0022;
          coreCrystalMesh.rotation.y = time * 0.0026;
        }
      }

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

  window.setActiveTheme = function (themeName) {
    const raw = (themeName || 'edith').toLowerCase().trim();
    const key = (raw === 'peter' || raw === 'peter1' || raw === 'peter 1' || raw === 'peter one' || raw === 'edith // peter 1' || raw === 'spidey') ? 'spiderman' : raw;
    currentThemeName = key;
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
