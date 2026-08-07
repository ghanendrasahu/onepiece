# 02 — Software Requirements Specification (SRS)

**WorldView VR** | Version 1.0 | Status: Draft | Owner: Engineering/Product

Legend for feasibility:
- **T0** = Today (ship with current tech)
- **T1** = Near-term (12–24 mo, proven tech)
- **T2** = Future (2–5 yrs, research/speculative)

---

## 1. Scope

This SRS specifies the functional and non-functional requirements for the WorldView VR platform: mobile/desktop/web/VR client applications, streaming infrastructure, AI services, creator platform, social layer, and supporting business systems.

## 2. Definitions
- **Stream** — a live or archived 360°/180°/flat video broadcast.
- **Tour** — a packaged, curated experience (live, on-demand, or AI-guided).
- **Creator/Guide** — a verified broadcaster or virtual-tour host.
- **Hotspot** — an interactive annotation anchored to a point in a scene/time.
- **AI World Guide** — the conversational/vision grounding service.
- **Presence** — social state (who is in the same virtual room/session).

---

## 3. Functional Requirements

### FR-1 Authentication & Identity
- FR-1.1 Sign-up/sign-in via email, Google, Apple, Meta, phone (OTP). (T0)
- FR-1.2 Profile: name, avatar, preferences, accessibility settings. (T0)
- FR-1.3 OAuth 2.1 + OpenID Connect; device/session management; MFA optional→default for creators/payment. (T0)
- FR-1.4 GDPR/CCPA data export & deletion via API. (T0)
- FR-1.5 Parental/guardian accounts and content restrictions for minors. (T1)

### FR-2 Live Streaming (Creator → Platform → Viewer)
- FR-2.1 Ingest from: 360° camera, smartphone, body cam, drone (legality-gated), desktop capture. (T0)
- FR-2.2 Auto bitrate ladder: 720p/1080p/1440p/4K; ABR (adaptive bitrate) per viewer. (T0)
- FR-2.3 End-to-end live latency: <2 s typical, ≤5 s p95 (see NFR-LAT). (T0)
- FR-2.4 Spatial audio: Ambisonics (first-order) for 360°; binaural for headphone VR. (T0)
- FR-2.5 Live captions in viewer's language (ASR → translate → caption render). (T0/T1)
- FR-2.6 Stream lifecycle: pre-roll title/thumbnail, LIVE, ENDED, ARCHIVED. (T0)
- FR-2.7 Recording → VOD archive with auto-split segments (1s), auto-transcribe, auto-thumbnail. (T0/T1)
- FR-2.8 DVR: pause/replay live within last 30 min. (T1)
- FR-2.9 Low-latency fallback: LL-HLS for web/desktop; WebRTC for VR/mobile interactive. (T0)
- FR-2.10 8K streaming (T1), 16K (T2, research).

### FR-3 Virtual Tourism / On-Demand
- FR-3.1 Catalog browse: map, category, region, featured, search. (T0)
- FR-3.2 VOD playback of archived 360° with ABR + spatial audio. (T0)
- FR-3.3 AI tour guide narration (TTS, multilingual) synchronized to timeline. (T0/T1)
- FR-3.4 Interactive hotspots: POI info, photos, links, quizzes. (T0)
- FR-3.5 Bookmark places, create travel lists. (T0)
- FR-3.6 Capture "VR photo" (still from viewport) & "memory clips" (30s). (T0)
- FR-3.7 Offline downloads for premium VOD tours. (T1)
- FR-3.8 Season/weather dial and historical reconstruction overlays. (T2)

### FR-4 AI World Guide
- FR-4.1 Text + voice (ASR) Q&A grounded on scene context (geo, POI, look direction, transcript). (T0/T1)
- FR-4.2 Multimodal: identify landmarks/plants/animals from current video frame. (T1)
- FR-4.3 Translate signage/labels from video frames (OCR → translate → overlay). (T1)
- FR-4.4 Recommend nearby attractions, food, itineraries (personalized). (T1)
- FR-4.5 Multilingual: 15 launch languages, 40+ roadmap. (T0/T1)
- FR-4.6 Answers must cite sources; uncertainty stated; hallucination guardrails. (T0)
- FR-4.7 AI itinerary generation from preferences + saved places. (T1)

### FR-5 Creator Platform
- FR-5.1 Onboarding: identity verification (ID + liveness), geo check, consent, equipment detection. (T0)
- FR-5.2 Legal checker: drone/permits/people-in-frame consent per jurisdiction. (T0/T1)
- FR-5.3 Go-live wizard: quality test, bandwidth estimate, battery, privacy reminders. (T0)
- FR-5.4 Live management: viewers, revenue, chat/mod tools, spotlight viewer request. (T0)
- FR-5.5 Monetization: tips, pay-per-tour, subscription tier, private tour booking. (T0/T1)
- FR-5.6 Payouts (Stripe Connect / Wise), tax forms, creator analytics. (T0/T1)
- FR-5.7 Equipment loaner / rental program integration. (T1)

### FR-6 Social VR
- FR-6.1 Avatar creation (cross-platform). (T0)
- FR-6.2 Friends, invites, presence, "watch together" sync. (T0/T1)
- FR-6.3 Voice chat (spatial) with echo cancellation. (T1)
- FR-6.4 Guided group tours with a leader. (T1)
- FR-6.5 Discovery of public rooms/events (opt-in), safety tools (block/mute/report/exit). (T1)

### FR-7 Accessibility
- FR-7.1 Auto captions (live + VOD), user-adjustable size/contrast. (T0)
- FR-7.2 Audio description for key scenes (AI-generated). (T1)
- FR-7.3 Comfort modes: snap-turn, reduced motion, vignette, seated height. (T0)
- FR-7.4 Adaptive input: single-switch, head/gaze (where HW), remappable controls. (T0/T1)
- FR-7.5 Screen-reader support on mobile/web; WCAG 2.2 AA target. (T0)

### FR-8 Payments, Billing, Compliance
- FR-8.1 Subscriptions (App Store/Play/browser), pay-per-tour, tips, private tour booking. (T0)
- FR-8.2 Refunds, invoices, tax/VAT handling, chargeback management. (T0)
- FR-8.3 Fraud detection on payments and creator payouts. (T1)

### FR-9 Moderation & Safety
- FR-9.1 Live chat moderation (pre-trained classifier + real-time rules + human review queue). (T0)
- FR-9.2 Stream pre-check and in-stream flags (adult/unsafe content). (T0)
- FR-9.3 User & stream reporting flow with SLAs. (T0)
- FR-9.4 Age verification for adult-adjacent content (if any). (T1)

### FR-10 Admin & Enterprise
- FR-10.1 Admin console: users, creators, streams, payouts, moderation. (T0)
- FR-10.2 Enterprise: white-label portal, school/group management, virtual events, tourism-board dashboards. (T1)

---

## 4. Non-Functional Requirements

### NFR-LAT Latency
| Activity | Target (T0) | Target (T1) |
|---|---|---|
| Stream start-to-first-frame (heat) | ≤ 2 s | ≤ 1.2 s |
| Live glass-to-glass latency | < 2 s typical / 5 s p95 | < 800 ms p95 |
| API P95 | < 300 ms | < 150 ms |
| AI guide answer (text) | < 2.5 s | < 1.5 s |
| Hotspot/anchor query | < 400 ms | < 200 ms |
| Presence/state sync | < 500 ms | < 200 ms |

### NFR-AVA Availability & Durability
- Service availability: **99.9%** (V1+), **99.5%** during MVP.
- Data durability: **99.999999999%** (11 nines) for metadata; video assets 99.99%.
- RPO ≤ 5 min; RTO ≤ 30 min (active-active multi-region, see [DevOps](09-devops-cicd.md)).

### NFR-CAP Capacity & Scale
- Support 10M registered users, 1M concurrent stream viewers in V1; 100M MAU at V2 target.
- Single stream fan-out: 100K+ concurrent viewers (web-scale) and ≤ 50K per WebRTC mesh.
- Ingestion: 40K+ concurrent live streams at V2.
- Tolerate 10× spikes (New Year's Eve events, Olympics).

### NFR-PER Performance
- 360° ABR switch time < 1.5 s. Frame drop < 0.5% at 4K/60fps.
- Chat message E2E < 500 ms. Presence updates < 200 ms between peers.
- Catalog search < 300 ms P95; recommendation fetch < 400 ms.

### NFR-SEC Security
- TLS 1.2+ everywhere; E2EE for private calls (see [Security](08-security-architecture.md)).
- OWASP ASVS L2 compliance; secrets via KMS/Secret Manager; no PII in logs.
- PCI-DSS via tokenized processor (we never store PANs).

### NFR-PRI Privacy
- GDPR/CCPA: right to export/delete; DPIA published; consent registry; DPA with all processors.
- Data residency options for EU (regional cluster).

### NFR-ACC Accessibility
- WCAG 2.2 AA on mobile/web; VR comfort standards documented; ATAG-aligned authoring tools for creators.

### NFR-OBS Observability
- Traces (OpenTelemetry) for 100% of API + streaming paths; logs < 60 s to query; metrics 15 s granularity; dashboards per service; SLO burn-rate alerts.

### NFR-DEV Developer Experience
- CI pipeline < 15 min on change; canary deploys; feature flags; contract tests gate integrations; environment parity (dev/stage/prod).

### NFR-ECON Cost
- Cost per viewer-stream-hour (media+network) ≤ $0.60 at 1M MAU scale; AI inference ≤ $0.0012/answer at scale. See [Roadmap](13-roadmap.md) §Costs.

---

## 5. Interface Requirements
- **Client platforms:** Meta Quest (2/3/Pro), Apple Vision Pro (T1), HTC Vive, Pico, PSVR2 (T1), PC VR (Steam), Android, iOS, Web (WebXR + WebGL/three.js), Desktop (Win/mac).
- **3rd-party integrations:** OpenStreetMap geo, OAuth providers, Stripe/Adyen, Wise, AWS S3/CloudFront, OpenAI/Anthropic/Google model APIs, speech (Deepgram/Azure/AWS Transcribe + TTS), moderation (Hive/AWS Rekognition custom), CDN (CloudFront/Cloudflare), observability (Datadog/Grafana).

## 6. Assumptions & Constraints
- Global content is legal where streamed; platform applies jurisdiction-aware restrictions.
- Apple App Store/Google Play in-app purchase rules govern mobile-native monetization (30/15% fee) → mitigation via web + "travel credits" model (see [Business Plan](12-business-plan.md)).
- Creators retain IP for their footage; platform holds exclusive/non-exclusive distribution license (contract-defined).
- Network conditions: minimum 5 Mbps for 1080p, 25 Mbps for 4K; graceful downgrade otherwise.

## 7. Acceptance Criteria (excerpts)
- **AC-2.2:** On a 50 Mbps connection, 4K ABR reaches steady-state ≤ 8 s after join, < 0.5% dropped frames over 10 min.
- **AC-4.1:** AI guide answers ≥ 90% of test QA set with grounded citations, < 5% harmful/unsupported answers.
- **AC-6.1:** Watch-together sync offset ≤ 250 ms between two clients on same region for 30 min.
- **AC-9.1:** 95% of hate-speech chat messages flagged before display to 99% of viewers.
- **AC-NFR:** SLOs enforced via SLO dashboards; burn-rate alerts page on-call < 5 min.

## 8. Traceability
Each FR maps to PRD §5 features and to LLD service boundaries in [Low-Level Design](04-low-level-design.md). Requirements changes require PRD + SRS co-update.
