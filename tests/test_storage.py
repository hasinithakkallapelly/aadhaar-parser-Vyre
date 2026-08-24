import sqlite3

from storage import AadhaarStore


def test_create_and_find_without_storing_full_number(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_HASH_KEY", "test-key")
    database = tmp_path / "test.db"
    store = AadhaarStore(database)
    data = {
        "aadhaar_number": "234567890123",
        "name": "Jane Test Doe",
        "dob": "1998-06-15",
        "gender": "FEMALE",
    }
    assert store.create(data) is True
    assert store.create(data) is False
    assert store.find(data["aadhaar_number"])["name"] == "Jane Test Doe"

    with sqlite3.connect(database) as connection:
        stored = connection.execute(
            "SELECT identifier_hash, aadhaar_last4 FROM aadhaar_records"
        ).fetchone()
    assert stored[0] != data["aadhaar_number"]
    assert stored[1] == "0123"

