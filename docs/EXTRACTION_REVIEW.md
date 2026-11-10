# Extraction gold set: spot-check

The ground truth in eval/extraction/gold/ was drafted by hand from the ten
PDFs. Before any score is published, a second reader checks a sample. The
three labels below were picked because each one needed a judgment call. For
each label, open the PDF at the page given, compare, and tick a box.

If a label is wrong, correct the YAML file and note it here. When all three
pass, set `status: REVIEWED` in every gold file and rerun the evaluation.

## 1. LM1117 dropout voltage at 800 mA

- File: eval/extraction/gold/lm1117.yaml
- PDF: https://www.ti.com/lit/ds/symlink/lm1117.pdf (SNOS412Q), page 6,
  table 7.5 "LM1117 Electrical Characteristics (continued)"
- Label: `dropout`, typ 1.2 V, max 1.3 V, pages [6]
- Why it needs a check: the row has three current conditions (100 mA,
  500 mA, 800 mA). The label takes 800 mA, the rated output current. The
  typical value is at TJ = 25 C; the maximum is over 0 C to 125 C. In the
  text layer the numbers sit on separate lines from their condition:
  "TJ = 25°C 1.2 / IOUT = 800 mA over the junction temperature range V / 1.3".
- [ ] Correct  [ ] Wrong, fixed value: ______

## 2. MCP1700 maximum output current

- File: eval/extraction/gold/mcp1700.yaml
- PDF: https://ww1.microchip.com/downloads/en/DeviceDoc/MCP1700-Low-Quiescent-Current-LDO-20001826E.pdf
  (DS20001826E), page 3, "DC Characteristics"
- Label: `iout`, min 0.25 A, pages [1, 3]
- Why it needs a check: the datasheet prints 250 mA in the Min column for
  output voltages of 2.5 V and above, and 200 mA below 2.5 V. The label
  takes 250 mA as a minimum, not a maximum. The comparison signs in this row
  use a symbol font: the text layer holds private-use code points instead
  of the greater-or-equal and less-than signs.
- [ ] Correct  [ ] Wrong, fixed value: ______

## 3. LM358 input bias current

- File: eval/extraction/gold/lm358.yaml
- PDF: https://www.ti.com/lit/ds/symlink/lm358.pdf (SLOS068AB), page 10,
  table 5.7 "Electrical Characteristics: LM358, LM358A"
- Label: `ibias`, typ 20 nA, max 250 nA, pages [10]
- Why it needs a check: the datasheet prints -20 and -250 nA. The sign gives
  the current direction. The label stores the magnitude, as Ersatz
  validation does, so rule OPA-06 compares sizes. The datasheet covers twelve
  devices; the label takes the LM358 row at 25 C, not LM358A and not the
  0 C to 70 C row.
- [ ] Correct  [ ] Wrong, fixed value: ______

## Review log

| Date | Reader | Result |
|---|---|---|
| | | |
