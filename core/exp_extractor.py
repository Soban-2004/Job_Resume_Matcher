import re
from typing import Optional
from datetime import date

def extract_experience(text: str) -> int:
    if not isinstance(text, str):
        print("Error: Input must be a string.")
        return 0

    # Map for written numbers and fuzzy terms to their integer values.
    WORD_TO_NUMBER = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
        "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
        "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20, "twenty-five": 25,
        "few": 3, "several": 5
    }

    lower_text = text.lower()
    total_experience = 0

    # --- Step 1: Handle specific phrases with predefined values first ---
    if "fresher" in lower_text or "entry-level" in lower_text:
        return 0
    if "extensive experience" in lower_text:
        total_experience += 10

    # --- Step 2: Find and process number-based and word-based experience mentions ---
    experience_pattern = re.compile(
        r"""
        (?:
            (\d+\+?)                                     # Captures '5+' or '5'
            |(\d+)\s*[-–]\s*(\d+)                        # Captures '2-4' or '2–4'
            |(?:at\s+least|minimum|over|around)\s+(\d+)  # Captures 'at least 7', 'minimum 8', etc.
            |({})                                        # Captures a written number (e.g., 'five', 'several')
        )\s*
        (?:years?|yrs?)
        """.format('|'.join(WORD_TO_NUMBER.keys())),
        re.VERBOSE | re.IGNORECASE
    )

    all_matches = experience_pattern.finditer(lower_text)

    # A pattern to identify and filter out false positives
    false_positive_pattern = re.compile(
        r"years?\s+old|company\s+history|handled\s+a\s+project|founded\s+years|ago|company\s+has|been\s+around\s+for|education|school|college|degree|university|engineering|science|studies|institute|program|course",
        re.IGNORECASE
    )

    for match in all_matches:
        # Check surrounding context for false positives
        start_pos = max(0, match.start() - 75)
        end_pos = min(len(lower_text), match.end() + 75)
        context = lower_text[start_pos:end_pos]

        if false_positive_pattern.search(context):
            continue

        # Process the different types of matches
        if match.group(1):  # Simple number or number+
            exp_val = int(match.group(1).replace('+', ''))
            total_experience += exp_val
        elif match.group(2) and match.group(3):  # Range
            exp_val = int(match.group(3)) # Take the upper bound
            total_experience += exp_val
        elif match.group(4):  # At least / minimum / over
            exp_val = int(match.group(4))
            total_experience += exp_val
        elif match.group(5):  # Written number or fuzzy term
            exp_word = match.group(5)
            exp_val = WORD_TO_NUMBER.get(exp_word, 0)
            if exp_val > 0:
                total_experience += exp_val

    # --- Step 3: Find and calculate experience from date ranges (years only) ---
    date_range_pattern = re.compile(
        r"(?:\w{3,}\s+)?(\d{4})\s*(?:-|–|to)\s*(?:\w{3,}\s+)?(\d{4}|present)", re.IGNORECASE
    )
    date_matches = date_range_pattern.finditer(lower_text)

    for match in date_matches:
        try:
            start_year_str, end_year_str = match.groups()

            if start_year_str is None or end_year_str is None:
                continue

            start_year = int(start_year_str)

            if end_year_str.lower() == 'present':
                end_year = date.today().year
            else:
                end_year = int(end_year_str)

            # Check context for false positives before adding to total_from_dates
            start_pos = max(0, match.start() - 75)
            end_pos = min(len(lower_text), match.end() + 75)
            context = lower_text[start_pos:end_pos]
            if false_positive_pattern.search(context):
                continue

            if end_year >= start_year:
                years_diff = end_year - start_year
                total_experience += years_diff
        except (ValueError, IndexError):
            continue

    # --- Step 4: Return total experience, or 0 if nothing was found ---
    if total_experience > 0:
        return total_experience
    else:
        return 0
