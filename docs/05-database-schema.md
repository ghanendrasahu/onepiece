# 05 — Database Schema

**WorldView VR** | Version 1.0 | Status: Draft

## 1. Storage Strategy Overview

| Store | Data | Why |
|---|---|---|
| **PostgreSQL (Aurora)** | Users, sessions, tours, POIs, bookings, payouts, moderation, admin | ACID, relational integrity |
| **Redis** | Sessions, presence, hot-cache, rate-limit, leaderboards | Microsecond access, TTL |
| **Kafka** | Event backbone (durable) | Streaming/fan-out source of truth for derived data |
| **Milvus** | Embeddings (POI knowledge, transcripts, visual) | Similarity search for AI guide + recommendations |
| **TimescaleDB** | Stream metrics, watch-time, telemetry | Time-series compression |
| **S3 + Iceberg** | Raw events → lakehouse | BI/analytics at scale |
| **OpenSearch** | Catalog text/geo/facet index | Search relevance |

## 2. Conventions
- IDs: `ULID` (26-char, time-sorted) for all PKs.
- Every table has `created_at`, `updated_at` timestamps, and soft-delete `deleted_at` where legal-retention applies.
- Money stored as `BIGINT` cents (integer), never float.
- Multi-tenancy: `region_key` partition column on cross-region tables; tenant_id for Enterprise.
- Soft FK via ULID; explicit FK constraints within a database where beneficial; cross-service references by ULID without FK.

## 3. Core Tables (PostgreSQL)

### 3.1 identity
```sql
CREATE TABLE users (
  id                ULID PRIMARY KEY,
  email             TEXT UNIQUE,
  phone             TEXT,
  password_hash     TEXT,           -- argon2id, only if not social-only
  display_name      TEXT NOT NULL,
  avatar_url        TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at        TIMESTAMPTZ,
  is_verified       BOOL DEFAULT false,
  accessibility     JSONB,          -- {"reduced_motion":true,...}
  locale            TEXT DEFAULT 'en',
  region_key        TEXT NOT NULL
);
CREATE INDEX idx_users_region ON users (region_key);

CREATE TABLE user_identities (
  provider    TEXT NOT NULL,        -- google/apple/meta/phone
  subject     TEXT NOT NULL,
  user_id     ULID NOT NULL REFERENCES users(id),
  PRIMARY KEY (provider, subject)
);

CREATE TABLE sessions (
  id            ULID PRIMARY KEY,
  user_id       ULID NOT NULL REFERENCES users(id),
  refresh_token_hash TEXT NOT NULL,
  device_id     TEXT NOT NULL,
  expires_at    TIMESTAMPTZ NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at    TIMESTAMPTZ
);
CREATE INDEX idx_sessions_user ON sessions (user_id);

CREATE TABLE consent_records (
  user_id       ULID NOT NULL,
  policy_id     TEXT NOT NULL,     -- gdpr_privacy_v3 / tos_v2 ...
  accepted_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  ip            INET,
  user_agent    TEXT,
  PRIMARY KEY (user_id, policy_id)
);
```

### 3.2 catalog
```sql
CREATE TABLE tours (
  id             ULID PRIMARY KEY,
  title          JSONB NOT NULL,          -- i18n {"en":..., "fr":...}
  description    JSONB,
  kind           TEXT NOT NULL,           -- live|vod|ai_guided|time_travel
  status         TEXT NOT NULL DEFAULT 'draft',  -- draft|published|archived|removed
  creator_id     ULID REFERENCES users(id),
  geo_center     POINT,
  region_key     TEXT NOT NULL,
  price_cents    BIGINT DEFAULT 0,
  is_free        BOOL DEFAULT false,
  premium        BOOL DEFAULT false,
  duration_sec   INT,
  language       TEXT DEFAULT 'en',
  published_at   TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_tours_status ON tours (status, published_at DESC);
CREATE INDEX idx_tours_geo ON tours USING GIST (geo_center);

CREATE TABLE tour_categories (
  tour_id   ULID REFERENCES tours(id) ON DELETE CASCADE,
  category  TEXT NOT NULL,          -- landmark/city/nature/festival/culture/concert
  PRIMARY KEY (tour_id, category)
);

CREATE TABLE pois (
  id          ULID PRIMARY KEY,
  tour_id     ULID NOT NULL REFERENCES tours(id) ON DELETE CASCADE,
  name        JSONB NOT NULL,
  description JSONB,
  t_begin_sec NUMERIC,              -- time in tour timeline
  t_end_sec   NUMERIC,
  look_dir    JSONB,                -- {"yaw":..,"pitch":..} anchoring hotspot
  geohash     TEXT,
  type        TEXT                  -- landmark/food/animal/plant/art...
);
CREATE INDEX idx_pois_tour ON pois (tour_id, t_begin_sec);

CREATE TABLE hotspots (
  id          ULID PRIMARY KEY,
  poi_id      ULID NOT NULL REFERENCES pois(id) ON DELETE CASCADE,
  kind        TEXT,                 -- info/photo/quiz/audio/ar_overlay
  payload     JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.3 streaming
```sql
CREATE TABLE stream_sessions (
  id              ULID PRIMARY KEY,
  tour_id         ULID REFERENCES tours(id),
  creator_id      ULID NOT NULL REFERENCES users(id),
  status          TEXT NOT NULL DEFAULT 'preparing', -- preparing|live|paused|ended|archived
  ingest_endpoint TEXT,
  stream_key_id   ULID,
  quality_ladder  JSONB,            -- ["720p","1080p","4k_tiled"]
  spatial_audio   BOOL DEFAULT false,
  started_at      TIMESTAMPTZ,
  ended_at        TIMESTAMPTZ,
  dvr_retention_s INT DEFAULT 1800,
  region_key      TEXT NOT NULL,
  version         INT DEFAULT 0,    -- optimistic concurrency
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_streams_status ON stream_sessions (status, started_at DESC);

CREATE TABLE stream_events (         -- event-sourced: state machine ledger
  id         ULID PRIMARY KEY,
  session_id ULID NOT NULL REFERENCES stream_sessions(id),
  type       TEXT NOT NULL,         -- started|paused|ended|health
  payload    JSONB,
  at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.4 social
```sql
CREATE TABLE friendships (
  user_a       ULID NOT NULL REFERENCES users(id),
  user_b       ULID NOT NULL REFERENCES users(id),
  status       TEXT NOT NULL,       -- pending|accepted|blocked
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (user_a, user_b)
);
CREATE INDEX idx_friends_b ON friendships (user_b, status);

CREATE TABLE watch_rooms (
  id          ULID PRIMARY KEY,
  type        TEXT NOT NULL,        -- tour|stream|event
  ref_id      ULID NOT NULL,
  host_id     ULID NOT NULL,
  state       JSONB,                -- {"t":143.2,"playState":"playing"}
  member_ids  ULID[],
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.5 payments
```sql
CREATE TABLE subscriptions (
  id              ULID PRIMARY KEY,
  user_id         ULID NOT NULL REFERENCES users(id),
  plan_id         TEXT NOT NULL,
  status          TEXT NOT NULL,    -- active|past_due|canceled
  provider        TEXT NOT NULL,    -- stripe|apple|google|web
  provider_sub_id TEXT,
  current_period_end TIMESTAMPTZ NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_subs_user ON subscriptions (user_id, status);

CREATE TABLE transactions (         -- all money movement
  id                ULID PRIMARY KEY,
  user_id           ULID NOT NULL REFERENCES users(id),
  type              TEXT NOT NULL,  -- sub_renewal|pay_per_tour|tip|payout|refund
  gross_cents       BIGINT NOT NULL,
  fee_cents         BIGINT NOT NULL,
  net_cents         BIGINT NOT NULL,
  currency          TEXT NOT NULL DEFAULT 'USD',
  provider_tx_id    TEXT,
  idempotency_key   TEXT UNIQUE,
  status            TEXT NOT NULL DEFAULT 'pending', -- pending|succeeded|failed|disputed
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_tx_user ON transactions (user_id, created_at DESC);

CREATE TABLE tips (
  id         ULID PRIMARY KEY,
  stream_id  ULID REFERENCES stream_sessions(id),
  from_user  ULID NOT NULL REFERENCES users(id),
  to_creator ULID NOT NULL REFERENCES users(id),
  cents      BIGINT NOT NULL,
  message    TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.6 moderation
```sql
CREATE TABLE moderation_items (
  id             ULID PRIMARY KEY,
  object_type    TEXT NOT NULL,     -- chat|stream|avatar|profile
  object_id      ULID NOT NULL,
  risk_score     REAL,
  decision       TEXT,              -- approved|flagged|removed|escalated
  auto_flag      BOOL DEFAULT false,
  reviewed_by    ULID,
  reviewed_at    TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_mod_obj ON moderation_items (object_type, object_id, created_at DESC);
```

### 3.7 bookmarks, memories, captures
```sql
CREATE TABLE travel_lists (
  id      ULID PRIMARY KEY,
  user_id ULID NOT NULL REFERENCES users(id),
  name    TEXT NOT NULL,
  is_default BOOL DEFAULT false
);

CREATE TABLE bookmarks (
  id       ULID PRIMARY KEY,
  user_id  ULID NOT NULL REFERENCES users(id),
  tour_id  ULID REFERENCES tours(id),
  poi_id   ULID REFERENCES pois(id),
  list_id  ULID REFERENCES travel_lists(id),
  note     TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE captures (
  id        ULID PRIMARY KEY,
  user_id   ULID NOT NULL REFERENCES users(id),
  tour_id   ULID NOT NULL REFERENCES tours(id),
  kind      TEXT NOT NULL,          -- vr_photo|memory_clip
  url       TEXT NOT NULL,          -- signed media URL
  t_begin   NUMERIC,
  t_end     NUMERIC,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 4. Vector Store (Milvus) Collections
```sql
-- collection: poi_knowledge
--   pk: poi_id (ULID)
--   vector: text-embedding-3-large (3072d) of {name, description, transcript, tags}
--   metadata: tour_id, t_begin, t_end, geohash, category, language

-- collection: tour_transcript
--   pk: segment_id
--   vector: embedding of transcript segment (per language)
--   metadata: tour_id, t_begin, t_end, language

-- collection: visual_scene
--   pk: scene_id
--   vector: CLIP-style embedding of representative frame
--   metadata: tour_id, t_begin, t_end, thumbnail_url

-- collection: user_prefs
--   vector: embedding of user interests (updated weekly, T1)
```

## 5. Time-Series (TimescaleDB)
```sql
CREATE TABLE stream_health (
  ts        TIMESTAMPTZ NOT NULL,
  session_id ULID,
  bitrate_mbps REAL,
  loss_pct  REAL,
  viewers   INT
);
-- hypertable partitioned by day, retention 90 days

CREATE TABLE watch_events (
  ts        TIMESTAMPTZ NOT NULL,
  user_id   ULID,
  tour_id   ULID,
  session_id ULID,
  device    TEXT,
  watch_sec INT,
  region    TEXT
);
-- hypertable → feed watch-time analytics + billing for pay-per-tour
```

## 6. Lakehouse (S3 + Iceberg)
- Kafka topics → S3 Iceberg tables via Kafka Connect:
  - `app_events` (all business events), `chat_events`, `moderation_events`, `payment_events`.
- BI via Athena/Trino; dbt models for reporting: MAU, WAU, retention, LTV, stream hours, creator payouts.

## 7. Indexing & Search (OpenSearch)
- `tours` index: title/description (multi-language analyzers), categories, geo_point, price, status.
- `pois` index: name, type, geohash, tour_id.
- Replication strategy: CDC from Postgres (Debezium) → Kafka → indexer.

## 8. Partitioning & Sharding Notes
- **Hot tables** (`users`, `stream_sessions`, `transactions`): partition by `region_key` (Postgres declarative partitioning at 100M+ row scale).
- **Global uniqueness:** email/user_id unique globally — use global sequence range shards or ULID + unique constraint via per-region writer with conflict retry; at Spanner scale (T2) rely on global PK.
- **Purge policy:** GDPR deletion is a logical delete + async purge of PII columns; physical rows retained anonymized for 90 d for fraud/legal.

## 9. Backup & DR
- Postgres: PITR (30 d), cross-region snapshot (RPO 5 min, RTO 30 min).
- S3 versioning + replication for media.
- Kafka: cross-region MirrorMaker2 replicas.
- Milvus: rolling backups + index rebuild from lakehouse as ultimate restore.
