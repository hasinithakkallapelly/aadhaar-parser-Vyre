from parser.aadhaar_parser import parse_aadhaar_data
from parser.document_validator import validate_document_type
from parser.field_validation import has_valid_verhoeff_checksum


def valid_number(prefix="23456789012"):
    return next(prefix + str(digit) for digit in range(10)
                if has_valid_verhoeff_checksum(prefix + str(digit)))


def test_parse_fields_from_ocr_text():
    number = valid_number()
    grouped = f"{number[:4]} {number[4:8]} {number[8:]}"
    text = f"Government of India\nJane Test Doe\nDOB: 15/06/1998\nFEMALE\n{grouped}\nUIDAI"
    data = parse_aadhaar_data(text)
    assert data == {
        "aadhaar_number": number,
        "dob": "1998-06-15",
        "gender": "FEMALE",
        "name": "Jane Test Doe",
    }
    assert validate_document_type(text).is_valid_aadhaar


def test_invalid_date_is_not_returned():
    data = parse_aadhaar_data("Jane Test Doe\nDOB: 99/99/9999\n2345 6789 0123")
    assert data["dob"] is None


def test_pan_is_rejected():
    text = "Income Tax Department\nPermanent Account Number\nABCDE1234F"
    result = validate_document_type(text)
    assert result.is_valid_aadhaar is False
    assert result.likely_document_type == "pan card"

