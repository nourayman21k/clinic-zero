import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = os.getenv("CLINIC_DB", str(PROJECT_ROOT / "clinic.db"))
CHECKPOINTS_PATH = os.getenv("CLINIC_CHECKPOINTS", str(PROJECT_ROOT / "checkpoints.sqlite"))

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute("PRAGMA foreign_keys = ON")
cur = conn.cursor()

PHONE_PATTERN = re.compile(r"^(?:0020|20|\+20)?0?1[0-25]\d{8}$")


def is_valid_phone(phone: str) -> bool:
    return bool(PHONE_PATTERN.match(re.sub(r"[\s\-]", "", phone)))


def normalize_phone(phone: str) -> str:
    """Convert any phone format into the DB's stored format: 0XXXXXXXXXX."""
    digits = re.sub(r"\D", "", phone)  # strip spaces, dashes, +, etc.

    if digits.startswith("0020"):
        digits = digits[2:]
    if digits.startswith("20") and len(digits) == 12:
        digits = "0" + digits[2:]

    return digits


def is_valid_date(date_str: str) -> bool:
    """Check that the date is in YYYY-MM-DD format and is a real calendar date."""
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False
