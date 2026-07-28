import os
import re
import shutil

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import mysql.connector

from parser.aadhaar_parser import extract_text, parse_aadhaar_data, insert_into_database
from parser.document_validator import validate_document_type

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def _get_db_connection():
    """Reads DB credentials from environment variables -- see .env.example."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "aadhaar_db"),
    )


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    text = extract_text(file_location)

    # Basic document-type check BEFORE full field extraction -- catches
    # wrong document types (PAN card, voter ID, etc.) or unreadable
    # uploads early, with a clear reason, instead of silently producing
    # garbage parsed data from a non-Aadhaar document.
    validation = validate_document_type(text)
    if not validation.is_valid_aadhaar:
        return JSONResponse(
            status_code=400,
            content={
                "message": "Uploaded document does not appear to be an Aadhaar card.",
                "reasons": validation.reasons,
                "likely_document_type": validation.likely_document_type,
            },
        )

    data = parse_aadhaar_data(text)

    if not data['aadhaar_number']:
        # BUG FIX: the original code returned `{"..."}`, which is a Python
        # SET literal, not a dict -- FastAPI/JSON cannot serialize a set,
        # so this line would raise a 500 error instead of the intended 400
        # response. Confirmed by running json.dumps() on the original
        # literal directly. Fixed by using an actual dict below.
        return JSONResponse(status_code=400, content={"message": "Aadhaar number not found."})

    cursor = None
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM aadhaar_data WHERE aadhaar_number = %s", (data['aadhaar_number'],))
        result = cursor.fetchone()
        if result:
            # Same set-vs-dict bug existed here too.
            return {"message": f"Welcome back, {result[0]}! Thanks for joining us."}
        else:
            insert_into_database(data)
            return {"message": "Aadhaar data saved successfully.", "data": data}
    except mysql.connector.Error as err:
        return JSONResponse(status_code=500, content={"message": f"Database error: {err}"})
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.post("/recognise")
async def recognise_image(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    text = extract_text(file_location)
    match = re.search(r"\d{4}\s\d{4}\s\d{4}|\d{12}", text)
    if not match:
        return JSONResponse(status_code=400, content={"message": "Aadhaar number not detected."})

    aadhaar_number = match.group().replace(" ", "")

    cursor = None
    conn = None
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM aadhaar_data WHERE aadhaar_number = %s", (aadhaar_number,))
        result = cursor.fetchone()
        if result:
            return {"message": f"Welcome back, {result[0]}! Thanks for joining us."}
        else:
            return {"message": "You are a new user. Please sign in."}
    except mysql.connector.Error as err:
        return JSONResponse(status_code=500, content={"message": f"Database error: {err}"})
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
