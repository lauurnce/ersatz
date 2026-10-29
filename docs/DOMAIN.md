# Ersatz domain rules

This document holds every domain rule Ersatz applies: lifecycle definitions, form, fit and function definitions, package equivalence groups, pin vocabularies and parameter rules for each category, provider facts, and extraction rules. Code reads its rule tables from files that mirror this document, and every rule row names a source here.

Status markers:
- CITED: a primary or clearly attributed source is given, with a short quote.
- PROPOSED: an Ersatz design choice with no external standard behind it. Each one has an entry in docs/DECISIONS.md.
- UNVERIFIED: the claim could not be confirmed against a primary source. An UNVERIFIED rule never contributes to a VERIFIED verdict.

Quotes are kept short and verbatim. Where a primary site refused automated retrieval, the source used instead is named.

## 1. Lifecycle and notices

### Manufacturer status definitions (CITED)

Texas Instruments uses five statuses ([L1]):
- PREVIEW: "This product is not in production, although prototype or experimental parts are available for purchase."
- ACTIVE: "This product has been released to the market and is available for purchase."
- NRND: "This product is available for existing designs." and "for new designs, we recommend considering an alternate."
- LAST TIME BUY: "This product is in the process of being discontinued."
- OBSOLETE: "This product is no longer in production."

Renesas uses Under Development, Mass Production, Non-Promotion (NRND), EOL-notified and EOLed ([L2]). EOL-notified means "Discontinuation of production has been announced for these products". Final orders "will be accepted for 6 to 12 months" from notification, and notification is made "in accordance with JEDEC (J-STD-048)".

ROHM uses Under Development, Recommended, Active, Not Recommended for New Designs, Last Time Buy and Obsolete ([L3]). It separates Recommended ("Recommended for new designs") from Active ("Products currently being supplied"). Last Time Buy means "Products discontinuation (EOL) has been announced."

STMicroelectronics: an ST employee states that an end of life product page is marked "NRND" or "OBSOLETE", "otherwise it is "ACTIVE"" ([L4], forum answer). An official ST definitions page could not be retrieved: UNVERIFIED.

Microchip, Nexperia, Diodes Incorporated and onsemi status glossaries could not be retrieved: UNVERIFIED. Their discontinuance notices were read and are covered below.

"End of life" is not one status. TI has no EOL status; LAST TIME BUY is the step before OBSOLETE. Renesas uses EOL for both the notified and the completed state. Ersatz therefore never stores "EOL" as a lifecycle value. It maps EOL to LAST_TIME_BUY while a last order date is in the future and to OBSOLETE after it (PROPOSED).

### Notices and standards (CITED)

Two joint standards govern notices. J-STD-046 covers product and process change notices (PCN). J-STD-048 covers product discontinuance notices. Both have A revisions published on 2025-11-01 that supersede the 2016 and 2014 editions ([L5], [L6], standards reseller listings). JEDEC's own site refused retrieval.

The predecessor JESD48C (December 2011) is free from JEDEC and was read in full from a mirrored copy ([L7]). It requires "a minimum of 6 months from the notice to place final orders, and 12 months from the notice for final shipments". Minimum notice content is "the effective date for placing last purchase orders, and (b) the affected supplier part numbers". It also asks suppliers to help "locate an alternate source". Whether J-STD-048A keeps the 6 and 12 month windows is UNVERIFIED.

Observed manufacturer practice matches that baseline: onsemi allows six months to order and twelve to ship ([L8]); Nexperia allows six months for multiple-source parts and nine for sole-source parts ([L9]); Diodes Incorporated states a last order date and a last ship date six months apart ([L10]).

A notice is not always issued. Z2Data reports that 323,286 of 621,909 parts that went obsolete in 2025 (52 percent) had no product change notification ([L11]). Lifecycle data from distributors is therefore the primary signal, and notices are supporting evidence.

### Distributor lifecycle fields

| Provider | Field | Values | Status |
|---|---|---|---|
| Digi-Key API v4 | Product.ProductStatus.Status (string), plus EndOfLife, Discontinued, DateLastBuyChance | Forum lists Active, Discontinued at Digi-Key, Not Recommended for New Design, Last Time Buy, Obsolete ([L12], [L13]) | Field CITED from the OpenAPI file. Exact API strings UNVERIFIED |
| Mouser Search API | MouserPart.LifecycleStatus (string), IsDiscontinued (string) | None documented ([L14]) | Values UNVERIFIED |
| Nexar | spec attribute lifecyclestatus (homogenized) and manufacturerlifecyclestatus (raw) | EOL, NRND, New, Obsolete, Production ([L15]) | CITED |

"Discontinued at Digi-Key" means the distributor stopped stocking the part, not that the manufacturer stopped making it ([L13]). It maps to UNKNOWN, never to OBSOLETE.

### Ersatz lifecycle enum and mapping (PROPOSED)

| Ersatz value | Meaning | Mapped from |
|---|---|---|
| ACTIVE | in production, orderable | TI ACTIVE; Renesas Mass Production; ROHM Recommended or Active; Nexar Production or New; Digi-Key Active |
| NRND | orderable, not for new designs | TI NRND; Renesas Non-Promotion; ROHM NRND; Nexar NRND; Digi-Key Not Recommended for New Design |
| LAST_TIME_BUY | discontinuance announced, last order date not passed | TI LAST TIME BUY; Renesas EOL-notified; ROHM Last Time Buy; Nexar EOL with a future last buy date; Digi-Key Last Time Buy |
| OBSOLETE | no longer produced | TI OBSOLETE; Renesas EOLed; ROHM Obsolete; Nexar Obsolete; Digi-Key Obsolete |
| UNKNOWN | anything else | Preview and Under Development; Digi-Key Discontinued at Digi-Key; any unmapped string |

The mapping table is confirmed against real recorded responses in the provider phase, and any string seen there that is not in this table maps to UNKNOWN until it is added here with a source. When providers disagree, Ersatz reports every provider's value and uses the status furthest along the sequence ACTIVE, NRND, LAST_TIME_BUY, OBSOLETE for verdicts.

### Sources

- [L1] Texas Instruments, Product life cycle: https://www.ti.com/quality-reliability/quality/product-life-cycle.html
- [L2] Renesas, Supply policy and product lifecycle: https://www.renesas.com/en/support/supply-policy-product-lifecycle
- [L3] ROHM, Supply status: https://www.rohm.com/supply_status
- [L4] ST Community, How to check product end of life: https://community.st.com/t5/mems-sensors/how-to-check-product-end-of-life/td-p/166870
- [L5] J-STD-046A:2025 listing: https://shop.standards.ie/en-ie/standards/jedec-j-std-046a-2025-1162212_saig_jedec_jedec_3780931
- [L6] J-STD-048A:2025 listing: https://shop.standards.ie/en-ie/standards/jedec-j-std-048a-2025-1299320_saig_jedec_jedec_3780934/
- [L7] JESD48C, Product Discontinuance (mirror): https://www.infineon.com/assets/row/public/documents/support/jesd48c.pdf
- [L8] onsemi Product Discontinuance PD24192Z: https://www.onsemi.com/pcn/public/final-document/IBqfENanlquHHOIFixWeUQ
- [L9] Nexperia Discontinuation Notification CN-202410011DN (distributor-hosted copy): https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/6522/CN-202410011DN.pdf
- [L10] Diodes Incorporated PCN 2740 (distributor-hosted copy): https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/7202/Diodes_PCN_2740_EOL.pdf
- [L11] Z2Data, Components are going EOL without product change notifications: https://www.z2data.com/insights/components-are-going-eol-without-product-change-notifications-at-alarming-rates
- [L12] Digi-Key Product Information v4 OpenAPI file: https://developer.digikey.com/node/2360/oas-download
- [L13] Digi-Key TechForum, Part status obsolescence process explained: https://forum.digikey.com/t/part-status-obsolescence-process-explained/10614
- [L14] Mouser Search API Swagger V2: https://api.mouser.com/api/docs/V2
- [L15] Nexar, Supply lifecycle information for parts: https://support.nexar.com/support/solutions/articles/101000434626-supply-lifecycle-information-for-parts

## 2. Form, fit, function and packages

### Definitions (CITED)

US regulation 22 CFR 120.42 defines the three terms ([F1]):
- Form: "defined by its configuration (including the geometrically measured configuration), material, and material properties".
- Fit: "defined by its ability to physically interface or connect with or become an integral part of another commodity."
- Function: "the action or actions it is designed to perform."

MIL-HDBK-61A (Configuration Management Guidance, 2001) uses the same terms; its text could not be retrieved: UNVERIFIED.

Ersatz applies them to components as follows (PROPOSED):
- Form: package outline group and maximum seated height.
- Fit: pin count and the function of every pin, including the tab or exposed pad.
- Function: the category parameter rules in sections 3 and 4.

### Relationship classes used in industry (CITED)

Texas Instruments defines four cross-reference types ([F2]):
- "Drop-in replacement: Same function, same pinout, parametrically equivalent or better to the compared device."
- "Pin-for-pin replacement: Same function, same pinout but different parameters to the compared device."
- "Same functionality: Same function, but different pinout and parameters to the compared device."
- "Similar functionality: Similar function, pinout and or parameters to the compared device."

Digi-Key defines four substitute types ([F3]): Direct ("a high likelihood of form, fit, and function match"), Parametric Equivalent ("There may be features or pinouts that do not match"), MFR Recommended ("suggested by the manufacturer as a replacement") and Similar.

SiliconExpert grades crosses from A ("pin to pin drop in replacement with exact electrical features") through B, C and D to F, S and SF, as documented by Altium ([F4]).

No source defines a numeric tolerance for "equivalent". TI's "parametrically equivalent or better" is the rule Ersatz adopts: every function rule is a one-direction comparison, not a plus or minus window (PROPOSED, see D-017).

Ersatz relationship and verdict mapping (PROPOSED):

| Form | Fit | Function | Ersatz verdict | Nearest TI type |
|---|---|---|---|---|
| same group, height not greater | DROP_IN | all PASS | VERIFIED (if ACTIVE and stocked) | Drop-in |
| same group | DROP_IN | any WARN | PARTIAL | Pin-for-pin |
| same group | SAME_PACKAGE_REWIRE | any | PARTIAL | Same functionality |
| different group | any | any | MISMATCH | Same or similar functionality |
| any | NO | any | MISMATCH | Similar functionality |
| any | any | any FAIL | MISMATCH | none |

Any UNKNOWN in form, fit or function gives PARTIAL at best.

### Package equivalence groups

A group holds names that share one land pattern: same lead count, pitch and lead span. Height is recorded separately because a thinner part fits where a taller one fits, but not the reverse.

| Group | Names | Outline reference | Pitch, span | Max height | Status |
|---|---|---|---|---|---|
| SOT23-3 | SOT-23, SOT23, TO-236AB | JEDEC TO-236 [F5][F6] | 1.90 mm between outer leads | 1.0 to 1.45 mm by vendor | CITED |
| SOT23-5 | SOT-23-5, SOT-25, SC-74A, TSOP-5, SOT753 | JEDEC MO-178, JEITA SC-74A [F7][F8] | 0.95 mm, 2.8 mm | up to 1.45 mm | CITED |
| SOT23-6 | SOT-23-6, SOT-26, SC-74, TSOP-6, SOT457 | JEDEC MO-178, JEITA SC-74 [F9][F10] | 0.95 mm, 2.8 mm | up to 1.45 mm | CITED |
| TSOT23-5 | TSOT-23-5, TSOT-25, thin SOT-23-5 | JEDEC MO-193 [F11] | 0.95 mm, 2.8 mm | 1.00 mm | CITED |
| SOT223 | SOT-223, SC-73, TO-261 | JEDEC TO-261, JEITA SC-73 [F12] | 2.3 mm | 1.8 mm | CITED |
| SOT89 | SOT-89, SC-62, TO-243 | JEDEC TO-243, JEITA SC-62 [F13] | 1.5 mm | 1.6 mm | CITED |
| SOIC8N | SOIC-8, SO-8, SOP-8 with 3.9 mm body | JEDEC MS-012 [F14][F15] | 1.27 mm | 1.75 mm | CITED |
| MSOP8 | MSOP-8, VSSOP-8, TSSOP-8 with 3.0 mm body | JEDEC MO-187 [F16] | 0.65 mm | about 1.1 mm | CITED, height UNVERIFIED |
| TSSOP8W | TSSOP-8 with 4.4 mm body | JEDEC MO-153 [F17] | 0.65 mm | 1.2 mm | MO-153 reference UNVERIFIED |
| DPAK | DPAK, TO-252, SC-63 | JEDEC TO-252, JEITA SC-63 [F18] | 2.29 mm | 2.38 mm | CITED |
| D2PAK3 | D2PAK, TO-263 three lead | JEDEC TO-263 [F19] | 2.54 mm | 4.3 mm body | CITED |
| TO220 | TO-220, TO-220AB, SC-46 | JEDEC TO-220AB, JEITA SC-46 [F20] | 2.54 mm | through hole | CITED |
| TO92 | TO-92, SC-43A | JEDEC TO-92, JEITA SC-43A [F21] | 1.27 mm | through hole, lead forming varies | CITED |

Cross-group relations:
- TSOT23-5 into a SOT23-5 position: same land pattern, lower height. Form PASS.
- SOT23-5 into a TSOT23-5 position: same land pattern, height may exceed the original. Form WARN.
- SOT23-5 and SOT23-6 are different groups even though pitch and span match.

Names that never form a group: DFN, WSON, SON, QFN and similar no-lead packages. Pad and thermal pad geometry differ per drawing even within JEDEC MO-229 ([F22]). These are compared only by outline drawing and score UNKNOWN until a drawing comparison exists.

Ambiguous names: "SOP-8" can mean the 3.9 mm MS-012 body or a 5.3 mm body, and "TSSOP-8" can mean a 3.0 mm or a 4.4 mm body ([F17]). An ambiguous name without a body width scores UNKNOWN.

### Normalization procedure (PROPOSED)

1. Uppercase, remove spaces, unify hyphens.
2. Look up the alias table. Require pin count; require body width for SOP, SOIC and TSSOP names.
3. If the name is unknown or ambiguous, the package group is UNKNOWN.
4. When a datasheet gives an IPC-7351B land pattern name, use it as a cross-check. In SOT95P280X145-5N, 95 is 0.95 mm pitch, 280 is 2.80 mm nominal lead span, 145 is 1.45 mm maximum height, 5 is the pin count and N is nominal density ([F23], [F24]). IPC-7351B is a paid standard; the convention is taken from secondary sources.

### Sources

- [F1] 22 CFR 120.42: https://www.law.cornell.edu/cfr/text/22/120.42
- [F2] Texas Instruments, cross-reference types: https://www.ti.com/ordering-resources/faqs/cross-reference-search/xref-type.html
- [F3] Digi-Key TechForum, cross reference tool: https://forum.digikey.com/t/digikey-cross-reference-tool/19514
- [F4] Altium, pulling SiliconExpert part data: https://www.altium.com/documentation/altium-designer/pulling-siliconexpert-part-data?version=23
- [F5] NXP SOT23 package information: https://cache.nxp.com/docs/en/package-information/SOT23.pdf
- [F6] JEDEC publication index: https://www.jedec.org/sites/default/files/Main.pdf
- [F7] NXP SOT753 (TSOP5, SC-74A): https://cache.nxp.com/docs/en/package-information/SOT753.pdf
- [F8] onsemi case 318BQ (SC-74A-5): https://www.onsemi.com/pub/Collateral/318BQ.PDF
- [F9] NXP SOT457 (TSOP6, SC-74): https://cache.nxp.com/docs/en/package-information/SOT457.pdf
- [F10] Texas Instruments DBV0006A (SOT-23, MO-178): https://ti.com/lit/pdf/mpds026
- [F11] Diodes Incorporated TSOT25 outline: https://www.diodes.com/assets/Package-Files/TSOT25.pdf
- [F12] NXP SOT223: https://cache.nxp.com/docs/en/package-information/SOT223.pdf
- [F13] NXP SOT89: https://cache.nxp.com/docs/en/package-information/SOT89.pdf
- [F14] NXP SOT96-1 (SO8, MS-012): https://cache.nxp.com/docs/en/package-information/SOT96-1.pdf
- [F15] onsemi case 751BD (SOIC-8, MS-012): https://www.onsemi.com/download/package-drawing/pdf/751bd.pdf
- [F16] onsemi case 846AD (MSOP-8, MO-187): https://www.onsemi.com/download/package-drawing/pdf/846ad.pdf
- [F17] onsemi case 948AL (TSSOP-8, 4.4 mm body): https://www.onsemi.com/download/package-drawing/pdf/948al.pdf
- [F18] NXP SOT428 (DPAK, TO-252): https://cache.nxp.com/docs/en/package-information/SOT428.pdf
- [F19] onsemi case 418AJ (D2PAK-3, TO-263): https://www.onsemi.com/download/package-drawing/pdf/418aj.pdf
- [F20] NXP SOT78 (TO-220AB): https://cache.nxp.com/docs/en/package-information/SOT78.pdf
- [F21] NXP SOT54 (TO-92): https://cache.nxp.com/docs/en/package-information/SOT54.pdf
- [F22] JEDEC MO index: https://www.jedec.org/sites/default/files/MOINDEX.pdf
- [F23] PCB Libraries, footprint naming design options: https://www.pcblibraries.com/Products/FPX/UserGuide/Console%20Options/3.2%20Design.asp
- [F24] IPC-7351B naming convention summary: https://www.pcb-3d.com/wordpress/tutorials/ipc-7351b-naming-convention-for-surface-mount-device-3d-models-and-footprints/

## 3. LDO regulator rules

Every rule compares a candidate (C) with the original (O). A rule returns PASS, WARN, FAIL or UNKNOWN. A rule whose input value is missing on either side returns UNKNOWN. A rule whose test conditions differ between the two datasheets returns WARN at best. Directions follow TI's drop-in definition, "parametrically equivalent or better" ([F2]). Numeric slack is never added unless a row says so (PROPOSED, D-017).

| ID | Parameter | Rule | Result if broken | Source |
|---|---|---|---|---|
| LDO-01 | Output type | Fixed or adjustable must match | FAIL | [R1] |
| LDO-02 | Nominal output voltage (fixed) | C equals O exactly | FAIL | [R1] |
| LDO-03 | Reference voltage (adjustable) | C equals O exactly | WARN, divider must be recomputed | [R1] |
| LDO-04 | Input voltage range (recommended operating) | C min <= O min and C max >= O max | FAIL | [R2] |
| LDO-05 | Absolute maximum input voltage | C >= O | FAIL | [R2] |
| LDO-06 | Output voltage accuracy | C band <= O band, compared over temperature when both give it | WARN | [R3] |
| LDO-07 | Rated output current | C >= O | FAIL | [R2] |
| LDO-08 | Dropout voltage | C <= O at the same output current; a value without a current condition is UNKNOWN | FAIL if higher at same current, WARN if conditions differ | [R3], [R4] |
| LDO-09 | Quiescent or ground current | C <= O at the same load | WARN | [R3] |
| LDO-10 | Shutdown current | C <= O | WARN | [R3] |
| LDO-11 | PSRR | C >= O at the same frequency and load | WARN | [R3], [R4] |
| LDO-12 | Line and load regulation | C <= O over the same span | WARN | [R3] |
| LDO-13 | Output capacitor stability | see below | FAIL or WARN | [R5], [R6], [R7] |
| LDO-14 | Enable pin | Same polarity and floating default; C high threshold <= O, C low threshold >= O | FAIL on polarity, WARN on thresholds | [R2] |
| LDO-15 | Thermal | C junction-to-ambient resistance <= O in the same package; C max junction temperature >= O | WARN | [R3], [R4] |
| LDO-16 | Tab or exposed pad connection | Must match (fit rule) | FAIL | [R8], [R9], [R10], [R11] |

Definitions behind the rules (CITED):
- Dropout is "the input-to-output differential voltage at which the circuit ceases to regulate against further reductions in input voltage" ([R3]). It rises with output current and "PMOS architectures will have lower dropout at higher output voltages" ([R4]). A dropout value is only comparable at the same current and output voltage.
- Quiescent current "is the difference between input and output currents" ([R3]). For bipolar parts it "increases proportionally with the output current" ([R4]).
- PSRR is typically given "at a frequency of 120Hz or 1kHz" ([R4]). Values at different frequencies are not compared.

### Output capacitor stability (LDO-13)

Older LDOs are stable only inside an ESR window. Newer ones are stable with low-ESR ceramic capacitors (CITED):
- "Virtually all LDO regulators require that the ESR of the output capacitor be within a set range to assure regulator stability" and large ceramic capacitors "typically have very low ESR values (< 20 mΩ)" ([R6]).
- Older TI datasheets "designed when tantalum or high-ESR capacitors were more common" specify a capacitor value and an ESR range; newer devices are "inherently ceramic capacitor stable" ([R5]).
- One older part requires an output capacitor ESR "between 0.3 Ω to 22 Ω" ([R11]).

Ersatz classifies each LDO as CERAMIC_STABLE, ESR_WINDOW (with min and max ESR) or UNKNOWN (PROPOSED):

| Original | Candidate | Result |
|---|---|---|
| ESR_WINDOW | CERAMIC_STABLE | PASS, with a note that the board may carry an unneeded tantalum capacitor |
| ESR_WINDOW | ESR_WINDOW | PASS if C window contains O window, else WARN |
| CERAMIC_STABLE | CERAMIC_STABLE | PASS if C minimum capacitance <= O minimum |
| CERAMIC_STABLE | ESR_WINDOW with minimum ESR above 20 mΩ | FAIL: the ceramic capacitor on the board is outside the candidate's stable range |
| any | UNKNOWN | UNKNOWN |

### Regulator tab connections (CITED)

The tab is not the same pin across families, so a three-lead match is not enough:
- 78xx family: "Heatsink surface connected to Pin 2", which is Ground ([R9]); TI's LM340 drawing reads "TAB IS GND" ([R8]).
- LM317: "OUTPUT 2, TAB" ([R10]).
- LM1117 in SOT-223: the tab is VOUT ([R11]).

Fitting a part whose tab is OUT into a board where the tab copper is GND shorts the output to ground. LDO-16 is a fit rule and always FAIL on mismatch.

### LDO pin vocabulary (PROPOSED)

IN, OUT, GND, EN, NR (noise reduction or bypass), PG (power good), ADJ, SENSE, NC, TAB. TAB carries the function it is connected to, for example TAB=GND.

### Sources

- [R1] Texas Instruments LM1117 datasheet: https://www.ti.com/lit/ds/symlink/lm1117.pdf and LM317 datasheet: https://www.ti.com/lit/ds/symlink/lm317.pdf
- [R2] Texas Instruments TPS7A02 datasheet (example of recommended operating conditions and EN thresholds): https://www.ti.com/lit/ds/symlink/tps7a02.pdf
- [R3] Texas Instruments SLVA079, Understanding the terms and definitions of LDO voltage regulators: https://www.ti.com/lit/an/slva079/slva079.pdf
- [R4] Texas Instruments LDO Basics e-book, Rev. A: https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/slyy151a.pdf
- [R5] Texas Instruments SLVA115A, ESR, Stability, and the LDO Regulator: https://www.ti.com/lit/an/slva115/slva115.pdf
- [R6] Texas Instruments SNVA020B (AN-1148): https://www.ti.com/lit/an/snva020b/snva020b.pdf
- [R7] Texas Instruments SLVA072, Technical Review of Low Dropout Voltage Regulator Operation and Performance: https://www.ti.com/lit/an/slva072/slva072.pdf
- [R8] Texas Instruments LM340 datasheet: https://www.ti.com/lit/ds/symlink/lm340.pdf
- [R9] onsemi MC7800 datasheet: https://www.onsemi.com/pdf/datasheet/mc7800-d.pdf
- [R10] Texas Instruments LM317 datasheet: https://www.ti.com/lit/ds/symlink/lm317.pdf
- [R11] Texas Instruments LM1117 datasheet: https://www.ti.com/lit/ds/symlink/lm1117.pdf

## 4. Op-amp rules

Same conventions as section 3.

| ID | Parameter | Rule | Result if broken | Source |
|---|---|---|---|---|
| OPA-01 | Channels per package | C equals O | FAIL | [P1] |
| OPA-02 | Supply range (total) | C min <= O min and C max >= O max | FAIL | [P2], [P3] |
| OPA-03 | Gain bandwidth product | C >= O; flag C above 10 times O | FAIL if lower, WARN if far higher (stability margin) | [P2] |
| OPA-04 | Slew rate | C >= O | FAIL | [P2] |
| OPA-05 | Input offset voltage | C maximum <= O maximum at the same temperature | WARN | [P2], [P4] |
| OPA-06 | Input bias current | C <= O; input stage type (bipolar, JFET, CMOS) should match | WARN | [P2] |
| OPA-07 | Rail-to-rail input | C includes every rail O includes | FAIL | [P2], [P4], [P5] |
| OPA-08 | Rail-to-rail output | C swings at least as close to the rails as O at the same load | FAIL | [P2], [P5] |
| OPA-09 | Input common-mode range | C range contains O range | FAIL | [P2] |
| OPA-10 | Voltage noise density | C <= O at the same frequency, usually 1 kHz | WARN | [P2], [P3] |
| OPA-11 | Minimum stable gain | C <= O; unity-gain stable is always safe | FAIL | [P2], [P6] |
| OPA-12 | Quiescent current per channel | normalize to per channel, then C <= O | WARN | [P2], [P4] |
| OPA-13 | Pinout | pin function map equal (fit rule) | FAIL | [P3], [P4], [P5], [P7] |

Definitions behind the rules (CITED, [P2]):
- Gain bandwidth: "GBW specifies the gain-bandwidth product of the op amp in an open loop configuration and the output loaded".
- Slew rate: "the rate of change in the output voltage caused by a step input".
- Input offset voltage: "the DC voltage that must be applied between the input terminals to force the quiescent DC output voltage to zero".
- Common-mode range: "the range over which normal operation is guaranteed".
- Supply current is "usually the total quiescent current draw for the whole package", with named exceptions, so OPA-12 normalizes per channel.
- Decompensated parts exist: "Some op amps come in de-compensated versions" ([P2]); one family pairs a "Unity-gain stable" part with one "Stable in gain ≥ 5" ([P6]).

### Standard pinouts (CITED)

Single op-amp, 8 pin, industry standard ([P3]): 1 OFFSET N1, 2 IN-, 3 IN+, 4 V-, 5 OFFSET N2, 6 OUT, 7 V+, 8 NC. Current production of the same family lists pins 1, 5 and 8 as "Do not connect" in some packages ([P3]), so offset null pins are treated as NC-compatible with a WARN.

Dual op-amp, 8 pin, industry standard ([P4], [P5]): 1 OUT A, 2 IN- A, 3 IN+ A, 4 V-, 5 IN+ B, 6 IN- B, 7 OUT B, 8 V+.

Single op-amp in SOT-23-5 is not standardized. Three TI parts use three maps:
- 1 IN+, 2 V-, 3 IN-, 4 OUT, 5 V+ ([P5])
- 1 OUT, 2 V-, 3 IN+, 4 IN-, 5 V+ ([P3])
- 1 OUT, 2 V+, 3 IN+, 4 IN-, 5 V- ([P7])

Ersatz never assumes a SOT-23-5 pinout. It compares extracted pin tables, and a part without one scores fit UNKNOWN.

### Op-amp pin vocabulary (PROPOSED)

Per channel: INP, INN, OUT. Shared: VCC (V+), VEE (V-), NULL, SHDN, NC.

### Sources

- [P1] Texas Instruments LM358 datasheet: https://www.ti.com/lit/ds/symlink/lm358.pdf
- [P2] Texas Instruments SLOA011B, Understanding Operational Amplifier Specifications: https://www.ti.com/lit/an/sloa011b/sloa011b.pdf
- [P3] Texas Instruments TL071 datasheet: https://www.ti.com/lit/ds/symlink/tl071.pdf
- [P4] Texas Instruments LM358 datasheet: https://www.ti.com/lit/ds/symlink/lm358.pdf
- [P5] Texas Instruments LMV321 family datasheet: https://www.ti.com/lit/ds/symlink/lmv321.pdf
- [P6] Texas Instruments OPA627 and OPA637 datasheet: https://www.ti.com/lit/ds/symlink/opa637.pdf
- [P7] Texas Instruments LMC7101 datasheet: https://www.ti.com/lit/ds/symlink/lmc7101.pdf

## 5. Providers

| | Digi-Key Product Information v4 | Mouser Search API | Nexar (Octopart) |
|---|---|---|---|
| Auth | OAuth2, client credentials or authorization code; token endpoint https://api.digikey.com/v1/oauth2/token; 2-legged token lives "10 minutes"; headers X-DIGIKEY-Client-Id and Bearer token [V1] | API key as the apiKey query parameter [V4] | OAuth2 client credentials at identity.nexar.com, scope supply.domain; "Access tokens live for 24 hours" [V7] |
| Part details | GET /products/v4/search/{productNumber}/productdetails, optional manufacturerId [V2] | POST /api/v1/search/partnumber (max 50 parts), POST /api/v2/search/partnumberandmanufacturer [V4] | GraphQL supSearchMpn and supMultiMatch (exact match) [V8] |
| Parametric search | Yes. POST /products/v4/search/keyword with ParameterFilterRequest by numeric ParameterId and value ids [V3] | No. Keyword search with one of None, Rohs, InStock, RohsAndInStock [V4] | Yes. supSearch filters by attribute shortname, ranges like "(8__16)" [V9] |
| Lifecycle | ProductStatus.Status, EndOfLife, Discontinued, DateLastBuyChance [V2] | LifecycleStatus, IsDiscontinued [V4] | spec lifecyclestatus [V10] |
| Datasheet, parameters, stock | DatasheetUrl; Parameters with ParameterType; QuantityAvailable [V2] | DataSheetUrl; ProductAttributes; Availability, AvailabilityInStock [V4] | bestDatasheet; specs; sellers.offers.inventoryLevel [V8] |
| Substitutes | GET /products/v4/search/{productNumber}/substitutions; SubstituteType has no documented values [V5] | SuggestedReplacement (string), source undocumented [V4] | similarParts, "similar in specification and functionality" [V11] |
| Free limits | "120 per minute" and "1000 per day" for Product Information [V1]; exceeding gives "a ten-minute suspension" [V6] | 1,000 calls per day and 30 per minute (UNVERIFIED, search snippets only) | Evaluation plan "Up to 100 matched parts" [V12]; FAQ says 1000 [V13]; conflict UNVERIFIED |
| Sandbox | Yes; data "may not match your request" [V14] | None documented | None |

### Terms that shape the design (CITED unless marked)

Digi-Key API user agreement [V6]:
- Permitted uses are "your public website" and internal purchasing applications, "in ways that complement and enhance DigiKey's own services".
- §3.2(iv): may not "distribute or disclose DigiKey Data to any third parties" outside those uses.
- §3.1.4: "You must clearly and conspicuously attribute DigiKey as the source of all DigiKey Data."
- §5.1(b): may not "aggregate, in any way, any DigiKey Data with third party content or data without distinction".
- §5.1(e): may not "use the API, DigiKey Data, or Documentation to update or create your own database of information".
- §5.1(a): may not use it "in a way that is competitive to or inconsistent with DigiKey's services".
- No caching clause exists. §4 treats "Any data derived from DigiKey Data" as Digi-Key confidential information.

Mouser API terms: the terms page refused automated retrieval. Search snippets show a license "to copy and display the Mouser Electronics Data solely on your Application", required attribution, and a bar on creating "your own database". All Mouser terms are UNVERIFIED until read in full before the Mouser adapter is written.

Nexar API terms [V15]:
- §1.2(vi): may not "use the Nexar API to cache and/or store data for more than twenty-four (24) hours".
- §1.2(v): may not "self-host any content including but not limited to datasheets and images".
- §1.2(vii): may not use it for "(a) benchmarking or competitive analysis of the Nexar API; (b) developing, using, or providing a competing software product or service".
- §1.4: requires a followable link to octopart.com on indexable pages.

Consequences for Ersatz:
1. No recorded provider response is committed to the public repository. Test fixtures are synthetic (D-019).
2. Every displayed value carries its provider name, which also satisfies the attribution and "without distinction" clauses.
3. Provider data in the cache has a time-to-live and is never exported. The benchmark dataset stores no provider data.
4. Datasheets are linked, never re-hosted.
5. The public demo is a reference-checking tool that links to distributor product pages. Whether that counts as "complement and enhance" under Digi-Key §5.1(a) is a judgment call, recorded as a risk.

### Recommendation (PROPOSED, D-018)

- Digi-Key is the primary provider: lookup, lifecycle, and the only free parametric search.
- Mouser is the secondary provider: lookup, a second lifecycle opinion, stock. It cannot drive candidate search.
- Nexar is out of v0.1: the free allowance is too small to be useful, storage is capped at 24 hours, and the competing-product clause is a risk for a tool that ranks alternates.

### Category mapping (UNVERIFIED)

Data file: ersatz/rules/categories.yaml. Every provider string below is UNVERIFIED until it appears in a local recording, then it is marked CITED with the recording date.

| Provider | Provider category | Extra check | Ersatz |
|---|---|---|---|
| Digi-Key | Voltage Regulators - Linear, Low Drop Out (LDO) Regulators | none | ldo |
| Digi-Key | Instrumentation, Op Amps, Buffer Amps | Amplifier Type is General Purpose, CMOS, J-FET, Chopper (Zero-Drift) or Voltage Feedback | opamp |
| Digi-Key | Instrumentation, Op Amps, Buffer Amps | Amplifier Type is Instrumentation, Buffer, Current Sense, Differential, Current Feedback, Programmable Gain or Video | out of scope |
| Mouser | LDO Voltage Regulators | none | ldo |
| Mouser | Operational Amplifiers - Op Amps | none | opamp |

Any other category is out of scope. A category that needs the extra check and lacks it, or has an unlisted value, is UNKNOWN.

### Sources

- [V1] Digi-Key API documentation: https://developer.digikey.com/documentation
- [V2] Digi-Key ProductDetails OpenAPI: https://developer.digikey.com/node/2360/oas-download
- [V3] Digi-Key KeywordSearch OpenAPI: https://developer.digikey.com/node/2357/oas-download
- [V4] Mouser Search API Swagger V1 and V2: https://api.mouser.com/api/docs/V1 and https://api.mouser.com/api/docs/V2
- [V5] Digi-Key Substitutions OpenAPI: https://developer.digikey.com/node/2378/oas-download
- [V6] Digi-Key API user agreement: https://developer.digikey.com/api-user-agreement
- [V7] Nexar, application access token: https://support.nexar.com/support/solutions/articles/101000452406-application-access-token
- [V8] Nexar, playground query examples: https://support.nexar.com/support/solutions/articles/101000494582-nexar-playground-graphql-query-examples
- [V9] Nexar, sorting and filtering: https://support.nexar.com/support/solutions/articles/101000452264-supply-sorting-and-filtering-your-queries
- [V10] Nexar, lifecycle information: https://support.nexar.com/support/solutions/articles/101000434626-supply-lifecycle-information-for-parts
- [V11] Nexar, similar parts: https://support.nexar.com/support/solutions/articles/101000434631-supply-similar-parts
- [V12] Nexar, compare plans: https://nexar.com/compare-plans
- [V13] Nexar, frequently asked questions: https://support.nexar.com/support/solutions/articles/101000497890-frequently-asked-questions
- [V14] Digi-Key FAQ: https://developer.digikey.com/faq
- [V15] Nexar API license terms of use (Altium, last updated 2022-08-01): https://nexar.com/api/legal

## 6. Datasheet extraction

### PDF libraries (CITED from each project's PyPI page)

| Library | License | Tables | Text with coordinates | OCR | Use in Ersatz |
|---|---|---|---|---|---|
| pdfplumber | MIT [X1] | yes, table to row to cell | yes, per character | no | primary text and table layer |
| pypdfium2 | BSD-3-Clause, Apache-2.0 [X2] | no | per character boxes | no, renders pages | page rendering |
| pdfminer.six | MIT [X3] | no | yes | no | used through pdfplumber |
| pypdf | BSD-3-Clause [X4] | no | partial | no | not used |
| PyMuPDF | "GNU AFFERO GPL 3.0 or Artifex Commercial License" [X5] | yes | yes | Tesseract | not used: AGPL obligations apply to a hosted API |
| Camelot | MIT [X6] | yes, lattice and stream | tables only | optional | fallback for hard tables |
| docling | MIT [X7] | yes, ML models | yes | yes | optional later path |
| marker | Apache-2.0 code, model weights under a modified OpenRAIL-M license with a revenue threshold [X8] | yes | yes | yes | not used: weight license |
| unstructured | Apache-2.0 [X9] | yes, as HTML | yes | yes | not used |
| OCRmyPDF | MPL-2.0 [X10] | no | no | adds a text layer | out of v0.1 (no OCR) |

### Language model features (CITED)

- PDF input: "Maximum pages per request" is 600, and "Each page typically uses 1,500–3,000 tokens depending on content density" [X11]. Each page is sent as an image plus its extracted text.
- Citations return page_location with 1-indexed "start_page_number" and exclusive "end_page_number" [X12].
- Structured outputs use output_config.format with a JSON schema [X13]. "Numerical constraints (such as minimum, maximum, multipleOf)" are not supported, so range checks happen in code.
- "Citations cannot be used together with structured outputs." [X12]
- Batch requests are "charged at 50 percent of the standard API prices" [X14].

### Citation strategy (PROPOSED, D-021)

Because API citations and structured outputs cannot be combined, Ersatz does not rely on API citations:
1. Select pages by keyword from pdfplumber text (ordering information, pin configuration, electrical characteristics, recommended operating conditions, absolute maximum ratings, package information).
2. Send only those pages with a strict schema in which every field carries the value as a string, the unit as a string, min, typ and max columns, the test condition, the page number and a verbatim quote of at most 200 characters.
3. Verify each quote locally: after whitespace and Unicode normalization, the quote must appear on the cited page's pdfplumber text, and the value string must appear inside the quote. Failing values are dropped and logged, never shown.
4. Parse units deterministically (below) and validate (below).

### Unit parsing with pint (CITED from the pint project, BSD-3-Clause [X15])

pint defines "micro- = 1e-6 = μ- = µ- = u- = mu- = mc-", "ppm = 1e-6" and "percent = 0.01 = %" [X16]. Pitfalls found by running pint 0.24.4 locally:
- "50 ppm/°C" raises an offset unit error; the denominator must be rewritten as delta_degC first. pint documents that offset units in products are "problematic" [X17].
- "1.2 to 3.3 V" and "1.2-3.3 V" do not parse; ranges are split by regex before pint sees them.
- "±2 %" parses as 2 percent with the sign dropped; tolerances are split first.
- "a" is the year unit and "MV" is megavolt; case is significant, so unit strings are matched against an allow-list per parameter before parsing.
- Pin pint at 0.24.2 or later, which accepts both micro code points and "u".

### Reading pitfalls (CITED)

- Typical is not guaranteed. "The typical value published in the data sheet is the mean or average value of the distribution" [X18]. Rules compare guaranteed min or max columns where they exist and fall back to typical with a WARN.
- Conditions live in headers and footnotes, for example "All typical values are at VCC = 3.3 V, TA = 25°C" [X19]. The extraction schema carries the condition text for every value.
- Sign convention: "maximum refers to the most-positive value" [X19].
- Absolute maximum ratings "are stress ratings only" [X19] and are never used as operating limits.
- Package and variant: one datasheet covers several packages, and the orderable part number table maps suffixes to packages [X19]. Extraction reads that table first and then extracts values per variant.
- Revision: TI literature numbers end in a revision letter with dates, for example "SZZA036C – December 2002 – Revised June 2016" [X19]. Every extraction stores the literature number, revision and SHA-256.
- Image-only PDFs: a page with no or very few characters is an image [X20]. Such datasheets are UNEXTRACTED in v0.1.

### Validation rules

| Rule | Status |
|---|---|
| min <= typ <= max for every value | CITED convention [X19] |
| Every value has a page and a verified quote | PROPOSED |
| LDO: minimum input voltage >= output voltage + dropout | CITED basis [R3] |
| LDO: output voltage < maximum recommended input voltage | PROPOSED |
| LDO: 0 < dropout < output voltage; dropout has a current condition | PROPOSED, basis [R4] |
| LDO: quiescent current < rated output current; shutdown current <= quiescent current | PROPOSED |
| LDO: accuracy magnitude <= 10 percent | PROPOSED |
| Op-amp: slew rate > 0, GBW > 0 | CITED definitions [P2] |
| Op-amp: supply min < supply max <= absolute maximum | PROPOSED |
| Op-amp: output swing within the supply rails | PROPOSED |
| Units: parsed dimension matches the parameter's dimension | PROPOSED |

### Sources

- [X1] https://pypi.org/project/pdfplumber/
- [X2] https://pypi.org/project/pypdfium2/
- [X3] https://pypi.org/project/pdfminer.six/
- [X4] https://pypi.org/project/pypdf/
- [X5] https://pypi.org/project/PyMuPDF/
- [X6] https://pypi.org/project/camelot-py/
- [X7] https://pypi.org/project/docling/
- [X8] https://pypi.org/project/marker-pdf/
- [X9] https://pypi.org/project/unstructured/
- [X10] https://pypi.org/project/ocrmypdf/
- [X11] Claude PDF support: https://platform.claude.com/docs/en/build-with-claude/pdf-support
- [X12] Claude citations: https://platform.claude.com/docs/en/build-with-claude/citations
- [X13] Claude structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- [X14] Claude batch processing: https://platform.claude.com/docs/en/build-with-claude/batch-processing
- [X15] https://pypi.org/project/Pint/
- [X16] pint default unit definitions: https://raw.githubusercontent.com/hgrecco/pint/master/pint/default_en.txt
- [X17] pint non-multiplicative units: https://pint.readthedocs.io/en/stable/user/nonmult.html
- [X18] Texas Instruments SLOA083, Understanding Op Amp Parameters: https://e2e.ti.com/cfs-file/__key/telligent-evolution-components-attachments/00-14-01-00-00-99-01-86/Understanding-Op-Amp-Parameters.pdf
- [X19] Texas Instruments SZZA036C, Understanding and Interpreting Standard-Logic Data Sheets: https://www.ti.com/document-viewer/lit/html/SZZA036
- [X20] World Bank AI4Data cookbook, scanned documents: https://worldbank.github.io/ai4data/cookbook/data-from-documents/scanned

## 7. Related work and positioning

- Z2Data argues that general language models return "Non-existent part numbers that follow a plausible naming pattern but were never manufactured" and "can't confirm whether a part number is still active or has entered into NRND" [W1]. It reports no measured error rate.
- Zenode Alts takes a part number, "extracts specs, pinouts, and package info from datasheets" and returns alternates "scored on functional match, availability, and lifecycle" [W2]. It is closed and publishes no accuracy figures. Its own site refused retrieval; the description comes from an investor write-up.
- Octopart and Nexar offer similar parts "identified by Nexar to be similar in specification and functionality" [W3].
- SiliconExpert grades crosses from A (drop-in) to SF (similar functionality) [F4] and covers "over a billion electronic parts" [W4].
- Research benchmarks test language models on board-level design (HWE-Bench, best pass rate 8.15 percent [W5]), PCB question answering (PCB-QA [W6]) and power supply design [W7]. None tests replacement recommendations against manufacturer notices.
- The closest method is the study of invented software package names, which checks every suggested name against a registry and reports rates of "at least 5.2% for commercial models and 21.7% for open-source models" [W8]. Ersatz-Bench applies the same existence check to part numbers.

### Where Ersatz differs

Ersatz is open source and every value it shows links to the provider response or datasheet page it came from. It never generates a part number: candidates come only from provider responses, and a language model is used only to read datasheets. Its matching rules are published in this document with sources, so a component engineer can audit why a candidate passed or failed. Its verify mode checks a replacement someone else suggested, including a chatbot's, instead of only proposing its own. Ersatz-Bench publishes a measured rate of invented, inactive and mismatched chatbot suggestions with raw data, which no commercial tool or paper found here provides.

### Sources

- [W1] Z2Data, Using AI for electronic part search is more risky than you think: https://www.z2data.com/insights/using-ai-for-electronic-part-search-is-more-risky-than-you-think
- [W2] Bee Partners, Zenode Alts: https://beepartners.vc/zenode-alts-component-search
- [W3] Altium, Octopart API example queries: https://www.altium.com/documentation/altium-developer-center/octopart/api/example-queries
- [W4] Altium, SiliconExpert: https://www.altium.com/capabilities/supply-chain/siliconexpert
- [W5] HWE-Bench: https://arxiv.org/abs/2603.18102
- [W6] PCB-QA: https://arxiv.org/abs/2606.23704
- [W7] Evaluating LLM-based workflows for switched-mode power supply design: https://arxiv.org/abs/2507.10639
- [W8] Package hallucination study, USENIX Security 2025: https://arxiv.org/abs/2406.10279
