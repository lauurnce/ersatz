# Progress

One prompt is one phase. Each phase ends with a Gate Report and waits for approval. Day numbers count build days.

- [x] E1: project brief, hard parts, assumptions, risks, questions
- [x] E2: repository setup: license, environment template, docs skeleton
- [x] E3: domain spec: docs/DOMAIN.md, docs/BENCHMARK_DESIGN.md, decision entries
- [x] E4: architecture and build plan: docs/ARCHITECTURE.md
- [x] E5 (Day 2): scaffold, tooling, CI
- [x] E6 (Day 3): ersatz.providers and ersatz.cache: Digi-Key adapter, synthetic fixtures, budgets, lookup command, make smoke. Parametric search waits for filter IDs (D-029)
- [x] E7 (Day 4): ersatz.model and ersatz.normalize: part model, units, packages, categories, lifecycle mapping, lookup --normalize
- [ ] E8 (Day 5): ersatz.datasheets and ersatz.llm: fetch, page text, LLM extraction, quote verification, validation rules, gold set of 10 datasheets, scripts/eval_extraction.py. Built; label spot-check and first live run pending
- [x] E9 (Day 6): ersatz.match: rule files, form, fit and lifecycle filters, function scoring, diff, candidate search, ersatz find. Live find pending Digi-Key keys
- [ ] E10 (Day 7): Mouser adapter, ersatz.resolve, lookup command
- [ ] E11 (Day 8): free; its planned scope (match) moved into E9
- [ ] E12 (Day 9): ersatz.candidates and ersatz.verify, full CLI
- [ ] E13 (Day 10): api: FastAPI, contract tests, deployment
- [ ] E14 (Day 11): ersatz.bench: dataset v1, harness, first results
- [ ] E15 (Day 12): web demo and landing page, README with results, v0.1 tag
- [ ] Stretch, after v0.1: mcp server
