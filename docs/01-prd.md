# 01 — Product Requirements Document (PRD)

**WorldView VR** | Version 1.0 | Status: Draft | Owner: Product

---

## 1. Vision

> *"Experience the world as if you are physically there — from your living room, your wheelchair, your hospital bed, or your lunch break."*

WorldView VR is an immersive virtual travel platform combining **live 360° streaming from real places**, **AI-guided virtual tourism**, **verified human guides**, and **social presence** — delivered across VR headsets, mobile, desktop, and web.

The product goal is the "**Google Maps + YouTube Live + Meta Quest + Apple Vision Pro**" of world exploration: the place to *be* anywhere, anytime.

## 2. Problem & Opportunity

### 2.1 The Problem
- **~8 billion people**, but only ~1.4 billion international tourist arrivals *per year* (pre-pandemic, UNWTO).
- Travel is blocked by: cost, disability, age, health, safety, time, visas, and environmental concern (aviation ≈ 2.5% of global CO₂).
- Existing "virtual travel" (Google Street View, YouTube 360°, static VR tourism) is **passive, flat, stale, or lonely** — no liveness, no guidance, no social interaction, no agency.

### 2.2 The Opportunity
- VR/MR headset shipments projected to reach tens of millions of units/year by 2028–2030.
- Global virtual tourism + online events market in the **$10–30B** range long-term (see [Business Plan §3](12-business-plan.md)).
- No dominant platform currently owns *live* guided virtual travel. First-mover + network effects (creators ↔ travelers ↔ guides) create a defensible moat.

## 3. Product Strategy: What We Build First

**Thrust priority (MVP order):**

1. **Live 360° streaming** (creator platform) — this is the differentiator.
2. **AI World Guide** (conversational, multilingual) on-demand tourism over archived/curated 360° content — fast to ship, high perceived value.
3. **Virtual Tourism catalog** (on-demand VOD 360°) with AI narration.
4. **Social VR presence** — comes after the above have critical mass.

We deliberately **delay** speculative features (full digital twins, dynamic weather simulation, real-time photogrammetry, haptics) to later phases; they are not on the MVP critical path.

## 4. Customer Personas

| Persona | Description | Core need | Willingness to pay |
|---|---|---|---|
| **P1 Senior Explorer** (age 65+) | Limited mobility, loves travel documentaries | Safe, comfortable immersion with simple controls, narration, large text | High; premium subscription |
| **P2 Disabled Traveler** | Wheelchair user or sight/hearing-impaired | Accessible controls, captions, audio description, comfort modes | High; loyal |
| **P3 Budget Backpacker** (18–30) | Wants to "try before booking" trips | Affordable single-tour passes, social sharing | Medium; pay-per-tour |
| **P4 Remote Worker / Digital Nomad** | Curious, time-poor | Quick curated "10-minute world walk" sessions during lunch | Medium; monthly |
| **P5 VR Enthusiast / Gamer** | Owns Quest/Pico/PSVR | High-immersion, multiplayer, leaderboards, avatar presence | High; premium + events |
| **P6 Educator / Student** | Teachers, university | Curriculum-aligned tours, group mode, lesson plans | Institutional pricing |
| **P7 Local Creator / Guide** | Travelers, photographers, tour operators | Monetization, viewer reach, tooling | Revenue share (20–50%) |
| **P8 Travel Agency / DMO** | National/regional tourism boards | White-label promotion, virtual previews, analytics | Enterprise contracts |

## 5. Features (Prioritized)

Priority: **P0** = MVP, **P1** = Beta/V1, **P2** = V2, **P3** = Future/Research.

### 5.1 Live World Exploration — **P0**
- Join live streams (browse by map, category, trending).
- 360°/180° video playback with pan/tilt/look-around; smartphone = touch-drag; VR = head rotation.
- Spatial audio (binaural / Ambisonics).
- Ultra-low latency targets (see SRS §3.2).
- Stream quality ladder: 720p → 4K (8K/16K progressive enhancement, **T2**).
- Chat + reactions alongside stream.
- **P1:** multi-camera (follow guide vs. drone), live captions, donation/tip UI.

### 5.2 Virtual Tourism (On-Demand) — **P0/P1**
- Curated catalog: landmarks, cities, nature, culture.
- AI tour guide narration (multilingual).
- Interactive hotspots (objects/timeline/photos).
- Pause, bookmark, capture VR photo, create memory clips.
- **P1:** historical reconstruction overlays, seasonal archives.

### 5.3 Live Human Guides / Creator Platform — **P0**
- Creator onboarding + verification (ID + geo-check + license check where needed).
- Stream from 360° camera, smartphone, body cam, drone (legality flagged per jurisdiction).
- Viewer → guide interaction: request destinations, Q&A (voice-to-text), tips, private tours.
- Monetization: tips, pay-per-tour, subscriptions, rev-share.

### 5.4 AI World Guide — **P0 (V1) / P1 (multilingual, voice)**
- Ask: "What building is this?", "What's popular to eat here?", "Translate this sign", "Tell me the history".
- Grounded on geo-tagged knowledge base (RAG), spatial awareness (POI at current look-direction).
- Multilingual input/output (initially 15 languages, 40+ later).
- Identify plants, animals, landmarks from video frames (vision model).

### 5.5 Interactive Exploration — **P0**
- Look around (parallax/tile streaming).
- Teleport & smooth movement in captured 3D spaces (**P2**, 6-DoF).
- Bookmark, memories, VR photo capture, share.

### 5.6 Time Travel Mode — **P1/P2**
- Replay archives (Tokyo spring, Times Square NYE, festivals).
- **P2:** ancient city reconstructions (procedural + photogrammetry), "season dial".

### 5.7 Social VR — **P1/P2**
- Avatars, friends, watch-together sync, voice chat, guided group tours, meet new people (opt-in).
- **P2:** shared presence in 6-DoF spaces.

### 5.8 Accessibility — **P0 (baseline)**
- Captions (auto, live), audio description, high-contrast UI, comfort modes (reduced motion, vignette, snap-turn), adaptive controls (single-switch, eye-gaze where available), screen-reader support on mobile/web.

### 5.9 Advanced / Future Features
| Feature | Horizon |
|---|---|
| AI environmental reconstruction (Gaussian Splatting) | P3 / T2 |
| Digital twins of cities | P3 / T2 |
| Dynamic weather + real-time lighting simulation | P3 / T2 |
| Haptics, eye tracking, hand tracking | P2 (gating on HW), P3 full |
| Voice navigation | P1 |
| AI itinerary generation & recommendations | P1 |
| Offline downloads (VOD catalog) | P1 |
| Mixed Reality mode (passthrough overlays) | P2 |
| 8K/16K streaming | P2 (8K), T2 (16K) |

## 6. User Journeys

### Journey A — First-timer joins a live stream (phone)
1. Install app → social sign-in (1 tap) → grant location (optional) → onboarding carousel.
2. Home shows "Live now" map + trending tiles → tap "Tokyo — Shibuya Crossing live".
3. Stream starts ≤ 2s; auto-switches to best quality for network; captions on by default in system language.
4. Look-around via drag; hears binaural street audio; asks AI guide "What's that red gate?" → answer card with hotspot.
5. Adds place to "Travel list", captures a VR photo, shares to socials.
6. Upsell: "Loved Tokyo? Unlock on-demand Tokyo tours + AI guide for $X/mo."

### Journey B — Creator goes live from a remote location
1. Creator dashboard → "Go Live" → device selector (phone/360 camera) → checks bandwidth & battery.
2. Legal + geo checklist auto-shown (drone permission, people-in-frame consent).
3. Stream key provisioned; quality auto-negotiated; status = LIVE; viewers join; live captions enabled.
4. During stream: viewer requests ("Take me to the temple"), tips flow, mod auto-filters hate speech.
5. Stream ends → auto-save VOD → auto-transcribe → suggest segments → monetize as on-demand tour.

### Journey C — VR group tour (Quest + friends)
1. Launch VR app → Meet friends in lobby → "Private guided tour of Machu Picchu".
2. Avatars around user; spatial voice; AI guide narrates; hotspots appear; group syncs 30fps state.
3. One user is "leader" (tour host); others follow avatar positions.
4. Shared capture → memory reel → share.

### Journey D — Educator uses classroom mode
1. Teacher creates class group → books virtual tour slot.
2. Students join via web/VR with restricted chat; teacher controls narration pace; quiz hotspots.
3. Post-tour: analytics (engagement per student), export worksheet.

## 7. Success Metrics

| Metric | MVP (6 mo) | V1 (18 mo) | V2 (36 mo) |
|---|---|---|---|
| Registered users | 250K | 3M | 10M MAU |
| Weekly active | 60K | 600K | 2.5M |
| Live streams/month | 800 | 8K | 40K |
| Avg watch time / active user | 12 min/day | 20 min/day | 28 min/day |
| Retention (D30) | 22% | 32% | 38% |
| Paying conversion | 3% | 6% | 8% |
| Creator payouts | — | $500K/mo | $8M/mo |
| NPS | 40 | 52 | 60 |
| 99.9% uptime | — | Yes | Yes |

**North-star metric:** *Meaningful exploration minutes per active user* (MAU × engaged session length), because it correlates with both retention and monetization.

## 8. Out of Scope (MVP)
- User-generated 3D world building / UGC metaverse worlds.
- Full city-scale digital twins.
- P2P avatar marketplace.
- Native ad network (only non-intrusive sponsorships).
- Physical VR arcade hardware program (pilot only).

## 9. Assumptions & Risks (Product)
- **Assumption:** creator supply can be seeded via partnerships with travel creators/influencers and tourism boards. Mitigation: guarantee minimum payout + equipment loaner program.
- **Assumption:** 360° live latency < 2s is achievable at 10M users with WebRTC mesh + CDN edge. Risk of cost blow-up → tiered quality for free tier (see [Low-Level Design](04-low-level-design.md)).
- **Assumption:** users accept phone/tablet/desktop as the primary surface (VR is a growth surface, not the gate). This broadens TAM immediately.
- **Regulatory risk:** privacy/consent for filming in public, drone laws, content moderation liability. See [Security](08-security-architecture.md) and [Risk Assessment](11-risk-assessment.md).

## 10. Versioning & Feature Revisions
- PRD is a living doc. Feature changes require Product + Engineering + Legal sign-off.
- Every "Today/Near/Future" label in the [SRS](02-srs.md) governs commit priority.
