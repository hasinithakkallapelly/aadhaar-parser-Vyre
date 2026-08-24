from dataclasses import dataclass, field


_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)


def has_valid_verhoeff_checksum(number: str) -> bool:
    if len(number) != 12 or not number.isdigit() or number[0] in "01":
        return False
    checksum = 0
    for index, digit in enumerate(reversed(number)):
        checksum = _D[checksum][_P[index % 8][int(digit)]]
    return checksum == 0


def mask_aadhaar(number: str) -> str:
    return f"XXXXXXXX{number[-4:]}"


@dataclass
class FieldValidationResult:
    valid: bool
    errors: list = field(default_factory=list)


def validate_fields(data: dict) -> FieldValidationResult:
    errors = []
    number = data.get("aadhaar_number")
    if not number:
        errors.append("Aadhaar number was not detected")
    elif not has_valid_verhoeff_checksum(number):
        errors.append("Aadhaar number failed checksum validation")
    if not data.get("name"):
        errors.append("Name was not detected")
    if not data.get("dob"):
        errors.append("A valid date of birth was not detected")
    return FieldValidationResult(valid=not errors, errors=errors)

