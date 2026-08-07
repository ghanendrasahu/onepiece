export type Source = "api" | "demo";

export interface Tour {
  id: string;
  title_en: string;
  mode: "live" | "vod";
  region_key: string;
}

export interface Stream {
  id: string;
  title: string;
  status: string;
  viewer_count: number;
}

export interface Language {
  code: string;
  label: string;
}

const BASE = {
  identity: "/api/identity/v1",
  catalog: "/api/catalog/v1",
  streaming: "/api/streaming/v1",
  guide: "/api/ai-guide/v1",
};

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

const DEMO_TOURS: Tour[] = [
  { id: "tour-tokyo", title_en: "Tokyo — Shibuya Crossing", mode: "live", region_key: "ap-northeast-1" },
  { id: "tour-paris", title_en: "Paris — Eiffel Panorama", mode: "vod", region_key: "eu-west-3" },
];

const DEMO_STREAMS: Stream[] = [
  { id: "stream-tokyo-1", title: "Shibuya Crossing — Live", status: "live", viewer_count: 1284 },
  { id: "stream-tokyo-2", title: "Asakusa Senso-ji", status: "live", viewer_count: 342 },
  { id: "stream-paris-1", title: "Champs-Élysées Walk", status: "paused", viewer_count: 0 },
];

const DEMO_LANGS: Language[] = [
  { code: "en", label: "English" },
  { code: "ja", label: "日本語" },
  { code: "fr", label: "Français" },
  { code: "es", label: "Español" },
  { code: "de", label: "Deutsch" },
  { code: "zh", label: "中文" },
];

const DEMO_ANSWERS: Record<string, string> = {
  "tour-tokyo": "That's Tokyo Tower — a 333 m lattice tower you're looking at right now. At night it glows orange, and from here you can also spot Mt. Fuji on clear evenings. (demo answer — connect to the ai_guide service for live grounding)",
  "tour-paris": "That's the Eiffel Tower, the iron lattice structure built for the 1889 World's Fair. You're viewing it from the Trocadéro side. (demo answer — connect to the ai_guide service for live grounding)",
};

export const api = {
  async ping(): Promise<boolean> {
    try {
      const r = await fetch("/api/identity/healthz");
      return r.ok;
    } catch {
      return false;
    }
  },

  async tours(): Promise<{ data: Tour[]; source: Source }> {
    try {
      const r = await req<{ items: Tour[] }>(`${BASE.catalog}/tours`);
      return { data: r.items, source: "api" };
    } catch {
      return { data: DEMO_TOURS, source: "demo" };
    }
  },

  async liveStreams(): Promise<{ data: Stream[]; source: Source }> {
    try {
      const data = await req<Stream[]>(`${BASE.streaming}/streams/live`);
      return { data, source: "api" };
    } catch {
      return { data: DEMO_STREAMS, source: "demo" };
    }
  },

  async languages(): Promise<{ data: Language[]; source: Source }> {
    try {
      const r = await req<{ languages: Language[] }>(`${BASE.guide}/languages`);
      return { data: r.languages, source: "api" };
    } catch {
      return { data: DEMO_LANGS, source: "demo" };
    }
  },

  async ask(tourId: string, t: number, text: string, lang: string): Promise<{ data: string; source: Source }> {
    try {
      const r = await req<{ answer: string }>(`${BASE.guide}/guide/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tour_id: tourId, t, text, lang }),
      });
      return { data: r.answer, source: "api" };
    } catch {
      return { data: DEMO_ANSWERS[tourId] ?? DEMO_ANSWERS["tour-tokyo"], source: "demo" };
    }
  },

  async register(): Promise<{ data: { email: string }; source: Source }> {
    try {
      const r = await req<{ email: string }>(`${BASE.identity}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: "guest@worldviewvr.com", password: "demo-password-1", display_name: "Guest" }),
      });
      return { data: r, source: "api" };
    } catch {
      return { data: { email: "guest@worldviewvr.com" }, source: "demo" };
    }
  },
};
