# Repository Playbook

Ready-to-paste README structure and architecture diagrams for each featured
project, plus the setup and troubleshooting notes for this profile repo.

Every diagram below was drawn from an audit that read the actual code — not
from the repository's own README. Where the two disagree, the code wins, and
the disagreement is listed below.

**Status: these findings have been worked through.** All five featured
repositories now have green CI. Items still open are marked WONTFIX-YET;
everything else previously listed here as a problem has been fixed and verified.
See each repository's history for the individual commits.

---

## The standard structure

Use this skeleton for every featured repo. Sections in *italics* are optional
only when genuinely not applicable.

```markdown
# Project Name

One sentence: what it does and for whom.

![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)

## Overview
Two short paragraphs. What problem it solves, and the one design decision
that makes it non-obvious.

## Features
- Concrete capability, not an adjective
- Another one

## Architecture
```mermaid
...
```

## Tech Stack
| Layer | Technology |
|---|---|
| Frontend | ... |
| Backend | ... |
| AI | ... |
| Database | ... |
| Infrastructure | ... |
| Testing | ... |

## Project Structure
Trimmed tree — directories and key files only, not every file.

## Getting Started
Prerequisites, then clone/install.

## Environment Variables
Point at `.env.example`. Never commit real values.

## Running Locally
Exact commands, verified by actually running them.

## API / Usage
*If it exposes one.*

## Screenshots
*If they exist.*

## Engineering Highlights
The 3–4 decisions worth defending in an interview.

## Future Improvements
Honest and specific.

## License
MIT — see [LICENSE](LICENSE).
```

Two rules that matter more than the structure:

1. **Never claim what isn't built.** Every featured repo currently overstates
   something. A reviewer who checks one claim and finds it false discounts the
   whole README.
2. **Separate built from planned.** Spendee's README already does this well;
   copy that pattern anywhere work is in progress.

---

## RAGForge — `RAGForge-Document_Search`

Self-hosted, multi-tenant RAG over private documents. Hybrid retrieval with
citation-backed streamed answers.

```mermaid
flowchart TB
    subgraph Client["Next.js 15 · App Router"]
        UI["Projects · Chat UI"]
        MW["clerkMiddleware()"]
    end
    subgraph API["FastAPI · asyncpg pool"]
        R1["/files · ingest"]
        R2["/chat · SSE stream"]
        AU["auth.py<br/>Clerk RS256 via JWKS"]
    end
    subgraph Ingest["Ingestion pipeline"]
        PA["Partition<br/>pdf · docx · pptx · csv · html · txt"]
        CH["Chunk"]
        EM["Embed<br/>MiniLM-L6-v2, L2-normalised"]
    end
    subgraph Store["PostgreSQL"]
        HV[("pgvector<br/>HNSW · vector_ip_ops")]
        TS[("tsvector<br/>GIN")]
    end
    subgraph Retrieve["Retrieval"]
        DN["Dense"]
        SP["Sparse"]
        RRF["Weighted RRF<br/>generic over N lists"]
        RK["Cross-encoder rerank<br/>ms-marco-MiniLM-L-6"]
    end
    LLM["Provider interface<br/>Claude · OpenAI"]

    UI --> MW --> R1 & R2 --> AU
    R1 --> PA --> CH --> EM --> HV
    CH --> TS
    R2 --> DN --> RRF
    R2 --> SP --> RRF
    HV --> DN
    TS --> SP
    RRF --> RK --> LLM --> R2 --> UI
```

**Engineering highlights worth writing up**
- Weighted Reciprocal Rank Fusion written generically over N ranked lists rather
  than hardcoded to two.
- Inner product (`vector_ip_ops`) instead of cosine, made valid by L2-normalising
  at embed time — cheaper distance, same ranking.
- OR-joined `tsquery` construction, with an in-code comment explaining why
  `plainto_tsquery` was wrong for this use.

**Fixed:** IDOR (chunk query now joins `project_documents` and constrains
`d.project_id`); SSRF (`server/urlguard.py` resolves every host, rejects private
/ loopback / link-local / reserved targets, and re-validates every redirect
hop); a PostgREST grant that gave `authenticated` full DML on every table with
no RLS anywhere, revoked with deny-by-default RLS added. 29 tests and CI added.
`/health` wording corrected.

**WONTFIX-YET**
- **Licensing - blocker.** No `LICENSE`, and the README itself notes the client
  scaffold came from a paid course "without an explicit grant." Resolve the
  provenance before adding any licence. Do not apply MIT to code you may not
  have the right to relicense.
- No Dockerfile - for a project described as "self-hosted", a reviewer will
  look for one.
*(Rate limiting added: 30 chat / 20 ingestion calls per minute, keyed on the
Clerk user id, 8 tests.)*

---

## InterviewPilot AI — `Interviewpilot_AI`

Adaptive mock interviewer. The model proposes; a server-side rule engine decides.

```mermaid
flowchart TB
    FE["Next.js 16 · interview room"]
    WS["WebSocket session"]
    subgraph Backend["FastAPI · SQLAlchemy"]
        SC["Answer scorer<br/>structured rubric"]
        EN["engine._enforce_rules()<br/>probe · hint · advance"]
        PR["AIProvider (ABC)"]
        RP["ReportLab · PDF"]
    end
    OAI["OpenAI<br/>main model + fast model"]
    DB[("PostgreSQL")]

    FE <--> WS --> SC --> PR --> OAI
    OAI --> SC --> EN
    EN -->|"overrides model<br/>when policy violated"| WS
    EN --> DB
    DB --> RP --> FE
```

**Engineering highlights**
- The LLM is an advisor, not an authority: `_enforce_rules()` overrides the
  model's suggested next action when it breaks interview policy, so a
  hallucinated control decision cannot derail a session.
- `AIProvider` is an ABC; the OpenAI SDK is never imported outside its concrete
  implementation.
- Separate main and fast models per call site — question generation and the
  coach report don't need the same model.
- `otp.py` states its threat model in the docstring before the code.

**Fixed:** `.env.local.example` added - it had been impossible to commit, since
Next.js's default `.gitignore` matches `.env*` with no exception and silently
dropped it. Redis and Alembic removed (declared, provisioned, pinned, used by
nothing). MIT `LICENSE` added. CI runs 20 backend tests plus frontend lint,
typecheck and build. Two setState-inside-effect errors fixed.

**WONTFIX-YET**
- `docker-compose.yml` provisions only Postgres - `docker compose up` still does
  not start the product itself.

---

## DevFlow — `Devflow`

Self-hosted CI/CD control plane driving the real Docker Engine and GitHub APIs.

```mermaid
flowchart TB
    UI["React 18 · Vite SPA"]
    subgraph Server["Express · Prisma"]
        AUTH["JWT + refresh<br/>single-flight rotation"]
        PIPE["Pipeline runner<br/>child processes"]
        DOCK["docker.service.ts<br/>dockerode"]
        GH["@octokit/rest"]
    end
    IO["Socket.IO<br/>per-build rooms"]
    DB[("PostgreSQL 16")]
    ENG["Docker Engine socket"]

    UI --> AUTH --> DB
    UI --> PIPE --> GH
    PIPE --> DOCK --> ENG
    PIPE -- "log frames + seq" --> IO --> UI
    PIPE --> DB
```

**Engineering highlights**
- Docker log frame demultiplexing: without a TTY the Engine prefixes each line
  with an 8-byte header, and the stream is decoded frame by frame.
- CPU percentage computed the way `docker stats` computes it —
  `cpuDelta/systemDelta` scaled by online CPU count.
- Monotonic per-build sequence numbers on log lines, so a client reconnecting
  mid-build resumes without gaps or duplicates.
- A signed JWT used as the OAuth `state` parameter, carrying the linking user id.

**Fixed:** default JWT secrets no longer apply in production - startup fails
unless both are set, are 32+ characters, are not a known placeholder, and differ
from each other (8 tests; mutation-verified, restoring the old defaults fails 5
of them). `npm test` works because tests now exist. eslint installed in both
workspaces, whose `lint` scripts had referenced a dependency neither declared.
Socket subscriptions to build and project rooms are now authorised through the
same helpers the REST layer uses - the handshake proved *who* was calling but
never *what* they could see. Unexpected error text no longer reaches clients in
production. 18 tests.

**WONTFIX-YET**
- `vitest` is installed, `npm test` is wired, CI runs a test step, and **zero
  spec files exist**, so `npm test` exits 1. Either add tests or drop the step —
  a red CI badge is worse than none.
- `docker-compose.yml` provisions only Postgres; the two real multi-stage
  Dockerfiles are never orchestrated.

---

## ResumePilot — `ResumePilot`

Streamlit RAG resume analyser with a pluggable LLM provider.

```mermaid
flowchart LR
    UP["Resume<br/>PDF · DOCX · TXT"] --> EX["PyMuPDF · python-docx"]
    EX --> CK["RecursiveCharacterTextSplitter"]
    CK --> EM["MiniLM-L6-v2"]
    EM --> CD[("ChromaDB<br/>one collection per resume")]
    JD["Job description"] --> RT["Retrieve"]
    CD --> RT
    RT --> PM["Prompt"]
    PM --> LM["gpt-4o-mini · gemini-2.5-flash"]
    LM --> SV["3-tier JSON salvage"]
    SV --> PD["pydantic · 20 fields"]
    PD --> OUT["Report · PDF / JSON / TXT"]
```

**Engineering highlights**
- Three-tier JSON salvage — fenced block, raw parse, then repair — before
  pydantic validation, because a model asked for JSON returns almost-JSON often
  enough to matter.
- One ChromaDB collection per resume, so retrieval never bleeds between
  candidates.
- `requirements.txt` pins the CPU-only torch wheel index, with a comment saying
  why. Small detail; reviewers notice it.

**Fixed:** CI runs the suite on every push and pull request - all **20** tests
pass with no API key, more than the 12 originally estimated. MIT `LICENSE` added.

**WONTFIX-YET**
- A silent zero-score failure path: when analysis fails the UI shows 0 rather
  than an error.
- The reranker is close to a no-op — either make it real or stop advertising
  "retrieve → rerank."
- README lists Docker as a deployment target; there is no Dockerfile.
- OCR is described as scaffolded; it is unreachable.


---

## DevVerse AI — `Devverse_AI`

Procedural three.js portfolio on Cloudflare Workers.

```mermaid
flowchart TB
    B["Browser"] --> CF["Cloudflare Worker<br/>OpenNext adapter"]
    CF --> LY["app/layout.tsx<br/>boot script before paint"]
    LY --> SC["Scene.tsx"]
    SC --> GPU["GPU tier detection<br/>reads driver string"]
    GPU --> QT["Quality tier"]
    QT --> GEN["Procedural meshes + textures<br/>seeded mulberry32 · no .glb"]
    GEN --> RL["Render loop<br/>frameloop='never' when offscreen"]
    CF --> API["Route handlers<br/>/api/github · /api/ai · /api/contact"]
    API --> EXT["GitHub API · OpenAI"]
```

**Engineering highlights**
- Every mesh and texture is generated in code — no `.glb` assets in the repo.
- Quality tier chosen by reading the real GPU driver string from a throwaway
  WebGL context.
- All randomness from a seeded PRNG, so the scene is byte-identical each load.
- The render loop halts when the hero scrolls out of view.

**Fixed:** MIT `LICENSE` added. `/api/ai` now rate-limited (12/min per IP) with
message-count and character caps, since it is unauthenticated and calls a paid
API. `/api/contact` no longer writes the sender's name, email or message to the
Cloudflare logs. 10 tests, CI added.

**WONTFIX-YET**
- README lists GSAP; it isn't a dependency. The theme switcher persists a value
  nothing reads.

---

## Spendee — `Spendee`

Android + Spring Boot monorepo, actively in development.

Verified directly: 89 Kotlin files (~16,600 lines), 28 Java files (~2,300),
16 Gradle modules, 2 test classes (15 + 9 assertions).

**Fixed:** CI had been red since 2026-08-04. All three lint errors were the same
`FullBackupContent` violation - an `<exclude>` naming a path in a domain never
`<include>`d, which auto-backup already excludes by construction. Removed;
Android, static analysis and backend jobs all pass.

**Verified accurate**
- "`core:common` ... 15 tests pass" - exactly 15 `@Test` methods.
- "The JWT secret must decode to at least 32 bytes; the app refuses to start" -
  implemented in `JwtService`, covered by `shortSecretIsRejectedAtConstruction`.

**Discrepancies - reported, then fixed on approval**
- README said "14 modules"; `settings.gradle.kts` declares **16**
  (`:app`, 4 `:core:*`, 11 `:feature:*`). Corrected.
- `application.yml` defaults `SPENDEE_JWT_SECRET` to a committed value decoding
  to 51 bytes, so it passes the length guard. An unset variable in production
  would sign with a published secret - the same class of problem DevFlow had,
  which a length check alone does not catch.

---

## Setup and troubleshooting

### Where things live

```text
Kushwaha-Hemant/                  ← the profile repo (special: name == username)
├── README.md                     ← renders on github.com/Kushwaha-Hemant
├── assets/
│   ├── portrait-boot.webp        ← profile hero animation
│   ├── portrait-{square,wide,small}.{webp,gif,mp4}
│   ├── engineering-focus.svg
│   ├── developer-journey.svg
│   └── make_charts.py            ← regenerates both SVGs
├── ascii-portrait/               ← the portrait generator
└── .github/workflows/snake.yml   ← contribution snake, every 12h
```

### Regenerating

```bash
# charts
python assets/make_charts.py

# portrait — preview first, it takes ~1s
python ascii-portrait/generate.py --image path/to/photo.png --preview
python ascii-portrait/generate.py --image path/to/photo.png --only boot
```

### Committing

```bash
git add -A
git commit -m "Update profile"
git push origin main
```

The profile page updates within seconds. GitHub caches images aggressively
through its `camo` proxy — a changed asset at the same URL can take a few
minutes, or a hard refresh, to appear.

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Mermaid shows as a code block | Fence isn't exactly ```` ```mermaid ```` | Check the language tag; GitHub emits `lang="mermaid"` when correct |
| SVG doesn't render | External font/CSS reference | SVG in an `<img>` blocks all external requests — inline everything |
| Animation doesn't play | Rendered as a static frame | Confirm the file is animated: `python -c "from PIL import Image;print(Image.open('a.webp').n_frames)"` |
| Image is stale | `camo` cache | Hard refresh, or change the filename |
| Chart looks wrong in light mode | Theme-dependent colours | These charts are opaque dark cards by design; keep them self-contained |
| Contribution graph empty | Commit email not on the account | See the note in the profile README history — add and verify the email |
