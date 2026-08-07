# 11 — Risk Assessment

**WorldView VR** | Version 1.0 | Status: Draft

## 1. Risk Heatmap

| ID | Risk | Category | Likelihood | Impact | Mitigation / Owner |
|---|---|---|---|---|---|
| R1 | Creator supply fails to materialize | Product/GTM | Med | High | Equipment loaner + minimum-payout guarantees + tourism-board partnerships |
| R2 | Live 360° latency/cost at scale exceeds targets | Technical | Med | High | Tiered protocol paths; tiled streaming; cost per stream-hour SLOs enforced |
| R3 | Content/moderation legal liability (DSA) | Legal | Med | High | Inline moderation, transparent reports, jurisdiction gating, legal counsel review |
| R4 | AI guide hallucination / harmful output | Trust/AI | Med | High | Grounded RAG + citations + output filters + benchmarks + red-team |
| R5 | Privacy/regulatory breach (GDPR, minors, filming consent) | Legal | Med | High | Consent registry, DSR pipeline, EU cluster, age gate, creator consent UX |
| R6 | Payment fraud / chargeback abuse | Financial | Med | Med-High | Radar rules, velocity limits, KYC for payouts, 3DS2 |
| R7 | Store fee economics erode margins | Financial | High | Med | Web checkout preference, "travel credits" model, subscription on web |
| R8 | VR hardware adoption slower than expected | Market | Med | High | Phone/desktop/web-first strategy — VR is growth surface not gate |
| R9 | Major event scale spike (NYE) overwhelms | Technical | Med | Med | Mega-event runbook: pre-scale, queue joins, degrade free tier, load test 120% |
| R10 | DRM/capture loophole for premium content | Business | Med | Med | Watermarks, DRM, forensic tracking; accept some leakage |
| R11 | Single cloud/vendor lock-in (AWS, AI vendors) | Technical | Med | Med | Abstraction layers; multi-model gateway; IaC portable; multi-cloud option |
| R12 | Community safety incidents (harassment, CSAM) | Trust/Legal | Low-Med | High | Auto-mod + hash-match + human review + fast SLA + serial-abuser detection |
| R13 | Accessibility compliance lawsuit | Legal | Low-Med | Med | WCAG 2.2 AA as release gate; VPAT; periodic audits |
| R14 | Key talent scarcity (VR engineers, media engineers) | Talent | Med | Med | Competitive comp, remote-friendly, contractor partners, docs culture |
| R15 | Competition (Big Tech launches immersive travel) | Market | Med | High | Network effects (creators), speed, niche verticals, B2B/G2 partnerships |

## 2. Risk Mitigation Detail (top 5)

### R2 — Streaming cost at scale
- Tiled viewport streaming cuts bandwidth 4–10× (see [LLD §4](04-low-level-design.md)).
- Tiered delivery: LL-HLS for free/web mass, WebRTC for premium/VR. Cost per viewer-hour tracked as SLO with budget.
- Media transcode on spot instances; CDN contracts with committed discounts at volume.
- **Fallback:** if media cost > 65% of revenue, push more of the ladder to VOD/edge-cache, cap free-tier bitrate.

### R3/R12 — Content & moderation
- Layered moderation (fast classifier → human queue → appeal). Live pre-check + in-stream flag path.
- Hash-matching for CSAM with immediate legal escalation.
- Jurisdiction-aware legal checker for creators (drone permits, public filming).
- **Fallback:** auto-shutoff streams that spike risk score; geoblock where required by law.

### R4 — AI safety
- RAG grounding mandatory (answers cite POI/knowledge entries).
- Output filter + toxicity classifier before display; no PII fed into prompts.
- Offline benchmark gate before every model/prompt release; online drift alerts.
- **Fallback:** scripted narration fallback if AI unavailable.

### R5 — Privacy & regulatory
- EU cluster residency; consent registry; DSR pipeline automated.
- Minor safety: age gate + guardian mode; no ads to minors.
- Legal checker integrated into creator onboarding.
- **Fallback:** content unavailable in jurisdictions without sufficient legal basis.

### R8 — VR adoption
- Cross-platform from day one (phone/web/desktop first). VR is a differentiated surface, not the only surface.
- Enterprise/education/B2B GTM doesn't depend on consumer VR hardware adoption.

## 3. Risk Register Cadence
- Risk review monthly (updated likelihood/impact); top-10 tracked in board pack.
- Insurance: cyber liability, media errors & omissions, D&O.
- Legal review of ToS/DPA/creator agreements per region expansion.

## 4. Residual Risk Appetite
- Accept: some premium content leakage (DRM watermark only), store-fee friction, platform liability managed by moderation ops.
- Avoid: advertising to minors, real-money gambling-adjacent mechanics, unverified anonymous payments.
