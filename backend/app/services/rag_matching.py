import datetime as dt
import re
from typing import Callable

import numpy as np
import requests
from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel
from rank_bm25 import BM25Okapi

from app.config import settings
from app.core.app_logging import get_logger
from app.core.embeddings import embed_texts
from app.core.llm import call_llm, call_structured
from app.core.reranker import rerank
from app.core.vector_store import fetch_chunks, upsert_chunks
from app.models.schemas import (
    CertificationSuggestionList,
    RequirementVerdict,
    RubricResult,
    RubricResultCore,
)
from app.services.chunking import chunk_text


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _ranks_from_scores(scores: np.ndarray) -> np.ndarray:
    """Rank 0 = best. Ties broken by original order."""
    order = np.argsort(-scores, kind="stable")
    ranks = np.empty_like(order)
    ranks[order] = np.arange(len(scores))
    return ranks


def index_document(batch_id: str, filename: str, text: str) -> int:
    """Chunks a document and durably stores its embeddings. Returns chunk count."""
    logger = get_logger()
    logger.debug(
        "index_document filename=%s text_len=%d raw_text=%r", filename, len(text), text
    )
    chunks = chunk_text(text)
    logger.debug("index_document filename=%s chunk_count=%d chunks=%r", filename, len(chunks), chunks)
    upsert_chunks(batch_id, filename, chunks)
    return len(chunks)


def estimate_provisional_score(
    batch_id: str,
    filename: str,
    jd_skill_weights: dict[str, float],
    floor: float = 0.15,
    ceiling: float = 0.55,
) -> float:
    """Cheap, local, LLM-free round-1 screen: for each requirement, take the
    best dense cosine similarity against any resume chunk (no BM25, no
    reranker, no Groq call) as a continuous match-degree signal.

    `floor`/`ceiling` calibrate raw similarity into a 0-1 range: this
    embedding model's cosine scores for genuinely-unrelated text still sit
    around ~0.15-0.2 (never near 0) and even a strong topical match rarely
    clears ~0.55, so a hard threshold in between (e.g. 0.45) would zero out
    almost every real resume. Min-max scaling against this model's actual
    range keeps the score continuous.

    Any single requirement's dense score is noisy on its own (BM25 was tried
    per-requirement too, but with only a handful of chunks as the "corpus" its
    IDF term degenerates -- a term appearing in most of a resume's own chunks
    gets penalized, not rewarded, which is backwards for a presence signal).
    Real JDs carry 15-20+ weighted requirements, so per-requirement noise
    mostly cancels out in the weighted average -- exactly what round 1 needs:
    a relative ranking signal across candidates, not a precise per-skill
    verdict (that's what round 2's LLM review is for).
    """
    if not jd_skill_weights:
        return 0.0

    chunks = fetch_chunks(batch_id, filename)
    if not chunks:
        return 0.0

    vectors = np.array([c["vector"] for c in chunks])
    requirements = list(jd_skill_weights.keys())
    query_vectors = embed_texts(requirements)

    total_weight = sum(jd_skill_weights.values())
    if total_weight == 0:
        return 0.0

    weighted_sum = 0.0
    for i, requirement in enumerate(requirements):
        best_similarity = float(np.max(vectors @ query_vectors[i]))
        normalized = (best_similarity - floor) / (ceiling - floor)
        normalized = min(1.0, max(0.0, normalized))
        weighted_sum += jd_skill_weights[requirement] * normalized

    return min(100.0, weighted_sum / total_weight * 100)


def estimate_skill_match_score(
    jd_skill_weights: dict[str, float],
    resume_skills: dict[str, float],
    floor: float = 0.4,
    ceiling: float = 0.9,
) -> float:
    """Round 2's medium-cost narrowing signal: compares the JD's weighted
    skills against the candidate's own extracted skill list (from
    `extract_weighted_skills_from_resume`) via same-granularity phrase-vs-
    phrase cosine similarity -- both sides are short skill phrases, unlike
    round 1's phrase-vs-paragraph-chunk comparison. That granularity match
    makes this dramatically more discriminative: exact/near skill matches
    saturate near 1.0 raw cosine, unrelated pairs sit around 0.3-0.4, versus
    round 1's ~0.2-0.4 band for both matching and unrelated content.

    Still not evidence-grounded truth -- a resume can list a skill it can't
    actually back up -- which is exactly why this only decides who reaches
    round 3's real verification, never the final verdict itself.
    """
    if not jd_skill_weights or not resume_skills:
        return 0.0

    total_weight = sum(jd_skill_weights.values())
    if total_weight == 0:
        return 0.0

    jd_requirements = list(jd_skill_weights.keys())
    jd_vectors = embed_texts(jd_requirements)
    resume_vectors = embed_texts(list(resume_skills.keys()))

    weighted_sum = 0.0
    for i, requirement in enumerate(jd_requirements):
        best_similarity = float(np.max(resume_vectors @ jd_vectors[i]))
        normalized = (best_similarity - floor) / (ceiling - floor)
        normalized = min(1.0, max(0.0, normalized))
        weighted_sum += jd_skill_weights[requirement] * normalized

    return min(100.0, weighted_sum / total_weight * 100)


def retrieve_evidence(
    batch_id: str, filename: str, requirements: list[str], top_k: int | None = None
) -> dict[str, list[str]]:
    """For each requirement, fuse BM25 + dense-similarity rankings over the
    document's stored chunks, then rerank the fused candidates with a
    cross-encoder to pick the final evidence snippets.
    """
    logger = get_logger()
    top_k = top_k or settings.evidence_top_k
    empty = {req: [] for req in requirements}

    chunks = fetch_chunks(batch_id, filename)
    logger.debug(
        "retrieve_evidence filename=%s chunk_count=%d requirements=%r",
        filename,
        len(chunks),
        requirements,
    )
    for c in chunks:
        logger.debug(
            "retrieve_evidence filename=%s chunk_index=%s tokens=%r text=%r",
            filename,
            c.get("chunk_index"),
            _tokenize(c["text"]),
            c["text"],
        )
    if not chunks or not requirements:
        return empty

    texts = [c["text"] for c in chunks]
    vectors = np.array([c["vector"] for c in chunks])
    bm25 = BM25Okapi([_tokenize(t) for t in texts])
    query_vectors = embed_texts(requirements)

    evidence_map: dict[str, list[str]] = {}
    for i, requirement in enumerate(requirements):
        dense_scores = vectors @ query_vectors[i]
        bm25_scores = np.array(bm25.get_scores(_tokenize(requirement)))

        fused = (
            1.0 / (settings.rrf_k + _ranks_from_scores(dense_scores) + 1)
            + 1.0 / (settings.rrf_k + _ranks_from_scores(bm25_scores) + 1)
        )
        candidate_idx = np.argsort(-fused)[: settings.fusion_candidate_k]
        candidate_texts = [texts[idx] for idx in candidate_idx]

        logger.debug(
            "retrieve_evidence filename=%s requirement=%r tokenized_query=%r "
            "bm25_scores=%r dense_scores=%r fusion_candidates=%r",
            filename,
            requirement,
            _tokenize(requirement),
            bm25_scores.tolist(),
            dense_scores.tolist(),
            candidate_texts,
        )

        rerank_scores = rerank(requirement, candidate_texts)
        ranked = sorted(zip(candidate_texts, rerank_scores), key=lambda pair: pair[1], reverse=True)
        evidence_map[requirement] = [snippet for snippet, _ in ranked[:top_k]]

        logger.debug(
            "retrieve_evidence filename=%s requirement=%r rerank_scores=%r final_evidence=%r",
            filename,
            requirement,
            rerank_scores,
            evidence_map[requirement],
        )

    return evidence_map


def _requirement_section(requirement: str, weight: float, evidence_map: dict[str, list[str]]) -> str:
    snippets = evidence_map.get(requirement, [])
    evidence_block = "\n".join(f"- {s}" for s in snippets) if snippets else "(no evidence found)"
    return (
        f'Requirement: "{requirement}" (importance weight: {weight:.2f})\n'
        f"Evidence snippets from resume:\n{evidence_block}"
    )


# Qwen (qwen/qwen3.6-27b) is a reasoning model that reliably outperforms
# llama-3.1-8b-instant on evidence-citation accuracy, but fails outright
# under Groq's forced tool_choice -- it burns its completion budget on an
# internal <think> trace before ever emitting the tool call. The fix isn't a
# bigger budget (that just buys it more room to think, not to answer -- and
# at 4096 tokens it was still spending ~2400 on the trace alone); it's
# reasoning_effort="none" plus a plain-text completion instead of tool
# calling. Any model added here must go through _evaluate_rubric_batch_plaintext.
_PLAINTEXT_MODELS = {"qwen/qwen3.6-27b"}

_VERDICT_FIELD_RE = re.compile(
    r"^(requirement|satisfied|confidence|evidence|justification)\s*:\s*(.*)$", re.IGNORECASE
)

_BATCH_REASONING_RULES = (
    "Evaluate each requirement below using ONLY the evidence snippets provided for it. "
    "Each requirement's evidence snippets belong ONLY to that requirement -- never cite or "
    "reference a snippet from a different requirement's evidence block, even if it looks "
    "related to a different listed requirement. "
    "Within a requirement's OWN evidence snippets, prioritize in this order: "
    "(1) First, check whether any snippet names the exact requirement, or an unambiguous "
    "abbreviation/synonym of it. If one does, you MUST cite that exact snippet -- never "
    "substitute a different snippet that only shares a general subject area but never "
    "actually names the required skill/tool itself. "
    "(2) Only when no exact or near-exact mention exists, you may satisfy the requirement "
    "through a genuinely named specific instance of the required category (for a general "
    "category requirement like a platform or methodology family, naming one real member of "
    "that family counts as satisfying it -- a real subset relationship). Do not extend this "
    "same allowance to two separate, individually-named tools/skills that merely appear "
    "together often in practice -- naming one specific tool never demonstrates experience "
    "with a different specific tool. "
    "If no evidence is given, or the evidence doesn't clearly demonstrate the requirement "
    "under either rule above, mark satisfied=false. Do not assume or infer skills beyond "
    "what the evidence shows. "
)

_RUBRIC_SYSTEM_PROMPT = (
    "You are a meticulous technical recruiter who grounds every verdict strictly in cited evidence."
)


def _parse_plaintext_verdicts(raw: str) -> list[dict]:
    """Parses the Requirement/Satisfied/Confidence/Evidence/Justification block
    format used by the plain-text (non-tool-calling) rubric path. Deliberately
    lenient -- a block with a missing or malformed field just yields a partial
    dict, and _reconcile_batch_verdicts already backfills anything unusable,
    the same safety net that covers tool-calling failures.
    """
    blocks = re.split(r"\n\s*-{3,}\s*\n?", raw.strip())
    parsed: list[dict] = []
    for block in blocks:
        fields: dict[str, str] = {}
        current_key: str | None = None
        for line in block.splitlines():
            match = _VERDICT_FIELD_RE.match(line.strip())
            if match:
                current_key = match.group(1).lower()
                fields[current_key] = match.group(2).strip()
            elif current_key and line.strip():
                fields[current_key] += " " + line.strip()
        if "requirement" not in fields:
            continue
        requirement_match = re.search(r'"([^"]+)"', fields["requirement"])
        requirement = (
            requirement_match.group(1) if requirement_match else fields["requirement"].split("(")[0].strip()
        )
        try:
            confidence = float(fields.get("confidence", "0"))
        except ValueError:
            confidence = 0.0
        evidence_text = fields.get("evidence", "").strip().strip("'\"")
        evidence = [] if evidence_text.lower() in ("", "none") else [evidence_text]
        parsed.append(
            {
                "requirement": requirement,
                "weight": 0.0,  # overwritten by _reconcile_batch_verdicts with the real batch weight
                "satisfied": fields.get("satisfied", "").strip().lower() == "true",
                "confidence": max(0.0, min(1.0, confidence)),
                "justification": fields.get("justification", ""),
                "evidence": evidence,
            }
        )
    return parsed


def _call_structured_groq(model: str, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
    return call_structured(system=system, user=user, schema=schema, model=model)


def _resolve_schema_refs(schema, defs: dict):
    """Gemini's function-calling schema won't resolve $ref -- inline $defs manually."""
    if isinstance(schema, dict):
        if "$ref" in schema:
            return _resolve_schema_refs(defs[schema["$ref"].split("/")[-1]], defs)
        return {k: _resolve_schema_refs(v, defs) for k, v in schema.items()}
    if isinstance(schema, list):
        return [_resolve_schema_refs(item, defs) for item in schema]
    return schema


def _strip_unsupported_schema_keys(schema):
    """Gemini's function-calling schema is a subset of OpenAPI 3.0 -- drop keys
    it doesn't accept (title/default/$defs), recursively."""
    if not isinstance(schema, dict):
        return schema
    cleaned = {}
    for key, value in schema.items():
        if key in ("title", "default", "$defs"):
            continue
        if isinstance(value, dict):
            cleaned[key] = _strip_unsupported_schema_keys(value)
        elif isinstance(value, list):
            cleaned[key] = [_strip_unsupported_schema_keys(v) if isinstance(v, dict) else v for v in value]
        else:
            cleaned[key] = value
    return cleaned


_gemini_client: genai.Client | None = None


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    return _gemini_client


def _call_structured_gemini(model: str, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
    raw_schema = schema.model_json_schema()
    resolved_schema = _strip_unsupported_schema_keys(_resolve_schema_refs(raw_schema, raw_schema.get("$defs", {})))
    tool_name = f"emit_{schema.__name__.lower()}"
    tool = genai_types.Tool(
        function_declarations=[
            genai_types.FunctionDeclaration(
                name=tool_name,
                description=f"Return the extracted data conforming to the {schema.__name__} schema.",
                parameters=resolved_schema,
            )
        ]
    )
    config = genai_types.GenerateContentConfig(
        system_instruction=system,
        temperature=0.0,
        tools=[tool],
        tool_config=genai_types.ToolConfig(
            function_calling_config=genai_types.FunctionCallingConfig(mode="ANY", allowed_function_names=[tool_name])
        ),
    )
    response = _get_gemini_client().models.generate_content(model=model, contents=user, config=config)
    parts = response.candidates[0].content.parts
    function_call = next((p.function_call for p in parts if p.function_call), None)
    if function_call is None:
        raise RuntimeError(f"Gemini model {model} returned no function call")
    return schema.model_validate(dict(function_call.args))


def _call_structured_ollama(model: str, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
    tool_name = f"emit_{schema.__name__.lower()}"
    tool = {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": f"Return the extracted data conforming to the {schema.__name__} schema.",
            "parameters": schema.model_json_schema(),
        },
    }
    response = requests.post(
        "http://127.0.0.1:11434/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "tools": [tool],
            "options": {"temperature": 0.0},
            "stream": False,
        },
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        # Ollama Cloud's exact error taxonomy for rate/quota limits on the free
        # tier isn't fully characterized yet -- treat any error response here
        # as fallback-triggering rather than guessing at specific text to match.
        raise RuntimeError(f"Ollama error: {data['error']}")
    tool_calls = data.get("message", {}).get("tool_calls")
    if not tool_calls:
        raise RuntimeError(f"Ollama model {model} returned no tool call")
    return schema.model_validate(tool_calls[0]["function"]["arguments"])


def _build_rubric_toolcall_prompt(sections: list[str], requirement_count: int) -> str:
    return (
        _BATCH_REASONING_RULES
        + f"Return EXACTLY {requirement_count} verdict object(s) in the list -- one per requirement "
        "listed below, no more, no fewer, in the same order. Do not invent, add, or infer any "
        "additional requirements from the evidence text itself (e.g. do not turn resume phrases "
        "like job titles or skills into new requirements). Each verdict object must contain "
        "exactly these keys, each only once: requirement, weight, satisfied, confidence, "
        "justification, evidence.\n\n" + "\n\n".join(sections)
    )


def _evaluate_rubric_batch_toolcall(
    call_fn: Callable[[str, str, str, type[BaseModel]], BaseModel],
    model: str,
    batch: list[tuple[str, float]],
    sections: list[str],
    requirement_count: int,
    logger,
) -> list[RequirementVerdict]:
    user_prompt = _build_rubric_toolcall_prompt(sections, requirement_count)
    logger.debug(
        "_evaluate_rubric_batch_toolcall model=%s batch=%r prompt=%r",
        model,
        [req for req, _ in batch],
        user_prompt,
    )
    result: RubricResultCore = call_fn(model, _RUBRIC_SYSTEM_PROMPT, user_prompt, RubricResultCore)
    logger.debug(
        "_evaluate_rubric_batch_toolcall model=%s raw_model_verdicts=%r",
        model,
        [v.model_dump() for v in result.verdicts],
    )
    return [RequirementVerdict(**core.model_dump(), suggested_certification=None) for core in result.verdicts]


# Three-tier fallback chain for the rubric check (the "skill matching" call).
# Each tier is (provider label, model name, call function) -- all three now
# share one tool-calling pipeline shape, so the only thing that differs
# per-tier is which client/API actually makes the request:
#   1. Gemma 4 31B via Ollama Cloud -- free, generous daily quota (~14.4K/day
#      class), validated for citation accuracy on the full 16-requirement JD.
#   2. Gemini 3.1 Flash Lite via Google AI Studio -- good quality, 500 req/day
#      quota (vs. ~20/day for the full Gemini Flash tier), a real second-tier
#      option rather than one that never actually gets exercised.
#   3. llama-3.1-8b-instant via Groq -- the original, most heavily-hardened
#      path in this codebase; final safety net if both of the above fail.
# We don't have Ollama's or Google's exact rate-limit error taxonomy
# characterized (unlike Groq's, where is_daily_quota_error distinguishes a
# per-minute limit from a real daily quota exhaustion) -- so rather than
# guess at error text to match, any exception from tiers 1-2 is treated as
# "move to the next tier". The trade-off: a real bug in a non-final tier
# looks identical to a quota exhaustion and falls through to Groq rather
# than surfacing loudly -- acceptable here because Groq/llama is the
# independently-validated fallback, not a guess.
_RUBRIC_EXHAUSTED_TIERS: dict[int, str] = {}  # tier index -> ISO date last marked exhausted


def _rubric_tier_available(tier_index: int) -> bool:
    today = dt.date.today().isoformat()
    exhausted_on = _RUBRIC_EXHAUSTED_TIERS.get(tier_index)
    if exhausted_on is None:
        return True
    if exhausted_on != today:
        # Daily quotas reset at midnight -- retry a previously-exhausted tier
        # once the day has actually changed instead of skipping it forever.
        del _RUBRIC_EXHAUSTED_TIERS[tier_index]
        return True
    return False


def _mark_rubric_tier_exhausted(tier_index: int, provider: str, model: str, error: Exception, logger) -> None:
    _RUBRIC_EXHAUSTED_TIERS[tier_index] = dt.date.today().isoformat()
    logger.warning(
        "_evaluate_rubric_batch tier=%d provider=%s model=%s failed (%s: %s), falling back to next tier",
        tier_index,
        provider,
        model,
        type(error).__name__,
        error,
    )


def _evaluate_rubric_batch_tiered(
    batch: list[tuple[str, float]], sections: list[str], requirement_count: int, logger
) -> list[RequirementVerdict]:
    tiers = [
        ("ollama", settings.rubric_ollama_model, _call_structured_ollama),
        ("gemini", settings.rubric_gemini_model, _call_structured_gemini),
        ("groq", settings.rubric_check_fallback_model, _call_structured_groq),
    ]
    last_tier_index = len(tiers) - 1

    for tier_index, (provider, tier_model, call_fn) in enumerate(tiers):
        if tier_index != last_tier_index and not _rubric_tier_available(tier_index):
            continue
        try:
            return _evaluate_rubric_batch_toolcall(call_fn, tier_model, batch, sections, requirement_count, logger)
        except Exception as e:
            if tier_index == last_tier_index:
                raise
            _mark_rubric_tier_exhausted(tier_index, provider, tier_model, e, logger)

    raise RuntimeError("_evaluate_rubric_batch_tiered: no tier available")  # unreachable -- last tier always raises


def _evaluate_rubric_batch_plaintext(
    model: str, batch: list[tuple[str, float]], sections: list[str], requirement_count: int, logger
) -> list[RequirementVerdict]:
    user_prompt = (
        _BATCH_REASONING_RULES
        + f"For EACH of the {requirement_count} requirements below, output a block in EXACTLY this "
        "plain-text format (no JSON, no markdown, no extra commentary outside these fields):\n\n"
        "Requirement: <the requirement text>\n"
        "Satisfied: <True or False>\n"
        "Confidence: <a number between 0 and 1>\n"
        "Evidence: <a single short quoted snippet from the evidence provided, under 25 words, or 'none'>\n"
        "Justification: <one short sentence>\n"
        "---\n\n"
        "Repeat this block once per requirement, separated by a line containing only ---, in the "
        "same order as listed below. Do not invent, add, or infer any additional requirements.\n\n"
        + "\n\n".join(sections)
    )
    logger.debug(
        "_evaluate_rubric_batch_plaintext model=%s batch=%r prompt=%r",
        model,
        [req for req, _ in batch],
        user_prompt,
    )
    raw = call_llm(
        system=_RUBRIC_SYSTEM_PROMPT,
        user=user_prompt,
        model=model,
        temperature=0.0,
        max_tokens=1024,
        reasoning_effort=settings.rubric_check_reasoning_effort,
    )
    logger.debug("_evaluate_rubric_batch_plaintext model=%s raw_output=%r", model, raw)
    parsed = _parse_plaintext_verdicts(raw)
    return [RequirementVerdict(**item, suggested_certification=None) for item in parsed]


def _evaluate_rubric_batch(
    batch: list[tuple[str, float]], evidence_map: dict[str, list[str]], model: str | None
) -> list[RequirementVerdict]:
    # No explicit `model` -- the normal production path -- runs the tiered
    # Ollama/Gemini/Groq fallback chain. An explicit override (used by test
    # scripts to force a specific model) bypasses the chain entirely and
    # calls that one model directly, via whichever pipeline shape it needs.
    logger = get_logger()
    sections = [_requirement_section(requirement, weight, evidence_map) for requirement, weight in batch]
    requirement_count = len(batch)

    if model is None:
        full_verdicts = _evaluate_rubric_batch_tiered(batch, sections, requirement_count, logger)
    elif model in _PLAINTEXT_MODELS:
        full_verdicts = _evaluate_rubric_batch_plaintext(model, batch, sections, requirement_count, logger)
    else:
        full_verdicts = _evaluate_rubric_batch_toolcall(
            _call_structured_groq, model, batch, sections, requirement_count, logger
        )

    # An unsatisfied requirement citing evidence is self-contradictory (if the
    # evidence actually proved it, satisfied should be True) -- some models,
    # especially under tool-calling, dump irrelevant evidence blocks into
    # unsatisfied verdicts instead of leaving the field empty. Enforce the
    # schema's own "empty if unsatisfied" contract in code rather than
    # trusting every model to honor it.
    for v in full_verdicts:
        if not v.satisfied:
            v.evidence = []

    reconciled = _reconcile_batch_verdicts(batch, full_verdicts)
    logger.debug(
        "_evaluate_rubric_batch batch=%r reconciled_verdicts=%r",
        [req for req, _ in batch],
        [v.model_dump() for v in reconciled],
    )
    return reconciled


def _reconcile_batch_verdicts(
    batch: list[tuple[str, float]], verdicts: list[RequirementVerdict]
) -> list[RequirementVerdict]:
    """Guards against a real failure mode: the model (especially smaller
    ones, and especially after the malformed-tool-call recovery path, which
    accepts any schema-valid JSON with no further checks) can hallucinate
    verdicts for extra "requirements" it invented from the evidence text --
    duplicating resume phrases as if they were JD requirements. Keep only
    verdicts that actually match a requirement in THIS batch, and backfill a
    safe "unverified" verdict for anything the model dropped, so the output
    is always exactly one verdict per requested requirement -- never more.
    """
    by_key = {req.strip().lower(): (req, weight) for req, weight in batch}
    kept: dict[str, RequirementVerdict] = {}

    for v in verdicts:
        key = v.requirement.strip().lower()
        if key in by_key and key not in kept:
            original_requirement, weight = by_key[key]
            # Coerce back to the exact requested text/weight so the frontend
            # (and anything else keying off `requirement`) matches reliably,
            # regardless of how the model reformatted it.
            kept[key] = v.model_copy(update={"requirement": original_requirement, "weight": weight})

    for key, (original_requirement, weight) in by_key.items():
        if key not in kept:
            kept[key] = RequirementVerdict(
                requirement=original_requirement,
                weight=weight,
                satisfied=False,
                confidence=0.0,
                justification="Could not be reliably evaluated for this candidate.",
                evidence=[],
                suggested_certification=None,
            )

    # Preserve the batch's original order.
    return [kept[req.strip().lower()] for req, _ in batch]


_CERTIFICATION_SYSTEM = (
    "You are a career advisor who recommends certifications to close specific skill gaps. "
    "Never suggest a certification for a skill other than the one it's listed under."
)


def _suggest_certifications(requirements: list[str], model: str | None) -> dict[str, str | None]:
    """One follow-up call covering every unsatisfied requirement from a full
    rubric evaluation -- decoupled from the batch-scoring call entirely so a
    certification guess can never bleed into (or get bled into by) the
    actual satisfied/evidence verdict. Reconciled the same way batch
    verdicts are: only keep suggestions matching a requested skill, backfill
    null for anything the model drops or mismatches.
    """
    logger = get_logger()
    if not requirements:
        return {}

    sections = "\n".join(f'- "{r}"' for r in requirements)
    user_prompt = (
        f"For EACH of these {len(requirements)} unsatisfied skill(s), suggest ONE real, "
        "well-known, currently-offered certification or course that would close that specific "
        "gap (e.g. 'Microsoft Certified: Azure Fundamentals (AZ-900)') -- only if you are "
        "confident it genuinely exists and is clearly relevant to that exact skill. If no "
        "widely recognized certification exists for a skill, set suggested_certification to "
        "null for it. Never invent a certification, and never suggest one that belongs to a "
        f"different skill in this list. Return EXACTLY {len(requirements)} suggestion object(s), "
        "one per skill listed below, no more, no fewer, in the same order.\n\n" + sections
    )

    logger.debug("_suggest_certifications requirements=%r prompt=%r", requirements, user_prompt)

    result: CertificationSuggestionList = call_structured(
        system=_CERTIFICATION_SYSTEM,
        user=user_prompt,
        schema=CertificationSuggestionList,
        model=model,
    )
    logger.debug(
        "_suggest_certifications requirements=%r raw_suggestions=%r",
        requirements,
        [s.model_dump() for s in result.suggestions],
    )

    by_key = {r.strip().lower(): r for r in requirements}
    kept: dict[str, str | None] = {}
    for s in result.suggestions:
        key = s.requirement.strip().lower()
        if key in by_key and key not in kept:
            kept[key] = s.suggested_certification

    final_map = {original: kept.get(key) for key, original in by_key.items()}
    logger.debug("_suggest_certifications final_map=%r", final_map)
    return final_map


def evaluate_rubric(
    evidence_map: dict[str, list[str]],
    jd_skill_weights: dict[str, float],
    model: str | None = None,
    on_activity: Callable[[str], None] | None = None,
    on_verdict: Callable[[RequirementVerdict], None] | None = None,
    batch_size: int | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> RubricResult:
    """Judges every requirement against ONLY its cited evidence, batching
    requirements across several structured LLM calls so a single request
    never risks exceeding a smaller model's per-request token ceiling.

    `on_activity`/`on_verdict` fire per batch (`batch_size`, defaulting to
    `settings.rubric_batch_size` -- recruiter mode passes its own larger
    value), so the caller can stream "checking X now" and each resolved
    verdict live instead of only after the whole rubric evaluation finishes.

    `should_stop` is checked before each batch -- a batch already sent to
    Groq can't be interrupted mid-call, but no new batch starts once it's
    set. Whatever requirements weren't reached get an explicit "stopped"
    verdict instead of silently vanishing from the result.
    """
    if not jd_skill_weights:
        return RubricResult(verdicts=[])

    requirements = list(jd_skill_weights.items())
    batch_size = batch_size or settings.rubric_batch_size

    all_verdicts = []
    for i in range(0, len(requirements), batch_size):
        if should_stop and should_stop():
            for requirement, weight in requirements[i:]:
                stopped_verdict = RequirementVerdict(
                    requirement=requirement,
                    weight=weight,
                    satisfied=False,
                    confidence=0.0,
                    justification="Stopped before this could be evaluated.",
                    evidence=[],
                    suggested_certification=None,
                )
                if on_verdict:
                    on_verdict(stopped_verdict)
                all_verdicts.append(stopped_verdict)
            break

        batch = requirements[i : i + batch_size]
        if on_activity:
            on_activity(", ".join(req for req, _ in batch))
        verdicts = _evaluate_rubric_batch(batch, evidence_map, model)
        for verdict in verdicts:
            if on_verdict:
                on_verdict(verdict)
        all_verdicts.extend(verdicts)

    # Certifications are generated in one dedicated follow-up call, never as
    # part of batch scoring -- see `_suggest_certifications`. Skipped if a
    # stop was requested meanwhile, same as the rest of the pipeline: nothing
    # new starts once the user asks to stop.
    unsatisfied = [v for v in all_verdicts if not v.satisfied]
    if unsatisfied and not (should_stop and should_stop()):
        cert_map = _suggest_certifications([v.requirement for v in unsatisfied], model)
        all_verdicts = [
            v.model_copy(update={"suggested_certification": cert_map.get(v.requirement)})
            if not v.satisfied
            else v
            for v in all_verdicts
        ]

    return RubricResult(verdicts=all_verdicts)


def match_resume_to_requirements(
    batch_id: str,
    filename: str,
    resume_text: str,
    jd_skill_weights: dict[str, float],
    model: str | None = None,
    on_stage: Callable[[str, str], None] | None = None,
    on_activity: Callable[[str], None] | None = None,
    on_verdict: Callable[[RequirementVerdict], None] | None = None,
    batch_size: int | None = None,
    evidence_top_k: int | None = None,
    already_indexed: bool = False,
    should_stop: Callable[[], bool] | None = None,
) -> RubricResult:
    """Full pipeline: index -> hybrid retrieve+rerank -> evidence-grounded rubric scoring.

    `batch_size`/`evidence_top_k` let recruiter mode use its own tuned values
    (larger batches, fewer snippets per requirement) while job-seeker mode
    keeps using the `settings` defaults by leaving these unset.

    `already_indexed=True` skips re-chunking/re-embedding: recruiter mode's
    round 1 prescreen already indexed this exact resume under this batch_id,
    and `upsert_chunks` always mints new point IDs, so indexing twice doesn't
    just waste embedding compute -- it silently duplicates every chunk in
    Qdrant, corrupting BM25/RRF fusion and evidence retrieval for that
    candidate.
    """
    logger = get_logger()
    logger.info(
        "match_resume_to_requirements START filename=%s already_indexed=%s jd_skill_weights=%r",
        filename,
        already_indexed,
        jd_skill_weights,
    )

    def notify(stage: str, state: str) -> None:
        if on_stage:
            on_stage(stage, state)

    notify("indexing", "running")
    if not already_indexed:
        index_document(batch_id, filename, resume_text)
    notify("indexing", "done")

    notify("retrieval", "running")
    requirements = list(jd_skill_weights.keys())
    evidence_map = retrieve_evidence(batch_id, filename, requirements, top_k=evidence_top_k)
    notify("retrieval", "done")

    notify("scoring", "running")
    result = evaluate_rubric(
        evidence_map,
        jd_skill_weights,
        model=model,
        on_activity=on_activity,
        on_verdict=on_verdict,
        batch_size=batch_size,
        should_stop=should_stop,
    )
    notify("scoring", "done")
    logger.info(
        "match_resume_to_requirements END filename=%s verdicts=%r",
        filename,
        [v.model_dump() for v in result.verdicts],
    )

    return result
