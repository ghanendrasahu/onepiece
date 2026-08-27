import * as THREE from "three";
import Hls from "hls.js";

export interface Hotspot {
  id: string;
  yawDeg: number;
  pitchDeg: number;
  label: string;
  desc: string;
  ask: string;
}

export interface TourDef {
  id: string;
  name: string;
  mode: "live" | "vod";
  regionKey: string;
  lat: number;
  lng: number;
  hotspots: Hotspot[];
  hlsUrl?: string;
}

const W = 2048;
const H = 1024;
const HORIZON = 560;

const D2R = Math.PI / 180;
const RAND = (seed: number) => {
  let s = seed;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
};

function sky(ctx: CanvasRenderingContext2D, top: string, mid: string, bot: string) {
  const g = ctx.createLinearGradient(0, 0, 0, HORIZON);
  g.addColorStop(0, top);
  g.addColorStop(0.55, mid);
  g.addColorStop(1, bot);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, HORIZON);
}

function sun(ctx: CanvasRenderingContext2D, x: number, y: number, r: number) {
  const glow = ctx.createRadialGradient(x, y, 0, x, y, r * 5);
  glow.addColorStop(0, "rgba(255,244,214,0.95)");
  glow.addColorStop(0.25, "rgba(255,228,160,0.5)");
  glow.addColorStop(1, "rgba(255,228,160,0)");
  ctx.fillStyle = glow;
  ctx.beginPath();
  ctx.arc(x, y, r * 5, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#fff8e2";
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.fill();
}

function stars(ctx: CanvasRenderingContext2D, seed: number, count: number) {
  const r = RAND(seed);
  ctx.fillStyle = "rgba(255,255,255,0.85)";
  for (let i = 0; i < count; i++) {
    const x = r() * W;
    const y = r() * (HORIZON - 80);
    const s = 1 + r() * 1.6;
    ctx.globalAlpha = 0.3 + r() * 0.7;
    ctx.fillRect(x, y, s, s);
  }
  ctx.globalAlpha = 1;
}

function clouds(ctx: CanvasRenderingContext2D, seed: number, count: number, alpha = 0.9) {
  const r = RAND(seed);
  for (let i = 0; i < count; i++) {
    const cx = r() * W;
    const cy = 90 + r() * (HORIZON - 240);
    const cw = 120 + r() * 260;
    const ch = 18 + r() * 30;
    const g = ctx.createLinearGradient(0, cy - ch, 0, cy + ch);
    g.addColorStop(0, `rgba(255,255,255,${alpha})`);
    g.addColorStop(1, `rgba(255,255,255,0)`);
    ctx.fillStyle = g;
    for (let p = 0; p < 5; p++) {
      ctx.beginPath();
      ctx.ellipse(cx + (p - 2) * cw * 0.2, cy + Math.sin(p) * ch * 0.3, cw * 0.28, ch, 0, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

interface Building {
  x: number;
  w: number;
  h: number;
}

function skyline(
  ctx: CanvasRenderingContext2D,
  buildings: Building[],
  color: string,
  winColor: string,
  lit: number,
  seed: number,
) {
  const r = RAND(seed);
  for (const b of buildings) {
    ctx.fillStyle = color;
    ctx.fillRect(b.x, HORIZON - b.h, b.w, b.h + 4);
    ctx.fillStyle = winColor;
    const cols = Math.floor(b.w / 14);
    const rows = Math.floor(b.h / 20);
    for (let c = 0; c < cols; c++) {
      for (let row = 0; row < rows; row++) {
        if (r() < lit) {
          ctx.fillRect(b.x + 5 + c * 14, HORIZON - b.h + 6 + row * 20, 6, 9);
        }
      }
    }
  }
}

function drawTokyoTower(ctx: CanvasRenderingContext2D, cx: number, base: number, h: number) {
  const yTop = base - h;
  ctx.strokeStyle = "#ff5a3c";
  ctx.lineWidth = 2;
  const tiers = [
    { w1: 74, w2: 34, y1: base, y2: base - h * 0.55 },
    { w1: 34, w2: 16, y1: base - h * 0.55, y2: base - h * 0.85 },
  ];
  for (const t of tiers) {
    ctx.beginPath();
    ctx.moveTo(cx - t.w1, t.y1);
    ctx.lineTo(cx - t.w2, t.y2);
    ctx.lineTo(cx + t.w2, t.y2);
    ctx.lineTo(cx + t.w1, t.y1);
    ctx.closePath();
    ctx.stroke();
    ctx.strokeRect(cx - t.w1 + 4, t.y1 - 3, t.w1 * 2 - 8, 3);
  }
  ctx.beginPath();
  ctx.moveTo(cx, yTop);
  ctx.lineTo(cx - 3, yTop + h * 0.18);
  ctx.lineTo(cx + 3, yTop + h * 0.18);
  ctx.closePath();
  ctx.fillStyle = "#ff5a3c";
  ctx.fill();
  ctx.strokeRect(cx - 34, base - h * 0.55, 68, 4);
  ctx.strokeRect(cx - 16, base - h * 0.85, 32, 4);
}

function drawSkytree(ctx: CanvasRenderingContext2D, cx: number, base: number, h: number) {
  const yTop = base - h;
  const grad = ctx.createLinearGradient(cx - 30, 0, cx + 30, 0);
  grad.addColorStop(0, "#9db4c8");
  grad.addColorStop(0.5, "#eef4fa");
  grad.addColorStop(1, "#9db4c8");
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.moveTo(cx - 30, base);
  ctx.lineTo(cx - 12, base - h * 0.62);
  ctx.lineTo(cx + 12, base - h * 0.62);
  ctx.lineTo(cx + 30, base);
  ctx.closePath();
  ctx.fill();
  ctx.fillRect(cx - 12, base - h * 0.62, 24, 6);
  ctx.fillStyle = "#dce9f2";
  ctx.fillRect(cx - 3, base - h * 0.62, 6, h * 0.2);
  ctx.strokeStyle = "#9db4c8";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(cx, yTop + h * 0.2);
  ctx.lineTo(cx, yTop + 6);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(cx, yTop, 7, 0, Math.PI * 2);
  ctx.fillStyle = "#cfe3f0";
  ctx.fill();
}

function drawFuji(ctx: CanvasRenderingContext2D, cx: number, base: number, h: number) {
  const g = ctx.createLinearGradient(0, base - h, 0, base);
  g.addColorStop(0, "#3b4a63");
  g.addColorStop(1, "#20293a");
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.moveTo(cx - 240, base);
  ctx.quadraticCurveTo(cx - 40, base - h * 0.95, cx, base - h);
  ctx.quadraticCurveTo(cx + 40, base - h * 0.95, cx + 240, base);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#eef4fb";
  ctx.beginPath();
  ctx.moveTo(cx, base - h);
  ctx.lineTo(cx - 34, base - h * 0.82);
  ctx.lineTo(cx + 30, base - h * 0.84);
  ctx.closePath();
  ctx.fill();
}

function drawEiffel(ctx: CanvasRenderingContext2D, cx: number, base: number, h: number) {
  ctx.fillStyle = "#8a6a4f";
  ctx.beginPath();
  ctx.moveTo(cx - 70, base);
  ctx.lineTo(cx - 26, base - h * 0.6);
  ctx.lineTo(cx + 26, base - h * 0.6);
  ctx.lineTo(cx + 70, base);
  ctx.closePath();
  ctx.fill();
  ctx.fillRect(cx - 32, base - h * 0.6, 64, 8);
  ctx.beginPath();
  ctx.moveTo(cx - 26, base - h * 0.6);
  ctx.lineTo(cx - 8, base - h * 0.88);
  ctx.lineTo(cx + 8, base - h * 0.88);
  ctx.lineTo(cx + 26, base - h * 0.6);
  ctx.closePath();
  ctx.fill();
  ctx.fillRect(cx - 2, base - h * 0.88, 4, h * 0.06);
  ctx.strokeStyle = "#8a6a4f";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(cx - 40, base - h * 0.72);
  ctx.lineTo(cx + 40, base - h * 0.72);
  ctx.moveTo(cx - 16, base - h * 0.82);
  ctx.lineTo(cx + 16, base - h * 0.82);
  ctx.stroke();
}

function drawArc(ctx: CanvasRenderingContext2D, cx: number, base: number, h: number) {
  ctx.fillStyle = "#c8b99b";
  ctx.fillRect(cx - 48, base - h, 96, h + 4);
  ctx.fillStyle = "#efe6d2";
  ctx.fillRect(cx - 38, base - h * 0.86, 76, 4);
  ctx.fillRect(cx - 38, base - h * 0.18, 76, h * 0.14);
  ctx.fillStyle = "#e8ddc8";
  ctx.fillRect(cx - 16, base - h * 0.62, 32, h * 0.44);
  ctx.fillStyle = "#6b5b41";
  ctx.fillRect(cx - 10, base - h * 0.56, 20, h * 0.38);
}

function ground(ctx: CanvasRenderingContext2D, color: string, lineAlpha: number) {
  ctx.fillStyle = color;
  ctx.fillRect(0, HORIZON, W, H - HORIZON);
  ctx.strokeStyle = `rgba(255,255,255,${lineAlpha})`;
  ctx.lineWidth = 1;
  for (let i = 1; i <= 8; i++) {
    const y = HORIZON + Math.pow(i / 8, 2) * (H - HORIZON);
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(W, y);
    ctx.stroke();
  }
  for (let i = -14; i <= 14; i++) {
    ctx.beginPath();
    ctx.moveTo(W / 2, HORIZON);
    ctx.lineTo(W / 2 + i * 90, H);
    ctx.stroke();
  }
  const g = ctx.createLinearGradient(0, HORIZON, 0, H);
  g.addColorStop(0, `rgba(255,255,255,${lineAlpha * 1.6})`);
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.moveTo(W / 2 - 46, HORIZON);
  ctx.lineTo(W / 2 + 46, HORIZON);
  ctx.lineTo(W / 2 + 210, H);
  ctx.lineTo(W / 2 - 210, H);
  ctx.closePath();
  ctx.fill();
}

function drawTokyoNight(): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = W;
  c.height = H;
  const ctx = c.getContext("2d")!;
  sky(ctx, "#0a1230", "#16224a", "#2a3f72");
  stars(ctx, 7, 220);
  const moon = ctx.createRadialGradient(1640, 130, 0, 1640, 130, 60);
  moon.addColorStop(0, "rgba(235,240,255,1)");
  moon.addColorStop(0.4, "rgba(200,215,245,0.9)");
  moon.addColorStop(1, "rgba(200,215,245,0)");
  ctx.fillStyle = moon;
  ctx.beginPath();
  ctx.arc(1640, 130, 60, 0, Math.PI * 2);
  ctx.fill();
  clouds(ctx, 3, 8, 0.12);
  drawFuji(ctx, 114, HORIZON + 2, 210);
  drawFuji(ctx, 1870, HORIZON + 2, 150);
  skyline(
    ctx,
    Array.from({ length: 34 }, (_, i) => ({
      x: Math.floor((i * 63) % W),
      w: 42 + (i % 3) * 14,
      h: 70 + (i * 37) % 150,
    })),
    "#0d1526",
    "rgba(255,214,120,1)",
    0.55,
    11,
  );
  drawSkytree(ctx, 1960, HORIZON + 2, 380);
  drawTokyoTower(ctx, 1137, HORIZON + 2, 300);
  ground(ctx, "#0a0f1c", 0.1);
  return c;
}

function drawParisDay(): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = W;
  c.height = H;
  const ctx = c.getContext("2d")!;
  sky(ctx, "#6db3f2", "#bcdcf5", "#f3e6cf");
  sun(ctx, 520, 150, 46);
  clouds(ctx, 21, 10, 0.9);
  skyline(
    ctx,
    Array.from({ length: 40 }, (_, i) => ({
      x: Math.floor((i * 52) % W),
      w: 56 + (i % 4) * 10,
      h: 46 + (i * 29) % 92,
    })),
    "#d8cfc0",
    "rgba(120,130,140,0.6)",
    0.12,
    5,
  );
  drawEiffel(ctx, 1024, HORIZON + 2, 380);
  drawArc(ctx, 700, HORIZON + 2, 130);
  drawArc(ctx, 1380, HORIZON + 2, 110);
  ground(ctx, "#7c8f6f", 0.16);
  ctx.fillStyle = "#58785a";
  ctx.fillRect(0, HORIZON + 2, W, 4);
  return c;
}

export const TOURS: TourDef[] = [
  {
    id: "tour-tokyo",
    name: "Tokyo — Shibuya Crossing",
    mode: "live",
    regionKey: "ap-northeast-1",
    lat: 35.6586,
    lng: 139.7454,
    hotspots: [
      { id: "tokyo-tower", yawDeg: 20, pitchDeg: -4, label: "Tokyo Tower", desc: "A 333 m broadcasting tower, symbol of post-war Japan.", ask: "Tell me about Tokyo Tower and what it looks like right now." },
      { id: "shibuya", yawDeg: -60, pitchDeg: -6, label: "Shibuya Crossing", desc: "The world-famous scramble crossing, busy even at night.", ask: "How many people cross Shibuya Crossing every day?" },
      { id: "fuji", yawDeg: 110, pitchDeg: -12, label: "Mt. Fuji", desc: "Visible on clear nights from central Tokyo.", ask: "When is the best time to see Mt. Fuji from Tokyo?" },
      { id: "skytree", yawDeg: 165, pitchDeg: -8, label: "Tokyo Skytree", desc: "A 634 m tower, the tallest structure in Japan.", ask: "What is the Tokyo Skytree and how tall is it?" },
    ],
    hlsUrl: "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
  },
  {
    id: "tour-paris",
    name: "Paris — Eiffel Panorama",
    mode: "vod",
    regionKey: "eu-west-3",
    lat: 48.8566,
    lng: 2.3522,
    hotspots: [
      { id: "eiffel", yawDeg: 0, pitchDeg: -6, label: "Eiffel Tower", desc: "Iron lattice tower on the Champ de Mars, built for the 1889 Exposition.", ask: "Tell me the story of the Eiffel Tower." },
      { id: "arc", yawDeg: -42, pitchDeg: -8, label: "Arc de Triomphe", desc: "Honors those who fought for France; sits on the Champs-Élysées.", ask: "What does the Arc de Triomphe commemorate?" },
      { id: "seine", yawDeg: 95, pitchDeg: 4, label: "River Seine", desc: "Flows through the heart of Paris past Notre-Dame.", ask: "Why is the Seine so important to Paris?" },
    ],
    hlsUrl: "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
  },
];

export function textureFor(tourId: string): HTMLCanvasElement {
  if (tourId === "tour-tokyo") return drawTokyoNight();
  return drawParisDay();
}

export function tourById(id: string): TourDef {
  return TOURS.find((t) => t.id === id) ?? TOURS[0];
}

export class PanoramaScene {
  private scene = new THREE.Scene();
  private camera = new THREE.PerspectiveCamera(75, innerWidth / innerHeight, 0.1, 1000);
  private renderer: THREE.WebGLRenderer;
  private sphere = new THREE.Mesh(
    new THREE.SphereGeometry(500, 64, 64),
    new THREE.MeshBasicMaterial({ side: THREE.BackSide }),
  );
  private yaw = 0;
  private pitch = 0;
  private autoYaw = 0;
  private lastInput = performance.now();
  private raf = 0;
  private hls: Hls | null = null;
  private video: HTMLVideoElement | null = null;

  constructor(container: HTMLElement) {
    this.scene.add(this.sphere);
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(innerWidth, innerHeight);
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    container.appendChild(this.renderer.domElement);
  }

  private destroyHls() {
    if (this.hls) {
      this.hls.destroy();
      this.hls = null;
    }
    if (this.video) {
      this.video.pause();
      this.video.src = "";
      this.video.load();
      this.video = null;
    }
  }

  setTour(tourId: string) {
    this.destroyHls();
    const canvas = textureFor(tourId);
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    this.sphere.material.map = tex;
    this.sphere.material.needsUpdate = true;
  }

  setHlsVideo(hlsUrl: string) {
    this.destroyHls();
    const video = document.createElement("video");
    video.crossOrigin = "anonymous";
    video.loop = true;
    video.muted = true;
    video.playsInline = true;
    video.autoplay = true;
    this.video = video;

    if (Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        maxBufferLength: 10,
        maxMaxBufferLength: 30,
      });
      hls.loadSource(hlsUrl);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {});
      });
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          console.error("HLS fatal error:", data.type, data.details);
        }
      });
      this.hls = hls;
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = hlsUrl;
      video.addEventListener("loadedmetadata", () => {
        video.play().catch(() => {});
      });
    } else {
      console.warn("HLS not supported in this browser");
      return;
    }

    const tex = new THREE.VideoTexture(video);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.minFilter = THREE.LinearFilter;
    tex.magFilter = THREE.LinearFilter;
    this.sphere.material.map = tex;
    this.sphere.material.needsUpdate = true;
  }

  setVideo(src: string) {
    this.destroyHls();
    const video = document.createElement("video");
    video.src = src;
    video.crossOrigin = "anonymous";
    video.loop = true;
    video.muted = true;
    video.playsInline = true;
    video.autoplay = true;
    this.video = video;
    video.play().catch(() => {});
    const tex = new THREE.VideoTexture(video);
    tex.colorSpace = THREE.SRGBColorSpace;
    this.sphere.material.map = tex;
    this.sphere.material.needsUpdate = true;
  }

  get look() {
    return { yaw: this.yaw, pitch: this.pitch };
  }

  rotate(dx: number, dy: number) {
    this.yaw -= dx * 0.12;
    this.pitch = Math.max(-85, Math.min(85, this.pitch - dy * 0.12));
    this.lastInput = performance.now();
  }

  start() {
    const tick = (now: number) => {
      this.raf = requestAnimationFrame(tick);
      if (now - this.lastInput > 5000) {
        this.autoYaw += 0.01;
        this.yaw += this.autoYaw;
      } else {
        this.autoYaw = 0;
      }
      this.camera.rotation.set(this.pitch * D2R, this.yaw * D2R, 0, "YXZ");
      this.renderer.render(this.scene, this.camera);
    };
    tick(performance.now());
  }

  resize() {
    this.camera.aspect = innerWidth / innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(innerWidth, innerHeight);
  }

  setYaw(yaw: number) {
    this.yaw = yaw;
    this.lastInput = performance.now();
  }

  dispose() {
    cancelAnimationFrame(this.raf);
    this.destroyHls();
    this.renderer.dispose();
  }
}
