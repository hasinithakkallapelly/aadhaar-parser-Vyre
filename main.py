"""
main.py -- single-image CLI entry point.

CLARITY NOTE: the original repo had two different "main" flows that did
different things and could confuse anyone reading the repo -- this file
hardcoded a single image path and only called save_json (no DB insert),
while parser/aadhaar_parser.py's own __main__ block does batch folder
processing WITH database insertion. Both are still here, but now clearly
labeled for what each is:
  - main.py            -> single image, prints result, saves JSON only
  - parser/aadhaar_parser.py (run directly) -> batch-process every image
    in images/, saving JSON + inserting into MySQL for each

Usage: python main.py [image_path]
Defaults to images/sample_aadhaar.jpg if no path given.
"""

import os
import sys
from parser.aadhaar_parser import extract_text, parse_aadhaar_data, save_json

DEFAULT_IMAGE_PATH = "images/sample_aadhaar.jpg"
OUTPUT_PATH = "output/parsed_data.json"


def main():
    image_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGE_PATH

    if not os.path.exists(image_path):
        print(f"Image not found at {image_path}")
        print(f"Usage: python main.py [image_path]  (default: {DEFAULT_IMAGE_PATH})")
        return

    text = extract_text(image_path)
    data = parse_aadhaar_data(text)
    save_json(data, OUTPUT_PATH)

    print("Data extracted and saved to", OUTPUT_PATH)
    print("Parsed Data:")
    print(data)


if __name__ == "__main__":
    main()
