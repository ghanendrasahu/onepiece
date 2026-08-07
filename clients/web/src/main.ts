import * as THREE from "three";

/**
 * WorldView VR 360° web player.
 *
 * Loads an equirectangular (360°) video into a scene-mapped sphere. The camera
 * orbits via pointer drag / touch, matching the "look around" UX of the mobile
 * player. WebXR (true VR headsets) is the follow-up integration.
 *
 * Usage: ?src=<absolute video URL>. If omitted, a demo procedural skybox plays.
 */

const container = document.getElementById("app")!;
const params = new URLSearchParams(location.search);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, innerWidth / innerHeight, 0.1, 1000);

// Orbit state
const target = new THREE.Euler(0, 0, 0, "YXZ");
const look = { yaw: 0, pitch: 0 };

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
container.appendChild(renderer.domElement);

// Invert the sphere so the texture is visible from inside.
const sphere = new THREE.Mesh(
  new THREE.SphereGeometry(500, 64, 64),
  new THREE.MeshBasicMaterial({ side: THREE.BackSide }),
);
scene.add(sphere);

const src = params.get("src");
if (src) {
  const video = document.createElement("video");
  video.src = src;
  video.crossOrigin = "anonymous";
  video.loop = true;
  video.muted = true;
  video.play();
  sphere.material.map = new THREE.VideoTexture(video);
  sphere.material.needsUpdate = true;
} else {
  // Procedural demo fallback: a gradient skybox with a "sun".
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 1024;
  const ctx = canvas.getContext("2d")!;
  const grad = ctx.createLinearGradient(0, 0, 0, 1024);
  grad.addColorStop(0, "#1b2f63");
  grad.addColorStop(0.5, "#0a0f1e");
  grad.addColorStop(1, "#2e6bff");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 1024, 1024);
  sphere.material.map = new THREE.CanvasTexture(canvas);
  sphere.material.needsUpdate = true;
}

// --- Pointer/touch look controls ---
let dragging = false;
let lastX = 0;
let lastY = 0;

renderer.domElement.addEventListener("pointerdown", (e) => {
  dragging = true;
  lastX = e.clientX;
  lastY = e.clientY;
});
addEventListener("pointerup", () => (dragging = false));
addEventListener("pointermove", (e) => {
  if (!dragging) return;
  const dx = e.clientX - lastX;
  const dy = e.clientY - lastY;
  lastX = e.clientX;
  lastY = e.clientY;
  look.yaw -= dx * 0.003;
  look.pitch -= dy * 0.003;
  look.pitch = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, look.pitch));
});

// Touch on mobile
renderer.domElement.addEventListener("touchstart", (e) => {
  dragging = true;
  lastX = e.touches[0].clientX;
  lastY = e.touches[0].clientY;
});
renderer.domElement.addEventListener("touchmove", (e) => {
  if (!dragging) return;
  const t = e.touches[0];
  const dx = t.clientX - lastX;
  const dy = t.clientY - lastY;
  lastX = t.clientX;
  lastY = t.clientY;
  look.yaw -= dx * 0.004;
  look.pitch -= dy * 0.004;
  look.pitch = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, look.pitch));
});
renderer.domElement.addEventListener("touchend", () => (dragging = false));

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

function animate() {
  requestAnimationFrame(animate);
  camera.rotation.set(look.pitch, look.yaw, 0, "YXZ");
  renderer.render(scene, camera);
}
animate();

// Expose for tests / console debugging.
declare global {
  interface Window {
    worldViewPlayer?: { setYaw(y: number): void };
  }
}
window.worldViewPlayer = {
  setYaw(y: number) {
    look.yaw = y;
  },
};
