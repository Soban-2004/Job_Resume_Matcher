import re

from app.config import settings

# Normalizes a variety of real-world header wordings onto one canonical name
# per section type. Matching happens after lowercasing/whitespace collapse,
# so casing and trailing colons don't matter.
_HEADER_ALIASES = {
    "skills": "skills",
    "technical skills": "skills",
    "core technologies": "skills",
    "technology stack": "skills",
    "expertise": "skills",
    "key skills": "skills",
    "core competencies": "skills",
    "experience": "experience",
    "professional experience": "experience",
    "work experience": "experience",
    "employment history": "experience",
    "professional development": "experience",
    "internships": "experience",
    "projects": "projects",
    "academic projects": "projects",
    "personal projects": "projects",
    "education": "education",
    "academic background": "education",
    "educational qualifications": "education",
    "summary": "summary",
    "professional summary": "summary",
    "objective": "summary",
    "profile": "summary",
    "certifications": "certifications",
    "certificates": "certifications",
    "licenses & certifications": "certifications",
}

# PROJECTS/EXPERIENCE have a real repeating sub-structure (a title/role line
# followed by bullet details) worth splitting further if they overflow
# chunk_size. SKILLS/CERTIFICATIONS/EDUCATION/SUMMARY don't have a
# comparable "entry" unit smaller than the section itself, so they fall
# straight to line-packing when oversized instead.
_ENTRY_AWARE_SECTIONS = {"projects", "experience"}

_DATE_RANGE_RE = re.compile(
    r"\(?\b(19|20)\d{2}\b\s*[-–—]\s*(present|current|\b(19|20)\d{2}\b)\)?", re.IGNORECASE
)


def _normalize_header(line: str) -> str:
    return re.sub(r"[:\s]+", " ", line.strip().lower()).strip()


def _looks_noisy(line: str) -> bool:
    """Blocks lines that are short and/or ALL-CAPS but obviously aren't a
    section header -- contact info, dates, GPAs/percentages, stray
    acronyms (e.g. "AWS", "IIT DELHI", "(2022-2026)", "89%").
    """
    if "@" in line or "http" in line.lower():
        return True
    digit_ratio = sum(c.isdigit() for c in line) / max(len(line), 1)
    if digit_ratio > 0.3:
        return True
    if _DATE_RANGE_RE.search(line):
        return True
    return False


def _is_header(line: str) -> str | None:
    """Returns the canonical section name if `line` looks like a section
    header, else None. Primary path: normalized text matches a known
    alias. Fallback path (for header wording not in the alias list): a
    short, standalone, ALL-CAPS line that doesn't look noisy.
    """
    stripped = line.strip()
    if not stripped or len(stripped) > 40:
        return None

    normalized = _normalize_header(stripped)
    if normalized in _HEADER_ALIASES:
        return _HEADER_ALIASES[normalized]

    word_count = len(stripped.split())
    if stripped.isupper() and 1 <= word_count <= 4 and not _looks_noisy(stripped):
        return normalized

    return None


def _is_entry_boundary(line: str) -> bool:
    """Looser heuristic than `_is_header` -- entry titles (project names,
    job titles) aren't drawn from a fixed vocabulary, so this looks for
    shape instead: a short-ish line containing a pipe separator (common in
    "Project Name | [LINK]" style headings) or a date range ("2020 -
    Present", "(2018-2020)").
    """
    stripped = line.strip()
    if not stripped or len(stripped) > 100:
        return False
    return "|" in stripped or bool(_DATE_RANGE_RE.search(stripped))


def _split_into_sections(lines: list[str]) -> list[tuple[str, list[str]]]:
    """Groups non-empty lines into (section_name, lines) tuples. Content
    before the first detected header becomes its own "preamble" section
    (name/contact info always precedes the first real header).
    """
    sections: list[tuple[str, list[str]]] = []
    current_name = "preamble"
    current_lines: list[str] = []

    for line in lines:
        header_name = _is_header(line)
        if header_name:
            if current_lines:
                sections.append((current_name, current_lines))
            current_name = header_name
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_name, current_lines))

    return sections


def _split_into_entries(lines: list[str]) -> list[str]:
    """Splits an entry-aware section's lines into entries, each starting at
    a detected entry-boundary line. If no boundaries are found (section
    doesn't use a title/date-range style), the whole section comes back as
    a single entry, and the caller's line-packing fallback takes over.
    """
    entries: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if _is_entry_boundary(line) and current:
            entries.append(current)
            current = [line]
        else:
            current.append(line)

    if current:
        entries.append(current)

    return ["\n".join(entry) for entry in entries]


def _pack_units(units: list[str], chunk_size: int, overlap: int) -> list[str]:
    """Packs text units (lines or entries) into chunks up to `chunk_size`,
    falling back to character-window slicing only for a single unit that's
    too big to fit on its own.
    """
    chunks: list[str] = []
    buffer = ""

    for unit in units:
        if len(buffer) + len(unit) + 1 <= chunk_size:
            buffer = f"{buffer}\n{unit}".strip()
            continue

        if buffer:
            chunks.append(buffer)
            buffer = ""

        if len(unit) <= chunk_size:
            buffer = unit
        else:
            start = 0
            while start < len(unit):
                end = start + chunk_size
                chunks.append(unit[start:end])
                start = end - overlap

    if buffer:
        chunks.append(buffer)

    return chunks


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    """Splits resume text into section-aware chunks.

    Resumes have real structure (EDUCATION, SKILLS, PROJECTS, EXPERIENCE...)
    that PDF extraction almost never preserves as blank-line paragraphs --
    every line comes back separated by a single "\\n", so a blind
    fixed-size window regularly mixes unrelated sections into one chunk
    (a skills line diluted by surrounding degree/GPA text is exactly what
    caused a real evidence-retrieval bug: NumPy was correctly retrieved but
    the model dismissed it, evidence buried in a chunk mostly about
    education). Instead:

      1. Detect section headers and split the resume into sections.
      2. A section that fits in `chunk_size` becomes one chunk.
      3. PROJECTS/EXPERIENCE sections that overflow get split by entry
         (project/role boundaries) first, not blind character windows.
      4. Only a single entry (or a section with no entry structure, like an
         overflowing SKILLS block) that's still too big falls back to
         line-packing, and character-window slicing as the last resort.
    """
    chunk_size = chunk_size or settings.chunk_size
    overlap = overlap or settings.chunk_overlap

    text = text.strip()
    if not text:
        return []

    lines = [line for line in text.split("\n") if line.strip()]
    if not lines:
        return []

    sections = _split_into_sections(lines)

    chunks: list[str] = []
    for name, section_lines in sections:
        section_text = "\n".join(section_lines)

        if len(section_text) <= chunk_size:
            chunks.append(section_text)
            continue

        if name in _ENTRY_AWARE_SECTIONS:
            units = _split_into_entries(section_lines)
        else:
            units = section_lines

        chunks.extend(_pack_units(units, chunk_size, overlap))

    return chunks
