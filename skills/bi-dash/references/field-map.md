# Field map

Written before the build: one row per field the approved mockup shows. It proves the data exists, and it records every choice made where it is ambiguous.

| Mockup field (chart) | Model.column | Status | Profile | Choice and reason |
|---|---|---|---|---|
| order date (Orders per week) | `orders.created_at`, `orders.order_date` | variant | no nulls in either; they differ on about 1 order in 4 (UTC vs local day) | `order_date`: the asker reads weeks in the local day |
| region (Revenue by region) | `orders.region` | exists | 4 values, no nulls; `north` and `North` merged | - |
| sales channel (Orders by channel) | - | missing | - | Back to the asker: drop the chart or source the channel |

## Status

- **exists:** exactly one column holds the field.
- **variant:** two or more candidate columns (a timestamp in UTC and a local date; a billing and a shipping region; a raw and a cleaned name). Record which one, and why; the asker confirms when the choice changes a number they read.
- **missing:** no column holds it. The chart cannot be built as drawn: the asker drops it, or the data is sourced first.

A `missing` row or an unchosen `variant` stops the build. Say both in the reply as well as in the file.

## Profile each mapped column

```sql
SELECT COUNT(*) AS rows, COUNT(col) AS non_null, COUNT(DISTINCT col) AS distinct_values, MIN(col), MAX(col) FROM t;
SELECT LOWER(TRIM(col)) AS v, COUNT(DISTINCT col) AS spellings FROM t GROUP BY 1 HAVING spellings > 1;  -- duplicate spellings
```

Look for nulls, values outside a sane range (negative amounts, dates in the future), and one value spelled several ways.
