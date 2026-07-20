import re


def extract_degrees(text: str) -> dict:
    """
    Extracts educational degrees from the given text, normalizes them to canonical categories,
    handles variations, abbreviations, apostrophes, and ambiguous words with context checking.
    Returns a dictionary with all found degrees (duplicates allowed) and the highest degree based on ranking.
    """

    found_degrees = []

    keywords = {
        'degree', 'course', 'program', 'engineering', 'science',
        'arts', 'technology', 'management'
    }

    ranking = {
        'diploma': 1,
        'associate': 2,
        'bachelor': 3,
        'master': 4,
        'phd': 5
    }

    patterns = {
        'bachelor': {
            'abbrev': [r'\bB\.?Sc\.?\b', r'\bB\.E\.?\b', r'\bBE\b', r'\bB\.?Tech\.?\b', r'\bB\.?A\.?\b', r'\bB\.?S\.?\b'],
            'full': r'\bBachelor(?:\'s|’s)?\b'
        },
        'master': {
            'abbrev': [r'\bMBA\b', r'\bM\.E\.?\b', r'\bME\b', r'\bM\.?Tech\.?\b', r'\bM\.?A\.?\b', r'\bM\.?S\.?\b', r'\bM\.?Sc\.?\b'],
            'full': r'\bMaster(?:\'s|’s)?\b'
        },
        'phd': {
            'abbrev': [r'\bPh\.?D\.?\b', r'\bDPhil\b'],
            'full': r'\bDoctorate\b'
        },
        'diploma': {
            'abbrev': [r'\bDip\.?\b'],
            'full': r'\b(?:PG )?Diploma\b'
        },
        'associate': {
            'abbrev': [r'\bA\.A\.?\b', r'\bA\.S\.?\b', r'\bA\.A\.S\.?\b'],
            'full': r'\bAssociate(?:\'s|’s)?\b'
        }
    }

    ambiguous_cats = {'bachelor', 'master', 'associate'}

    for cat, pats in patterns.items():
        for p in pats.get('abbrev', []):
            flags = 0 if p in [r'\bB\.E\.?\b', r'\bBE\b', r'\bM\.E\.?\b', r'\bME\b'] else re.IGNORECASE
            for match in re.finditer(p, text, flags):
                found_degrees.append((match.start(), cat))

        full_pattern = pats.get('full', None)
        if full_pattern:
            is_ambiguous = cat in ambiguous_cats
            for match in re.finditer(full_pattern, text, re.IGNORECASE):
                matched_text = match.group(0)
                has_apostrophe = "'" in matched_text or "’" in matched_text

                if has_apostrophe or not is_ambiguous:
                    found_degrees.append((match.start(), cat))
                    continue

                following_text = text[match.end():]
                next_words = re.findall(r'\b\w+\b', following_text, re.IGNORECASE)[:3]
                if any(word.lower() in keywords for word in next_words):
                    found_degrees.append((match.start(), cat))

    found_degrees.sort(key=lambda x: x[0])
    all_degrees = [deg for _, deg in found_degrees]

    if not all_degrees:
        highest = None
    else:
        max_rank = max(ranking[deg] for deg in all_degrees)
        highest = next(deg for deg in ranking if ranking[deg] == max_rank)

    return {
        "all": all_degrees,
        "highest": highest
    }
