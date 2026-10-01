from datetime import date, datetime, time

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.models import Appointment, Doctor


def validate_appointment_date(
    appointment_date: date
):
    if appointment_date < date.today():
        return False, "Appointment date cannot be in the past."

    return True, None


def validate_appointment_time(
    appointment_time
):
    if isinstance(appointment_time, time):
        return True, None

    if isinstance(appointment_time, datetime):
        return True, None

    if not isinstance(appointment_time, str):
        return False, "Invalid appointment time."

    try:
        datetime.strptime(
            appointment_time,
            "%H:%M"
        )
    except ValueError:
        return False, "Appointment time must be in HH:MM format."

    return True, None


def get_active_doctor(
    db: Session,
    doctor_id: int
):
    return (
        db.query(Doctor)
        .filter(
            Doctor.id == doctor_id,
            Doctor.availability_status == "active"
        )
        .first()
    )


def doctor_slot_is_available(
    db: Session,
    doctor_id: int,
    appointment_date: date,
    appointment_time
):
    existing = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.appointment_time == appointment_time,
            Appointment.status == "booked"
        )
        .first()
    )

    return existing is None


def create_appointment(
    db: Session,
    patient_id: int,
    doctor_id: int,
    appointment_date: date,
    appointment_time
):
    doctor = get_active_doctor(
        db,
        doctor_id
    )

    if not doctor:
        return None, "Doctor not found or inactive."

    valid_date, date_error = validate_appointment_date(
        appointment_date
    )

    if not valid_date:
        return None, date_error

    valid_time, time_error = validate_appointment_time(
        appointment_time
    )

    if not valid_time:
        return None, time_error

    if not doctor_slot_is_available(
        db,
        doctor_id,
        appointment_date,
        appointment_time
    ):
        return None, "This doctor is already booked for this date and time."

    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        status="booked",
        payment_status="pending"
    )

    db.add(appointment)

    try:
        db.commit()
        db.refresh(appointment)

    except IntegrityError:
        db.rollback()

        return None, (
            "This appointment slot was just booked by someone else. "
            "Please choose another time."
        )

    return appointment, None