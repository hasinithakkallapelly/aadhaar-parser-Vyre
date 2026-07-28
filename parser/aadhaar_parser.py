"""
aadhaar_parser.py

OCR extraction and field parsing for Aadhaar card images, plus MySQL
persistence.

CLEANUP NOTE: the original version of this file had ~5 earlier iterations
of these same functions left in as large commented-out blocks above the
active code (a manual "history" instead of using git commits for that).
Removed here -- git history is what git history is for, and it made the
file hard to read for no benefit. Only the final, active implementation
remains below.
"""

import os
import re
import sys
import json
import cv2
import pytesseract
import mysql.connector
from PIL import Image, UnidentifiedImageError
from dotenv import load_dotenv

load_dotenv()


def preprocess_image_for_ocr(image_path):
    """Grayscale, upscale, and threshold the image to improve OCR accuracy."""
    try:
        Image.open(image_path).verify()
    except UnidentifiedImageError:
        print("Error: File is not a valid image.")
        sys.exit(1)

    image = cv2.imread(image_path)
    if image is None:
        print("Error: Cannot read image file.")
        sys.exit(1)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    _, thresh = cv2.threshold(gray, 130, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    os.makedirs("images", exist_ok=True)
    processed_path = "images/_processed_temp.jpg"
    cv2.imwrite(processed_path, thresh)
    return Image.open(processed_path)


def extract_text(image_path):
    img = preprocess_image_for_ocr(image_path)
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(img, config=custom_config)
    return text


def parse_aadhaar_data(text):
    """Extracts aadhaar_number, dob, gender via regex, and name via a
    heuristic that scores nearby lines for 'looks like a name'-ness
    (low digit/special-char ratio, no boilerplate keywords, near the DOB
    line if found)."""
    data = {}
    # Match Aadhaar number tolerant of OCR spacing errors: try the
    # expected "1234 5678 9012" format first, then fall back to checking
    # each line individually for 12 consecutive digits once whitespace is
    # stripped FROM THAT LINE ONLY. Stripping whitespace from the whole
    # document instead would risk accidentally concatenating digits from
    # unrelated fields (e.g. part of a date + part of another number)
    # into a false 12-digit match -- restricting to one line at a time
    # avoids that.
    aadhaar_match = re.search(r"\d{4}\s\d{4}\s\d{4}", text)
    if not aadhaar_match:
        aadhaar_match = re.search(r"\d{12}", text)
    if not aadhaar_match:
        for line in text.split('\n'):
            stripped_line = re.sub(r"\s+", "", line)
            candidate = re.search(r"\d{12}", stripped_line)
            if candidate:
                aadhaar_match = candidate
                break

    dob_match = re.search(r"\d{2}/\d{2}/\d{4}", text)
    gender_match = re.search(r"Male|Female", text, re.IGNORECASE)

    data['aadhaar_number'] = aadhaar_match.group().replace(" ", "") if aadhaar_match else None
    data['dob'] = dob_match.group() if dob_match else None
    data['gender'] = gender_match.group().upper() if gender_match else None

    lines = [line.strip() for line in text.split('\n') if line.strip()]
    keywords = ['government', 'india', 'dob', 'male', 'female']

    def is_good_name_candidate(line):
        if any(k in line.lower() for k in keywords):
            return False
        digits = sum(c.isdigit() for c in line)
        specials = sum(not c.isalnum() and not c.isspace() for c in line)
        length = len(line)
        if length == 0:
            return False
        if digits / length > 0.2 or specials / length > 0.2:
            return False
        alpha_count = sum(c.isalpha() for c in line)
        if alpha_count < 3:
            return False
        return True

    name = None
    if data['dob']:
        dob_index = next((i for i, line in enumerate(lines) if data['dob'] in line), None)
        if dob_index is not None:
            candidates = [
                line for line in lines[max(0, dob_index - 5):dob_index]
                if is_good_name_candidate(line)
            ]
            if candidates:
                name = max(candidates, key=len)

    if not name:
        candidates = [line for line in lines if is_good_name_candidate(line)]
        if candidates:
            name = max(candidates, key=len)

    if name:
        name = re.sub(r"[^A-Za-z\s.'-]+", '', name)
        name = re.sub(r'\s+', ' ', name).strip()

    data['name'] = name
    return data


def save_json(data, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=4)


def _get_db_connection():
    """Reads DB credentials from environment variables instead of hardcoding
    them. Set DB_HOST / DB_USER / DB_PASSWORD / DB_NAME before running --
    see .env.example."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "aadhaar_db"),
    )


def insert_into_database(data):
    connection = None
    cursor = None
    try:
        connection = _get_db_connection()
        cursor = connection.cursor()
        insert_query = """
        INSERT INTO aadhaar_data (name, aadhaar_number, dob, gender)
        VALUES (%s, %s, %s, %s)
        """
        values = (data.get('name'), data.get('aadhaar_number'), data.get('dob'), data.get('gender'))
        cursor.execute(insert_query, values)
        connection.commit()
        print("Data inserted into MySQL.")
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# Batch processing: parse every image in the images/ folder.
if __name__ == "__main__":
    folder = "images"
    supported_exts = ('.png', '.jpg', '.jpeg')

    if not os.path.isdir(folder):
        print(f"'{folder}' directory not found.")
        sys.exit(1)

    image_files = [f for f in os.listdir(folder) if f.lower().endswith(supported_exts)]
    if not image_files:
        print(f"No image files found in '{folder}'")
        sys.exit(1)

    for img_file in image_files:
        image_path = os.path.join(folder, img_file)
        print(f"\nProcessing: {img_file}")

        text = extract_text(image_path)
        parsed = parse_aadhaar_data(text)
        print("Extracted Data:", json.dumps(parsed, indent=4))

        json_name = os.path.splitext(img_file)[0] + ".json"
        save_json(parsed, os.path.join("output", json_name))
        insert_into_database(parsed)
