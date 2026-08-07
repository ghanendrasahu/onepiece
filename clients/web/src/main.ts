import "./styles.css";
import { PanoramaScene, TOURS, tourById, type Hotspot } from "./scene";
import { api, type Source } from "./api";

const D2R = Math.PI / 180;

const app = document.getElementById("app")!;
const scene = new PanoramaScene(app);

const hud = document.createElement("div");
hud.id = "hud";
document.body.appendChild(hud);

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls = "", text = ""): HTMLElementTagNameMap[K] {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text) n.textContent = text;
  return n;
}

// ---------- Topbar ----------
const topbar = el("div", "panel", "");
topbar.id = "topbar";
const brand = el("div", "brand", "");
brand.innerHTML = `<span class="live-dot"></span> WorldView VR <small>live virtual travel</small>`;
const tourName = el("div", "", "");
tourName.id = "tourName";
const spacer = el("div", "spacer", "");
const sourcePill = el("span", "pill offline", "● offline · demo data");
sourcePill.id = "sourcePill";
const connectBtn = el("button", "ghost", "Connect");
connectBtn.id = "connectBtn";
topbar.append(brand, tourName, spacer, sourcePill, connectBtn);
hud.appendChild(topbar);

// ---------- Tour bar ----------
const tourBar = el("div", "panel", "");
tourBar.id = "tourBar";
TOURS.forEach((t) => {
  const chip = el("button", "chip", "");
  const tag = t.mode === "live" ? el("span", "tag", "LIVE") : el("span", "", "VOD");
  tag.className = t.mode === "live" ? "tag" : "tag vod";
  chip.append(tag, document.createTextNode(t.name));
  chip.dataset.tour = t.id;
  tourBar.appendChild(chip);
});
hud.appendChild(tourBar);

// ---------- Hotspots layer ----------
const hotspotsLayer = el("div", "", "");
hotspotsLayer.id = "hotspots";
hud.appendChild(hotspotsLayer);

// ---------- Streams panel ----------
const streamsPanel = el("div", "panel", "");
streamsPanel.id = "streamsPanel";
const streamsHead = el("div", "chat-head", "");
streamsHead.appendChild(el("h3", "", "● Live Now"));
const refreshBtn = el("button", "ghost", "↻");
streamsHead.appendChild(refreshBtn);
const streamList = el("div", "", "");
streamList.id = "streamList";
streamsPanel.append(streamsHead, streamList);
hud.appendChild(streamsPanel);

// ---------- Chat (AI World Guide) ----------
const chatPanel = el("div", "panel", "");
chatPanel.id = "chatPanel";
const chatHead = el("div", "chat-head", "");
chatHead.appendChild(el("h3", "", "AI World Guide"));
const signToggle = el("button", "sign-toggle", "🖐 Sign");
signToggle.id = "signToggle";
chatHead.appendChild(signToggle);
const chatMsgs = el("div", "", "");
chatMsgs.id = "chatMsgs";
const chatInputRow = el("div", "", "");
chatInputRow.id = "chatInputRow";
const chatInput = el("input", "", "");
chatInput.id = "chatInput";
chatInput.placeholder = "Ask about what you see…";
const langSel = el("select", "", "");
langSel.id = "langSel";
const sendBtn = el("button", "", "Ask");
sendBtn.id = "sendBtn";
chatInputRow.append(chatInput, langSel, sendBtn);
chatPanel.append(chatHead, chatMsgs, chatInputRow);
hud.appendChild(chatPanel);

// ---------- Sign overlay ----------
const signOverlay = el("div", "", "");
signOverlay.id = "signOverlay";
signOverlay.innerHTML = `<span class="hand">👋</span><span class="st">Sign-language interpretation<br/>active (demo)</span>`;
hud.appendChild(signOverlay);

// ---------- Stats / hint / toast / info card ----------
const stats = el("div", "", "");
stats.id = "stats";
const hint = el("div", "", "drag to look around · click hotspots · ask the AI guide");
hint.id = "hint";
const toastEl = el("div", "", "");
toastEl.id = "toast";
const infoCard = el("div", "", "");
infoCard.id = "infoCard";
hud.append(stats, hint, toastEl, infoCard);

// ---------- State ----------
let currentTour = tourById("tour-tokyo");
let connected = false;
let signOn = false;
let toastTimer = 0;

function toast(msg: string) {
  toastEl.textContent = msg;
  toastEl.style.display = "block";
  clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => (toastEl.style.display = "none"), 3200);
}

// ---------- Projection ----------
const FOV_V = 75 * D2R;
const tanV = Math.tan(FOV_V / 2);

function project(h: Hotspot, camYaw: number, camPitch: number) {
  let dy = ((h.yawDeg - camYaw + 180) % 360 + 360) % 360 - 180;
  const dp = h.pitchDeg - camPitch;
  const aspect = innerWidth / innerHeight;
  const tanH = Math.tan(FOV_V / 2) * aspect;
  const x = innerWidth / 2 + (Math.tan(dy * D2R) / tanH) * (innerWidth / 2);
  const y = innerHeight / 2 - (Math.tan(dp * D2R) / tanV) * (innerHeight / 2);
  return { x, y, visible: Math.abs(dy) < 95 };
}

const markers = new Map<string, HTMLElement>();

function renderHotspots(camYaw: number, camPitch: number) {
  for (const h of currentTour.hotspots) {
    let m = markers.get(h.id);
    if (!m) {
      m = el("div", "hotspot", "");
      m.innerHTML = `<span class="pulse-ring"></span><span class="hotspot-label"></span>`;
      m.addEventListener("click", (e) => openInfo(h, e.clientX, e.clientY));
      hotspotsLayer.appendChild(m);
      markers.set(h.id, m);
    }
    const p = project(h, camYaw, camPitch);
    const label = m.querySelector(".hotspot-label")!;
    label.textContent = h.label;
    m.style.display = p.visible ? "flex" : "none";
    m.style.left = `${p.x}px`;
    m.style.top = `${p.y}px`;
  }
}

function openInfo(h: Hotspot, x: number, y: number) {
  infoCard.innerHTML = "";
  infoCard.appendChild(el("h4", "", h.label));
  infoCard.appendChild(el("p", "", h.desc));
  const actions = el("div", "actions", "");
  const ask = el("button", "ghost", "Ask AI Guide");
  const close = el("button", "ghost", "Close");
  actions.append(ask, close);
  infoCard.appendChild(actions);
  infoCard.style.left = `${Math.max(12, Math.min(x + 16, innerWidth - 280))}px`;
  infoCard.style.top = `${Math.max(12, Math.min(y - 20, innerHeight - 180))}px`;
  infoCard.style.display = "block";
  ask.addEventListener("click", () => {
    infoCard.style.display = "none";
    askGuide(h.ask);
  });
  close.addEventListener("click", () => (infoCard.style.display = "none"));
}

// ---------- Chat ----------
function addMsg(role: "user" | "ai", text: string, src?: Source) {
  const m = el("div", `msg ${role}`, "");
  m.textContent = text;
  if (role === "ai" && src) {
    const tag = el("span", "src", src === "api" ? "live · ai_guide" : "demo data");
    m.appendChild(tag);
  }
  chatMsgs.appendChild(m);
  chatMsgs.scrollTop = chatMsgs.scrollHeight;
}

async function askGuide(text: string) {
  const t = Math.round((scene.look.yaw + 360) % 360) * 2;
  addMsg("user", text);
  const think = el("div", "msg ai", "…");
  chatMsgs.appendChild(think);
  chatMsgs.scrollTop = chatMsgs.scrollHeight;
  const { data, source } = await api.ask(currentTour.id, t, text, langSel.value);
  think.remove();
  addMsg("ai", data, source);
}

// ---------- Streams ----------
async function refreshStreams() {
  const { data, source } = await api.liveStreams();
  if (source === "api") setConnected(true);
  streamList.innerHTML = "";
  if (data.length === 0) streamList.appendChild(el("div", "stream-title", "No live streams."));
  for (const s of data) {
    const row = el("div", "stream-row", "");
    const badge = el("span", `stream-badge ${s.status}`, s.status.toUpperCase());
    const body = el("div", "", "");
    const title = el("div", "stream-title", s.title);
    const meta = el("div", "stream-meta", s.status === "live" ? `${s.viewer_count} viewers` : "offline");
    body.append(title, meta);
    row.append(badge, body);
    row.addEventListener("click", () => {
      toast(`Opening stream: ${s.title}`);
      if (s.title.includes("Shibuya") || s.title.includes("Tokyo")) switchTour("tour-tokyo");
      else if (s.title.includes("Paris") || s.title.includes("Champs")) switchTour("tour-paris");
    });
    streamList.appendChild(row);
  }
}

// ---------- Tours ----------
function switchTour(id: string) {
  currentTour = tourById(id);
  scene.setTour(id);
  tourName.textContent = currentTour.name;
  document.querySelectorAll("#tourBar .chip").forEach((c) => c.classList.toggle("active", (c as HTMLElement).dataset.tour === id));
  markers.forEach((m) => m.remove());
  markers.clear();
  infoCard.style.display = "none";
  toast(`${currentTour.mode === "live" ? "Live" : "Prerecorded"} · ${currentTour.name}`);
}

// ---------- Connect ----------
function setConnected(online: boolean) {
  connected = online;
  sourcePill.textContent = online ? "● connected · live API" : "● offline · demo data";
  sourcePill.className = `pill ${online ? "online" : "offline"}`;
}

async function connect() {
  connectBtn.textContent = "Connecting…";
  connectBtn.disabled = true;
  const ok = await api.ping();
  if (ok) {
    const { source } = await api.register();
    setConnected(source === "api");
  } else {
    setConnected(false);
  }
  await Promise.all([refreshStreams(), loadLanguages(), api.tours()]);
  toast(connected ? "Connected — live data" : "Backends offline — showing demo data");
  connectBtn.textContent = "Connect";
  connectBtn.disabled = false;
}

async function loadLanguages() {
  const { data } = await api.languages();
  langSel.innerHTML = "";
  for (const l of data) langSel.appendChild(new Option(l.label, l.code));
}

// ---------- Input wiring ----------
sendBtn.addEventListener("click", () => {
  const v = chatInput.value.trim();
  if (!v) return;
  chatInput.value = "";
  void askGuide(v);
});
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendBtn.click();
});
signToggle.addEventListener("click", () => {
  signOn = !signOn;
  signToggle.classList.toggle("on", signOn);
  signOverlay.style.display = signOn ? "flex" : "none";
  if (signOn) setTimeout(() => signOverlay.style.display = "none", 4000);
});
connectBtn.addEventListener("click", () => void connect());
refreshBtn.addEventListener("click", () => void refreshStreams());
document.querySelectorAll("#tourBar .chip").forEach((c) =>
  c.addEventListener("click", () => switchTour((c as HTMLElement).dataset.tour!)),
);

// ---------- Pointer look ----------
let dragging = false;
let lastX = 0;
let lastY = 0;
scene.start();
app.addEventListener("pointerdown", (e) => {
  dragging = true;
  lastX = e.clientX;
  lastY = e.clientY;
});
addEventListener("pointerup", () => (dragging = false));
addEventListener("pointermove", (e) => {
  if (!dragging) return;
  scene.rotate(e.clientX - lastX, e.clientY - lastY);
  lastX = e.clientX;
  lastY = e.clientY;
});
app.addEventListener("touchstart", (e) => {
  dragging = true;
  lastX = e.touches[0].clientX;
  lastY = e.touches[0].clientY;
});
app.addEventListener("touchmove", (e) => {
  if (!dragging) return;
  const t = e.touches[0];
  scene.rotate(t.clientX - lastX, t.clientY - lastY);
  lastX = t.clientX;
  lastY = t.clientY;
});
app.addEventListener("touchend", () => (dragging = false));

addEventListener("resize", () => scene.resize());

// ---------- Frame loop: hotspots + stats ----------
function frame() {
  requestAnimationFrame(frame);
  const { yaw, pitch } = scene.look;
  renderHotspots(yaw, pitch);
  stats.textContent = `yaw ${yaw.toFixed(0)}° · pitch ${pitch.toFixed(0)}°`;
}
requestAnimationFrame(frame);

// ---------- Video override via ?src= ----------
const srcParam = new URLSearchParams(location.search).get("src");
if (srcParam) scene.setVideo(srcParam);

// ---------- Init ----------
const initTour = new URLSearchParams(location.search).get("tour") ?? "tour-tokyo";
switchTour(initTour);
void loadLanguages();
void connect();
setTimeout(() => {
  hint.style.opacity = "0";
  setTimeout(() => (hint.style.display = "none"), 1100);
}, 9000);

// Expose for console/testing.
declare global {
  interface Window {
    worldViewPlayer?: {
      setYaw(y: number): void;
      setTour(id: string): void;
      ask(q: string): void;
    };
  }
}
window.worldViewPlayer = {
  setYaw: (y) => scene.setYaw(y),
  setTour: (id) => switchTour(id),
  ask: (q) => void askGuide(q),
};

addMsg("ai", "Welcome to WorldView VR. Look around, tap the glowing hotspots, and ask me anything about what you see.", "demo");
