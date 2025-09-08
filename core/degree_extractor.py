import re

def extract_degrees(text):
    """
    Extracts educational degrees from the given text, normalizes them to canonical categories,
    handles variations, abbreviations, apostrophes, and ambiguous words with context checking.
    Returns a dictionary with all found degrees (duplicates allowed) and the highest degree based on ranking.
    """

    # List of all found degrees with their positions for ordering
    found_degrees = []

    # Degree-related keywords for context checking of ambiguous words
    keywords = {
        'degree', 'course', 'program', 'engineering', 'science',
        'arts', 'technology', 'management'
    }

    # Ranking for determining the highest degree
    ranking = {
        'diploma': 1,
        'associate': 2,
        'bachelor': 3,
        'master': 4,
        'phd': 5
    }

    # Patterns for each degree category
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

    # Flag for ambiguous categories that require context checking for full words without apostrophes
    ambiguous_cats = {'bachelor', 'master', 'associate'}

    # Search for matches in the text
    for cat, pats in patterns.items():
        # Handle abbreviations (always count, no context needed)
        for p in pats.get('abbrev', []):
            # Use case-sensitive matching for BE and ME, case-insensitive for others
            flags = 0 if p in [r'\bB\.E\.?\b', r'\bBE\b', r'\bM\.E\.?\b', r'\bME\b'] else re.IGNORECASE
            for match in re.finditer(p, text, flags):
                # print(f"Found abbreviation match: '{match.group(0)}' at {match.start()} for category {cat} (text context: '{text[max(0, match.start()-10):match.end()+10]}')")
                found_degrees.append((match.start(), cat))

        # Handle full words
        full_pattern = pats.get('full', None)
        if full_pattern:
            is_ambiguous = cat in ambiguous_cats
            for match in re.finditer(full_pattern, text, re.IGNORECASE):
                matched_text = match.group(0)
                has_apostrophe = "'" in matched_text or "’" in matched_text
                # print(f"Found full word match: '{matched_text}' at {match.start()} for category {cat}, has_apostrophe={has_apostrophe}, is_ambiguous={is_ambiguous} (text context: '{text[max(0, match.start()-10):match.end()+10]}')")

                # If has apostrophe or not ambiguous, always count
                if has_apostrophe or not is_ambiguous:
                    # print(f"  Adding {cat} (apostrophe or not ambiguous)")
                    found_degrees.append((match.start(), cat))
                    continue

                # Otherwise, check context for ambiguous full words without apostrophe
                following_text = text[match.end():]
                next_words = re.findall(r'\b\w+\b', following_text, re.IGNORECASE)[:3]
                # print(f"  Context check for '{matched_text}': next words = {next_words}")
                if any(word.lower() in keywords for word in next_words):
                    # print(f"  Adding {cat} (context check passed)")
                    found_degrees.append((match.start(), cat))
                # else:
                #     print(f"  Skipping {cat} (context check failed)")

    # Sort found degrees by their starting position in the text
    found_degrees.sort(key=lambda x: x[0])

    # Extract the list of normalized degrees
    all_degrees = [deg for _, deg in found_degrees]

    # Determine the highest degree
    if not all_degrees:
        highest = None
    else:
        max_rank = max(ranking[deg] for deg in all_degrees)
        highest = next(deg for deg in ranking if ranking[deg] == max_rank)

    return {
        "all": all_degrees,
        "highest": highest
    }
