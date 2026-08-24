import re
from dataclasses import dataclass, field


AADHAAR_MARKER_GROUPS = (
    ("government of india", "govt of india", "government ot india"),
    ("unique identification authority", "uidai", "aadhaar"),
)
OTHER_DOCUMENT_MARKERS = {
    "pan card": ("income tax department", "permanent account number", "pan card"),
    "voter id": ("election commission", "voter id", "epic no"),
    "driving license": ("driving licence", "driving license", "transport department"),
}


@dataclass
class ValidationResult:
    is_valid_aadhaar: bool
    confidence: str
    reasons: list = field(default_factory=list)
    likely_document_type: str | None = None


def validate_document_type(ocr_text: str) -> ValidationResult:
    text = re.sub(r"\s+", " ", ocr_text.lower())
    for document_type, markers in OTHER_DOCUMENT_MARKERS.items():
        if any(marker in text for marker in markers):
            return ValidationResult(
                False, "high", [f"Text matches {document_type} markers"], document_type
            )

    matched_groups = sum(
        any(marker in text for marker in group) for group in AADHAAR_MARKER_GROUPS
    )
    has_number = any(
        len(re.sub(r"\D", "", match.group())) == 12
        for line in ocr_text.splitlines()
        for match in re.finditer(r"(?<!\d)(?:\d[\s-]?){12}(?!\d)", line)
    )

    if matched_groups == len(AADHAAR_MARKER_GROUPS) and has_number:
        return ValidationResult(True, "high", ["Expected Aadhaar text and number pattern found"])
    if matched_groups >= 1 and has_number:
        return ValidationResult(True, "medium", ["Partial Aadhaar text and number pattern found"])
    return ValidationResult(False, "high", ["Required Aadhaar markers were not found"])

