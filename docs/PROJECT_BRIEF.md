# Ersatz project brief

Replacement parts you can verify.

## Problem

When an electronic component is discontinued (end of life, not recommended for new designs, obsolete), finding a form, fit and function replacement takes hours of datasheet comparison. People now ask chatbots. General language models without live data can return parts that are themselves discontinued, wrong specifications, or part numbers that look plausible and do not exist. Commercial tools cover part of this problem (Z2Data, Zenode Alts, Octopart, SiliconExpert), but there is no open, verifiable pipeline and no public measurement of how often chatbots get it wrong.

## Users

Primary: procurement buyers and hardware engineers dealing with discontinued components.

Secondary: anyone who asked a chatbot for a replacement part and needs to know whether the answer is real.

## v0.1 scope

Categories: LDO voltage regulators and op-amps.

1. Lookup. For a manufacturer part number (MPN), fetch normalized data (category, package, pin count, lifecycle status, key parameters, datasheet URL, stock) from public distributor APIs through provider adapters, with caching and recorded test fixtures.
2. Datasheet extraction. Download the datasheet PDF and extract package, pinout and key electrical specifications into a typed schema. Every value is cited to its page. Structured extraction by a language model, followed by deterministic unit parsing and validation.
3. Candidate search. Find alternates in the same category through parametric search.
4. Form, fit, function scoring. Form (package and footprint), fit (pin count and pinout mapping), function (category-specific parameter windows), plus lifecycle and availability. Every candidate gets an explainable diff.
5. Verify mode. Check any suggested replacement, for example one a chatbot gave. Verdicts: VERIFIED, PARTIAL, MISMATCH, NOT FOUND.
6. Ersatz-Bench. An open dataset of discontinued parts with manufacturer-published recommended replacements, and a harness that measures how often general language models invent part numbers, suggest inactive parts or miss form, fit and function, compared with the Ersatz pipeline.
7. Deliverables. A Python library and CLI, an API, a web demo and a landing page. Stretch goal: an MCP server, so AI assistants can call verify before suggesting a part.

## Non-goals for v0.1

- Categories beyond LDOs and op-amps.
- Scraping distributor or manufacturer sites. Lookup is API only. Benchmark notices are collected by hand with their URLs recorded.
- OCR of image-only datasheets. These are marked UNEXTRACTED.
- CAD footprint geometry comparison. Package equivalence comes from a cited alias table.
- Thermal, derating or simulation analysis.
- Bulk storage or mirroring of distributor catalogs. Pricing comparison.
- User accounts, saved projects, BOM upload.
- Any part number produced by a language model. The model extracts values from datasheets and is the subject under test in the benchmark, nothing else.
- Publishing to PyPI, a custom domain, or the MCP server, unless time remains.

## Hard rules

- Never show a part number unless it came from a provider response (live or recorded). No MPN is ever generated as free text.
- Every value shown traces to a source: a provider response or a datasheet page.
- Public data only. Demo examples and benchmark rows are vendor-neutral.
- Follow each provider's terms of service and rate limits. Keys live in .env (git-ignored), with a committed .env.example. The benchmark stores only part numbers, manufacturer names, recommended replacements and source URLs, never bulk distributor data.
- Not engineering sign-off: every result says that replacements must be validated by an engineer.
- Every domain rule (lifecycle definitions, package equivalences, parameter windows) comes from a cited source in docs/DOMAIN.md. Anything that cannot be verified is marked UNVERIFIED and never counts toward a VERIFIED verdict.

## Success criteria

- A verified pipeline that never shows a part that does not exist.
- Ersatz-Bench results in the README: a table of invented-part and mismatch rates per model against Ersatz, with the method and raw data published.
- A landing page and README that a component engineer would respect.

## The story behind the name

During World War I, the British naval blockade cut Germany off from imports such as Chilean saltpeter. Germany answered with Ersatzstoffe, substitute materials: nitrogen pulled from the air by the Haber-Bosch process replaced Chilean nitrate, paper-fabric drive belts replaced leather ones, and nettle fiber stood in for cotton. In English, "ersatz" came to mean a cheap imitation. Ersatz exists to make sure your substitute is not one.

## Stack

Python 3.12 library named ersatz, managed with uv, tested with pytest, with pydantic models. FastAPI for the API. Web: Next.js (App Router, TypeScript, Tailwind) on Vercel. The PyPI name ersatz is taken, so the distribution name is ersatz-parts and the import name stays ersatz.
