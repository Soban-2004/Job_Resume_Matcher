import re
from datetime import date


def extract_experience(text: str) -> int:
    if not isinstance(text, str):
        return 0

    WORD_TO_NUMBER = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
        "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
        "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20, "twenty-five": 25,
        "few": 3, "several": 5
    }

    lower_text = text.lower()
    explicit_total = 0
    date_range_total = 0

    if "fresher" in lower_text or "entry-level" in lower_text:
        return 0
    if "extensive experience" in lower_text:
        explicit_total += 10

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

    false_positive_pattern = re.compile(
        r"years?\s+old|company\s+history|handled\s+a\s+project|founded\s+years|ago|company\s+has|been\s+around\s+for|education|school|college|degree|university|engineering|science|studies|institute|program|course",
        re.IGNORECASE
    )

    for match in all_matches:
        start_pos = max(0, match.start() - 75)
        end_pos = min(len(lower_text), match.end() + 75)
        context = lower_text[start_pos:end_pos]

        if false_positive_pattern.search(context):
            continue

        if match.group(1):
            exp_val = int(match.group(1).replace('+', ''))
            explicit_total += exp_val
        elif match.group(2) and match.group(3):
            exp_val = int(match.group(3))
            explicit_total += exp_val
        elif match.group(4):
            exp_val = int(match.group(4))
            explicit_total += exp_val
        elif match.group(5):
            exp_word = match.group(5)
            exp_val = WORD_TO_NUMBER.get(exp_word, 0)
            if exp_val > 0:
                explicit_total += exp_val

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

            start_pos = max(0, match.start() - 75)
            end_pos = min(len(lower_text), match.end() + 75)
            context = lower_text[start_pos:end_pos]
            if false_positive_pattern.search(context):
                continue

            if end_year >= start_year:
                years_diff = end_year - start_year
                date_range_total += years_diff
        except (ValueError, IndexError):
            continue

    # Both signals estimate the same thing (total experience) from different
    # evidence -- summing them double-counts (e.g. a resume stating "6+ years"
    # AND listing employment dates spanning 6 years would otherwise report
    # 12). Employment date ranges are the more reliable, concrete signal when
    # present; the explicit "X years" phrasing is only a fallback for resumes
    # with no parseable date ranges at all.
    total_experience = date_range_total if date_range_total > 0 else explicit_total
    return total_experience if total_experience > 0 else 0
