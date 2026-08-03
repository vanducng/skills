"""vd_langfuse - Zero-dependency Langfuse OTLP/JSON exporter.

Langfuse ingests OTLP over HTTP with a JSON body, so the whole exporter is
stdlib: no langfuse SDK, no uv, no pip. Credentials come from the environment
(LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_BASE_URL).

Span ids are derived deterministically from the session id, so re-running the
exporter over a longer transcript appends new turns to the same Langfuse trace
instead of creating a duplicate.
"""

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://cloud.langfuse.com"
OTLP_PATH = "/api/public/otel/v1/traces"
TIMEOUT_S = 20
MAX_CHARS_DEFAULT = 20000
BATCH_SIZE = 400


class LangfuseConfig:
    def __init__(self, public_key, secret_key, base_url, user_id=None,
                 environment=None, max_chars=MAX_CHARS_DEFAULT, debug=False):
        self.public_key = public_key
        self.secret_key = secret_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.user_id = user_id
        self.environment = environment
        self.max_chars = max_chars
        self.debug = debug

    @property
    def enabled(self):
        return bool(self.public_key and self.secret_key)

    @property
    def auth_header(self):
        raw = "%s:%s" % (self.public_key, self.secret_key)
        return "Basic " + base64.b64encode(raw.encode("utf-8")).decode("ascii")


ENVRC_KEYS = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL")
_ENVRC_LINE = re.compile(
    r"""^\s*(?:export\s+)?(LANGFUSE_[A-Z_]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s#]+))\s*(?:#.*)?$""")


def load_envrc(path=None):
    """Read literal LANGFUSE_* assignments out of an .envrc.

    Agent hooks don't inherit a direnv-loaded shell, so the keys usually aren't
    in os.environ. This reads them textually and NEVER executes the file - a
    real .envrc also shells out to secret managers, which would hang a hook.
    Values containing shell expansion ($, `, ()) are skipped as unresolvable.
    """
    path = path or os.path.expanduser("~/.envrc")
    found = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                match = _ENVRC_LINE.match(line)
                if not match:
                    continue
                key = match.group(1)
                if key not in ENVRC_KEYS:
                    continue
                value = next((g for g in match.groups()[1:] if g is not None), "")
                if any(ch in value for ch in "$`("):
                    continue
                found[key] = value
    except OSError:
        return {}
    return found


def load_config(env=None):
    """Build config from the environment, falling back to ~/.envrc. Never raises."""
    env = dict(env if env is not None else os.environ)
    if not (env.get("LANGFUSE_PUBLIC_KEY") and env.get("LANGFUSE_SECRET_KEY")):
        for key, value in load_envrc(env.get("VD_LANGFUSE_ENVRC")).items():
            env.setdefault(key, value)
    max_chars = MAX_CHARS_DEFAULT
    try:
        max_chars = int(env.get("VD_LANGFUSE_MAX_CHARS") or MAX_CHARS_DEFAULT)
    except (TypeError, ValueError):
        pass
    return LangfuseConfig(
        public_key=env.get("LANGFUSE_PUBLIC_KEY"),
        secret_key=env.get("LANGFUSE_SECRET_KEY"),
        base_url=env.get("LANGFUSE_BASE_URL"),
        user_id=env.get("VD_LANGFUSE_USER_ID") or env.get("LANGFUSE_USER_ID") or env.get("USER"),
        environment=env.get("VD_LANGFUSE_ENVIRONMENT") or env.get("LANGFUSE_TRACING_ENVIRONMENT"),
        max_chars=max_chars,
        debug=bool(env.get("VD_LANGFUSE_DEBUG")),
    )


def _hex(seed, width):
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:width]


def trace_id_for(session_id, seed=""):
    return _hex("vd-langfuse:trace:%s:%s" % (seed, session_id), 32)


def span_id_for(session_id, suffix, seed=""):
    return _hex("vd-langfuse:span:%s:%s:%s" % (seed, session_id, suffix), 16)


def _truncate(value, max_chars):
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    if len(text) > max_chars:
        return text[:max_chars] + "\n...[truncated %d chars]" % (len(text) - max_chars)
    return text


def _attr(key, value):
    if isinstance(value, bool):
        return {"key": key, "value": {"boolValue": value}}
    if isinstance(value, int):
        return {"key": key, "value": {"intValue": str(value)}}
    if isinstance(value, float):
        return {"key": key, "value": {"doubleValue": value}}
    if isinstance(value, (list, tuple)):
        return {"key": key, "value": {"arrayValue": {
            "values": [{"stringValue": str(v)} for v in value]}}}
    return {"key": key, "value": {"stringValue": str(value)}}


def build_attributes(mapping):
    return [_attr(k, v) for k, v in mapping.items() if v is not None]


def make_span(trace_id, span_id, name, start_ns, end_ns, attributes, parent_span_id=None):
    span = {
        "traceId": trace_id,
        "spanId": span_id,
        "name": name,
        "kind": 1,
        "startTimeUnixNano": str(int(start_ns)),
        # A zero-length span renders as an instant in Langfuse; keep end >= start.
        "endTimeUnixNano": str(max(int(end_ns), int(start_ns))),
        "attributes": build_attributes(attributes),
    }
    if parent_span_id:
        span["parentSpanId"] = parent_span_id
    return span


def usage_attributes(usage):
    """Map a normalized usage dict onto Langfuse/OTel token attributes."""
    if not usage:
        return {}
    out = {}
    for src, dst in (
        ("input", "gen_ai.usage.input_tokens"),
        ("output", "gen_ai.usage.output_tokens"),
        ("cache_read", "gen_ai.usage.cache_read_input_tokens"),
        ("cache_write", "gen_ai.usage.cache_creation_input_tokens"),
        ("reasoning", "gen_ai.usage.reasoning_tokens"),
    ):
        value = usage.get(src)
        if isinstance(value, int) and value >= 0:
            out[dst] = value
    return out


def export_spans(config, spans, service_name="vd-agents"):
    """POST spans to Langfuse, batching so a long session can't blow the request
    size limit. Returns (ok, status, detail); the first failing batch stops the run."""
    if not config.enabled:
        return False, 0, "langfuse credentials not set"
    if not spans:
        return True, 0, "no spans"

    sent = 0
    for start in range(0, len(spans), BATCH_SIZE):
        batch = spans[start:start + BATCH_SIZE]
        ok, status, detail = _post_batch(config, batch, service_name)
        if not ok:
            return False, status, "%s (after %d/%d spans)" % (detail, sent, len(spans))
        sent += len(batch)
    return True, 200, "%d spans" % sent


def _post_batch(config, spans, service_name):
    payload = {"resourceSpans": [{
        "resource": {"attributes": build_attributes({"service.name": service_name})},
        "scopeSpans": [{"scope": {"name": "vd-langfuse"}, "spans": spans}],
    }]}

    request = urllib.request.Request(
        config.base_url + OTLP_PATH,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": config.auth_header,
            "x-langfuse-ingestion-version": "4",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return True, response.status, "ok"
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        return False, exc.code, body
    except Exception as exc:
        return False, 0, str(exc)
