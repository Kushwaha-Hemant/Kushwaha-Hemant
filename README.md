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
the application around it. MCA graduate based in Pune, India — open to backend
and AI engineering roles.

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

<table>
<tr>
<td width="50%" valign="top">

### 🔍 RAGForge

[![CI](https://github.com/Kushwaha-Hemant/RAGForge-Document_Search/actions/workflows/ci.yml/badge.svg)](https://github.com/Kushwaha-Hemant/RAGForge-Document_Search/actions/workflows/ci.yml)

**Self-hosted document intelligence.** Upload private documents, ask questions, get answers *with citations*. Multi-tenant from the ground up.

`Python` `FastAPI` `PostgreSQL` `pgvector` `Next.js` `Clerk`

<details>
<summary><b>Engineering detail</b></summary>

Retrieval is hybrid, not just vector search. A dense HNSW index and a Postgres
`tsvector`/GIN index are queried in parallel and fused with **weighted Reciprocal
Rank Fusion**, written generically over N ranked lists rather than hardcoded to
two, with optional cross-encoder reranking on top.

Embeddings are L2-normalised at write time so the index can use inner product
(`vector_ip_ops`) instead of cosine — cheaper distance, identical ranking.

</details>

**[Repository →](https://github.com/Kushwaha-Hemant/RAGForge-Document_Search)**

</td>
<td width="50%" valign="top">

### 🎙️ InterviewPilot AI

[![CI](https://github.com/Kushwaha-Hemant/Interviewpilot_AI/actions/workflows/ci.yml/badge.svg)](https://github.com/Kushwaha-Hemant/Interviewpilot_AI/actions/workflows/ci.yml)

**Adaptive mock interviewer.** Not a fixed question list — every answer is scored against a rubric, and a rule engine decides what happens next.

`Python` `FastAPI` `SQLAlchemy` `PostgreSQL` `OpenAI` `WebSockets`

<details>
<summary><b>Engineering detail</b></summary>

The LLM is an advisor, not an authority. `engine._enforce_rules()` takes the
model's suggested next action and **overrides it** when it violates interview
policy, so a hallucinated control decision cannot derail a session.

The provider is an ABC, so the OpenAI SDK is never imported outside its own
implementation. Question generation and the final coach report deliberately run
on different models.

</details>

**[Repository →](https://github.com/Kushwaha-Hemant/Interviewpilot_AI)**

</td>
</tr>
<tr>
<td width="50%" valign="top">

### ⚙️ DevFlow

[![CI](https://github.com/Kushwaha-Hemant/Devflow/actions/workflows/ci.yml/badge.svg)](https://github.com/Kushwaha-Hemant/Devflow/actions/workflows/ci.yml)

**Self-hosted CI/CD control plane.** Clones repos, runs build stages as real child processes, and drives the Docker Engine socket directly.

`TypeScript` `Express` `Prisma` `PostgreSQL` `Docker` `Socket.IO`

<details>
<summary><b>Engineering detail</b></summary>

The integrations are real rather than mocked, and the fiddly parts show it.
Without a TTY, Docker's Engine API prefixes every log line with an 8-byte
header, so the stream is **demultiplexed frame by frame**. Container CPU
percentage is computed the way `docker stats` actually computes it, scaling
`cpuDelta/systemDelta` by online CPU count.

Build logs carry a monotonic per-build sequence number, so a client that
reconnects mid-build resumes without gaps or duplicates.

</details>

**[Repository →](https://github.com/Kushwaha-Hemant/Devflow)**

</td>
<td width="50%" valign="top">

### 📄 ResumePilot

[![CI](https://github.com/Kushwaha-Hemant/ResumePilot/actions/workflows/ci.yml/badge.svg)](https://github.com/Kushwaha-Hemant/ResumePilot/actions/workflows/ci.yml)

**RAG resume analyser.** Scores a resume against a job description, surfaces skill gaps, and exports a PDF report.

`Python` `Streamlit` `LangChain` `ChromaDB` `pydantic`

<details>
<summary><b>Engineering detail</b></summary>

Each resume gets its **own ChromaDB collection**, so retrieval never bleeds
between candidates.

The model's reply passes through a three-tier JSON salvage — fenced block, then
raw parse, then repair — before being validated into a 20-field pydantic model,
because an LLM asked for JSON returns almost-JSON often enough to matter.

</details>

**[Repository →](https://github.com/Kushwaha-Hemant/ResumePilot)**

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🌌 DevVerse AI

[![CI](https://github.com/Kushwaha-Hemant/Devverse_AI/actions/workflows/ci.yml/badge.svg)](https://github.com/Kushwaha-Hemant/Devverse_AI/actions/workflows/ci.yml)

**Procedural 3D web experiment.** A workspace you explore instead of a page you scroll — built with no 3D assets at all.

`TypeScript` `Next.js 16` `React Three Fiber` `Cloudflare Workers`

<details>
<summary><b>Engineering detail</b></summary>

Every mesh and texture in the scene is **generated in code** — there is no
`.glb` file anywhere in the repository.

Quality tier is chosen by reading the actual GPU driver string from a throwaway
WebGL context. Every random value comes from a seeded PRNG, so the scene is
identical on every load, and the render loop stops entirely when the hero is
scrolled out of view.

</details>

**[Live ↗](https://devverse-ai.kushwaha-hemant.workers.dev)** · **[Repository →](https://github.com/Kushwaha-Hemant/Devverse_AI)**

</td>
<td width="50%" valign="top">

### 💸 Spendee

[![CI](https://github.com/Kushwaha-Hemant/Spendee/actions/workflows/ci.yml/badge.svg)](https://github.com/Kushwaha-Hemant/Spendee/actions/workflows/ci.yml)

**AI personal finance platform.** A monorepo pairing a native Android app with a Spring Boot backend.

`Kotlin` `Jetpack Compose` `Spring Boot` `Java` `Gradle`

<details>
<summary><b>Engineering detail</b></summary>

The Android side is split across **16 Gradle modules** with a shared design
system, built to practise modularisation at a scale where it starts to matter.

The JWT layer refuses to start on a secret shorter than 256 bits, or on the
development default outside a dev profile — a length check alone would not catch
the second case.

*Actively in development. The repository README separates what is built today
from what is still scaffolded.*

</details>

**[Repository →](https://github.com/Kushwaha-Hemant/Spendee)**

</td>
</tr>
</table>

<sub>Every badge above is live. All six repositories run tests, lint and build on
every push — click any badge for the run.</sub>

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
- Bringing Spendee's Android and Spring Boot halves to feature parity
- Deepening system design — the part that only shows up once something is running
- Open to backend and AI engineering roles

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
