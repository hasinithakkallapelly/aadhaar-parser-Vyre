import argparse
import json

from parser.aadhaar_parser import extract_text, parse_aadhaar_data
from parser.document_validator import validate_document_type
from parser.field_validation import mask_aadhaar, validate_fields


def main():
    parser = argparse.ArgumentParser(description="Parse one Aadhaar image locally")
    parser.add_argument("image", help="Path to a JPEG or PNG image")
    args = parser.parse_args()

    text = extract_text(args.image)
    document = validate_document_type(text)
    if not document.is_valid_aadhaar:
        raise SystemExit("The image does not appear to contain an Aadhaar document")

    data = parse_aadhaar_data(text)
    validation = validate_fields(data)
    if not validation.valid:
        raise SystemExit("Validation failed: " + "; ".join(validation.errors))

    safe_output = {
        "aadhaar_masked": mask_aadhaar(data["aadhaar_number"]),
        "name": data["name"],
        "dob": data["dob"],
        "gender": data.get("gender"),
    }
    print(json.dumps(safe_output, indent=2))


if __name__ == "__main__":
    main()

