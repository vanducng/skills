# UAT checklist

Run by the QA seat on real data, after the build. Each line is checked or failed with its evidence.

- [ ] Every question-sheet row has a real-data screenshot that answers it; the screenshot names the row.
- [ ] Every KPI matches `reconciliation.md` and sits inside its tolerance.
- [ ] Each filter on the sheet works and changes the numbers it should.
- [ ] The refresh on the sheet holds: the data's latest timestamp is within the stated freshness.
- [ ] A reader gets each answer inside the sheet's time-to-read budget (timed on the first screen, at the reader's usual screen size).
- [ ] Design fidelity scores 9 or more out of 10 against the signed-off mockup.
- [ ] The chart rules hold: no dual axes or 3D, bars start at zero, no pie over five slices, a colour-blind-safe palette, never colour alone.
- [ ] Every metric carries its description in the tool, and the glossary lists definition, source, logic, owner and refresh.
- [ ] The screenshots mask personal data with a white blur.
