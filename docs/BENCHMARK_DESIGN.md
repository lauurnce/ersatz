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
