# Ersatz-Bench design

Ersatz-Bench measures how often general language models, asked for a replacement for a discontinued electronic component, invent part numbers, recommend parts that are themselves inactive, or recommend parts that do not match on form, fit and function. It compares those rates with the Ersatz pipeline run on the same inputs.

Status markers used in this document: CITED (a source is given), PROPOSED (an Ersatz design choice with no external standard behind it), UNVERIFIED (a claim that could not be confirmed against a primary source).

## Purpose and claims

The benchmark supports three claims and no others.

1. A general model answering from memory produces part numbers that resolve to no product at any configured distributor, at a measurable rate.
2. When the part number does resolve, the part is itself not recommended for new designs, last time buy or obsolete, at a measurable rate.
3. When the part resolves and is active, it fails Ersatz form, fit or function checks at a measurable rate, and it matches the manufacturer's own recommended replacement at a measurable rate.

The benchmark does not claim that a model's answer is wrong for a particular board. It does not test models with tools or browsing. It does not rank models beyond the reported rates and their confidence intervals.
