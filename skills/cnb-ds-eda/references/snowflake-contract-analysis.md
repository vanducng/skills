# Snowflake And Contract Analysis

Use explicit date parameters in every report query:

```sql
with params as (
    select
        to_date('YYYY-MM-DD') as report_start_date,
        to_date('YYYY-MM-DD') as report_end_exclusive
)
```

For "through yesterday" requests, make `report_end_exclusive` the next day after the inclusive last data date in `America/New_York`.

## Retell Scheduled Callback Detection

The lead-agent contract classifies scheduled callbacks from Retell call logs by:

1. Normalize `calls.to_number` into `contact_number`.
2. Keep calls whose `agent_id` matches `INT_TRANSFER_AI__COMPANY_CONFIG.lead_agent_id`.
3. Build sessions by `contact_number, agent_id`; a new session starts when the previous call is missing or more than 30 days earlier.
4. Number calls inside each session by `call_start_at`.
5. Mark `scheduled_callback` when `call_no > 1` and the prior call has a collected `callback_time`.

The relevant contract file is:

```text
/Users/vanducng/git/work/cnb/cnb-data-contract/contracts/constraints/snowflake/transfer_ai_lead_agent_should_not_call.yaml
```

## Non-Qualified Scheduled Callback Recheck

To measure scheduled callbacks that should not have proceeded, apply the same call-time checks used by the lead-agent contract to scheduled callbacks:

1. `no_qualified_lead_before_call`: no qualified `LEAD_DETAIL` row matching phone/company, created within 30 days before call, valid campaign, and `source_key <> 'TW'`.
2. `intelliapp_call_within_30d`: an IntelliApp source application plus an IntelliApp agent Retell call exists within 30 days before the scheduled callback.
3. `ineligible_worklist`: for C.R. England (`rocket_company_id = 43`), the latest app worklist is not `D - Exp Driver`.
4. `excluded_terminal_status`: latest app status matches `PROD_PREP.PUBLIC.STG_SEED__TENSTREET_EXCLUDED_TERMINAL_STATUS`.
5. Otherwise classify as `eligible_by_recheck`.

Preserve this priority order unless the user explicitly asks to count overlapping reasons.

## Data Sources

Common tables:

```text
PROD_RAW.RETELL.CALLS
PROD_RAW.TENSTREET.LEAD_NURTURE
PROD_RAW.TRANSFER_AI.TENSTREET_APPLICANT_RECORDS
PROD_RAW.TRANSFER_AI.WORKFLOW_EVENTS
PROD_RAW.TRANSFER_AI.WORKFLOW_STEPS
PROD_ANALYTICS.NEW_MARTS_COMMON.LEAD_DETAIL
PROD_PREP.INTERMEDIATE.INT_TRANSFER_AI__COMPANY_CONFIG
PROD_PREP.INTERMEDIATE.INT_TRANSFER_AI__VALID_CAMPAIGNS
PROD_PREP.PUBLIC.STG_SEED__TENSTREET_EXCLUDED_TERMINAL_STATUS
```

Use `convert_timezone('UTC', 'America/New_York', timestamp)` for report windows and call/app comparisons.
