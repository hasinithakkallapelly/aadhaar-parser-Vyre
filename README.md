# Aadhaar OCR and Record-Matching Prototype

A local document-processing web application that extracts structured fields from an Aadhaar image, validates the OCR result, and performs privacy-conscious returning-record lookup.

The application uses Tesseract for OCR, OpenCV for image preprocessing, FastAPI for the API, and SQLite for local storage.

## Features

- Responsive drag-and-drop web interface with image preview
- Clear loading, validation, and record-status feedback
- Accepts JPEG and PNG uploads up to 5 MB
- Processes images in memory without retaining uploaded documents
- Rejects unsupported, empty, oversized, and invalid files
- Checks for Aadhaar-specific text before extracting fields
- Extracts name, date of birth, gender, and Aadhaar number
- Validates Aadhaar numbers using the Verhoeff checksum
- Rejects impossible or future dates
- Stores an HMAC identifier and last four digits instead of the full Aadhaar number
- Uses SQLite, requiring no separate database server
- Masks Aadhaar numbers in every API response

## Processing flow

```text
Upload
  -> file type and size validation
  -> in-memory image decoding and preprocessing
  -> Tesseract OCR
  -> document-type validation
  -> structured field extraction
  -> checksum and date validation
  -> HMAC-based SQLite lookup
  -> masked response
```

## Requirements

- Python 3.10–3.12
- Tesseract OCR
- macOS, Linux, or Windows

## Setup on macOS

Install Tesseract:

```bash
brew install tesseract
```

Clone and set up the project:

```bash
git clone https://github.com/hasinithakkallapelly/aadhaar-parser-Vyre.git
cd aadhaar-parser-Vyre

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## Setup on Windows

1. Install Tesseract from the maintained Windows distribution:
   https://github.com/UB-Mannheim/tesseract/wiki
2. Make sure the Tesseract installation directory is available on `PATH`.
3. Run:

```powershell
git clone https://github.com/hasinithakkallapelly/aadhaar-parser-Vyre.git
cd aadhaar-parser-Vyre

py -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## Run the API

```bash
uvicorn api:app --reload
```

Open the web interface:

http://127.0.0.1:8000

The interactive API documentation remains available at:

http://127.0.0.1:8000/docs

The SQLite database is created automatically at `data/aadhaar.db`.

On the first database operation, a random local HMAC key is created in `.local_hash_key`. Both files are ignored by Git.

## API endpoints

### `POST /upload`

Parses and validates the image, then creates a record if it does not already exist.

Response fields are masked:

```json
{
  "status": "created",
  "data": {
    "aadhaar_masked": "XXXXXXXX9012",
    "name": "Jane Test Doe",
    "dob": "1998-06-15",
    "gender": "FEMALE"
  }
}
```

### `POST /recognise`

Runs the same validated OCR pipeline and reports whether the identifier already exists without creating a record.

### `GET /health`

Returns a small health response for local checks and deployment monitoring.

## Run the command-line parser

The CLI parses one image without saving it to the database:

```bash
python main.py /path/to/document.jpg
```

It prints only masked data.

## Run tests

```bash
pytest -q
```

The tests cover:

- Verhoeff checksum validation
- Aadhaar masking
- OCR-text field parsing
- Invalid date rejection
- PAN-card rejection
- SQLite insert and returning-record lookup
- Confirmation that the full Aadhaar number is not stored

## Configuration

The defaults work locally. For a persistent deployment, copy the example environment file:

```bash
cp .env.example .env
```

Generate a key:

```bash
openssl rand -hex 32
```

Place the generated value in `APP_HASH_KEY`.

| Variable | Purpose | Default |
|---|---|---|
| `APP_HASH_KEY` | HMAC key used for private identifier lookup | Locally generated key file |
| `DATABASE_PATH` | SQLite database location | `data/aadhaar.db` |
| `MAX_UPLOAD_BYTES` | Maximum upload size | `5242880` |

## Project structure

```text
api.py                              FastAPI endpoints, upload controls, and UI serving
static/index.html                    Document upload interface
static/styles.css                    Responsive visual design
static/app.js                        Upload, preview, and result interactions
main.py                             Single-image command-line entry point
storage.py                          HMAC identifiers and SQLite operations
parser/aadhaar_parser.py            In-memory preprocessing, OCR, and extraction
parser/document_validator.py        Document-type checks
parser/field_validation.py          Checksum, masking, and required-field validation
tests/                              Automated unit tests
```

## Security and privacy decisions

- Original uploads are not retained by the application
- Client filenames are never used as filesystem paths
- The complete Aadhaar number is not returned by the API
- The complete Aadhaar number is not stored in SQLite
- Parameterized database statements are used
- Local secrets and database files are ignored by Git

## Limitations

- This is an OCR and record-matching prototype, not official UIDAI verification
- Keyword validation cannot detect a sophisticated forged document
- OCR accuracy depends on image resolution, lighting, orientation, and print quality
- The name extractor is heuristic and can fail on unusual layouts
- Secure QR-code verification and liveness or tamper detection are not implemented
- Production use would require authentication, authorization, encryption, audit controls, rate limiting, and a formal privacy review

