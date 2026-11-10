# Question sheet

One row per business question the dashboard answers. Write it before any mockup. Fill what the records show; put `?` in each cell only the asker can answer, and ask for those cells. The sheet is done when no `?` is left and the asker has said yes.

| # | Question | Audience | Decision supported | Metric (one-sentence definition) | Grain | Filters | Refresh | Time-to-read budget |
|---|---|---|---|---|---|---|---|---|
| 1 | Are first-time buyers coming back? | ? | ? | Repeat-purchase rate: customers with 2 or more orders in the period / customers with 1 or more | month | region | daily | 10 s |

- **Question:** what the reader asks, in their words. A question with no decision behind it is a candidate to drop.
- **Audience:** who reads it, and how often. One audience per row; two audiences usually means two dashboards.
- **Decision supported:** what the reader does differently on a high or low number. This is the cell that cuts charts.
- **Metric:** one sentence a second analyst could compute from without asking: numerator, denominator, exclusions (test orders, refunds, internal accounts).
- **Grain:** the time and entity level of one point (day, week, month; order, customer, region).
- **Filters:** what the reader can slice by. Each filter must exist as a column (check it in the field map).
- **Refresh:** how fresh the number must be (hourly, daily, weekly) and when the reader looks.
- **Time-to-read budget:** how long the reader has to get the answer from the chart. UAT checks the layout against it.

## Questions to ask the asker

1. Who will read this, and how often?
2. What will they decide or do from each number?
3. How is each metric defined today, and which report or system holds the number they trust?
4. What grain, filters and refresh do they need?
5. How long do they have to read it?
