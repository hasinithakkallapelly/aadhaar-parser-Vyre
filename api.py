import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from parser.aadhaar_parser import InvalidImageError, extract_text_from_bytes, parse_aadhaar_data
from parser.document_validator import validate_document_type
from parser.field_validation import mask_aadhaar, validate_fields
from storage import AadhaarStore


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 5 * 1024 * 1024))

app = FastAPI(title="Aadhaar OCR Prototype", version="2.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _store():
    return AadhaarStore()


def process_image(image_bytes: bytes) -> dict:
    try:
        text = extract_text_from_bytes(image_bytes)
    except InvalidImageError:
        raise
    except Exception as exc:
        raise RuntimeError("OCR processing failed") from exc

    document = validate_document_type(text)
    if not document.is_valid_aadhaar:
        raise ValueError("Uploaded document does not appear to be an Aadhaar card")

    data = parse_aadhaar_data(text)
    fields = validate_fields(data)
    if not fields.valid:
        raise ValueError("; ".join(fields.errors))
    return data


async def _read_upload(file: UploadFile) -> bytes:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Only JPEG and PNG images are supported")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded image exceeds the size limit")
    return content


async def _extract(file: UploadFile):
    content = await _read_upload(file)
    try:
        return await run_in_threadpool(process_image, content)
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _public_fields(data: dict):
    return {
        "aadhaar_masked": mask_aadhaar(data["aadhaar_number"]),
        "name": data["name"],
        "dob": data["dob"],
        "gender": data.get("gender"),
    }


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@app.post("/upload", status_code=201, tags=["documents"])
async def upload_image(file: UploadFile = File(...)):
    data = await _extract(file)
    store = _store()
    existing = store.find(data["aadhaar_number"])
    if existing:
        return {"status": "existing", "data": _public_fields(data)}
    try:
        created = store.create(data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not save the parsed record") from exc
    return {"status": "created" if created else "existing", "data": _public_fields(data)}


@app.post("/recognise", tags=["documents"])
async def recognise_image(file: UploadFile = File(...)):
    data = await _extract(file)
    existing = _store().find(data["aadhaar_number"])
    return {
        "status": "existing" if existing else "new",
        "data": _public_fields(data),
    }

