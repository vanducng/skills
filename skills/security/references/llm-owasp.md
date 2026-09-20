# OWASP LLM Top-10 (2025) + agent/MCP lens

Run this in addition to STRIDE×OWASP whenever the scope calls an LLM, builds a prompt from user/tool/retrieved data, or gives a model the ability to act. Map findings the same way (verdict, severity only if `confirmed`, `file:line`, masked PoC, remediation).

Agent/MCP rows below are distilled from Cloudflare `security-audit-skill` AI-AND-LLM (MIT).

| Ref | Category | Inspect for | Remediation anchor |
|---|---|---|---|
| **LLM01** | Prompt injection | User/tool/retrieved text concatenated into a prompt and treated as instructions; system prompt assumed to be a security boundary (it is not). | Treat all non-system text as data; constrain output format; don't let model output trigger privileged actions without a deterministic gate. |
| **LLM02 / LLM07** | Sensitive-info disclosure / system-prompt leakage | Secrets, keys, or other tenants' data in the prompt/context; cross-tenant context bleed; prompt caches keyed too broadly. | No secrets in prompts; per-tenant context isolation; assume the system prompt is exfiltratable. |
| **LLM05** | Improper output handling | Model output flowing unescaped into `eval`, SQL, shell, `innerHTML`, file paths, or a downstream API. The model is an **untrusted input source**. | Validate/escape model output at every sink exactly like user input; never `eval` it. |
| **LLM06** | Excessive agency | Tools with broader scope than the task; write/delete/spend/send with no human gate; unbounded tool-call loops. | Least-privilege tools; confirmation gate on irreversible/outbound actions; cap tool-call depth and spend. |
| **LLM08** | Vector/embedding weaknesses | RAG store mixing tenants or trust levels; unsanitized documents indexed (injection-via-retrieval); no per-tenant partition on retrieval. | Partition the index per tenant/trust level; sanitize + attribute retrieved chunks; treat retrieved text as LLM01 data. |
| **LLM10** | Unbounded consumption | No token/cost/rate cap per request or per tenant; user-controlled `max_tokens`/loops; model-driven loops with no ceiling. | Hard caps on tokens, cost, tool-call count, and recursion depth; per-tenant quotas. |

## Agent / MCP extensions (beyond the Top-10 labels)

**Prompt injection alone is not a finding.** Require a code-level boundary failure: content reaches another principal's context, invokes authority the requester lacks, discloses data they cannot read, or drives a sink they cannot reach directly. A guardrail prompt is not a security boundary.

| Class | Hunt for |
|---|---|
| **Indirect injection via retrieval** | Attacker-writable RAG/email/issue/tool text enters another principal's context with enabled capabilities |
| **Persistent memory poisoning** | Low-trust content written into memory that later shapes another user or privileged session |
| **Prompt role / provenance confusion** | Untrusted text impersonates system/tool/memory via concatenation or caller-controlled roles |
| **Tool-argument injection** | Model args reach SQL/shell/file/URL/privileged APIs without handler-side validation - schema ≠ authz |
| **Confused deputy** | Agent uses a broad service identity; handler does not re-check requester permission on the named resource |
| **Action-binding failure** | User approved action A; execution uses mutated args/resource/principal, or attacker content triggers a side effect under a victim's valid authority without that victim's intentional request |
| **Tool-schema vs dispatcher disagreement** | Aliases, extra fields, coercions accepted by schema but interpreted differently by handler |
| **MCP / sub-agent trust inheritance** | Delegate gets full session/credentials/memory instead of least authority |
| **MCP identity confusion** | Routing by attacker-influenceable server/tool names rather than authenticated connection + outstanding request |
| **MCP metadata as policy** | Peer-supplied descriptions/schemas treated as authorization - must not grant capability |

## Quick greps

- Prompt construction from request/DB/retrieval: `` grep -rnE 'system|user|prompt' `` near string-concat with request data.
- Output sinks: model response feeding `eval(`, `exec(`, raw SQL, `dangerouslySetInnerHTML`, `child_process`, path joins.
- Tool definitions: enumerate every tool/function the agent can call - does any write, delete, pay, or send with no gate?
- Caps: search the LLM call site for `max_tokens`, timeout, rate-limit, per-tenant quota - absence is LLM10.
- MCP: server/tool registration, capability narrowing on delegate, whether metadata can expand allowlists.

## Posture

The model is a confused-deputy waiting to happen: it will faithfully follow injected instructions and faithfully emit unsafe output. Defenses are **deterministic and around** the model (input boundaries, output validation, least-privilege tools, hard caps, action binding), never "ask the model to behave."
