# Extraction gold set

Ten public datasheets, five LDOs and five op-amps, from five manufacturers.
Each file in gold/ names one datasheet by URL and SHA-256 and lists the
values a correct extraction must find. The PDFs are not committed; the
evaluation script downloads them into cache/ and refuses a file whose hash
differs from the label file.

## Label rules

- Values are in Ersatz canonical units: V, A, Hz, V/s, V/sqrt(Hz), F, ohm,
  percent, dB, degC.
- Only the columns printed in the datasheet are labeled. A label with min
  and max is matched only by an extraction with both.
- `any_slot: true` marks a value whose column the PDF text layer does not
  show; it matches in any column.
- `alt_names` lists other parameter names that hold the same value, for
  example quiescent current per amplifier reported as `iq`.
- `pages` lists every page that prints the value. A citation is correct
  when it points to one of them.
- Pin labels name the package with one or more substrings. A pin matches
  when an extracted pinout whose package contains one of them has that pin
  number with that function.
- Labels were drafted by hand from the PDFs. Status stays DRAFT until a
  second reader checks them (docs/EXTRACTION_REVIEW.md).

## Scoring

A value matches when it is within 1 percent of the label. Field accuracy is
correct labels over all labels. Citation accuracy is correct labels whose
cited page is in `pages`, over correct labels.
