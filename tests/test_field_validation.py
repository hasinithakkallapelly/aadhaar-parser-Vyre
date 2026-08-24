from parser.field_validation import has_valid_verhoeff_checksum, mask_aadhaar, validate_fields


def valid_number(prefix="23456789012"):
    return next(prefix + str(digit) for digit in range(10)
                if has_valid_verhoeff_checksum(prefix + str(digit)))


def test_verhoeff_checksum():
    number = valid_number()
    assert has_valid_verhoeff_checksum(number)
    replacement = "9" if number[-1] != "9" else "8"
    assert not has_valid_verhoeff_checksum(number[:-1] + replacement)


def test_masking():
    assert mask_aadhaar("234567890123") == "XXXXXXXX0123"


def test_required_fields():
    result = validate_fields({"aadhaar_number": None, "name": None, "dob": None})
    assert result.valid is False
    assert len(result.errors) == 3

