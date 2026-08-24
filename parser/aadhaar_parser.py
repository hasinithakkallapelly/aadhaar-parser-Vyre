import json
import os
import re
from datetime import date, datetime
from io import BytesIO

import cv2
import numpy as np
import pytesseract
from PIL import Image, UnidentifiedImageError


class InvalidImageError(ValueError):
    pass


def _decode_image(image_bytes: bytes):
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError("The uploaded file is not a valid image") from exc

    encoded = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None:
        raise InvalidImageError("The uploaded image could not be decoded")
    return image


def preprocess_image_bytes(image_bytes: bytes) -> Image.Image:
    """Prepare an image for OCR without writing any intermediate files."""
    image = _decode_image(image_bytes)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    processed = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]
    return Image.fromarray(processed)


def extract_text_from_bytes(image_bytes: bytes) -> str:
    image = preprocess_image_bytes(image_bytes)
    return pytesseract.image_to_string(image, config=r"--oem 3 --psm 6")


def extract_text(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return extract_text_from_bytes(image_file.read())


def _find_aadhaar_candidate(text: str):
    for line in text.splitlines():
        for match in re.finditer(r"(?<!\d)(?:\d[\s-]?){12}(?!\d)", line):
            digits = re.sub(r"\D", "", match.group())
            if len(digits) == 12:
                return digits
    return None


def _valid_dob(value: str):
    try:
        parsed = datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError:
        return None
    if parsed > date.today() or parsed.year < 1900:
        return None
    return parsed.isoformat()


def parse_aadhaar_data(text: str) -> dict:
    number = _find_aadhaar_candidate(text)
    dob_match = re.search(r"\b\d{2}/\d{2}/\d{4}\b", text)
    gender_match = re.search(r"\b(Male|Female|Transgender)\b", text, re.IGNORECASE)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    excluded = {
        "government", "india", "aadhaar", "uidai", "dob", "birth",
        "male", "female", "transgender", "address", "authority",
    }

    def name_candidate(line):
        lowered = line.lower()
        if any(word in lowered for word in excluded):
            return False
        if re.search(r"\d", line):
            return False
        cleaned = re.sub(r"[^A-Za-z .'-]", "", line).strip()
        words = cleaned.split()
        return 1 <= len(words) <= 5 and all(len(word) >= 2 for word in words)

    name = None
    dob_index = None
    if dob_match:
        dob_index = next((i for i, line in enumerate(lines) if dob_match.group() in line), None)
    if dob_index is not None:
        nearby = [line for line in lines[max(0, dob_index - 3):dob_index] if name_candidate(line)]
        if nearby:
            name = nearby[-1]
    if name is None:
        candidates = [line for line in lines if name_candidate(line)]
        if candidates:
            name = candidates[0]

    if name:
        name = re.sub(r"[^A-Za-z .'-]", "", name)
        name = re.sub(r"\s+", " ", name).strip()

    return {
        "aadhaar_number": number,
        "dob": _valid_dob(dob_match.group()) if dob_match else None,
        "gender": gender_match.group().upper() if gender_match else None,
        "name": name,
    }


def save_json(data: dict, output_path: str):
    directory = os.path.dirname(output_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    safe_data = dict(data)
    number = safe_data.pop("aadhaar_number", None)
    if number:
        safe_data["aadhaar_masked"] = f"XXXXXXXX{number[-4:]}"
    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(safe_data, output_file, indent=2)

