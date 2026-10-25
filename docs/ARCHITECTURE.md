# Ersatz architecture

This document describes the system design for v0.1. Domain rules live in docs/DOMAIN.md, benchmark rules in docs/BENCHMARK_DESIGN.md, and every choice that changed from the first proposal has an entry in docs/DECISIONS.md.

## 1. System diagram

```mermaid
flowchart LR
  subgraph Providers
    DK[Digi-Key adapter]
    MO[Mouser adapter]
    NX[Nexar adapter, not in v0.1]
  end
  subgraph Core["ersatz library"]
    CACHE[(cache: SQLite local, Postgres deployed)]
    BUDGET[request and spend budgets]
    RES[resolve: exact MPN resolution]
    NORM[normalize: units, packages, categories, lifecycle]
    DS[datasheets: fetch, page text, LLM extraction, quote check, validation]
    MATCH[match: form, fit, function rules, diff]
    CAND[candidates: parametric search and ranking]
    VER[verify: verdicts with reasons and sources]
  end
  subgraph Surfaces
    CLI[CLI]
    API[FastAPI api]
    WEB[Next.js web demo and landing page]
    MCP[MCP server, stretch]
  end
  BENCH[bench: dataset, runners, scoring, reports]
  LLM[LLM provider for extraction]
  SUBJ[benchmark subject models]

  DK & MO & NX --> CACHE
  BUDGET --- DK & MO & LLM
  CACHE --> RES --> NORM
  NORM --> DS
  DS --> LLM
  DS --> MATCH
  NORM --> MATCH
  RES --> CAND --> MATCH
  MATCH --> VER
  CAND --> VER
  VER --> CLI & API
  API --> WEB
  API --> MCP
  BENCH --> SUBJ
  BENCH --> RES
  BENCH --> VER
```

The library is the product. CLI, API, web and MCP are thin surfaces over it. Language model extraction runs offline from the CLI or a batch job and stores its results; no API request waits on a language model call.
