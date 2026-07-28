from parser.document_validator import validate_document_type


def test_valid_aadhaar_text():
    text = """
    Government of India
    Aadhaar
    Jane Test Doe
    DOB: 15/06/1998
    Female
    1234 5678 9012
    """
    result = validate_document_type(text)
    print(f"Aadhaar-like text -> is_valid={result.is_valid_aadhaar}, confidence={result.confidence}")
    assert result.is_valid_aadhaar is True
    assert result.confidence == "high"


def test_pan_card_rejected():
    text = """
    INCOME TAX DEPARTMENT
    GOVT. OF INDIA
    Permanent Account Number Card
    ABCDE1234F
    Jane Test Doe
    """
    result = validate_document_type(text)
    print(f"PAN card text -> is_valid={result.is_valid_aadhaar}, "
          f"confidence={result.confidence}, likely_type={result.likely_document_type}")
    assert result.is_valid_aadhaar is False
    assert result.likely_document_type == "pan card"


def test_garbage_text_rejected():
    text = "asdkjh 128739 random noise text nothing useful"
    result = validate_document_type(text)
    print(f"Garbage text -> is_valid={result.is_valid_aadhaar}, confidence={result.confidence}")
    assert result.is_valid_aadhaar is False


def test_ocr_typo_tolerance():
    # OCR commonly misreads "of" as "ot" -- validator should still pass
    text = """
    Government ot India
    Jane Test Doe
    1234 5678 9012
    UIDAI
    """
    result = validate_document_type(text)
    print(f"OCR-typo Aadhaar text -> is_valid={result.is_valid_aadhaar}, confidence={result.confidence}")
    assert result.is_valid_aadhaar is True


def test_voter_id_rejected():
    text = """
    ELECTION COMMISSION OF INDIA
    EPIC NO: ABC1234567
    Jane Test Doe
    """
    result = validate_document_type(text)
    print(f"Voter ID text -> is_valid={result.is_valid_aadhaar}, "
          f"confidence={result.confidence}, likely_type={result.likely_document_type}")
    assert result.is_valid_aadhaar is False
    assert result.likely_document_type == "voter id"


if __name__ == "__main__":
    test_valid_aadhaar_text()
    test_pan_card_rejected()
    test_garbage_text_rejected()
    test_ocr_typo_tolerance()
    test_voter_id_rejected()
    print("\nAll document_validator tests passed.")
