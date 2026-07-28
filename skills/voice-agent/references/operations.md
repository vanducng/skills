# Voice Agent Operations Reference

Use generated `vac ... --help` for exact arguments and flags. This matrix describes the stable workflow categories verified against current Voice Agent CLI source on 2026-07-28.

Legend: RO is remote read, LW is local write, RW is remote mutation/action, DR is dry-run available. No command exposes `--confirm`.

| Group | RO or local operations | RW operations | Guard |
| --- | --- | --- | --- |
| `login` | Validate key | Write restricted config | Interactive secret input |
| `agents` | `list`, `info`, `versions`, `mcp-tools`, `tags get` | `create`, `delete`, version create/delete, `publish`, `tags assign` | Tag assignment DR; other writes no DR |
| `agent` | `get` | `update` | Update DR |
| `agent-publish` | None | Publish compatibility alias | No DR |
| `prompts` | `diff`; `pull` is RO + LW | `update` draft | Update DR; pull can overwrite |
| `tools` | `list`, `get`; `export` may write locally | `add`, `update`, `remove`, `import` | DR for all four writes |
| `tests cases` | `list`, `get` | `create`, `update`, `delete` | No DR |
| `tests batch` | `list`, `get` | `create` and run simulations | No DR; possible usage cost |
| `tests runs` | `list`, `get` | None | RO |
| `kb` / `kb sources` | KB `list`, `get` | KB create/delete; source add/delete | No DR |
| `flows` | `list`, `get` | `create`, `update`, `delete` | No DR |
| `flow-components` | `list`, `get` | `create`, `update`, `delete` | No DR |
| `phone-numbers` | `list`, `get` | `import`, purchase, update, release | No DR; update supports single-agent numeric/tag versions |
| `calls` | Read through `transcripts` | create phone/web, register, update, update-live, stop, delete | No DR; external effect |
| `transcripts` | `list`, `get`, `search`, `analyze` | None | RO |
| `exports` | `list` | None | RO |
| `batch-calls` | None | `create` | No DR; bulk external effect |
| `llms` | `list`, `get` | `create`, `update`, `delete` | No DR |
| `voices` | `list`, `get`, `search` | `add-resource`, `clone` | No DR; audio upload |
| `chats` | `list`, `get` | create, update, complete, SMS, end, delete | No DR; external effect |
| `playground` | Stateless completion | `complete` action | Possible usage cost |
| `chat-agents` | `list`, `get`, `versions` | create/update/delete, version create/delete, publish | No DR |
| `concurrency` | `get` | None | RO |
| `upgrade` | Version discovery | Change global install | No DR |

Cursor pagination is available on most list operations but not every resource. Use the command help and preserve opaque cursor values. Validate local output targets before `tools export`.

## Current Retell contract

The project pins `retell-sdk` 5.48.0, verified 2026-07-28. Re-check `npm view retell-sdk version` and official deprecations before changing SDK-dependent code.

Current and upcoming migrations:

| Effective date | Required contract |
| --- | --- |
| 2026-03-31 | Use weighted `inbound_agents` and `outbound_agents` phone assignments |
| 2026-06-15 | Use versioned list endpoints and `post_call_analysis_data` / `post_chat_analysis_data` |
| 2026-07-20 | Publish voice/chat drafts through `/publish-agent-version/{agent_id}` |
| 2026-07-31 | List voice/chat agents through `POST /v2/list-agents` with channel filters |
| 2026-07-31 | Use explicit locale arrays instead of scalar `language: "multi"` |
| 2026-08-31 | Use Update Call for ended calls and Update Live Call for ongoing calls |

Do not accept old top-level arrays for current versioned lists. Current list responses use `items`, optional `pagination_key`, and `has_more`.

Environment tags point an agent environment to a version and carry tag-specific dynamic variables. Moving a tag switches dependent phone numbers, webhooks, and other traffic immediately. `vac retell agents tags assign` accepts existing tags and versions only, supports dry-run, preserves the complete tag map, and verifies the selected tag after assignment.

Phone-number updates accept `--inbound-agent-version` with `--inbound-agent` and `--outbound-agent-version` with `--outbound-agent`. Version references can be numeric versions, `latest`, `latest_published`, or environment tags. Each single-agent shorthand replaces that direction with one binding at weight `1`.

## Webhooks

Keep webhook types distinct:

- Call event webhooks deliver `call_started`, `call_ended`, and `call_analyzed`. Agent configuration can set an event webhook URL.
- Inbound call/SMS webhooks live on phone-number routing and can return routing overrides or rejection.
- `vac` configures URLs but does not host or verify receivers.

Verify `x-retell-signature` against the raw body using the designated webhook key, timestamp freshness, and constant-time comparison. The current TypeScript SDK no longer exposes the old `Retell.verify` helper. Inbound hooks require a response within 10 seconds and may retry up to three times.

## Primary sources

- [Retell documentation index](https://docs.retellai.com/llms.txt)
- [Retell API overview](https://docs.retellai.com/api-references/overview)
- [Retell API key permissions](https://docs.retellai.com/accounts/manage-api-keys)
- [Agent versioning and environment tags](https://docs.retellai.com/agent/version)
- [Official TypeScript SDK](https://github.com/RetellAI/retell-typescript-sdk)
- [SDK 5.48.0 release](https://github.com/RetellAI/retell-typescript-sdk/releases/tag/v5.48.0)
- [Versioned list migration](https://docs.retellai.com/deprecation-notice/2026/06-15_legacy_list_endpoints)
- [Unified publish migration](https://docs.retellai.com/deprecation-notice/2026/07-20_agent_version_endpoints)
- [Agent list migration](https://docs.retellai.com/deprecation-notice/2026/07-31_agent_list_endpoints)
- [Multilingual locale arrays](https://docs.retellai.com/deprecation-notice/2026/07-31_legacy_multilingual_setting)
- [Update Call restriction](https://docs.retellai.com/deprecation-notice/2026/08-31_update_call_ended_calls_only)
- [Weighted phone assignments](https://docs.retellai.com/deprecation-notice/2026/03-31_phone_number_agent_fields)
- [Update Phone Number](https://docs.retellai.com/api-references/update-phone-number)
- [Update Live Call](https://docs.retellai.com/api-references/update-live-call)
- [Web call flow](https://docs.retellai.com/deploy/web-call)
- [Secure webhook verification](https://docs.retellai.com/features/secure-webhook)
- [Inbound webhook behavior](https://docs.retellai.com/features/inbound-call-webhook)
