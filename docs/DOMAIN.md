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
