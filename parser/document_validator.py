"""
document_validator.py

Basic document-type validation for Aadhaar uploads: checks whether the OCR
text extracted from an uploaded image actually looks like an Aadhaar card,
BEFORE running the full field-extraction pipeline.

SCOPE, STATED HONESTLY:
This is keyword/structure-based validation, not forgery detection. It can
catch:
  - Wrong document type entirely (e.g. a PAN card uploaded instead of
    Aadhaar -- different boilerplate text, no 12-digit Aadhaar-shaped
    number).
  - Images with no readable Aadhaar-specific text at all (blank/garbage
    upload).

It CANNOT catch:
  - A well-made forged Aadhaar card that includes the right boilerplate
    text and a plausible-looking 12-digit number.
  - Digitally tampered but otherwise well-formatted cards.

Real forgery detection would need QR-code cross-validation (Aadhaar cards
issued since ~2018 carry a UIDAI-signed secure QR code encoding the same
data printed on the card -- decoding it and comparing against the OCR
text is the standard real approach) and/or image tamper analysis (error
level analysis, copy-move detection). Neither is implemented here --
that's a meaningfully bigger project, not a basic check.
"""

import re
from dataclasses import dataclass, field


REQUIRED_MARKER_GROUPS = [
    # At least one phrase from each group must appear (case-insensitive)
    # for the document to be considered "Aadhaar-shaped."
    ["government of india", "govt of india", "government ot india"],  # OCR sometimes misreads "of" as "ot"
    ["unique identification authority", "uidai", "aadhaar"],
]

# Markers that suggest a DIFFERENT document type entirely -- if these show
# up prominently and Aadhaar markers don't, it's a strong signal this is
# the wrong document.
OTHER_DOCUMENT_MARKERS = {
    "pan card": ["income tax department", "permanent account number", "pan card"],
    "voter id": ["election commission", "voter id", "epic no"],
    "driving license": ["driving licence", "driving license", "transport department"],
}


@dataclass
class ValidationResult:
    is_valid_aadhaar: bool
    confidence: str  # "high", "medium", "low"
    reasons: list = field(default_factory=list)
    likely_document_type: str | None = None


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower())


def validate_document_type(ocr_text: str) -> ValidationResult:
    """
    Basic check: does this OCR text look like it came from an Aadhaar card?

    Returns a ValidationResult with is_valid_aadhaar, a confidence level,
    and human-readable reasons -- meant to be checked BEFORE running full
    field extraction, so obviously-wrong documents get rejected early
    with a clear reason instead of silently producing garbage parsed data.
    """
    text = _normalize(ocr_text)
    reasons = []

    # Check for Aadhaar-specific marker groups
    matched_groups = 0
    for group in REQUIRED_MARKER_GROUPS:
        if any(marker in text for marker in group):
            matched_groups += 1

    # Check for a 12-digit-shaped number (with or without spaces) --
    # doesn't validate it's a REAL Aadhaar number, just that something
    # number-shaped like one is present.
    has_number_pattern = bool(
        re.search(r"\d{4}\s?\d{4}\s?\d{4}", text) or re.search(r"\d{12}", re.sub(r"\s+", "", text))
    )

    # Check whether text strongly matches a DIFFERENT known document type
    likely_other_doc = None
    for doc_type, markers in OTHER_DOCUMENT_MARKERS.items():
        if any(marker in text for marker in markers):
            likely_other_doc = doc_type
            break

    if likely_other_doc:
        reasons.append(f"Text matches known markers for '{likely_other_doc}', not Aadhaar.")
        return ValidationResult(
            is_valid_aadhaar=False,
            confidence="high",
            reasons=reasons,
            likely_document_type=likely_other_doc,
        )

    if matched_groups == len(REQUIRED_MARKER_GROUPS) and has_number_pattern:
        reasons.append("Found expected Aadhaar boilerplate text and a 12-digit-shaped number.")
        return ValidationResult(is_valid_aadhaar=True, confidence="high", reasons=reasons)

    if matched_groups >= 1 and has_number_pattern:
        reasons.append("Found a 12-digit-shaped number and some Aadhaar-related text, but not all expected markers.")
        return ValidationResult(is_valid_aadhaar=True, confidence="medium", reasons=reasons)

    if matched_groups == 0 and not has_number_pattern:
        reasons.append("No Aadhaar-specific text or Aadhaar-shaped number found at all.")
        return ValidationResult(is_valid_aadhaar=False, confidence="high", reasons=reasons)

    reasons.append("Partial match -- some expected elements missing. Flagging for manual review.")
    return ValidationResult(is_valid_aadhaar=False, confidence="low", reasons=reasons)
