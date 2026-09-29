from langchain_core.tools import tool
from langgraph.types import interrupt

from .db import conn, cur, is_valid_date, is_valid_phone, normalize_phone


@tool
def search_patient(name: str | None = None, phone: str | None = None) -> str:
    """Use this tool to look up a patient by phone number or name. Prefer the phone number over the name when both are given."""

    if phone and is_valid_phone(phone):
        normalized = normalize_phone(phone)
        cur.execute("SELECT id, name FROM patients WHERE phone = ?", (normalized,))
        row = cur.fetchone()
        if row:
            patient_id, patient_name = row
            return f"id={patient_id}, name={patient_name}"
        return f"No patient found with phone '{phone}'."

    if name:
        cur.execute("SELECT id, name, phone FROM patients WHERE name LIKE ?", (f"%{name}%",))
        rows = cur.fetchall()
        if rows:
            return "\n".join(f"id={r[0]}, name={r[1]}, phone={r[2]}" for r in rows)
        return f"No patient found with name '{name}'."

    return "Please provide a patient name or phone number to search."


@tool
def get_patient_history(name: str | None = None, phone: str | None = None) -> str:
    """Use this tool to look up a patient's history of past appointments by phone number or name. Prefer the phone number over the name when both are given."""

    if phone and is_valid_phone(phone):
        normalized = normalize_phone(phone)
        cur.execute("SELECT id, name FROM patients WHERE phone = ?", (normalized,))
        row = cur.fetchone()

        if row:
            patient_id, patient_name = row
            cur.execute(
                """SELECT s.date, s.time, d.name, a.status, a.reason
                   FROM appointments a
                   JOIN slots s ON a.slot_id = s.id
                   JOIN doctors d ON a.doctor_id = d.id
                   WHERE a.patient_id = ?
                   ORDER BY s.date, s.time""",
                (patient_id,)
            )
            appointments = cur.fetchall()

            if not appointments:
                return f"{patient_name} (id={patient_id}) has no appointment history."

            lines = [f"{date} {time} with {doctor} - {status} ({reason})"
                     for date, time, doctor, status, reason in appointments]
            return f"History for {patient_name} (id={patient_id}):\n" + "\n".join(lines)

        return f"No patient found with phone '{phone}'."

    if name:
        cur.execute("SELECT id, name, phone FROM patients WHERE name LIKE ?", (f"%{name}%",))
        rows = cur.fetchall()
        if rows:
            return "\n".join(f"id={r[0]}, name={r[1]}, phone={r[2]}" for r in rows)
        return f"No patient found with name '{name}'."

    return "Please provide a patient name or phone number."


@tool
def list_doctors(speciality: str | None = None) -> str:
    """Use this tool to look up the clinic's doctors. Optionally filter by speciality (e.g. 'dentist', 'cardiology'); leave it empty to list all doctors."""

    if speciality:
        cur.execute("SELECT id, name, specialty FROM doctors WHERE specialty LIKE ?", (f"%{speciality}%",))
    else:
        cur.execute("SELECT id, name, specialty FROM doctors")
    rows = cur.fetchall()

    if rows:
        return "\n".join(f"id={r[0]}, name={r[1]}, specialty={r[2]}" for r in rows)
    if speciality:
        return f"No doctors found with speciality '{speciality}'."
    return "No doctors found."


@tool
def check_availability(doctor_id: str | None = None, date: str | None = None) -> str:
    """Use this tool to look up the available (free) slots for a doctor on a specific date. Requires doctor_id and date, and the date must be in YYYY-MM-DD format."""
    if date and is_valid_date(date):
        cur.execute("SELECT id, time FROM slots WHERE doctor_id = ? AND date = ? AND is_booked = 0 ORDER BY time", (doctor_id, date))
        rows = cur.fetchall()

        if rows:
            return "\n".join(f"id={r[0]}, time={r[1]}" for r in rows)
        return f"No available slots for doctor {doctor_id} on {date}."

    return "Please provide a doctor_id and a date in YYYY-MM-DD format."


@tool
def get_treatment_price(name: str | None = None) -> str:
    """Use this tool to look up the price of a treatment by name."""
    if name:
        cur.execute("SELECT name, price FROM treatments WHERE name LIKE ?", (f"%{name}%",))
        rows = cur.fetchall()

        if rows:
            return "\n".join(f"name={r[0]}, price={r[1]} EGP" for r in rows)
        return f"No treatment found with name '{name}'."

    return "Please provide a treatment name."


@tool
def get_clinic_info(topic: str | None = None) -> str:
    """Use this tool to look up general clinic information (e.g. hours, address, insurance) by topic."""
    if topic:
        cur.execute("SELECT topic, content FROM clinic_info WHERE topic LIKE ?", (f"%{topic}%",))
        rows = cur.fetchall()

        if rows:
            return "\n".join(f"{r[0]}: {r[1]}" for r in rows)
        return f"No clinic information found for topic '{topic}'."

    return "Please provide a topic (e.g. hours, address, insurance)."


@tool
def book_appointment(patient_id: str | None = None, doctor_id: str | None = None, slot_id: str | None = None) -> str:
    """Use this tool to book an appointment for a patient with a doctor at a specific slot.
    Requires patient_id, doctor_id, and slot_id. This is a write action and requires human approval."""

    if not (patient_id and doctor_id and slot_id):
        return "Please provide patient_id, doctor_id, and slot_id."

    cur.execute("SELECT name FROM patients WHERE id = ?", (patient_id,))
    patient = cur.fetchone()
    if not patient:
        return f"No patient found with id '{patient_id}'."

    cur.execute("SELECT date, time, doctor_id, is_booked FROM slots WHERE id = ?", (slot_id,))
    slot = cur.fetchone()
    if not slot:
        return f"No slot found with id '{slot_id}'."
    date, time, slot_doctor_id, is_booked = slot
    if str(slot_doctor_id) != str(doctor_id):
        return f"Slot {slot_id} does not belong to doctor {doctor_id}."
    if is_booked:
        return f"Slot {slot_id} on {date} at {time} is already booked."

    decision = interrupt({
        "action": "book_appointment",
        "patient_id": patient_id,
        "patient_name": patient[0],
        "doctor_id": doctor_id,
        "slot_id": slot_id,
        "date": date,
        "time": time,
    })

    if not decision.get("approved"):
        return "Booking not approved - cancelled."

    # re-check: the slot may have been booked by someone else while waiting for approval
    cur.execute("SELECT is_booked FROM slots WHERE id = ?", (slot_id,))
    current = cur.fetchone()
    if not current or current[0]:
        return f"Slot {slot_id} is no longer available - it was booked while waiting for approval."

    cur.execute(
        "INSERT INTO appointments (patient_id, doctor_id, slot_id, status, reason) VALUES (?, ?, ?, 'booked', ?)",
        (patient_id, doctor_id, slot_id, decision.get("reason", "")),
    )
    cur.execute("UPDATE slots SET is_booked = 1 WHERE id = ?", (slot_id,))
    conn.commit()

    return f"Appointment booked: {patient[0]} with doctor {doctor_id} on {date} at {time}."


@tool
def cancel_appointment(appointment_id: str | None = None, reason: str | None = None) -> str:
    """Use this tool to cancel an existing booked appointment. Requires appointment_id;
    reason is optional context for the cancellation. This is a write action and requires human approval."""

    if not appointment_id:
        return "Please provide an appointment_id."

    cur.execute(
        """SELECT a.status, a.slot_id, a.patient_id, s.date, s.time, p.name
           FROM appointments a
           JOIN slots s ON a.slot_id = s.id
           JOIN patients p ON a.patient_id = p.id
           WHERE a.id = ?""",
        (appointment_id,)
    )
    row = cur.fetchone()
    if not row:
        return f"No appointment found with id '{appointment_id}'."

    status, slot_id, patient_id, date, time, patient_name = row
    if status != "booked":
        return f"Appointment {appointment_id} is already '{status}' - nothing to cancel."

    decision = interrupt({
        "action": "cancel_appointment",
        "appointment_id": appointment_id,
        "patient_name": patient_name,
        "date": date,
        "time": time,
        "cancellation_reason": reason,
    })

    if not decision.get("approved"):
        return "Cancellation not approved."

    cur.execute("SELECT status FROM appointments WHERE id = ?", (appointment_id,))
    current = cur.fetchone()
    if not current or current[0] != "booked":
        return f"Appointment {appointment_id} is no longer booked - nothing to cancel."

    cur.execute("UPDATE appointments SET status = 'cancelled' WHERE id = ?", (appointment_id,))
    cur.execute("UPDATE slots SET is_booked = 0 WHERE id = ?", (slot_id,))
    conn.commit()

    return f"Appointment {appointment_id} for {patient_name} on {date} at {time} cancelled."


@tool
def reschedule_appointment(appointment_id: str | None = None, new_slot_id: str | None = None) -> str:
    """Use this tool to move an existing booked appointment to a different slot.
    Requires appointment_id and new_slot_id. This is a write action and requires human approval."""

    if not (appointment_id and new_slot_id):
        return "Please provide an appointment_id and a new_slot_id."

    cur.execute(
        """SELECT a.status, a.slot_id, a.doctor_id, p.name, s.date, s.time
           FROM appointments a
           JOIN slots s ON a.slot_id = s.id
           JOIN patients p ON a.patient_id = p.id
           WHERE a.id = ?""",
        (appointment_id,)
    )
    row = cur.fetchone()
    if not row:
        return f"No appointment found with id '{appointment_id}'."

    status, old_slot_id, doctor_id, patient_name, old_date, old_time = row
    if status != "booked":
        return f"Appointment {appointment_id} is '{status}' - only booked appointments can be rescheduled."

    cur.execute("SELECT doctor_id, date, time, is_booked FROM slots WHERE id = ?", (new_slot_id,))
    new_slot = cur.fetchone()
    if not new_slot:
        return f"No slot found with id '{new_slot_id}'."
    new_doctor_id, new_date, new_time, new_is_booked = new_slot
    if str(new_doctor_id) != str(doctor_id):
        return f"Slot {new_slot_id} belongs to a different doctor than the current appointment."
    if new_is_booked:
        return f"Slot {new_slot_id} on {new_date} at {new_time} is already booked."
    if str(new_slot_id) == str(old_slot_id):
        return "That is already the appointment's current slot."

    decision = interrupt({
        "action": "reschedule_appointment",
        "appointment_id": appointment_id,
        "patient_name": patient_name,
        "old_date": old_date,
        "old_time": old_time,
        "new_date": new_date,
        "new_time": new_time,
    })

    if not decision.get("approved"):
        return "Reschedule not approved."

    cur.execute("SELECT status, slot_id FROM appointments WHERE id = ?", (appointment_id,))
    current = cur.fetchone()
    if not current or current[0] != "booked" or str(current[1]) != str(old_slot_id):
        return f"Appointment {appointment_id} changed while waiting for approval - please retry."

    cur.execute("SELECT is_booked FROM slots WHERE id = ?", (new_slot_id,))
    new_current = cur.fetchone()
    if not new_current or new_current[0]:
        return f"Slot {new_slot_id} is no longer available - it was booked while waiting for approval."

    cur.execute("UPDATE slots SET is_booked = 0 WHERE id = ?", (old_slot_id,))
    cur.execute("UPDATE slots SET is_booked = 1 WHERE id = ?", (new_slot_id,))
    cur.execute("UPDATE appointments SET slot_id = ? WHERE id = ?", (new_slot_id, appointment_id))
    conn.commit()

    return f"Appointment {appointment_id} for {patient_name} rescheduled from {old_date} {old_time} to {new_date} {new_time}."


@tool
def register_patient(name: str | None = None, phone: str | None = None, dob: str | None = None) -> str:
    """Use this tool to register a new patient. Requires name, phone, and dob (YYYY-MM-DD).
    This is a write action and requires human approval."""

    if not (name and phone and dob):
        return "Please provide name, phone, and dob (YYYY-MM-DD)."

    if not is_valid_phone(phone):
        return f"'{phone}' is not a valid phone number."
    if not is_valid_date(dob):
        return f"'{dob}' is not a valid date. Please use YYYY-MM-DD."

    normalized = normalize_phone(phone)
    cur.execute("SELECT id, name FROM patients WHERE phone = ?", (normalized,))
    existing = cur.fetchone()
    if existing:
        return f"A patient with this phone number already exists: id={existing[0]}, name={existing[1]}."

    decision = interrupt({
        "action": "register_patient",
        "name": name,
        "phone": normalized,
        "dob": dob,
    })

    if not decision.get("approved"):
        return "Registration not approved."

    # re-check: someone else may have registered this phone number while waiting for approval
    cur.execute("SELECT id FROM patients WHERE phone = ?", (normalized,))
    if cur.fetchone():
        return f"A patient with phone '{normalized}' was registered while waiting for approval."

    cur.execute(
        "INSERT INTO patients (name, phone, dob) VALUES (?, ?, ?)",
        (name, normalized, dob),
    )
    conn.commit()

    return f"Patient registered: id={cur.lastrowid}, name={name}, phone={normalized}."


tools = [
    search_patient,
    get_patient_history,
    list_doctors,
    check_availability,
    get_treatment_price,
    get_clinic_info,
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
    register_patient,
]
