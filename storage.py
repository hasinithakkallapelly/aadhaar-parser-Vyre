import hashlib
import hmac
import os
import secrets
import sqlite3
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE = BASE_DIR / "data" / "aadhaar.db"
LOCAL_KEY_FILE = BASE_DIR / ".local_hash_key"


def _hash_key() -> bytes:
    configured = os.getenv("APP_HASH_KEY")
    if configured:
        return configured.encode("utf-8")
    if not LOCAL_KEY_FILE.exists():
        LOCAL_KEY_FILE.write_text(secrets.token_hex(32), encoding="utf-8")
        try:
            LOCAL_KEY_FILE.chmod(0o600)
        except OSError:
            pass
    return LOCAL_KEY_FILE.read_text(encoding="utf-8").strip().encode("utf-8")


def identifier_hash(aadhaar_number: str) -> str:
    return hmac.new(_hash_key(), aadhaar_number.encode("utf-8"), hashlib.sha256).hexdigest()


class AadhaarStore:
    def __init__(self, database_path=None):
        configured = os.getenv("DATABASE_PATH")
        self.database_path = Path(database_path or configured or DEFAULT_DATABASE)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS aadhaar_records (
                    identifier_hash TEXT PRIMARY KEY,
                    aadhaar_last4 TEXT NOT NULL,
                    name TEXT NOT NULL,
                    dob TEXT NOT NULL,
                    gender TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def find(self, aadhaar_number: str):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT aadhaar_last4, name, dob, gender, created_at "
                "FROM aadhaar_records WHERE identifier_hash = ?",
                (identifier_hash(aadhaar_number),),
            ).fetchone()
        return dict(row) if row else None

    def create(self, data: dict) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO aadhaar_records "
                "(identifier_hash, aadhaar_last4, name, dob, gender) VALUES (?, ?, ?, ?, ?)",
                (
                    identifier_hash(data["aadhaar_number"]),
                    data["aadhaar_number"][-4:],
                    data["name"],
                    data["dob"],
                    data.get("gender"),
                ),
            )
            return cursor.rowcount == 1
