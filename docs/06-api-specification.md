# 06 — API Specification

**WorldView VR** | Version 1.0 | Status: Draft

Base URL: `https://api.worldview.vr` (per-region `https://eu.api.worldview.vr`, etc.)
Auth: `Authorization: Bearer <JWT>` (OAuth 2.1 / OIDC). Rate limits returned via `RateLimit-*` headers.

## 1. Conventions
- REST/JSON for CRUD; WebSocket for real-time (chat, presence, watch-sync); gRPC internal.
- Versioning: URL `/v1/`. Errors: RFC 7807 `application/problem+json`.
- Idempotency: `Idempotency-Key` header on POST/PATCH that create or move money.
- Pagination: cursor-based `?cursor=<opaque>&limit=50`; response contains `next_cursor`.
- All list endpoints support `?fields=`, `?lang=` for i18n.
- Streaming/media endpoints return signed URLs (10-min TTL).

## 2. Error Model
```json
{ "type": "https://worldview.vr/errors/rate_limited",
  "title": "Rate limit exceeded",
  "status": 429,
  "detail": "Retry after 30s",
  "instance": "req_xyz" }
```
Common statuses: 400 validation, 401 unauthenticated, 403 forbidden, 404 not found, 409 conflict, 422 unprocessable, 429 rate-limited, 5xx server.

## 3. Authentication & Identity
```
POST   /v1/auth/login                     {email, password} | {provider, code}
POST   /v1/auth/refresh                   {refresh_token}
POST   /v1/auth/logout
POST   /v1/auth/mfa/enroll                T0 optional
POST   /v1/auth/mfa/verify
GET    /v1/users/me                       -> Profile
PATCH  /v1/users/me                       {display_name, avatar, accessibility, locale}
GET    /v1/users/me/devices
DELETE /v1/users/me/devices/{device_id}
GET    /v1/users/me/consents
POST   /v1/gdpr/export                    -> async job, returns export_id
POST   /v1/gdpr/delete                    -> async, schedules deletion
```
Sample response:
```json
{ "id":"01H...", "display_name":"Mira", "locale":"en",
  "accessibility":{"reduced_motion":true,"subtitles":true},
  "is_verified":true, "plan":"free" }
```

## 4. Catalog
```
GET    /v1/tours                          ?status=published&category=&geo=lat,lng,r&q=&sort=
GET    /v1/tours/{tour_id}
GET    /v1/tours/{tour_id}/pois           ?t=143&lookDir=yaw,pitch
GET    /v1/tours/{tour_id}/hotspots       ?t=143
GET    /v1/pois/{poi_id}
GET    /v1/categories
POST   /v1/tours/{tour_id}/bookmark       {list_id?}
GET    /v1/travel-lists                   my lists
POST   /v1/travel-lists                   {name}
POST   /v1/tours/{tour_id}/capture        {kind:"vr_photo"|"memory_clip", t}
```
**Tour object (abridged):**
```json
{ "id":"01H...", "kind":"live", "title":{"en":"Shibuya Crossing","fr":"... "},
  "geo_center":[35.6595,139.7005], "is_live":true, "viewers":1240,
  "quality_max":"4k_tiled", "spatial_audio":true,
  "stream":{ "protocol":"llhls", "url":"https://cdn.worldview.vr/...","signed":true },
  "premium":false, "creator": {"id":"...","name":"...","is_verified":true} }
```

## 5. Streaming
```
POST   /v1/streams                        Creator: begin (returns ingest info + stream key)
POST   /v1/streams/{id}/start
POST   /v1/streams/{id}/pause             {auto_resume_sec?}
POST   /v1/streams/{id}/end
GET    /v1/streams/{id}                   viewer: join metadata + signed media URL
GET    /v1/streams/live                   ?geo=&category=&sort=trending
POST   /v1/streams/{id}/report            viewer report
POST   /v1/streams/{id}/tip               {cents, message} (idempotency required)
GET    /v1/streams/{id}/stats             creator: viewers, bitrate, tips
```
**Join response:**
```json
{ "session_id":"...", "protocol":"llhls",
  "manifest":"https://cdn.worldview.vr/.../index.m3u8?signature=...&expires=...",
  "tiles": { "cols":8, "rows":3, "profiles":["1.5m","4m","8m","16m"] },
  "spatial_audio":"ambisonics_a", "dvr_seconds":1800, "captions_langs":["en","ja","es"] }
```

## 6. AI World Guide
```
POST   /v1/guide/ask                     {tour_id, t, look_dir:{yaw,pitch}, text?, lang?}
```
- Returns **streaming** tokens over WebSocket/SSE + final structured answer with citations.
```json
{ "answer": "That's the Hachikō statue...", "lang":"en",
  "citations":[{"poi_id":"...","t":142.8,"type":"poi","name":"Hachikō Statue"}],
  "suggested_hotspots":["...","..."] }
```
```
POST   /v1/guide/translate-sign           {tour_id, t, image_region?}  -> overlay text + OCR source
POST   /v1/guide/identify                 {tour_id, t, bbox?}           -> plant/animal/landmark
GET    /v1/guide/itinerary                {prefs:[...], duration_hours}  T1
GET    /v1/guide/languages                supported languages
```

## 7. Social & Presence (WebSocket)
```
WS /v1/ws?token=JWT   (multiplexed events)
```
Events (JSON frames, `type` discriminated):
- `room.join {room_id, tour_id}`, `room.leave`
- `presence.sync {room_id, members:[{user_id, avatar, pos, rot}]}`
- `watch.sync {tour_id, t, playState}` (leader-driven)
- `chat.send {room_id, text, reply_to?}` → `chat.msg {msg_id, user_id, text, t, mod_flags}`
- `chat.reaction {msg_id, emoji}`
- `room.kick {user_id}` (leader/admin)
- `voice.state {enabled, speaking}` T1
- `stream.state {status, viewers, t}` (live stream metadata push)

## 8. Payments & Billing
```
GET    /v1/billing/plans
POST   /v1/billing/checkout               {plan_id, provider: web|apple|google}
POST   /v1/billing/portal                 return Stripe portal URL
GET    /v1/billing/invoices
POST   /v1/tips/{stream_id}               {cents, message}
GET    /v1/purchases                      pay-per-tour history
POST   /v1/tours/{tour_id}/purchase       {price_cents, idempotency}
```
Webhooks: `/v1/webhooks/stripe`, `/v1/webhooks/apple`, `/v1/webhooks/google`, `/v1/webhooks/adyen` — verified by signature, respond 200 fast, process async.

## 9. Creator Platform
```
POST   /v1/creators/apply                 {equipment, region, id_doc_token}
POST   /v1/creators/verify                {liveness_token, geocheck}
GET    /v1/creators/me/dashboard          metrics
GET    /v1/creators/me/streams
POST   /v1/creators/me/equipment-loan     T1 request
GET    /v1/creators/me/payouts
POST   /v1/creators/me/private-tours      create booking offering
```

## 10. Admin & Enterprise
```
GET    /v1/admin/users?q=&status=
POST   /v1/admin/users/{id}/suspend       {reason, duration}
GET    /v1/admin/moderation/queue
POST   /v1/admin/moderation/{id}/decision {decision, note}
GET    /v1/admin/streams
POST   /v1/enterprise/groups              create group
POST   /v1/enterprise/groups/{id}/members add users
POST   /v1/enterprise/events              create private virtual event
GET    /v1/enterprise/reports             engagement per group
```

## 11. Notification Service (internal + client)
```
POST   /v1/notifications/subscribe        {push_token, platform, topics[]}
POST   /v1/notifications/test             T1
```
Topics: `creator.live`, `tour.published`, `chat.mention`, `tip.received`, `booking.confirmed`.

## 12. Rate Limits (default)
| Endpoint class | Limit |
|---|---|
| Reads (catalog/search) | 120 req/min |
| Writes (bookmark, capture) | 60 req/min |
| Guide/ask (free tier) | 30 req/hr |
| Guide/ask (premium) | 600 req/hr |
| Auth (login) | 5 req/min per IP + captcha escalator |
| Tip/checkout | 10 req/min per user |
| WS events | 60 msg/s per connection |

## 13. Contract Testing & Versioning
- OpenAPI 3.1 spec auto-generated from protobuf annotations (buf + protoc).
- Contract tests in CI gate producer/consumer; breaking changes require `/v2/` + deprecation notice ≥ 6 months.
- Internal gRPC contracts versioned by `package v1x`; additive changes preferred.
