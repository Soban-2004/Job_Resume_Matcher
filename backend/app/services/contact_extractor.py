from app.core.llm import call_structured
from app.models.schemas import ContactInfo

_CONTACT_SYSTEM = (
    "You extract a candidate's contact details from resume text. Only return values that are "
    "explicitly present in the text -- never guess, infer, or invent a name, email, or phone "
    "number. Set a field to null if it doesn't clearly appear in the resume."
)


def extract_contact_info(resume_text: str, model: str | None = None) -> ContactInfo:
    """One lightweight, decoupled call per round-3 candidate -- same pattern as
    `_suggest_certifications`: a lower-stakes convenience field that shouldn't
    share a call (or a failure) with the actual rubric scoring, and doesn't
    need the rubric check's heavier three-tier fallback chain since a missed
    contact field just means the recruiter fills it in manually.
    """
    return call_structured(
        system=_CONTACT_SYSTEM,
        user=(
            "Extract this candidate's full name, email address, and phone number from the resume "
            f"text below. Use null for anything not explicitly present.\n\nResume:\n{resume_text}"
        ),
        schema=ContactInfo,
        model=model,
        max_completion_tokens=256,
    )
