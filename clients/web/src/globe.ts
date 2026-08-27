import Globe from "globe.gl";
import { TOURS, type TourDef } from "./scene";

export type GlobeSelectCallback = (tourId: string) => void;

const DARK_GLOBE_IMG = "https://unpkg.com/three-globe/example/img/earth-night.jpg";
const NIGHT_SKY_IMG = "https://unpkg.com/three-globe/example/img/night-sky.png";

interface GlobePoint {
  id: string;
  lat: number;
  lng: number;
  size: number;
  color: string;
  tour: TourDef;
}

let globeInstance: any = null;
let selectCallback: GlobeSelectCallback | null = null;

function tourToPoint(t: TourDef): GlobePoint {
  return {
    id: t.id,
    lat: t.lat,
    lng: t.lng,
    size: 0.6,
    color: t.mode === "live" ? "#ff3b30" : "#4cc9f0",
    tour: t,
  };
}

export function createGlobe(container: HTMLElement): void {
  if (globeInstance) destroyGlobe();

  const globe = (Globe as any)()(container)
    .globeImageUrl(DARK_GLOBE_IMG)
    .backgroundImageUrl(NIGHT_SKY_IMG)
    .pointsData(TOURS.map(tourToPoint))
    .pointLat("lat")
    .pointLng("lng")
    .pointAltitude(0.02)
    .pointRadius("size")
    .pointColor("color")
    .pointsMerge(false)
    .pointLabel((d: GlobePoint) => {
      const modeTag =
        d.tour.mode === "live"
          ? '<span style="background:#ff3b30;color:#fff;padding:2px 6px;border-radius:6px;font-size:10px;font-weight:700;margin-right:6px;">LIVE</span>'
          : '<span style="background:#4cc9f0;color:#000;padding:2px 6px;border-radius:6px;font-size:10px;font-weight:700;margin-right:6px;">VOD</span>';
      return `<div style="font-family:Inter,system-ui,sans-serif;padding:4px 2px;">
        ${modeTag}<b>${d.tour.name}</b><br/>
        <span style="color:#aaa;font-size:11px;">Click to enter tour</span>
      </div>`;
    })
    .onPointClick((d: GlobePoint) => {
      if (selectCallback) selectCallback(d.tour.id);
    });

  globeInstance = globe;
}

export function onGlobeSelect(cb: GlobeSelectCallback): void {
  selectCallback = cb;
}

export function focusTour(tourId: string, durationMs = 1200): void {
  if (!globeInstance) return;
  const tour = TOURS.find((t) => t.id === tourId);
  if (!tour) return;

  globeInstance.pointOfView(
    { lat: tour.lat, lng: tour.lng, altitude: 1.2 },
    durationMs,
  );
}

export function resizeGlobe(): void {
  if (!globeInstance) return;
  const el = globeInstance.domElement();
  if (el && el.parentElement) {
    const w = el.parentElement.clientWidth || window.innerWidth;
    const h = el.parentElement.clientHeight || window.innerHeight;
    globeInstance.width(w);
    globeInstance.height(h);
  }
}

export function destroyGlobe(): void {
  if (!globeInstance) return;
  const el = globeInstance.domElement();
  if (el && el.parentElement) el.parentElement.innerHTML = "";
  globeInstance = null;
  selectCallback = null;
}
