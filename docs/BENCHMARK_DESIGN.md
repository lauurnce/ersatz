# Ersatz-Bench design

Ersatz-Bench measures how often general language models, asked for a replacement for a discontinued electronic component, invent part numbers, recommend parts that are themselves inactive, or recommend parts that do not match on form, fit and function. It compares those rates with the Ersatz pipeline run on the same inputs.

Status markers used in this document: CITED (a source is given), PROPOSED (an Ersatz design choice with no external standard behind it), UNVERIFIED (a claim that could not be confirmed against a primary source).

## Purpose and claims

The benchmark supports three claims and no others.

1. A general model answering from memory produces part numbers that resolve to no product at any configured distributor, at a measurable rate.
2. When the part number does resolve, the part is itself not recommended for new designs, last time buy or obsolete, at a measurable rate.
3. When the part resolves and is active, it fails Ersatz form, fit or function checks at a measurable rate, and it matches the manufacturer's own recommended replacement at a measurable rate.

The benchmark does not claim that a model's answer is wrong for a particular board. It does not test models with tools or browsing. It does not rank models beyond the reported rates and their confidence intervals.

## Selection criteria (PROPOSED)

A part qualifies for the dataset when all of the following hold on the snapshot date.

1. Category: the manufacturer lists it as an LDO voltage regulator or an operational amplifier.
2. Discontinued: a public manufacturer notice or product page states that the part is discontinued, end of life, obsolete, last time buy or not recommended for new designs, and at least one configured distributor reports a lifecycle other than ACTIVE.
3. Named replacement: the same notice or product page names at least one recommended replacement by manufacturer part number. Rows without a named replacement go to a separate list and are not scored for top-k hit.
4. Replacement status: the named replacement is ACTIVE at one or more configured distributors on the snapshot date. If it is not, the row is kept, flagged truth_inactive, and excluded from the headline top-k metric.
5. Vendor spread: at least five manufacturers, no single manufacturer above 30 percent of rows. Showcase and benchmark rows are vendor-neutral.
6. Date spread: at least 20 percent of rows have a notice dated within the 24 months before the snapshot date, so stale training data is tested. Results are reported by notice date bucket.
7. Variety: for LDOs, a mix of fixed and adjustable outputs and of through-hole and surface mount packages. For op-amps, a mix of single, dual and quad parts.
8. Public data only: every row carries the public notice URL. No row relies on material that is not publicly reachable.

Each row stores: original MPN, manufacturer, category, replacement MPN or MPNs, relationship label, notice URL, notice date, last time buy date if stated, snapshot date, and a labeler note. Nothing else from any distributor response is stored.

## Size (PROPOSED)

Start at 50 rows (25 LDO, 25 op-amp). Target 200 rows (100 and 100).

Reason: with n = 50 and an observed rate near 30 percent, a 95 percent Wilson interval is about plus or minus 12 points. With n = 200 it is about plus or minus 6 points. 50 rows is enough to show whether invented-part rates are near zero or clearly not. 200 rows is needed to separate models whose rates differ by less than 10 points.

Runs are repeated measures of the same rows, so confidence intervals are computed over rows, not over runs. Per-row results across runs are combined by majority (see Metrics).

## Labeling protocol (PROPOSED)

Every ground truth pair carries two independent labels.

Label A, relationship per the manufacturer, read from the notice text only:
- drop_in: the manufacturer says drop-in, pin-to-pin, pin-compatible, or same pinout and function.
- functional: the manufacturer says similar, alternative, functional equivalent, or lists a different package or pinout.
- unspecified: the notice names a replacement with no relationship wording.

The exact phrase that justified the label is stored with the row.

Label B, relationship per Ersatz: the form and fit result from the pipeline (DROP_IN, SAME_PACKAGE_REWIRE, NO, UNKNOWN), produced once the pipeline exists. Label B never overwrites Label A. Disagreement between A and B is reported as its own number, because it measures both the manufacturer's wording and Ersatz.

This is a single-labeler project. Consistency is measured by relabeling a random 20 percent of rows at least seven days after the first pass and reporting agreement. Rows whose label changes are read a third time, and the final label and reason are stored.

## Metrics (PROPOSED)

For each row, model and run, the model's free text response is scanned for MPN-like tokens (see Prompting and resolution protocol). Each token is resolved against the configured distributors. The primary suggestion is the first token in the response. Resolution gives one of: FOUND with lifecycle ACTIVE, NRND, LAST_TIME_BUY or OBSOLETE; or NOT_FOUND. A NOT_FOUND token is audited by hand before it counts as invented. The audited state is INVENTED or OBSCURE.

Per response:
- has_mpn: at least one token was found in the text.
- invented: the primary suggestion is INVENTED after audit.
- inactive: the primary suggestion is FOUND and its lifecycle is NRND, LAST_TIME_BUY or OBSOLETE.
- mismatch: the primary suggestion is FOUND and ACTIVE and Ersatz verify returns MISMATCH. PARTIAL is counted separately.
- hit@k: any of the first k tokens resolves to the same base part and package as a ground truth replacement, for k of 1 and 3. A base match in a different package is counted separately as hit_base@k.

Per row and model, the three runs are combined by majority for each boolean.

Rates per model, over rows:
- invented-MPN rate: invented rows divided by rows with has_mpn
- inactive-part rate: inactive rows divided by rows with a FOUND primary
- FFF mismatch rate: mismatch rows divided by rows with a FOUND and ACTIVE primary
- top-1 hit and top-3 hit: hit rows divided by rows with a usable truth (replacement ACTIVE)
- abstain rate: rows without has_mpn divided by all rows

Each rate carries a 95 percent Wilson interval and its denominator. Rates are also reported per category and per notice date bucket.

The Ersatz baseline is the pipeline's top candidate for each row, scored with the same definitions. Its invented rate is zero by construction, because candidates come only from provider responses. The honest comparison is on inactive rate, mismatch rate and top-k hit.

## Prompting and resolution protocol (PROPOSED)

Prompt. One fixed user message, no system prompt, no tools, no browsing:

    The part {mpn} from {manufacturer} is discontinued. Recommend one replacement part. Put the replacement's manufacturer part number on the first line by itself, then one sentence on why.

Sampling. Temperature 0 where the API accepts a temperature parameter, the API default where it does not. The exact request body is stored either way. Three runs per row and model. Maximum output 300 tokens.

Recorded per call: model identifier string exactly as sent, API version header if any, request timestamp in UTC, full request body, full response body, the provider's response identifier if given, and the SHA-256 of the response body.

MPN token extraction. Tokens matching a part number pattern (letters and digits, at least four characters, at least one digit, optional dash, slash or dot) are taken in order of appearance, first line first. The regex and its version are stored with the run.

Resolution. Each token is looked up at every configured distributor by exact part number and by prefix. A token resolves when a distributor returns a product whose manufacturer part number equals the token, or starts with it followed only by a known packaging suffix. Resolution results store only token, resolved MPN, manufacturer, lifecycle, distributor name and date.

Audit of NOT_FOUND. Every NOT_FOUND primary token is checked by hand on the manufacturer's public site and in a web search. If a product page exists, the token is OBSCURE and is excluded from the invented count. If none exists, it is INVENTED. The audit result and the URL checked are stored.

## Cost estimate (PROPOSED, list prices read on 2026-11-09)

Subject calls. About 300 input and 300 output tokens per call. At 50 rows, 5 models and 3 runs there are 150 calls per model. At the highest list price among the planned subjects (4 USD per million input tokens, 20 USD per million output tokens) that is about 1 USD per model and about 5 USD in total. At 200 rows it is about 22 USD in total. Vendor prices differ; the harness records actual token usage.

Resolution calls. Up to 750 tokens at 50 rows, fewer after de-duplication, limited by distributor quotas rather than dollars. At a 1,000 call per day quota this fits in one day at 50 rows and about a week at 200 rows.

Ersatz baseline. Each row needs the original datasheet and about three candidate datasheets extracted. At about 0.20 USD per datasheet with the default extraction model this is about 40 USD at 50 rows and about 160 USD at 200 rows. The 200 row figure alone exceeds the v0.1 budget cap of 150 USD, so the 200 row target uses the Batch API at half price and reuses cached extractions across rows.

Audit time. About five minutes per NOT_FOUND token by hand.

## Reproducibility (PROPOSED)

- Dataset: bench/dataset/v1/rows.csv with the fields listed under Selection criteria, plus a CHANGELOG. Versioned. CC BY 4.0.
- Runs: bench/runs/<date>/<model>/responses.jsonl, one line per call with the recorded fields, plus manifest.json listing every file with its SHA-256, the dataset version, the harness git commit, the regex version and the provider snapshot date.
- Resolution snapshot: bench/runs/<date>/resolution.jsonl with token, resolved MPN, manufacturer, lifecycle, distributor and date. No prices, stock counts or parameter data.
- Audit: bench/runs/<date>/audit.csv with token, verdict, URL checked and date.
- Results: bench/runs/<date>/results.md generated by the harness from the files above. The README table is copied from this file and names the run date.
- One command regenerates results from stored responses without any API call.
