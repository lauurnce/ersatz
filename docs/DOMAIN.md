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
