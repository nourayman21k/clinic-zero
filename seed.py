"""
seed_db.py - builds a fresh clinic.db with fake data for ClinicDesk Agent.
Run:  python seed_db.py   (deletes and recreates clinic.db every time)
"""
import os
import random
import sqlite3
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clinic.db")
random.seed(42)  # same fake data every run

SCHEMA = """
CREATE TABLE doctors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    specialty   TEXT NOT NULL
);

CREATE TABLE patients (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    phone       TEXT NOT NULL UNIQUE,
    dob         TEXT NOT NULL                -- YYYY-MM-DD
);

CREATE TABLE slots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id   INTEGER NOT NULL REFERENCES doctors(id),
    date        TEXT NOT NULL,               -- YYYY-MM-DD
    time        TEXT NOT NULL,               -- HH:MM
    is_booked   INTEGER NOT NULL DEFAULT 0,  -- 0 = free, 1 = booked
    UNIQUE (doctor_id, date, time)
);

CREATE TABLE appointments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id  INTEGER NOT NULL REFERENCES patients(id),
    doctor_id   INTEGER NOT NULL REFERENCES doctors(id),
    slot_id     INTEGER NOT NULL REFERENCES slots(id),
    status      TEXT NOT NULL CHECK (status IN ('booked', 'cancelled', 'completed')),
    reason      TEXT
);

CREATE TABLE treatments (
    name        TEXT PRIMARY KEY,
    price       INTEGER NOT NULL             -- EGP
);

CREATE TABLE clinic_info (
    topic       TEXT PRIMARY KEY,
    content     TEXT NOT NULL
);
"""

DOCTORS = [
    ("Dr. Ahmed Hassan", "General Dentistry"),
    ("Dr. Mona Khalil", "Orthodontics"),
    ("Dr. Karim Adel", "Endodontics"),
    ("Dr. Salma Youssef", "Pediatric Dentistry"),
]

PATIENTS = [
    ("Omar Farouk", "01012345678", "1995-03-14"),
    ("Nour Ibrahim", "01123456789", "2001-07-22"),
    ("Youssef Tarek", "01234567890", "1988-11-05"),
    ("Mariam Ali", "01098765432", "1999-01-30"),
    ("Hana Mostafa", "01187654321", "2015-06-18"),
    ("Khaled Samir", "01276543210", "1975-09-09"),
    ("Laila Mahmoud", "01555555123", "1992-12-01"),
    ("Mostafa Nabil", "01066677788", "1983-04-27"),
    ("Farida Sherif", "01199988877", "2012-10-11"),
    ("Ali Gamal", "01211122233", "1969-02-16"),
]

TREATMENTS = [
    ("Checkup", 300),
    ("Cleaning", 600),
    ("Filling", 900),
    ("Root Canal", 3500),
    ("Extraction", 1200),
    ("Whitening", 4000),
    ("Braces Consultation", 500),
    ("Crown", 5000),
]

CLINIC_INFO = [
    ("hours", "Saturday to Thursday, 10:00 to 17:00. Closed on Fridays."),
    ("address", "15 El-Merghany St, Heliopolis, Cairo, Egypt."),
    ("insurance", "We accept AXA, Allianz, and MetLife. Bring your insurance card to the visit."),
    ("parking", "Free street parking is available in front of the clinic."),
    ("cancellation_policy", "Please cancel at least 24 hours before your appointment."),
]

REASONS = ["Checkup", "Cleaning", "Filling", "Root Canal", "Extraction",
           "Whitening", "Braces Consultation", "Tooth pain", "Follow-up"]

TIMES = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
DAYS_BACK = 14      # past slots -> patient history
DAYS_AHEAD = 14     # future slots -> availability / booking


def build():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    cur.executemany("INSERT INTO doctors (name, specialty) VALUES (?, ?)", DOCTORS)
    cur.executemany("INSERT INTO patients (name, phone, dob) VALUES (?, ?, ?)", PATIENTS)
    cur.executemany("INSERT INTO treatments (name, price) VALUES (?, ?)", TREATMENTS)
    cur.executemany("INSERT INTO clinic_info (topic, content) VALUES (?, ?)", CLINIC_INFO)

    # slots: every working day (no Fridays) from DAYS_BACK ago to DAYS_AHEAD ahead
    today = date.today()
    for doctor_id in range(1, len(DOCTORS) + 1):
        for offset in range(-DAYS_BACK, DAYS_AHEAD + 1):
            d = today + timedelta(days=offset)
            if d.weekday() == 4:  # Friday
                continue
            for t in TIMES:
                cur.execute("INSERT INTO slots (doctor_id, date, time) VALUES (?, ?, ?)",
                            (doctor_id, d.isoformat(), t))

    patient_ids = list(range(1, len(PATIENTS) + 1))
    today_str = today.isoformat()

    # past appointments: 20 completed + 3 cancelled (history)
    past_slots = cur.execute(
        "SELECT id, doctor_id FROM slots WHERE date < ?", (today_str,)).fetchall()
    for i, (slot_id, doctor_id) in enumerate(random.sample(past_slots, 23)):
        status = "cancelled" if i < 3 else "completed"
        cur.execute(
            "INSERT INTO appointments (patient_id, doctor_id, slot_id, status, reason) VALUES (?, ?, ?, ?, ?)",
            (random.choice(patient_ids), doctor_id, slot_id, status, random.choice(REASONS)))
        if status == "completed":
            cur.execute("UPDATE slots SET is_booked = 1 WHERE id = ?", (slot_id,))

    # future appointments: 15 booked, so some slots are already taken
    future_slots = cur.execute(
        "SELECT id, doctor_id FROM slots WHERE date > ?", (today_str,)).fetchall()
    for slot_id, doctor_id in random.sample(future_slots, 15):
        cur.execute(
            "INSERT INTO appointments (patient_id, doctor_id, slot_id, status, reason) VALUES (?, ?, ?, 'booked', ?)",
            (random.choice(patient_ids), doctor_id, slot_id, random.choice(REASONS)))
        cur.execute("UPDATE slots SET is_booked = 1 WHERE id = ?", (slot_id,))

    conn.commit()

    # summary
    for table in ["doctors", "patients", "slots", "appointments", "treatments", "clinic_info"]:
        count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:<13} {count} rows")
    free = cur.execute("SELECT COUNT(*) FROM slots WHERE is_booked = 0 AND date > ?", (today_str,)).fetchone()[0]
    print(f"free future slots: {free}")
    print(f"created {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    build()