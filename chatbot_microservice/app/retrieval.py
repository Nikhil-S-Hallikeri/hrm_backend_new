from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_FILE = ROOT / "data" / "build" / "academy_knowledge.txt"

# Knowledge context budget — keep headroom for prompt + history + answer
DEFAULT_MAX_CHARS = 7_000

# Minimum relevance score for a chunk to be included at all
MIN_SCORE_THRESHOLD = 2

# Short but meaningful terms to always keep (not filtered by length)
SHORT_ALLOWLIST = {"ai", "ml", "hr", "bi", "ui", "ux", "db", "it"}

# Fingerprint length for near-duplicate detection
DEDUP_PREFIX_LEN = 120


# =========================================================
# QUERY TERMS
# =========================================================

def _extract_query_terms(query: str) -> set[str]:
    """
    Extract meaningful search terms from the query.
    Keeps short industry keywords (AI, ML, HR etc.) that would
    otherwise be filtered by the length check.
    """
    terms: set[str] = set()
    for term in query.lower().split():
        clean = re.sub(r"[^a-z0-9/]", "", term)  # strip punctuation
        if not clean:
            continue
        if len(clean) >= 3 or clean in SHORT_ALLOWLIST:
            terms.add(clean)
    return terms


def _extract_phrases(query: str) -> list[str]:
    """
    Extract multi-word phrases (2–3 consecutive words) from the query
    for boosted phrase-level matching.
    """
    words = [w.lower() for w in query.split() if len(w) >= 2]
    phrases: list[str] = []
    for i in range(len(words) - 1):
        phrases.append(f"{words[i]} {words[i+1]}")
    for i in range(len(words) - 2):
        phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")
    return phrases


# =========================================================
# SCORING
# =========================================================

def _score_chunk(chunk: str, query_terms: set[str], phrases: list[str]) -> int:
    lowered = chunk.lower()
    score = 0

    # Title section (before "page content:") gets a priority bonus
    if "page content:" in lowered:
        title_section = lowered.split("page content:")[0]
        body_section = lowered[len(title_section):]
    elif "page title:" in lowered:
        # Has a title marker but no body separator — treat whole thing as title
        title_section = lowered
        body_section = ""
    else:
        title_section = ""
        body_section = lowered

    # Term-level scoring
    for term in query_terms:
        if term in body_section:
            score += 2
        if term in title_section:
            score += 5  # title match is a strong signal

    # Phrase-level scoring (multi-word matches rank higher)
    for phrase in phrases:
        if phrase in lowered:
            score += 4  # phrase match beats individual word matches

    return score


# =========================================================
# CLEAN CHUNK
# =========================================================

def _clean_chunk(chunk: str) -> str:
    lines = [line.strip() for line in chunk.splitlines() if line.strip()]
    cleaned: list[str] = []
    seen: set[str] = set()
    for line in lines:
        normalized = line.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(line)
    return "\n".join(cleaned)


def _chunk_fingerprint(chunk: str) -> str:
    """Short fingerprint for near-duplicate detection."""
    return chunk[:DEDUP_PREFIX_LEN].strip().lower()


def _clip_at_sentence(text: str, max_len: int) -> str:
    """
    Clip text to max_len but try to end at a sentence boundary
    rather than cutting mid-word or mid-sentence.
    """
    if len(text) <= max_len:
        return text
    clipped = text[:max_len]
    # Try to end at last sentence boundary within the clip
    last_stop = max(
        clipped.rfind(". "),
        clipped.rfind(".\n"),
        clipped.rfind("? "),
        clipped.rfind("! "),
    )
    if last_stop > max_len // 2:  # only use boundary if it's not too far back
        return clipped[: last_stop + 1].strip()
    # Fall back to last word boundary
    last_space = clipped.rfind(" ")
    if last_space > 0:
        return clipped[:last_space].strip()
    return clipped.strip()


# =========================================================
# MAIN RETRIEVAL
# =========================================================

def _find_tenant_knowledge_file(tenant_id: str | None) -> Path | None:
    if not tenant_id:
        return None
    clean_tenant = re.sub(r"[^a-zA-Z0-9_-]", "", tenant_id.strip())
    if not clean_tenant:
        return None
    candidates = [
        ROOT / "data" / "docs" / f"{clean_tenant}.txt",
        ROOT / "data" / "docs" / f"{clean_tenant}_knowledge.txt",
        ROOT / "data" / "docs" / f"{clean_tenant}.md",
        ROOT / "data" / "build" / f"{clean_tenant}_knowledge.txt",
        ROOT / "data" / "build" / f"{clean_tenant}.txt",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def get_local_context(
    query: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    tenant_id: str | None = None,
) -> str:
    target_file = _find_tenant_knowledge_file(tenant_id) or KNOWLEDGE_FILE
    if not target_file.exists():
        return ""

    text = target_file.read_text(encoding="utf-8", errors="ignore")
    chunks = [c.strip() for c in text.split("\n\n---\n\n") if c.strip()]
    if not chunks:
        return ""

    query_terms = _extract_query_terms(query)
    phrases = _extract_phrases(query)

    # Score and filter
    scored: list[tuple[int, str]] = []
    for chunk in chunks:
        score = _score_chunk(chunk, query_terms, phrases)
        if score >= MIN_SCORE_THRESHOLD:
            scored.append((score, chunk))

    # If nothing passes threshold, fall back to top 3 chunks unfiltered
    # (better than returning empty context)
    if not scored:
        scored = [(0, chunk) for chunk in chunks[:3]]

    ranked = sorted(scored, key=lambda x: x[0], reverse=True)

    # Build context with near-duplicate filtering and sentence-boundary clipping
    selected: list[str] = []
    total_chars = 0
    seen_fingerprints: set[str] = set()

    for _score, chunk in ranked:
        if total_chars >= max_chars:
            break

        cleaned = _clean_chunk(chunk)
        fingerprint = _chunk_fingerprint(cleaned)

        if fingerprint in seen_fingerprints:
            continue
        seen_fingerprints.add(fingerprint)

        remaining = max_chars - total_chars
        clipped = _clip_at_sentence(cleaned, remaining)
        if not clipped:
            continue

        selected.append(clipped)
        total_chars += len(clipped)

    return "\n\n---\n\n".join(selected)