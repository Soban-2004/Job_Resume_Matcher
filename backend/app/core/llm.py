import json
import re
import time
from functools import lru_cache

from groq import BadRequestError, Groq, RateLimitError
from pydantic import BaseModel

from app.config import settings

_MAX_RETRY_ATTEMPTS = 5
_DEFAULT_BACKOFF_SECONDS = 5.0
# Separate from rate-limit retries: a smaller model can occasionally
# hallucinate extra, unasked-for content into a structured response, bloating
# it past the token budget and truncating into genuinely invalid JSON that no
# amount of parsing can recover. Since temperature isn't 0, a fresh attempt at
# the same prompt often just succeeds -- cheaper than tightening the schema
# further and still gives up cleanly rather than looping forever.
_MAX_MALFORMED_RETRY_ATTEMPTS = 2
# Groq's 429 body can report a wait tied to a daily/longer quota, not just
# the per-minute one -- without a cap, a single retry could silently block
# for a very long time with zero visibility, indistinguishable from a hang.
_MAX_BACKOFF_SECONDS = 75.0

# Per-model TPM ceilings on Groq's free/on-demand tier (see console.groq.com
# rate limits). A 413 "request too large" is NOT retryable -- the same
# oversized request fails every time -- so this must be checked and the
# prompt trimmed *before* sending, not handled reactively like rate limits.
_MODEL_TPM_LIMITS = {
    "llama-3.1-8b-instant": 6000,
    "llama-3.3-70b-versatile": 12000,
    "openai/gpt-oss-20b": 8000,
    "openai/gpt-oss-120b": 8000,
    "qwen/qwen3.6-27b": 8000,
}
_DEFAULT_TPM_LIMIT = 6000  # conservative fallback for any unlisted model
_CHARS_PER_TOKEN_ESTIMATE = 4  # rough heuristic, no tokenizer dependency needed
# Real technical text (resumes/JDs: acronyms, punctuation, camelCase schema
# fields) tokenizes less efficiently than plain English, so the 4-chars/token
# heuristic underestimates true usage. A wide margin absorbs that error.
_TPM_SAFETY_MARGIN = 0.7


def _estimate_tokens(text: str) -> int:
    return len(text) // _CHARS_PER_TOKEN_ESTIMATE


def _fit_user_prompt_to_budget(
    system: str, user: str, model: str, max_completion_tokens: int, extra_tokens: int = 0
) -> str:
    """Truncates `user` so system + user + completion (+ any extra, e.g. a
    tool schema) tokens stay under the model's per-minute ceiling, instead of
    discovering the overage as a 413 only after the request is already sent.
    """
    tpm_limit = _MODEL_TPM_LIMITS.get(model, _DEFAULT_TPM_LIMIT)
    budget = int(tpm_limit * _TPM_SAFETY_MARGIN) - max_completion_tokens - extra_tokens
    available_for_user = max(200, budget - _estimate_tokens(system))

    if _estimate_tokens(user) <= available_for_user:
        return user

    max_chars = available_for_user * _CHARS_PER_TOKEN_ESTIMATE
    return user[:max_chars] + "\n\n[...input truncated to fit the model's context limit...]"


@lru_cache
def get_groq_client() -> Groq:
    # An explicit timeout matters here: without one, a stalled connection
    # can block a worker thread forever with no way to recover, rather than
    # failing loudly so the retry logic in _call_with_retry can act.
    return Groq(api_key=settings.groq_api_key, timeout=60.0)


def _retry_delay_seconds(error: RateLimitError) -> float:
    """Groq's free/on-demand tier has low TPM limits that concurrent requests
    can exceed quickly; the 429 body tells us exactly how long to wait.
    """
    try:
        retry_after = error.response.headers.get("retry-after")
        if retry_after:
            return float(retry_after)
    except Exception:
        pass

    match = re.search(r"try again in ([\d.]+)s", str(error))
    if match:
        return float(match.group(1))

    return _DEFAULT_BACKOFF_SECONDS


def _recover_from_malformed_tool_call(error: BadRequestError, schema: type[BaseModel]) -> BaseModel | None:
    """Smaller/faster models occasionally emit a well-formed tool call as
    plain text (e.g. '<function=name>{...}</function>') instead of using
    the API's native tool_calls field, which Groq rejects outright as
    tool_use_failed. The JSON payload itself is often still valid -- salvage
    it instead of failing the whole request.
    """
    try:
        body = error.body or {}
        failed_generation = body.get("error", {}).get("failed_generation", "")
        match = re.search(r"\{.*\}", failed_generation, re.DOTALL)
        if not match:
            print("[groq] recovery: no JSON-like blob found in failed_generation", flush=True)
            return None
        return schema.model_validate_json(match.group())
    except Exception as e:
        print(f"[groq] recovery: parse attempt failed ({type(e).__name__}: {e})", flush=True)
        return None


def is_daily_quota_error(error: RateLimitError) -> bool:
    """Distinguishes a daily (RPD/TPD) quota exhaustion from an ordinary
    per-minute rate limit. The latter clears itself within _MAX_BACKOFF_SECONDS;
    the former won't clear for hours, so retrying it is pure wasted wait time --
    callers should fall back to a different model instead.
    """
    return "per day" in str(error).lower()


def _call_with_retry(fn):
    for attempt in range(_MAX_RETRY_ATTEMPTS):
        try:
            return fn()
        except RateLimitError as e:
            if is_daily_quota_error(e):
                print("[groq] daily quota exhausted, not retrying", flush=True)
                raise
            if attempt == _MAX_RETRY_ATTEMPTS - 1:
                raise
            wait = min(_retry_delay_seconds(e) + 0.5, _MAX_BACKOFF_SECONDS)
            print(
                f"[groq] rate limited (attempt {attempt + 1}/{_MAX_RETRY_ATTEMPTS}), "
                f"waiting {wait:.1f}s before retry",
                flush=True,
            )
            time.sleep(wait)


def call_llm(
    system: str,
    user: str,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    reasoning_effort: str | None = None,
) -> str:
    """Plain-text completion (cover letters, free-form prose).

    reasoning_effort is only meaningful for reasoning-capable models (Qwen,
    gpt-oss) -- their default behavior is to spend a chunk of max_tokens on
    an internal <think> trace before the actual answer, which can consume
    the whole budget and leave nothing for the response itself.
    "none" suppresses that trace entirely. Omitted (not passed) for models
    that don't support the param, since Groq rejects it outright otherwise.
    """
    resolved_model = model or settings.llm_model
    user = _fit_user_prompt_to_budget(system, user, resolved_model, max_tokens)
    client = get_groq_client()

    def _make_request():
        kwargs = {}
        if reasoning_effort is not None:
            kwargs["reasoning_effort"] = reasoning_effort
        return client.chat.completions.create(
            model=resolved_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    response = _call_with_retry(_make_request)
    return response.choices[0].message.content or ""


def call_structured(
    system: str,
    user: str,
    schema: type[BaseModel],
    model: str | None = None,
    temperature: float = 0.2,
    max_completion_tokens: int = 1024,
) -> BaseModel:
    """Force the model to return JSON matching `schema` via tool-calling.

    Replaces the old approach of regexing `{...}` out of free-form text --
    Groq validates the tool-call arguments against the JSON schema itself,
    so a malformed response fails the API call instead of silently parsing
    into garbage.
    """
    resolved_model = model or settings.llm_model
    client = get_groq_client()
    tool_name = f"emit_{schema.__name__.lower()}"
    tool = {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": f"Return the extracted data conforming to the {schema.__name__} schema.",
            "parameters": schema.model_json_schema(),
        },
    }
    # The tool/function schema is itself part of the request payload and
    # counts against the same TPM budget -- ignoring it was a real gap that
    # let requests through under-counted by up to a couple hundred tokens.
    tool_schema_tokens = _estimate_tokens(json.dumps(tool))
    user = _fit_user_prompt_to_budget(
        system, user, resolved_model, max_completion_tokens, extra_tokens=tool_schema_tokens
    )

    def _make_request():
        return client.chat.completions.create(
            model=resolved_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            tools=[tool],
            tool_choice={"type": "function", "function": {"name": tool_name}},
            temperature=temperature,
            # Without an explicit budget, a structured response can hit the
            # model's default completion-token ceiling mid-JSON, producing
            # an unrecoverable truncated tool call instead of a clean one.
            max_completion_tokens=max_completion_tokens,
        )

    for attempt in range(_MAX_MALFORMED_RETRY_ATTEMPTS + 1):
        try:
            response = _call_with_retry(_make_request)
        except BadRequestError as e:
            recovered = _recover_from_malformed_tool_call(e, schema)
            if recovered is not None:
                return recovered
            if attempt < _MAX_MALFORMED_RETRY_ATTEMPTS:
                print(
                    f"[groq] malformed/truncated tool call (attempt {attempt + 1}/"
                    f"{_MAX_MALFORMED_RETRY_ATTEMPTS + 1}), retrying",
                    flush=True,
                )
                continue
            raise

        message = response.choices[0].message
        if not message.tool_calls:
            if attempt < _MAX_MALFORMED_RETRY_ATTEMPTS:
                continue
            raise ValueError(f"Model did not return a tool call for schema {schema.__name__}")

        arguments = message.tool_calls[0].function.arguments
        return schema.model_validate_json(arguments)
