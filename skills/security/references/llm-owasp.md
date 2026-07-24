# OWASP LLM Top-10 (2025) - the agentic-security lens

Run this in addition to STRIDE×OWASP whenever the scope calls an LLM, builds a prompt from user/tool/retrieved data, or gives a model the ability to act. Map findings the same way (severity, `file:line`, masked PoC, remediation).

| Ref | Category | Inspect for | Remediation anchor |
|---|---|---|---|
| **LLM01** | Prompt injection | User/tool/retrieved text concatenated into a prompt and treated as instructions; "ignore previous instructions" reachable; the system prompt assumed to be a security boundary (it is not). | Treat all non-system text as data; constrain output format; don't let model output trigger privileged actions without a deterministic gate. |
| **LLM02 / LLM07** | Sensitive-info disclosure / system-prompt leakage | Secrets, keys, or other tenants' data in the prompt/context; system prompt holding credentials or rules that leak; cross-tenant context bleed. | No secrets in prompts; per-tenant context isolation; assume the system prompt is exfiltratable. |
| **LLM05** | Improper output handling | Model output flowing unescaped into `eval`, SQL, shell, `innerHTML`, file paths, or a downstream API. The model is an **untrusted input source**. | Validate/escape model output at every sink exactly like user input; never `eval` it. |
| **LLM06** | Excessive agency | Tools/functions with broader scope than the task needs; write/delete/spend/send actions with no human gate; an agent that can chain tools toward irreversible effects. | Least-privilege tools; confirmation gate on irreversible/outbound actions; cap tool-call depth. |
| **LLM08** | Vector/embedding weaknesses | RAG store mixing tenants or trust levels; unsanitized documents indexed (injection-via-retrieval); no per-tenant partition on retrieval. | Partition the index per tenant/trust level; sanitize + attribute retrieved chunks; treat retrieved text as LLM01 data. |
| **LLM10** | Unbounded consumption | No token/cost/rate cap per request or per tenant; user-controlled `max_tokens`/loops; model-driven loops with no ceiling. | Hard caps on tokens, cost, tool-call count, and recursion depth; per-tenant quotas. |

## Quick greps

- Prompt construction from request/DB/retrieval: `` grep -rnE 'system|user|prompt' `` near string-concat with request data.
- Output sinks: model response feeding `eval(`, `exec(`, raw SQL, `dangerouslySetInnerHTML`, `child_process`, path joins.
- Tool definitions: enumerate every tool/function the agent can call - does any write, delete, pay, or send with no gate?
- Caps: search the LLM call site for `max_tokens`, timeout, rate-limit, per-tenant quota - absence is LLM10.

## Posture

The model is a confused-deputy waiting to happen: it will faithfully follow injected instructions and faithfully emit unsafe output. Defenses are **deterministic and around** the model (input boundaries, output validation, least-privilege tools, hard caps), never "ask the model to behave."
