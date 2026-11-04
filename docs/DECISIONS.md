# Decision log

Each entry records the date, the decision, the reason and the alternatives considered. Newer entries go at the bottom.

## D-001 Stack

Date: 2026-11-09
Decision: Python 3.12 library named ersatz, managed with uv, tested with pytest, pydantic models. FastAPI for the API. Next.js (App Router, TypeScript, Tailwind) on Vercel for the web demo and landing page.
Reason: set by the project brief.
Alternatives considered: none at this stage.

## D-002 Providers for v0.1

Date: 2026-11-09
Decision: Digi-Key and Mouser adapters in v0.1. Nexar (Octopart) is added when a key exists. No manufacturer APIs for lookup.
Reason: both have documented public APIs with free keys, lifecycle status, parameters, datasheet URLs and stock.
Alternatives considered: Nexar first (key and quota timing uncertain), manufacturer APIs (approval required, narrow coverage), site scraping (against terms of service).

## D-003 Recorded fixtures in the public repository

Date: 2026-11-09
Decision: recorded provider responses may be committed as test fixtures, at most about 30 per provider, trimmed to the fields the models use, with keys scrubbed. The policy is stated in docs/PROVIDERS.md and revisited after each provider's terms are read in the adapter phase.
Reason: continuous integration must not depend on live network calls or secrets.
Alternatives considered: synthetic fixtures (do not match real response shapes), no fixtures (tests would need the network).

## D-004 Hosting

Date: 2026-11-09
Decision: FastAPI deployed to Vercel from this repository. Cache in Postgres from the Vercel marketplace. Demo examples precomputed. Live lookups rate limited per IP. Keys stay server side.
Reason: one platform for API and web, no separate infrastructure to run.
Alternatives considered: Fly.io with a SQLite volume, Render.

## D-005 Extraction model and benchmark subjects

Date: 2026-11-09
Decision: Claude Opus 5.5 (claude-opus-5-5) for datasheet extraction, behind an internal interface selected by a provider setting. Benchmark subjects: the current flagship chat model from each of OpenAI, Google and Anthropic, plus one open-weight model through a hosted API. Total language model budget cap for v0.1: 150 USD.
Reason: extraction accuracy matters more than cost at v0.1 volumes (estimated about 400 datasheets). The provider setting keeps the product free of a hard dependency on one vendor.
Alternatives considered: a smaller model for extraction (cheaper, accuracy to be measured first), local models (accuracy unmeasured), rules-only extraction (brittle on datasheet tables).

## D-006 Benchmark size and ground truth

Date: 2026-11-09
Decision: 50 discontinued parts per category, at least five manufacturers. Ground truth only from manufacturer end-of-life and product change notices that name a replacement. Distributor similar-parts lists are not ground truth.
Reason: manufacturer notices are the only external statement of a recommended replacement. Distributor lists mix manufacturer data with heuristics.
Alternatives considered: distributor substitute lists as truth, a larger dataset (cost and collection time).

## D-007 Verify mode display of parts that are not found

Date: 2026-11-09
Decision: a user-entered MPN that resolves to no provider record is shown verbatim, labeled "as entered", with the NOT FOUND verdict. It never appears in a suggestion list and is never autocompleted.
Reason: the user needs to see which string failed. Showing it as entered does not present it as a real part.
Alternatives considered: hiding the string (unusable), masking part of it (confusing).

## D-008 Package name and licenses

Date: 2026-11-09
Decision: distribution name ersatz-parts, import name ersatz. MIT for code, CC BY 4.0 for the benchmark data. v0.1 is tagged but not published to PyPI.
Reason: the PyPI name ersatz is taken. MIT and CC BY 4.0 are permissive and well understood.
Alternatives considered: other distribution names, Apache-2.0 for code, CC0 for data.

## D-009 Phase order

Date: 2026-11-09
Decision: fifteen prompts, one per phase, as listed in docs/PROGRESS.md: scaffold, adapters, lookup, extraction, form and fit, function rules, candidate search and verify, API, benchmark dataset, benchmark harness, web, MCP server (stretch), README and release.
Reason: each phase delivers one testable layer that the next phase builds on. The web and the README come last because they present results.
Alternatives considered: web first (nothing to demo), benchmark first (needs the pipeline).

## D-010 Verdict definitions

Date: 2026-11-09
Decision: VERIFIED needs form and fit DROP_IN, all function rules PASS, lifecycle ACTIVE, and stock at one provider or more. PARTIAL is any WARN, any UNKNOWN, a same-package rewire fit, or NRND. MISMATCH is any FAIL or an OBSOLETE candidate. NOT FOUND is a suggestion that resolves to no provider record. UNKNOWN never passes.
Reason: conservative verdicts. A missing value must not look like a match.
Alternatives considered: a numeric score only (hides the reasons), treating missing values as neutral (unsafe).

## D-011 Lifecycle enum

Date: 2026-11-09
Decision: lifecycle is normalized to ACTIVE, NRND, LAST_TIME_BUY, OBSOLETE, UNKNOWN. Each provider's status strings are mapped from recorded responses, and the mapping is cited in docs/DOMAIN.md.
Reason: providers use different words for the same states.
Alternatives considered: passing provider strings through (not comparable across providers).

## D-012 Datasheets are never committed

Date: 2026-11-09
Decision: datasheet PDFs are cached locally and never committed. The repository stores URL, SHA-256, revision string, fetch date and page numbers.
Reason: datasheets are copyrighted. Hash and revision keep citations reproducible if a PDF moves or changes.
Alternatives considered: committing PDFs (copyright), storing only URLs (citations break when a PDF is revised).

## D-013 Vendor-neutral examples

Date: 2026-11-09
Decision: showcase examples, demo data and benchmark rows are drawn from several manufacturers and are vendor-neutral. Provider candidate results are never filtered by manufacturer.
Reason: public data only. A benchmark should not favor or single out any vendor. Filtering candidates would hide real replacements.
Alternatives considered: single-vendor examples (simpler, less credible).

## D-014 Validation notice on every output

Date: 2026-11-09
Decision: every output surface (CLI, API JSON, web) carries the notice that replacements must be validated by an engineer, as a field in the result, not only as page text.
Reason: the notice must survive copy and paste and machine consumption.
Alternatives considered: page footer only.

## D-015 Lifecycle mapping and conflicts

Date: 2026-11-04
Decision: map every provider and manufacturer status to ACTIVE, NRND, LAST_TIME_BUY, OBSOLETE or UNKNOWN using the table in docs/DOMAIN.md section 1. "EOL" is never stored; it becomes LAST_TIME_BUY or OBSOLETE by last order date. "Discontinued at Digi-Key" maps to UNKNOWN. When providers disagree, verdicts use the status furthest along the sequence and every provider's value is shown.
Reason: manufacturers use different status sets, and EOL means different things at TI and Renesas. A distributor dropping a part is not a manufacturer discontinuance.
Alternatives considered: trusting one provider (hides disagreement), using the most optimistic status (unsafe).

## D-016 Package equivalence groups

Date: 2026-11-04
Decision: form is scored by package group (same lead count, pitch and span) plus maximum height, using the cited table in docs/DOMAIN.md section 2. Lower height is PASS, higher height is WARN. Ambiguous names without a body width, and all no-lead packages (DFN, WSON, QFN), score UNKNOWN.
Reason: aliases such as SOT-23-5, SOT-25 and SC-74A share a land pattern, while "TSSOP-8" names two different bodies and no-lead pads differ per drawing.
Alternatives considered: exact name match (misses true aliases), IPC-7351 names only (rarely present in provider data).

## D-017 One-direction function rules without numeric windows

Date: 2026-11-04
Decision: every function rule is a one-direction comparison ("equal or better"), following TI's drop-in definition "parametrically equivalent or better". No plus or minus tolerance is applied unless a rule row in docs/DOMAIN.md states one. Rules compare guaranteed min or max columns where available; typical-only comparisons and mismatched test conditions give WARN.
Reason: no manufacturer, distributor or standard publishes a numeric tolerance for "functionally equivalent". An invented window would be an uncited rule.
Alternatives considered: percentage windows per parameter (uncited), a weighted score (hides which rule failed).
