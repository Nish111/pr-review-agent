"""LLM provider layer, COPIED from the memory project (handoff: "copy, don't rewrite").

Source: AI-Sprint-Execution/05-Memory-Intelligence-System/incident_memory/spikes/extraction.py
(commit b62a943), the section from `class SpikeError` to the end of `pick_provider`. Only two changes:
the memory project's `Result` dataclass is left out, and USER_AGENT names this project.
Every comment below is the memory project's, including the incidents that justify each rule
(503 storms, daily vs per-minute 429s, Cloudflare 1010, Gemini reasoning tokens). They cost
real quota to learn and apply unchanged here.

Standard library only. temperature = 0 on every call. Keys come only from the environment.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request


class SpikeError(RuntimeError):
    pass


class ProviderUnavailable(SpikeError):
    """HTTP 503 twice in a row on one call: the provider is overloaded right now.

    M9 decision 503=A (review/DECIDE_M9_503.md). On 13 and 14 Oct, 503s retried 4 times each spent
    the whole 20-request daily quota before one answer came back (~58 requests, 0 answers). A 503
    now gets ONE retry; a caller that loops over many calls can stop the run on this class.
    """


class QuotaExhausted(SpikeError):
    """The provider's DAILY budget is gone. Every further request in this run will fail.

    A subclass rather than a flag, so a caller can stop the whole run on it while still
    treating ordinary SpikeErrors as per-document failures. The difference matters: one
    document failing is a gap to retry, a spent daily quota is the end of the session.
    """



# --------------------------------------------------------------------------- providers


TRANSPORT_ATTEMPTS = 4
"""How many times to retry a request that never produced an answer.

This is NOT a retry of the model. ADR-0001 forbids asking again for a better answer; it
says nothing about a TCP connection that hung, because a connection that hung produced no
answer to be dissatisfied with. The two are different events and only one of them is a
result. Transport attempts are counted into every result file so the distinction is
auditable rather than asserted.

Retried: timeouts, dropped connections, 429 rate limits, 5xx.
Not retried: 400/401/403/404 — those are configuration errors and repeating them is noise.
"""

USER_AGENT = "pr-review-agent/0.1 (stdlib urllib)"
"""Sent on every request, because the default one gets us blocked.

urllib announces itself as `Python-urllib/3.13`, and Groq sits behind Cloudflare, which
rejects that with HTTP 403 and `error code: 1010` before the request ever reaches Groq.
That is an edge block, not an auth failure - the key was fine - and the two look identical
if you only read the status code.

Not evasion: this is an honest identifier for an API client calling a public API with a
valid key. The point is to be identifiable, not to look like a browser.
"""

_ATTEMPTS = [TRANSPORT_ATTEMPTS]
"""Current transport-attempt budget. A one-element list so it can be swapped per run.

Module state, deliberately, because the provider functions are dispatched through a table
with a fixed signature and threading a parameter through every one of them to configure a
retry policy would be worse. `transport_budget()` is the only way it changes.
"""


class transport_budget:  # noqa: N801 - reads as a context manager at the call site
    """Temporarily change how many times a failed request is retried.

    Needed because retry policy is not a property of the code, it is a property of the
    PROVIDER. On Groq, where the constraint is tokens per minute, four attempts cost
    nothing but time. On Google, where the constraint is twenty requests per DAY, four
    attempts on three flaky documents is over half the budget - and this is the second time
    that has happened here. The first was 429s on the M4 baseline; this time it was 503s,
    which the terminal-quota check does not catch because a 503 genuinely is transient.

    The lesson that keeps recurring: a retry is only free when the thing being retried is
    not the scarce resource.
    """

    def __init__(self, n: int) -> None:
        self.n = max(1, int(n))

    def __enter__(self):
        self.previous = _ATTEMPTS[0]
        _ATTEMPTS[0] = self.n
        return self

    def __exit__(self, *exc) -> None:
        _ATTEMPTS[0] = self.previous


RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}

TERMINAL_QUOTA = re.compile(r"PerDay|per day|quota exceeded for metric.*free_tier", re.IGNORECASE)
"""A 429 is retryable; an EXHAUSTED DAILY quota is not, and the two arrive as the same code.

This cost a whole day's quota on the M4 run. Four probes failed transiently, each retry run
re-requested them, and every one of those requests burned four transport attempts against a
free-tier bucket of twenty per day. The retries did not fail because of the quota - they
CONSUMED the quota, and then failed because of it.

A per-minute limit clears inside the run and is worth waiting out. A per-day limit does not,
so retrying it is not resilience: it is spending the only thing that could have made the next
attempt work. Fail fast and say which kind it was.
"""

RETRY_HINT = re.compile(
    r"(?:retry in|try again in|retryDelay\"?\s*:\s*\"?)\s*([\d.]+)\s*s", re.IGNORECASE)
MAX_HINTED_WAIT = 90.0
"""Providers return 429 with the exact wait in the body. Honour it; guess only when there
is nothing to honour.

Two phrasings, because assuming one cost a run. Google says "Please retry in 24.366s";
Groq says "Please try again in 9.45s". The first version of this pattern matched only
"retry in", so every Groq hint was missed and the backoff fell back to 5/10/15s against a
server that had asked for 9.45s - which is how three documents burned four transport
attempts each and still failed. A regex that silently matches nothing is worse than no
regex, because the fallback looks like a decision rather than a miss.
"""


SHORT_WAIT_S = 600.0


def _short_wait(detail: str) -> bool:
    """A free-tier 429 that asks for a wait of seconds is a PER-MINUTE limit, not the day's quota.

    17 Oct: the body said "Quota exceeded for metric: ...free_tier_requests, limit: 5 ... Please retry
    in 52.7s". TERMINAL_QUOTA matched the metric name and the run aborted as "daily quota exhausted"
    after 6 requests sent in 46 s. The daily case says "retry in 16h38m...", which RETRY_HINT does not
    match (it only reads a plain number of seconds), so a matched hint under 10 minutes means wait.
    """
    hint = RETRY_HINT.search(detail)
    return bool(hint) and float(hint.group(1)) < SHORT_WAIT_S


def _edge_hint(code: int, detail: str) -> str:
    """Tell a CDN block apart from a rejected key. Both arrive as 403."""
    if code == 403 and "1010" in detail:
        return ("\n-> Cloudflare edge block (code 1010), NOT an authentication failure. The "
                "request was rejected before it reached the API, because of the client's "
                "User-Agent. Your key is not the problem.")
    return ""


def _redact(url: str) -> str:
    """Strip credentials out of a URL before it can reach a log, a terminal or a paste.

    Google passes the API key as a query parameter, so any error message quoting the URL
    quotes the key with it. That is the same class of mistake as a credential in a log
    line -- the fix is to scrub on the way out, not to remember not to paste it.
    """
    return re.sub(r"([?&](?:key|api_key|access_token)=)[^&\s]+", r"\1<redacted>", url)


HTTP_ATTEMPTS = [0]
"""Every HTTP request actually sent, retries included. M9: the trace counted one model_call per
logical call, but a 503 retried 4 times is 4 requests against a 20-a-day free quota. On 13 Oct five
503-retried calls (5 x 4 = 20 requests) spent a whole day's quota before a single answer came back.
Read by trace.py; changes nothing else."""


MAX_503_ATTEMPTS = 2
"""Requests one logical call may spend on HTTP 503 (1 try + 1 retry). M9 decision 503=A. Other
retryable failures keep the full transport budget: a per-minute 429 or a timeout is not evidence
that the provider is overloaded, and their waits are hinted or short."""


def http_attempts() -> int:
    return HTTP_ATTEMPTS[0]


def _post(url: str, headers: dict, payload: dict, timeout: int = 240) -> tuple[dict, int]:
    """Returns (response, transport_attempts_used)."""
    body = json.dumps(payload).encode("utf-8")
    last: Exception | None = None

    limit = _ATTEMPTS[0]
    for attempt in range(1, limit + 1):
        HTTP_ATTEMPTS[0] += 1
        req = urllib.request.Request(url, data=body,
                                     headers={"User-Agent": USER_AGENT, **headers},
                                     method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8")), attempt
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:600]
            if e.code == 413 or (e.code == 400 and "too large" in detail.lower()):
                # Structurally too large for this model/tier. Waiting cannot fix it: the
                # request exceeds the per-minute token cap ON ITS OWN, so the budget is
                # never large enough however long you pause. Distinct from 429, which is
                # the same cap with the minute already partly spent - that one does clear.
                raise SpikeError(
                    f"HTTP {e.code} from {_redact(url)} - request too large for this "
                    f"model/tier ON ITS OWN, not a transient rate limit.\n{detail}\n"
                    "Waiting will not help. Use a model or tier with a larger per-request "
                    "budget, or send less in one request."
                ) from e
            if e.code not in RETRYABLE_STATUS:
                raise SpikeError(f"HTTP {e.code} from {_redact(url)}\n{detail}"
                                 + _edge_hint(e.code, detail)) from e
            if e.code == 429 and TERMINAL_QUOTA.search(detail) and not _short_wait(detail):
                raise QuotaExhausted(
                    f"HTTP 429 from {_redact(url)} - DAILY quota exhausted, not a rate limit.\n"
                    f"{detail}\n"
                    "Not retried: every retry spends the quota it is waiting for. Either wait for "
                    "the daily window to reset, or re-run the whole set on one different provider "
                    "so the measurement stays single-model."
                ) from e
            if e.code == 503 and attempt >= MAX_503_ATTEMPTS:
                raise ProviderUnavailable(
                    f"HTTP 503 from {_redact(url)} on {attempt} attempts - provider unavailable "
                    f"(overloaded).\n{detail}\n"
                    "Not retried further: each retry is one more request out of the 20 a day the next "
                    "run needs (M9 decision 503=A)."
                ) from e
            last = SpikeError(f"HTTP {e.code} from {_redact(url)}\n{detail}")
        except Exception as e:  # noqa: BLE001 - timeouts, resets, DNS
            last = e

        if attempt < limit:
            hint = RETRY_HINT.search(str(last))
            if hint:
                wait = min(float(hint.group(1)) + 1.0, MAX_HINTED_WAIT)
            elif "503" in str(last):
                wait = 15 * attempt
            else:
                wait = 5 * attempt
            print(f"    transport attempt {attempt} failed ({type(last).__name__}); "
                  f"retrying in {wait}s", flush=True)
            time.sleep(wait)

    raise SpikeError(
        f"{limit} transport attempt(s) failed against {_redact(url)}\n"
        f"last error: {last}\n"
        "No model output was produced, so nothing has been recorded and re-running is not a retry."
    )


def call_anthropic(model: str, prompt: str, api_key: str) -> str:
    data, _ = _post(
        "https://api.anthropic.com/v1/messages",
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        {
            "model": model,
            "max_tokens": 2000,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
    return "".join(parts)


def call_openai(model: str, prompt: str, api_key: str,
                base_url: str = "https://api.openai.com/v1") -> str:
    """OpenAI Chat Completions, or anything that speaks the same shape.

    Groq, OpenRouter, Together, LM Studio and Ollama all expose this endpoint, so one
    implementation covers every free option worth using. `base_url` is what switches
    between them.
    """
    data, _ = _post(
        f"{base_url.rstrip('/')}/chat/completions",
        {"Authorization": f"Bearer {api_key or 'not-needed'}", "content-type": "application/json"},
        {
            "model": model,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    return data["choices"][0]["message"]["content"]


GEMINI_MAX_OUTPUT = 8192
"""Was 2000, and that is what broke the M5 extraction on gemini-3.5-flash.

Fifteen of seventeen documents came back as "Unterminated string" - the JSON simply
stopped mid-value. Several responses also BEGAN mid-sentence. Both symptoms, one cause:
Gemini 3.x models emit reasoning parts, those count against maxOutputTokens, and the
answer is what gets cut when the budget runs out. A 2,000-token ceiling that was ample for
the M2 spike's five short fields is not ample for six fields over an 8,000-word postmortem
once thinking is sharing the budget.

Raised rather than tuned: output tokens are not the scarce resource on these free tiers -
REQUESTS are (20 per day). Spending a request and truncating the answer wastes the thing
that is actually limited, to save the thing that is not.
"""


def call_gemini(model: str, prompt: str, api_key: str, base_url: str = "") -> str:
    """Google Generative Language API. Free tier, no card required."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    data, _ = _post(
        url,
        {"content-type": "application/json"},
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": GEMINI_MAX_OUTPUT},
        },
    )
    try:
        candidate = data["candidates"][0]
    except (KeyError, IndexError) as e:
        raise SpikeError(f"unexpected Gemini response shape: {json.dumps(data)[:500]}") from e

    reason = candidate.get("finishReason", "")
    parts = candidate.get("content", {}).get("parts", [])

    # Drop reasoning parts. They are marked `thought: true` and are NOT the answer; joining
    # them to it is what produced responses that began mid-sentence, because the model's
    # own thinking was prepended to the JSON and the parser saw prose where an object
    # should have been.
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))

    if reason == "MAX_TOKENS":
        # Say what happened. A truncated answer handed to a JSON parser reports
        # "Unterminated string", which reads like the model produced malformed output
        # rather than correct output that was cut off - a completely different diagnosis
        # and a completely different fix.
        raise SpikeError(
            f"Gemini stopped at the output limit ({GEMINI_MAX_OUTPUT} tokens) before "
            f"finishing. The answer is truncated, not malformed. Raise GEMINI_MAX_OUTPUT "
            f"or shorten the input. Got {len(text):,} characters."
        )
    if not text.strip():
        raise SpikeError(
            f"Gemini returned no answer text (finishReason={reason!r}, "
            f"{len(parts)} part(s), all of them reasoning). Raw: {json.dumps(data)[:400]}"
        )
    return text


def list_models(provider: str, api_key: str, base_url: str) -> list[str]:
    """Ask the provider which models it will actually serve to THIS key.

    Worth its own command because guessing cost a run already: `gemini-2.5-flash` is
    documented, was in the model list, and returns 404 for a key created after it was
    retired for new projects. A published model id is a claim about the world; this is
    a fact about the account.

    Read-only, and on every provider here it is a separate endpoint from generation, so
    it does not spend generation quota.
    """
    if provider == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}&pageSize=200"
        headers: dict[str, str] = {}
    elif provider == "anthropic":
        url = "https://api.anthropic.com/v1/models?limit=200"
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
    else:
        url = f"{(base_url or 'https://api.openai.com/v1').rstrip('/')}/models"
        headers = {"Authorization": f"Bearer {api_key or 'not-needed'}"}

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers},
                                 method="GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        raise SpikeError(f"HTTP {e.code} from {_redact(url)}\n{detail}"
                         + _edge_hint(e.code, detail)) from e

    if provider == "gemini":
        return sorted(
            m["name"].removeprefix("models/")
            for m in data.get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
        )
    return sorted(m["id"] for m in data.get("data", data.get("models", [])) if m.get("id"))


PROVIDERS = {
    "anthropic": call_anthropic,
    "openai": call_openai,
    "gemini": call_gemini,
}

# Everything OpenAI-compatible routes through call_openai with a different base URL.
OPENAI_COMPATIBLE = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://localhost:11434/v1",
}


def pick_provider(forced: str | None = None) -> tuple[str, str, str]:
    """Return (provider_name, api_key, base_url).

    Explicit --provider wins. Otherwise the first key found, in this order. The order is
    not a quality judgement; it is just deterministic so two runs on the same machine hit
    the same endpoint.
    """
    env_key = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "ollama": None,  # local, no key
    }

    def resolve(name: str) -> tuple[str, str, str]:
        base = OPENAI_COMPATIBLE.get(name, "")
        if name in OPENAI_COMPATIBLE:
            base = os.environ.get(f"{name.upper()}_BASE_URL", base)
        var = env_key[name]
        key = os.environ.get(var, "") if var else ""
        if var and not key:
            raise SpikeError(f"--provider {name} needs {var} set in your environment.")
        return name, key, base

    if forced:
        if forced not in env_key:
            raise SpikeError(f"unknown provider {forced!r}. "
                             f"Choose from: {', '.join(sorted(env_key))}")
        return resolve(forced)

    for name in ("anthropic", "openai", "gemini", "groq", "openrouter"):
        if os.environ.get(env_key[name] or ""):
            return resolve(name)

    raise SpikeError(
        "No API key found, and no --provider given.\n"
        "\n"
        "Free options that need no card:\n"
        "  Google AI Studio  aistudio.google.com  -> export GEMINI_API_KEY=...\n"
        "  Groq              console.groq.com     -> export GROQ_API_KEY=...\n"
        "  Ollama (local)    already installed?   -> --provider ollama --model <name>\n"
        "\n"
        "Paid, if you prefer:\n"
        "  export ANTHROPIC_API_KEY=sk-ant-...   or   export OPENAI_API_KEY=sk-...\n"
        "\n"
        "Windows CMD  : set GEMINI_API_KEY=...\n"
        "PowerShell   : $env:GEMINI_API_KEY=\"...\"\n"
        "Git Bash     : export GEMINI_API_KEY=...\n"
        "\n"
        "Keys are read from the environment and never written to disk by this script."
    )
