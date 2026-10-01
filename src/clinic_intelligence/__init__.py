from .routes import router


def doctor_for_user(user, db):
    from src.database.models import Doctor

    return (
        db.query(Doctor)
        .filter(Doctor.user_id == user.id)
        .first()
    )


def can_access_patient(
    current_user,
    patient_id,
    db,
):
    if current_user.role == "admin":
        return True

    if current_user.role == "patient":
        return current_user.id == patient_id

    if current_user.role == "doctor":
        doctor = doctor_for_user(
            current_user,
            db
        )

        if not doctor:
            return False

        from src.database.models import Appointment

        appointment = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == doctor.id,
                Appointment.patient_id == patient_id,
            )
            .first()
        )

        return appointment is not None

    return False


__all__ = [
    "router",
    "doctor_for_user",
    "can_access_patient",
]