<div align="center">

<img src="https://raw.githubusercontent.com/Kushwaha-Hemant/Kushwaha-Hemant/main/assets/portrait-boot.webp" width="420" alt="A terminal boots, then reconstructs a portrait of Hemant Kushwaha out of code characters" />

</div>

# Hi, I'm Hemant Kushwaha 👋

### Software Developer | AI & RAG Engineer

I build practical software systems where a language model has to survive contact
with real infrastructure — retrieval over private documents, agents that make
decisions mid-conversation, and the auth, storage, container and deployment
layers that make any of it usable by someone other than me.

Six systems below, each built end-to-end: the retrieval or build pipeline **and**
the application around it. Currently an MCA student in Pune, India, working
toward backend and AI engineering roles.

[![GitHub](https://img.shields.io/badge/GitHub-Kushwaha--Hemant-181717?style=flat-square&logo=github)](https://github.com/Kushwaha-Hemant)
[![Portfolio](https://img.shields.io/badge/Portfolio-hemantkushwaha.in-0891b2?style=flat-square&logo=googlechrome&logoColor=white)](https://hemantkushwaha.in)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-kushwaha--hemant-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/kushwaha-hemant/)
[![Email](https://img.shields.io/badge/Connect%40HemantKushwaha.in-EA4335?style=flat-square&logo=maildotru&logoColor=white)](mailto:Connect@HemantKushwaha.in)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Kotlin](https://img.shields.io/badge/Kotlin-7F52FF?style=flat-square&logo=kotlin&logoColor=white)

---

## Engineering Focus

<img src="https://raw.githubusercontent.com/Kushwaha-Hemant/Kushwaha-Hemant/main/assets/engineering-focus.svg" width="100%" alt="Engineering focus by number of shipped projects: AI/LLMs/RAG 3 of 6, Backend and APIs 4 of 6, Databases 4 of 6, Web and Frontend 4 of 6, Infra and DevOps 3 of 6, Android 1 of 6" />

---

## Selected Projects

### RAGForge — self-hosted document intelligence

Upload private documents, ask questions, get answers **with citations**.
Multi-tenant from the ground up: Clerk-authenticated, per-user isolation, and
per-project retrieval settings stored as data rather than config.

**Tech:** Python • FastAPI • PostgreSQL + pgvector • Next.js • Clerk • asyncpg

Retrieval is hybrid, not just vector search — a dense HNSW index and a Postgres
`tsvector`/GIN index are queried in parallel and fused with **weighted Reciprocal
Rank Fusion**, written generically over N ranked lists rather than hardcoded to
two, with optional cross-encoder reranking on top. Embeddings are L2-normalised
at write time so the index can use inner product (`vector_ip_ops`) instead of
cosine. Answers stream over SSE from either Claude or OpenAI behind one provider
interface.

[→ Repository](https://github.com/Kushwaha-Hemant/RAGForge-Document_Search)

### InterviewPilot AI — adaptive mock interviewer

Not a fixed question list. Every answer is scored against a structured rubric,
and a **server-side rule engine** — not the model — decides whether to probe
deeper, drop a hint, or move on.

**Tech:** Python • FastAPI • SQLAlchemy • PostgreSQL • OpenAI • WebSockets • Next.js

The interesting decision is treating the LLM as an advisor rather than an
authority: `engine._enforce_rules()` takes the model's suggested next action and
overrides it when it violates interview policy, so a hallucinated control
decision cannot derail a session. Question generation and the final coach report
run on deliberately different models, and the provider is an ABC so the OpenAI
SDK is never imported outside its implementation. Sessions stream over WebSocket
and end in a generated PDF report.

[→ Repository](https://github.com/Kushwaha-Hemant/Interviewpilot_AI)

### DevFlow — self-hosted CI/CD control plane

Clones GitHub repositories over the REST API, runs user-defined build stages as
real child processes, builds and deploys Docker images through the Engine
socket, and streams every log line to the browser.

**Tech:** TypeScript • Express • Prisma • PostgreSQL • Docker • Socket.IO • React

The integrations are real rather than mocked, and the fiddly parts show it:
Docker's Engine API prefixes every log line with an 8-byte header when there is
no TTY, so the log stream is **demultiplexed frame by frame**; container CPU
percentage is computed the way `docker stats` actually computes it, scaling
`cpuDelta/systemDelta` by online CPU count; and build logs carry a monotonic
per-build sequence number so a client that reconnects mid-build can resume
without gaps or duplicates.

[→ Repository](https://github.com/Kushwaha-Hemant/Devflow)

### ResumePilot — RAG resume analyser

Scores a resume against a job description, surfaces skill gaps, generates
interview questions, and exports a PDF report. The LLM provider is pluggable —
OpenAI or Gemini behind one pipeline.

**Tech:** Python • Streamlit • LangChain • ChromaDB • sentence-transformers • pydantic

Each resume gets its own ChromaDB collection so retrieval never bleeds between
candidates, and the model's reply is parsed through a **three-tier JSON salvage**
— fenced block, then raw parse, then repair — before being validated into a
20-field pydantic model, because an LLM asked for JSON returns almost-JSON often
enough to matter.

[→ Repository](https://github.com/Kushwaha-Hemant/ResumePilot)

### DevVerse AI — procedural 3D web experiment

A workspace you explore instead of a page you scroll. Click an object, the
camera flies to it, and it opens a real section of the site. Built to see how
far a browser scene can go with no 3D assets at all.

**Tech:** TypeScript • Next.js 16 • React Three Fiber • Tailwind v4 • Cloudflare Workers

Every mesh and texture in the scene is **generated procedurally in code** — there
is no `.glb` asset anywhere in the repo. Quality tier is chosen by reading the
actual GPU driver string from a throwaway WebGL context, every random value comes
from a seeded PRNG so the scene is identical on every load, and the render loop
stops entirely when the hero is scrolled out of view.

[Live](https://devverse-ai.kushwaha-hemant.workers.dev) · [→ Repository](https://github.com/Kushwaha-Hemant/Devverse_AI)

### Spendee — AI personal finance platform

A monorepo pairing a native Android app with a Spring Boot backend, built to
practise modularisation at a scale where it starts to matter.

**Tech:** Kotlin • Jetpack Compose • Spring Boot • Java • Gradle

The Android side is split across 16 Gradle modules with a shared design system.
*Actively in development — the repository README separates what is built today
from what is still scaffolded.*

[→ Repository](https://github.com/Kushwaha-Hemant/Spendee)

---

## How these systems fit together

Most of the projects above are the same shape: a client, an API, a model call,
a retrieval layer, and somewhere to put the vectors.

```mermaid
flowchart TD
    U["User"] --> FE["Frontend<br/>Next.js · React · Streamlit"]
    FE --> API["Backend API<br/>FastAPI · Express · Spring Boot"]
    API --> AUTH["Auth<br/>Clerk · JWT"]
    API --> LLM["LLM Layer<br/>provider interface"]
    LLM --> OAI["OpenAI / Claude / Gemini"]
    API --> RAG["Retrieval<br/>hybrid + rerank"]
    RAG --> VDB[("Vector Store<br/>pgvector · ChromaDB")]
    RAG --> REL[("Relational<br/>PostgreSQL")]
    API --> INF["Docker · CI/CD"]
    INF --> DEP["Deployment<br/>Cloudflare · self-hosted"]
```

<details>
<summary><b>The retrieval pipeline, in more detail</b></summary>

<br />

RAGForge's path from a raw file to a cited answer:

```mermaid
flowchart LR
    D["Documents<br/>PDF · DOCX · PPTX · URL"] --> P["Partition"]
    P --> C["Chunk"]
    C --> E["Embed<br/>MiniLM-L6-v2"]
    E --> V[("pgvector<br/>HNSW")]
    C --> T[("tsvector<br/>GIN")]

    Q["User query"] --> DR["Dense retrieve"]
    Q --> SR["Sparse retrieve"]
    V --> DR
    T --> SR
    DR --> F["Weighted RRF"]
    SR --> F
    F --> RR["Cross-encoder<br/>rerank"]
    RR --> L["LLM"]
    L --> A["Cited answer<br/>streamed over SSE"]
```

</details>

---

## Developer Journey

<img src="https://raw.githubusercontent.com/Kushwaha-Hemant/Kushwaha-Hemant/main/assets/developer-journey.svg" width="100%" alt="Timeline: Programming, Software Development, Backend and APIs, Databases, AI and ML, LLMs and RAG, Docker and CI/CD, Cloud and Production" />

---

## Currently

- Improving retrieval quality — chunking strategy, hybrid search weighting, and **evaluating** RAG output rather than eyeballing it
- Adding test coverage and CI across the projects above
- Bringing Spendee's Android and Spring Boot halves to feature parity
- Studying system design and DSA alongside the MCA coursework

<div align="center">

<br />

<sub>The portrait above is generated from a photograph by <a href="./ascii-portrait"><b>ascii-portrait</b></a> —<br />
a Python pipeline that maps brightness onto a glyph ramp ordered by <i>measured</i> ink coverage,<br />
then animates the characters assembling themselves into the image. <a href="./ascii-portrait/README.md">How it works →</a></sub>

<br /><br />

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Kushwaha-Hemant/Kushwaha-Hemant/output/snake-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/Kushwaha-Hemant/Kushwaha-Hemant/output/snake.svg" />
  <img alt="Contribution graph" src="https://raw.githubusercontent.com/Kushwaha-Hemant/Kushwaha-Hemant/output/snake.svg" />
</picture>

</div>
