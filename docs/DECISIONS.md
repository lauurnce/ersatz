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

## D-018 Provider set for v0.1

Date: 2026-11-04
Decision: Digi-Key is the primary provider (lookup, lifecycle, parametric search). Mouser is secondary (lookup, lifecycle, stock), with its terms read in full before its adapter is written. Nexar is not used in v0.1. This refines D-002.
Reason: Digi-Key is the only free API with parametric filtering. Mouser has no attribute filters. Nexar's free allowance is 100 to 1,000 parts in total, storage is limited to 24 hours, and its terms bar competing products.
Alternatives considered: Nexar as primary (allowance and terms), Mouser only (no candidate search).

## D-019 Synthetic provider fixtures

Date: 2026-11-04
Decision: supersedes D-003. No recorded provider response is committed. Test fixtures are synthetic: they follow each provider's published schema, use invented values and part numbers that start with TEST-, and are marked as synthetic. Real recordings live only in the local, git-ignored cache and are used by an opt-in local test run.
Reason: Digi-Key §3.2(iv) bars disclosing DigiKey Data to third parties and §5.1(e) bars building a database from it; Nexar §1.2(vi) bars storing data beyond 24 hours; Mouser's terms are unread. A public repository is a disclosure under each.
Alternatives considered: small trimmed recordings (still a disclosure), no fixtures (tests would need the network and keys).

## D-020 PDF library

Date: 2026-11-08
Decision: pdfplumber (MIT) for page text, coordinates and tables, pypdfium2 (BSD-3-Clause and Apache-2.0) for rendering, Camelot (MIT) as a fallback for hard tables. PyMuPDF and marker are not used. OCR is out of v0.1.
Reason: PyMuPDF is AGPL-3.0 or commercial, and AGPL obligations reach a hosted API. marker's model weights carry a revenue-limited license. pdfplumber gives character coordinates, which quote verification needs.
Alternatives considered: PyMuPDF with a commercial license (cost), docling (heavier install, kept as a later option).

## D-021 Extraction with local quote verification

Date: 2026-11-08
Decision: extraction uses structured outputs with a schema in which every value carries a page number and a verbatim quote. Ersatz then verifies each quote against that page's pdfplumber text and drops any value whose quote or value string is not found. API citations are not used.
Reason: the API does not allow citations and structured outputs in one request. Local verification gives the same guarantee, works with any model provider, and is testable without network access.
Alternatives considered: citations with line-per-field text output parsed by regex (fragile), two requests per datasheet (double cost).

## D-022 Benchmark labels from manufacturer wording

Date: 2026-11-08
Decision: Label A in Ersatz-Bench is mapped from the manufacturer's own relationship wording (TI cross-reference types, Renesas and ROHM notice columns) into drop_in, pin_compatible, functional or unspecified. Reactivated parts are removed. Distributor-hosted copies of notices are allowed with the notice number recorded.
Reason: several manufacturers already grade their replacements, which removes most labeler judgment. Reactivations would otherwise count a valid original as discontinued.
Alternatives considered: labeling every row by hand from scratch (less reproducible), using distributor substitute types (not manufacturer truth).

## D-023 Added modules: resolve, candidates, budget, rules

Date: 2026-11-08
Decision: add ersatz.resolve, ersatz.candidates and ersatz.budget to the proposed layout, and keep rule tables as data files in ersatz/rules with IDs that match docs/DOMAIN.md.
Reason: resolution is shared by verify, candidates and the benchmark; candidate search had no home; budgets are shared by providers, extraction and the benchmark; rules as data keep each rule traceable to its cited row.
Alternatives considered: resolution inside providers (duplicated per adapter), rules as Python code (harder to audit against the document).

## D-024 Source on every value

Date: 2026-11-08
Decision: Source is a model of its own and Sourced[T] wraps MPN, manufacturer, lifecycle, stock and datasheet URL; Parameter carries a Source directly. A Part cannot be built without a provider Source on its MPN, and the API serializer rejects any value without a Source.
Reason: the hard rule that every shown value traces to a source has to hold for all fields, not only parameters. Enforcing it in types and the serializer makes it testable.
Alternatives considered: a source field on Parameter only (lifecycle and MPN untraced), a separate provenance log (can drift from the data).

## D-025 Cache protocol with two backends

Date: 2026-11-08
Decision: Cache is a protocol with SQLite (local) and Postgres (deployed) implementations. Provider data expires after 24 hours; datasheet files and extraction results are keyed by PDF hash and extractor version and do not expire.
Reason: serverless functions have no persistent disk. A 24 hour limit is the strictest provider term found and keeps the cache from becoming a database of provider data.
Alternatives considered: SQLite only (does not work deployed), per-provider time-to-live (more configuration for no benefit in v0.1).

## D-026 No LLM call in an API request

Date: 2026-11-08
Decision: datasheet extraction runs from the CLI or a batch job and stores results. API requests read stored results; when none exist, function rules return UNKNOWN and the response says extraction is pending.
Reason: extraction can take longer than a function's request limit, costs money per call, and would let anonymous traffic spend the LLM budget.
Alternatives considered: extraction on demand with a queue (more infrastructure than v0.1 needs).

## D-027 Strict typing scope and secret scanning

Date: 2026-11-08
Decision: mypy strict on ersatz.model, ersatz.normalize, ersatz.match and ersatz.verify. gitleaks runs as a pre-commit hook and in CI. CI tests block network access.
Reason: verify produces the verdict a user acts on, so it joins the strict set. A secret scanner and a network block back the fixture policy in D-019.
Alternatives considered: strict everywhere (slows adapter work against loosely typed provider schemas), detect-secrets (gitleaks covers more key formats out of the box).

## D-028 One CI workflow for the scaffold

Date: 2026-11-08
Decision: a single .github/workflows/ci.yml with four jobs (python, web, hooks, secrets) replaces the three workflow files planned in ARCHITECTURE.md section 6. Every action is pinned to a commit SHA with the version in a comment. The web job runs on every push for now.
Reason: one file is easier to read while the project is small, and the scaffold prompt asked for ci.yml. Path filters for the web job can be added when web build time matters.
Alternatives considered: python.yml, web.yml and secrets.yml as planned (more files for the same checks), tags instead of SHAs (a moved tag would change what runs).

## D-029 Digi-Key adapter first, parametric search later

Date: 2026-11-08
Decision: the provider phase ships the Digi-Key adapter with product details and keyword search. Mouser waits until its terms are read. Parametric search raises NotSupported until Digi-Key filter IDs are mapped from local recordings. Committed fixtures stay synthetic, and recordings are scrubbed and kept local.
Reason: D-018 makes Mouser conditional on its terms. Filter IDs appear only in live responses, so guessing them would make untested code. D-019 bars committing recorded responses.
Alternatives considered: a Mouser adapter from its public docs (risks building against terms not yet read), hard-coded filter IDs (unverified), committed recordings with values replaced (still derived from provider data).

## D-030 Unit parsing and package matching never guess

Date: 2026-11-09
Decision: parse_value returns min, typ and max in SI base units with conditions keyed by quantity (I, V, f, T). It rejects text it cannot read in full: a value with a trailing tolerance such as "1.25 V ±1%", a backwards range, conflicting qualifiers, a bare number for a dimensional parameter, and any unit spelling outside a per-unit allow-list. package_group matches comma-separated provider names as alternatives and returns UNKNOWN with a reason for unknown, ambiguous, conflicting and no-lead names, and for a pin count or body width that does not fit the group. Unparsed provider strings stay on the Part verbatim with their source.
Reason: a wrong value or footprint produces a wrong verdict, while UNKNOWN only lowers it to PARTIAL (D-017). Case matters in units ("MV" is megavolt), so spellings are allow-listed before pint sees them (DOMAIN.md section 6).
Alternatives considered: fuzzy package matching (would guess between groups such as SOT23-5 and SOT23-6), reading tolerance as a range around the value (correct for some datasheets, wrong for others), passing raw strings to pint (accepts megavolt and years).

## D-031 Send page text, not page images

Date: 2026-11-10
Decision: extraction sends the pdfplumber text of the selected pages, each under a "=== PAGE n ===" marker, instead of PDF pages or images. The model sees exactly the text that quote verification later reads. The client interface takes a system prompt, a user message and a JSON schema, so any provider with structured outputs fits. This refines the LLMClient sketch in docs/ARCHITECTURE.md, which took PDF bytes.
Reason: a quote copied from the same text can be checked character for character after whitespace collapsing. Text costs a few thousand tokens per page less than a page image. Tables whose values sit on separate lines from their conditions remain hard; the gold set measures how hard.
Alternatives considered: PDF document input (quotes would come from the model's own reading of the page and often fail to match the text layer; higher cost), page images plus text (double cost for a gain the evaluation has not shown yet).

## D-032 Extraction gold set v1

Date: 2026-11-10
Decision: ten datasheets, five LDOs and five op-amps, from Texas Instruments, Microchip, Diodes, ROHM and Nisshinbo, labeled by hand in eval/extraction/gold/ with page references and DRAFT status until three labels are spot-checked (docs/EXTRACTION_REVIEW.md). Labels cover parameters, packages, pins and features, 188 in total. PDFs are referenced by URL and SHA-256 and never committed. Field accuracy and citation accuracy are reported per field type in docs/EXTRACTION_EVAL.md, failures included. A value matches within 1 percent.
Reason: the prompt for this phase asked for ten datasheets. Two vendors whose sites refused automated downloads were replaced rather than worked around. The architecture planned 15 per category; that size is kept as the target for a later gold set.
Alternatives considered: labels taken from distributor parametric data (not the datasheet, and not citable to a page), a larger set before the first run (labeling cost before the format was tested).

## D-033 Drop or mark LOW, never repair

Date: 2026-11-10
Decision: after quote verification, a value whose unit does not parse or whose columns are out of order is dropped. A value that breaks a plausibility window or a cross-field rule is kept and marked LOW confidence with the rule ID. Validation never changes a number to make a rule pass. The only rewrites are the sign conventions listed in docs/DOMAIN.md section 6.
Reason: a dropped value becomes UNKNOWN downstream, which is safe. A LOW value stays visible to the engineer with its reason. A repaired value would be an invented one.
Alternatives considered: dropping every LOW value (loses correct values on multi-variant datasheets where a rule misfires), a numeric confidence score (no calibration data yet).

## D-034 Synthetic datasheet page text in tests

Date: 2026-11-10
Decision: tests use small PDFs generated in the suite and synthetic page text stored under tests/fixtures/datasheets/, with TEST- part numbers and invented values. Real datasheet text stays in the local cache. The live run uses the real PDFs.
Reason: same reasoning as D-019. Datasheet text is the manufacturer's copyrighted material and does not belong in a public repository.
Alternatives considered: trimmed excerpts of real datasheets (redistribution), no stored text (tests would miss the layout of real tables).

## D-035 Function score weights

Date: 2026-10-17
Decision: function rules carry weights 3, 2 and 1 (docs/DOMAIN.md section 6a). The score is the weighted share of points over rules that apply, with PASS 1, WARN 0.5, FAIL and UNKNOWN 0. Candidates are ranked by fit, then by the number of FAIL results, then by score. Every rule result stays visible in the diff.
Reason: a single number is needed to order candidates, but a weighted score alone would hide a failed rule behind many passes (the concern in D-017). Counting FAIL results before the score keeps that from happening.
Alternatives considered: equal weights (output voltage would count the same as quiescent current), a pure lexicographic order by rule ID (no way to tell two clean candidates apart), learned weights (no labeled data).

## D-036 Keyword search until parametric search is mapped

Date: 2026-10-17
Decision: candidate search asks each provider for parametric search with the original's category, footprint group and key values. When a provider raises NotSupported, as Digi-Key does until its filter IDs are mapped (D-029), search falls back to a keyword query built from the original's own values, such as "3.3V LDO voltage regulator SOT23-5". The hard filters do the narrowing. Results are merged across providers, deduplicated by manufacturer and part number, and capped at 25 by default.
Reason: keyword search is the one search Digi-Key offers today. The query uses only values from the original's provider record, so no part number or value is invented.
Alternatives considered: waiting for parametric search before building matching (blocks the phase), candidate lists from distributor "similar parts" (not allowed as ground truth and not an Ersatz judgment).

## D-037 Find mode lists ACTIVE candidates only

Date: 2026-10-17
Decision: in find mode, a candidate that is not ACTIVE is excluded and listed with its lifecycle status. Verify mode keeps decision 9: an NRND suggestion is PARTIAL and an OBSOLETE one is MISMATCH.
Reason: the phase asks for an active-lifecycle hard filter. A replacement list that offers NRND parts recreates the problem the user came to solve. Verify mode answers a different question about a part the user already named.
Alternatives considered: NRND kept with a penalty (still offers a part on its way out), lifecycle as a soft rule (lets stock outweigh status).

## D-038 Resolution order and suffix rules

Date: 2026-10-17
Decision: ersatz.resolve cleans surrounding markup, looks the part number up exactly, then tries the suffix rules in rules/suffixes.yaml (a Digi-Key packaging code removed, or a manufacturer packaging suffix found by keyword search from that manufacturer only), and otherwise returns NOT FOUND. All three suffix rules are UNVERIFIED for now, so a part found through one is never VERIFIED.
Reason: users paste distributor part numbers and base part numbers without a packaging suffix, and both name a real part. Listing each rule keeps the step reviewable; everything else stays NOT FOUND, so an invented part number can never resolve to a real one.
Alternatives considered: fuzzy matching (the failure mode Ersatz exists to catch), no normalization at all (common inputs such as cut-tape part numbers would read as invented).

## D-039 One exit code table for every command

Date: 2026-10-17
Decision: 0 success or VERIFIED, 1 PARTIAL, 2 usage, configuration or provider error, 3 MISMATCH, 4 NOT FOUND. Commands that report several items exit with the worst one (NOT FOUND, then MISMATCH, then PARTIAL). Every command has --json, and the JSON always carries the notice.
Reason: scripts and CI jobs can act on the verdict without parsing text. Code 2 matches Click's usage error code.
Alternatives considered: 0 for any completed run (loses the verdict), separate codes per command (harder to remember).

## D-040 Synthetic catalog for CLI smoke tests

Date: 2026-10-17
Decision: CLI smoke tests run the real Digi-Key adapter against a synthetic catalog (tests/fixtures/digikey/catalog_ldo50.json) served by a routing mock transport. The "recorded fixtures" in the phase prompt are these synthetic, schema-shaped files, following D-019.
Reason: real recordings cannot be committed (D-019). Going through the adapter still tests request paths, parsing, caching and normalization.
Alternatives considered: faking the provider protocol in CLI tests (skips the adapter), local recordings in CI (not allowed, and CI has no keys).
