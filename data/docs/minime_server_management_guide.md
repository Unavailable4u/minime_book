# MiniMe — Server Management & Splitting Guide

*A practical execution guide, separate from but built directly on `minime_roadmap.md` (business/phasing)
and `minime_technical_roadmap.md` (architecture). This document answers one question only: **when and
how do you actually split servers, and how do you manage them once split** — sequenced against your
real phases (0 → 1 → 2 → 3a → 3b), not against a generic "best practice" timeline.*

Verified against the live repo (`docker-compose.yml`, `backend.Dockerfile`, `frontend.Dockerfile`,
`backend/api/routes/system.py`) as of this writing:
- Backend: FastAPI, port `8000`, already exposes `GET /api/health` → `{"status": "ok"}`.
- Frontend: Next.js, port `3000`, talks to backend via `NEXT_PUBLIC_API_URL`.
- Compose already separates the two into distinct containers/build contexts — you are *not* starting
  from a monolith, you're starting from "two containers on one host."
- A `backend-latency-probe` endpoint already exists and times Postgres/Redis round-trips — reuse this
  when you're deciding where a new server should physically sit (co-location matters, per that code's
  own comments).
- `daemon/` exists but is explicitly flagged in the roadmap as **out of scope for hosting decisions**
  until a tier's revenue funds a real security audit of it. Do not put it on any internet-facing server
  in the meantime.

---

## Guiding rule: splitting is gated, not scheduled

The business roadmap's core discipline (Part 3.5/3.6) — don't build the next tier until operational
capacity and demand both justify it — applies identically to infrastructure. **Don't split servers
ahead of the phase that needs it.** Every extra server is something you personally patch, monitor, pay
for, and debug at 2am, solo, until Phase 3a's hiring. The failure mode to avoid isn't "under-scaled and
slow" (fixable in an afternoon) — it's "over-built and unmaintained" (a solo founder quietly not
patching three droplets while building Moderate).

So this guide is phase-gated:

| Roadmap phase | Infra state | Why not more |
|---|---|---|
| Phase 0 (now → Apr 2027) | 1 server, Docker Compose, no public billing | No paying users yet — nothing to protect at scale |
| Phase 1 (pilot) | 1 server, hardened, real monitoring | Pilot traffic is bounded and known in advance |
| Phase 2 (Basic launch) | **First real split** — LB + 2 backend + reverse proxy | Real money and real strangers now hit this |
| Phase 3a (Moderate) | Horizontal scale-out, dedicated agent workers | Second tier's load profile differs from Basic's |
| Phase 3b (Ultimate) | Kubernetes or equivalent, autoscaling | Third model tier, longest-running agent jobs |

---

## Phase 0 (now) — one server, done properly

You don't need a second server yet. You need the *first* one to be boring and correct.

**Setup:**
- 1 VPS (DigitalOcean droplet or Hetzner CX, 2–4 vCPU / 4–8GB is plenty at this stage).
- Docker Compose as it exists in the repo today — no changes needed to `docker-compose.yml` structurally.
- Add **Caddy** in front on the same box, reverse-proxying to `localhost:3000` (frontend) and
  `localhost:8000/api/*` (backend). Caddy gets you automatic HTTPS with almost no config — this is the
  single highest-value/lowest-effort addition available to you right now.
- Point your domain at this box through Cloudflare (free plan) for DNS + basic DDoS/WAF — no code changes
  required, just DNS.

**Management practices to start now, not later:**
- **Cost-per-task logging** — per the roadmap's Part 15 #1, this is the single highest-leverage thing to
  have running before anything else. It also happens to be the data you'll need to size Phase 2's servers
  correctly instead of guessing.
- **Health checks are already there** — `GET /api/health` exists. Point Caddy's (or later, your load
  balancer's) health check at it now, even solo, so you build the habit before it's load-bearing.
- **Key consolidation** — you're running on ~57 free-tier keys today (per the technical roadmap's audit).
  Before Phase 2, this needs to become a real 5–8 provider production shortlist. Do this on the *current*
  single server first — it's a config change, not an infra change, and it's much easier to get right
  before you're also managing multiple hosts.
- **Backups** — Supabase and Upstash are already managed/backed-up externally, which is a real advantage;
  the only thing living solely on your one droplet is your Docker config and any local secrets. Keep
  `.env` files backed up somewhere off that box (a password manager or encrypted secret store — never a
  public repo; note the repo already runs Gitleaks pre-commit + CI scanning, keep that habit).

**Don't do yet:** load balancer, second server, Kubernetes, API gateway. All of these add operational
surface with zero users to justify it.

---

## Phase 1 (pilot) — same one server, hardened

Per the roadmap, Phase 1's job is producing real cost-per-task and usage data for Basic's tier profile —
not scaling. Pilot traffic is small and bounded (a Seed Fund cohort or a BD-connected pilot customer),
so a second server still isn't justified.

**What changes from Phase 0:**
- Real per-user rate limiting (independent of provider limits) — this is now protecting against a known
  but external set of pilot users, not just yourself.
- Basic monitoring dashboard — even a simple one (Grafana + the metrics you're already logging, or just
  a scheduled script emailing you a daily summary) so pilot problems surface before the pilot user tells
  you.
- Multi-tenancy and isolation should already be *real* by this point (per the roadmap's Phase 0 technical
  work) — this is where you find out if it actually holds under real concurrent pilot users, on the one
  server you already have.

**Still don't:** split servers. If the pilot is generating more load than one droplet handles comfortably,
that's a data point for sizing Phase 2's servers, not a reason to prematurely add a second box to a
system still running on Compose without a load balancer in front.

---

## Phase 2 (Basic launch) — the first real split

This is the actual point in your roadmap where splitting earns its cost: real billing, real strangers,
real uptime expectations. This is "Phase 2 – First real production" from the technical roadmap, made
concrete against your actual repo.

### Target architecture

```
Internet
   │
   ▼
Cloudflare (DNS + CDN + WAF)
   │
   ▼
Load Balancer  (DO LB / Hetzner LB — health check → GET /api/health)
   │
   ▼
Caddy (reverse proxy, TLS termination, one instance per node or a
       dedicated small proxy node — either works at this size)
   │
   ├──► Frontend nodes ×2  (Next.js containers, built from frontend.Dockerfile)
   │
   └──► Backend nodes ×2   (FastAPI containers, built from backend.Dockerfile)
              │
              ▼
   External managed services (unchanged): Supabase, Upstash, Pusher
```

### Concrete steps

1. **Split frontend and backend onto separate node groups first**, before adding more of either. They
   scale differently (frontend is nearly stateless and cheap to replicate; backend is where agent calls
   and cost live) and have different failure modes. The repo's Dockerfiles already build them
   independently — this is a deploy-topology change, not a code change.
2. **Two backend nodes minimum**, behind the load balancer, both pointed at the same Supabase/Upstash
   instances. `NEXT_PUBLIC_API_URL` on the frontend nodes should point at the load balancer's address,
   not at a single backend node's IP.
3. **Health checks become load-bearing now.** Configure the load balancer to poll `GET /api/health` on
   each backend node and pull unhealthy nodes out of rotation automatically. This endpoint already exists
   — you're wiring it up, not building it.
4. **Reverse proxy / TLS**: Caddy in front, same as Phase 0/1, just now proxying to multiple upstream
   nodes instead of `localhost`.
5. **Rate limiting at the edge**, not just per-user in application code — Basic is your highest-call-volume
   tier by design (per the roadmap's Part 4.2a), so this is where a runaway client or an abuse pattern
   would actually hurt.
6. **Consider whether an API gateway (Kong/Traefik) earns its cost yet.** The technical roadmap correctly
   flags this as optional at first pass — add it when you specifically need per-API-key limits, central
   auth across nodes, or per-tier request shaping, not just because it's "the more sophisticated option."
   At two backend nodes, a good reverse proxy config often covers what you need.
7. **Keep the daemon off every internet-facing node.** Nothing in this phase changes the roadmap's
   decision to keep it deferred until a funded security audit.

### Where each node should physically live

Use the repo's existing `backend-latency-probe` endpoint before choosing a region/provider for your new
nodes — it already measures real Postgres/Redis round-trip latency, not just a region label. Co-locate
backend nodes in the same region as Supabase and Upstash if the probe shows meaningful latency savings;
don't assume "same continent" is close enough.

### Management practices that start mattering here

- **Deploys**: move from "SSH in and `docker compose up`" to a scripted deploy (even a simple CI job
  that builds, pushes, and rolls each node) — with two nodes per tier, manual per-box deploys will drift.
- **Secrets across nodes**: your consolidated 5–8 provider keys now need to be distributed consistently
  to every backend node, not just one `.env` file on one box. A secrets manager (even your cloud
  provider's built-in one) beats copy-pasting `.env` files node to node.
- **Zero-downtime rollout**: with 2 backend nodes, you can roll one at a time behind the load balancer's
  health check — deploy to node A, wait for it to pass health checks, drain traffic to node B, repeat.
  This is the actual payoff of having split in the first place.
- **Logging/observability centralization**: two nodes means two sets of logs. Ship them somewhere
  central (even a simple log aggregator) before you need to debug an issue that only reproduces on one
  node.

**Don't do yet:** Kubernetes. Two frontend + two backend nodes behind a load balancer is a complete,
production-grade setup that doesn't need an orchestrator to manage.

---

## Phase 3a (Moderate) — scale out, don't re-architect

Per the roadmap's gates (3.5/3.6), this phase only starts once Basic's operational load is manageable
*and* real demand signal exists for a second tier. Assuming both gates clear:

- Moderate's load profile differs from Basic's (per Part 4.2a: fewer, larger, more expensive calls,
  smaller user base) — this usually means **fewer additional backend nodes than you'd guess**, tuned
  for longer-running requests rather than raw concurrency.
- This is the natural point to introduce **background workers / task queues** for agents whose work is
  long-running, using Redis (already on Upstash) with Celery, ARQ, or Taskiq — per the technical
  roadmap's design rule #2: never run heavy agent work on the same process serving HTTP. Add a worker
  node pool, separate from the request-serving backend nodes, rather than growing the backend node count
  further.
- Add real usage dashboards and basic abuse detection now if you haven't already — the roadmap
  explicitly gates Moderate's *build* on these existing for Basic, since they're what frees up the hours
  Moderate's build needs.

Architecture becomes:

```
LB → Caddy → Frontend nodes
              → Backend (request-serving) nodes — Basic + Moderate routing by tier
                    → Worker node pool (queue-consuming, long-running agent jobs)
```

Still no Kubernetes required at this point unless node count or deploy frequency has grown enough that
manual node management is itself consuming real hours — that's the actual trigger, not "it's the next
step everyone takes."

---

## Phase 3b (Ultimate) — this is where Kubernetes earns its place

By the time Ultimate is gated open (again: operational capacity + demand signal, not calendar), you
likely have: 3 tiers' worth of routing, a worker pool that's grown, frontier-model jobs that run longer
and need different resource limits per job, and — per the master timeline — a team of 3–5, not solo.
This is the point where the technical roadmap's Phase 3 recommendation (EKS/GKE/DOKS + Ingress +
horizontal pod autoscaling on CPU/queue depth) actually pays for its added complexity, because:

- You now have enough distinct node types (frontend, Basic/Moderate backend, Ultimate backend, workers)
  that manual provisioning is genuinely error-prone.
- Autoscaling on queue depth matters once Ultimate's frontier-model jobs create genuinely variable,
  bursty load.
- You have the headcount (per Part 8's hiring plan) to actually run it — this is explicitly the
  precondition the roadmap's operational-capacity gate is protecting.

Don't pull this phase forward. A solo or two-person team running Kubernetes for Basic-tier traffic is
solving a problem you don't have yet at the cost of hours you need elsewhere.

---

## Cross-phase reference: component choices

| Layer | Phase 0–1 | Phase 2 | Phase 3a–3b |
|---|---|---|---|
| DNS/CDN/WAF | Cloudflare (free) | Cloudflare (free) | Cloudflare (free or paid) |
| Load balancer | — (single box) | DO/Hetzner managed LB | Cloud LB or Ingress controller |
| Reverse proxy | Caddy, same box | Caddy, dedicated or per-node | Ingress (Traefik/Kong) |
| Frontend | 1 container | 2 containers | N containers, autoscaled |
| Backend | 1 container | 2 containers | N containers, tier-routed |
| Background workers | none | none | Celery/ARQ/Taskiq pool |
| Orchestration | Docker Compose | Docker Compose per node | Kubernetes |
| Database | Supabase (unchanged) | Supabase (unchanged) | Supabase or managed Postgres |
| Redis/vector | Upstash (unchanged) | Upstash (unchanged) | Upstash (unchanged) |
| Secrets | local `.env`, backed up | secrets manager | secrets manager + k8s secrets |

Database, Redis/vector, and realtime (Pusher) stay externally managed at every phase per the technical
roadmap's own recommendation — nothing above changes that.

---

## Infra-specific checklist (extends the roadmap's Part 15)

1. Caddy + Cloudflare in front of the single Phase 0 server — this week, not "eventually."
2. Cost-per-task logging live before anything else — you need this data to size Phase 2's node count
   correctly instead of guessing.
3. Consolidate the ~57 free-tier keys to a real 5–8 provider shortlist on the *current single server*,
   before Phase 2 multiplies the number of places a key has to live correctly.
4. Wire the load balancer's health check to the existing `GET /api/health` the moment Phase 2 starts —
   don't build a new endpoint, use what's already there.
5. Use `backend-latency-probe`'s real Postgres/Redis timing, not a region label, when choosing where
   Phase 2's new nodes physically sit.
6. Keep `daemon/` off every internet-facing node at every phase, until its own funded security audit
   happens — this isn't a hosting decision to revisit per-phase, it's a standing rule.
7. Don't add a load balancer, second server, or API gateway before Phase 2's real billing goes live —
   each is easy to add later and expensive to babysit solo, early.
8. Don't add Kubernetes before Phase 3b's headcount and load profile actually justify it.
