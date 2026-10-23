// Procedural illustrative athlete figure. Original geometry, no external assets.
// Local pinned three.js module only; no network, no paid runtime calls.

const REGION_WHITELIST = new Set(['arms', 'back', 'legs', 'chest']);

function getRegion() {
  try {
    const q = new URLSearchParams(window.location.search).get('region');
    return q && REGION_WHITELIST.has(q) ? q : 'back';
  } catch {
    return 'back';
  }
}

const region = getRegion();
const stage = document.getElementById('stage');
const fallback = document.getElementById('fallback');

function showFallback() {
  if (fallback) fallback.hidden = false;
}

async function main() {
  const THREE = await import('/ui-draft/vendor/three.module.min.js');

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  stage.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xeaf2fb);

  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  camera.position.set(0, 1.05, 4.4);
  camera.lookAt(0, 0.95, 0);

  // ---- Lighting: soft studio, no neon ----
  scene.add(new THREE.HemisphereLight(0xffffff, 0xcfdcec, 0.85));
  const key = new THREE.DirectionalLight(0xffffff, 1.1);
  key.position.set(2.5, 4, 3);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.camera.left = -3; key.shadow.camera.right = 3;
  key.shadow.camera.top = 4; key.shadow.camera.bottom = -2;
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xdfeaff, 0.35);
  fill.position.set(-3, 2, -2);
  scene.add(fill);

  // ---- Soft floor with procedural radial-gradient shadow texture ----
  const floorCanvas = document.createElement('canvas');
  floorCanvas.width = floorCanvas.height = 256;
  const fctx = floorCanvas.getContext('2d');
  const grad = fctx.createRadialGradient(128, 128, 10, 128, 128, 128);
  grad.addColorStop(0, 'rgba(70, 95, 130, 0.35)');
  grad.addColorStop(0.5, 'rgba(70, 95, 130, 0.12)');
  grad.addColorStop(1, 'rgba(70, 95, 130, 0)');
  fctx.fillStyle = grad;
  fctx.fillRect(0, 0, 256, 256);
  const shadowTex = new THREE.CanvasTexture(floorCanvas);
  const floorShadow = new THREE.Mesh(
    new THREE.PlaneGeometry(3.2, 3.2),
    new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false })
  );
  floorShadow.rotation.x = -Math.PI / 2;
  floorShadow.position.y = 0.001;
  scene.add(floorShadow);
  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(6, 48),
    new THREE.MeshStandardMaterial({ color: 0xdfeaf7, roughness: 1 })
  );
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);

  // ---- Materials ----
  const skin = new THREE.MeshStandardMaterial({ color: 0xe8c39e, roughness: 0.65 });
  const cloth = new THREE.MeshStandardMaterial({ color: 0x2f3644, roughness: 0.85 });
  const clothDark = new THREE.MeshStandardMaterial({ color: 0x272d3a, roughness: 0.9 });
  const hairMat = new THREE.MeshStandardMaterial({ color: 0x3a3f4a, roughness: 0.7 });
  const shoeMat = new THREE.MeshStandardMaterial({ color: 0xf2f5fa, roughness: 0.6 });
  const accent = new THREE.MeshStandardMaterial({
    color: 0x2f5fd0, roughness: 0.55, transparent: true, opacity: 0.85,
  });

  const figure = new THREE.Group();
  scene.add(figure);

  function mesh(geo, mat, x, y, z) {
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x, y, z);
    m.castShadow = true;
    figure.add(m);
    return m;
  }

  // Capsule limb helper: cylinder with rounded ends, oriented between two points.
  function limb(ax, ay, az, bx, by, bz, r, mat) {
    const a = new THREE.Vector3(ax, ay, az);
    const b = new THREE.Vector3(bx, by, bz);
    const len = a.distanceTo(b);
    const geo = new THREE.CapsuleGeometry(r, Math.max(len - r * 1.2, 0.02), 6, 16);
    const m = new THREE.Mesh(geo, mat);
    m.castShadow = true;
    m.position.copy(a).add(b).multiplyScalar(0.5);
    const dir = b.clone().sub(a).normalize();
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
    figure.add(m);
    return m;
  }

  // ---- Torso: lathe profile for a shapely athletic silhouette ----
  const torsoPts = [];
  const profile = [
    [0.00, 0.00], [0.16, 0.00], [0.185, 0.06], [0.175, 0.16],
    [0.15, 0.28], [0.145, 0.36], [0.165, 0.46], [0.20, 0.54],
    [0.215, 0.60], [0.19, 0.66], [0.10, 0.70], [0.07, 0.74], [0.00, 0.75],
  ];
  for (const [x, y] of profile) torsoPts.push(new THREE.Vector2(x, y));
  const torso = mesh(new THREE.LatheGeometry(torsoPts, 40), cloth, 0, 0.92, 0);
  torso.scale.z = 0.72; // anatomical depth vs width

  // Hips / shorts
  const hipPts = [];
  for (const [x, y] of [[0, 0], [0.175, 0], [0.19, 0.05], [0.175, 0.14], [0.12, 0.2], [0, 0.21]]) {
    hipPts.push(new THREE.Vector2(x, y));
  }
  const hips = mesh(new THREE.LatheGeometry(hipPts, 36), clothDark, 0, 0.78, 0);
  hips.scale.z = 0.78;

  // ---- Head, face hints, hair bun ----
  mesh(new THREE.SphereGeometry(0.115, 28, 22), skin, 0, 1.78, 0);
  mesh(new THREE.CylinderGeometry(0.045, 0.055, 0.09, 16), skin, 0, 1.68, 0);
  const hair = mesh(new THREE.SphereGeometry(0.118, 28, 22), hairMat, 0, 1.795, -0.015);
  hair.scale.set(1, 0.92, 1);
  mesh(new THREE.SphereGeometry(0.05, 18, 14), hairMat, 0, 1.88, -0.1); // bun
  const eyeMat = new THREE.MeshStandardMaterial({ color: 0x2a2f3a, roughness: 0.4 });
  mesh(new THREE.SphereGeometry(0.011, 10, 8), eyeMat, -0.042, 1.785, 0.105);
  mesh(new THREE.SphereGeometry(0.011, 10, 8), eyeMat, 0.042, 1.785, 0.105);

  // ---- Arms: slight A-pose, distinct shoulder/elbow/wrist transitions ----
  for (const s of [-1, 1]) {
    const sx = s * 0.235;
    mesh(new THREE.SphereGeometry(0.075, 20, 16), cloth, sx, 1.52, 0); // shoulder cap (sleeve)
    limb(sx, 1.52, 0, s * 0.30, 1.24, 0.02, 0.058, cloth);            // upper arm (sleeved)
    mesh(new THREE.SphereGeometry(0.05, 16, 12), skin, s * 0.30, 1.24, 0.02); // elbow
    limb(s * 0.30, 1.24, 0.02, s * 0.315, 1.00, 0.06, 0.047, skin);   // forearm
    mesh(new THREE.SphereGeometry(0.05, 16, 12), skin, s * 0.318, 0.95, 0.07); // hand
  }

  // ---- Legs: leggings, distinct knee/ankle transitions, sneakers ----
  for (const s of [-1, 1]) {
    const hx = s * 0.095;
    limb(hx, 0.86, 0, s * 0.115, 0.50, 0.01, 0.085, clothDark);  // thigh
    mesh(new THREE.SphereGeometry(0.068, 18, 14), clothDark, s * 0.115, 0.50, 0.01); // knee
    limb(s * 0.115, 0.50, 0.01, s * 0.125, 0.16, 0.02, 0.058, clothDark); // calf
    const shoe = mesh(new THREE.SphereGeometry(0.075, 18, 14), shoeMat, s * 0.128, 0.06, 0.06);
    shoe.scale.set(1, 0.62, 1.7); // sneaker
  }

  // ---- Cobalt target accents (muted overlays, finite, per region) ----
  const accents = [];
  function accentMesh(geo, x, y, z, sx = 1, sy = 1, sz = 1) {
    const m = mesh(geo, accent, x, y, z);
    m.scale.set(sx, sy, sz);
    accents.push(m);
    return m;
  }
  if (region === 'arms') {
    for (const s of [-1, 1]) {
      accentMesh(new THREE.SphereGeometry(0.062, 18, 14), s * 0.272, 1.38, 0.035, 1, 1.35, 1); // biceps
      accentMesh(new THREE.SphereGeometry(0.048, 16, 12), s * 0.308, 1.12, 0.05, 1, 1.3, 1);  // forearm
    }
  } else if (region === 'back') {
    for (const s of [-1, 1]) {
      accentMesh(new THREE.SphereGeometry(0.085, 18, 14), s * 0.10, 1.42, -0.135, 1.15, 1.5, 0.45); // lats
    }
    accentMesh(new THREE.SphereGeometry(0.07, 16, 12), 0, 1.56, -0.12, 1.6, 0.7, 0.4); // upper back
  } else if (region === 'legs') {
    for (const s of [-1, 1]) {
      accentMesh(new THREE.SphereGeometry(0.085, 18, 14), s * 0.105, 0.68, 0.045, 1, 1.5, 0.9); // quads
      accentMesh(new THREE.SphereGeometry(0.06, 16, 12), s * 0.122, 0.32, -0.03, 1, 1.3, 0.9);  // calves
    }
    accentMesh(new THREE.SphereGeometry(0.09, 16, 12), 0, 0.86, -0.1, 1.7, 0.9, 0.6); // glutes
  } else if (region === 'chest') {
    for (const s of [-1, 1]) {
      accentMesh(new THREE.SphereGeometry(0.085, 18, 14), s * 0.095, 1.47, 0.125, 1.2, 0.95, 0.45); // pecs
    }
    for (const s of [-1, 1]) {
      accentMesh(new THREE.SphereGeometry(0.05, 14, 10), s * 0.225, 1.50, 0.05, 1, 1, 1); // front delts
    }
  }

  // ---- Interaction: drag rotate (pointer capture), buttons, keyboard ----
  let targetYaw = 0;
  let yaw = 0;
  let dragging = false;
  let lastX = 0;
  let needsRender = true;
  let visible = true;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function requestRender() { needsRender = true; }
  function setYaw(v) { targetYaw = v; if (reduced) { yaw = v; figure.rotation.y = yaw; } requestRender(); }

  const el = renderer.domElement;
  el.style.touchAction = 'pan-y';
  el.tabIndex = 0;
  el.setAttribute('role', 'img');
  el.setAttribute('aria-label', 'Illustrated athlete figure, drag to rotate');

  el.addEventListener('pointerdown', (e) => {
    dragging = true;
    lastX = e.clientX;
    el.setPointerCapture(e.pointerId);
  });
  el.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const dx = e.clientX - lastX;
    lastX = e.clientX;
    setYaw(targetYaw + dx * 0.008);
  });
  function endDrag(e) {
    dragging = false;
    try { el.releasePointerCapture(e.pointerId); } catch { /* already released */ }
  }
  el.addEventListener('pointerup', endDrag);
  el.addEventListener('pointercancel', endDrag);
  el.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') { setYaw(targetYaw - 0.25); e.preventDefault(); }
    else if (e.key === 'ArrowRight') { setYaw(targetYaw + 0.25); e.preventDefault(); }
  });

  function bind(id, fn) {
    const b = document.getElementById(id);
    if (b) b.addEventListener('click', fn);
  }
  bind('btn-front', () => setYaw(0));
  bind('btn-back', () => setYaw(Math.PI));
  bind('btn-left', () => setYaw(targetYaw - Math.PI / 4));
  bind('btn-right', () => setYaw(targetYaw + Math.PI / 4));

  // ---- Resize: fit full body head-to-feet in any aspect ----
  function resize() {
    const w = stage.clientWidth || 1;
    const h = stage.clientHeight || 1;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    // Ensure the ~1.95-unit figure fits vertically and horizontally.
    const fitHeight = 2.1;
    const vFov = (camera.fov * Math.PI) / 180;
    const distV = fitHeight / (2 * Math.tan(vFov / 2));
    const distH = distV / Math.max(camera.aspect, 0.35);
    const dist = Math.max(distV, distH) + 1.2;
    camera.position.set(0, 1.0, dist);
    camera.lookAt(0, 0.95, 0);
    camera.updateProjectionMatrix();
    requestRender();
  }
  const ro = new ResizeObserver(resize);
  ro.observe(stage);
  resize();

  // ---- Render-on-demand; pause when hidden/offscreen ----
  const io = new IntersectionObserver((entries) => {
    visible = entries[0] ? entries[0].isIntersecting : true;
    if (visible) requestRender();
  });
  io.observe(el);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) requestRender();
  });

  let rafId = 0;
  let disposed = false;
  function tick() {
    if (disposed) return;
    rafId = requestAnimationFrame(tick);
    if (document.hidden || !visible) return;
    const diff = targetYaw - yaw;
    if (Math.abs(diff) > 0.0005) {
      yaw += diff * (reduced ? 1 : 0.18);
      figure.rotation.y = yaw;
      needsRender = true;
    }
    if (needsRender) {
      renderer.render(scene, camera);
      needsRender = false;
    }
  }
  tick();

  // ---- Disposal ----
  function dispose() {
    disposed = true;
    cancelAnimationFrame(rafId);
    ro.disconnect();
    io.disconnect();
    scene.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
        for (const m of mats) {
          if (m.map) m.map.dispose();
          m.dispose();
        }
      }
    });
    shadowTex.dispose();
    renderer.dispose();
    if (el.parentNode) el.parentNode.removeChild(el);
  }
  window.addEventListener('pagehide', dispose, { once: true });
}

main().catch((err) => {
  // WebGL or module load failure: show accessible static illustration.
  console.warn('Athlete companion 3D unavailable:', err);
  showFallback();
});
