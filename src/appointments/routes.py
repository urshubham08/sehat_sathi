
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.appointments.services import create_appointment
from src.database.database import get_db
from src.database.models import Appointment, Doctor, User


router = APIRouter(prefix="/appointments", tags=["Appointments"])


# ============================================================
# COMMON HELPERS
# ============================================================

def get_current_user(
    request: Request,
    db: Session,
):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please login first.",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        request.session.clear()
        raise HTTPException(
            status_code=401,
            detail="User not found.",
        )

    return user


def require_admin(
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )

    return user


def time_to_string(value):
    """
    MySQL TIME can sometimes come back as datetime.time
    and sometimes as timedelta.
    """
    if value is None:
        return ""

    if isinstance(value, time):
        return value.strftime("%H:%M")

    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = (total_seconds // 3600) % 24
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"

    value_string = str(value)

    if len(value_string) >= 5:
        return value_string[:5]

    return value_string


# ============================================================
# BOOK APPOINTMENT
# ============================================================

@router.get(
    "/book/{doctor_id}",
    response_class=HTMLResponse,
)
async def book_appointment_page(
    doctor_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    if user.role not in {"patient", "admin"}:
        raise HTTPException(
            status_code=403,
            detail="Only patients and admins can book appointments.",
        )

    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id == doctor_id,
            Doctor.availability_status == "active",
        )
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found or unavailable.",
        )

    return HTMLResponse(
        f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Book Appointment</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: #f4f7fb;
                    padding: 30px;
                }}

                .box {{
                    max-width: 550px;
                    margin: auto;
                    background: white;
                    padding: 30px;
                    border-radius: 14px;
                    box-shadow: 0 5px 20px rgba(0,0,0,.08);
                }}

                input, select, button {{
                    width: 100%;
                    padding: 12px;
                    margin-top: 8px;
                    margin-bottom: 18px;
                    box-sizing: border-box;
                }}

                button {{
                    background: #2563eb;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                }}

                a {{
                    text-decoration: none;
                }}
            </style>
        </head>

        <body>

        <div class="box">

            <h2>Book Appointment</h2>

            <p>
                <strong>Doctor:</strong> {doctor.name}
            </p>

            <p>
                <strong>Specialty:</strong> {doctor.specialty}
            </p>

            <p>
                <strong>Consultation Fee:</strong> ₹{doctor.consultation_fee}
            </p>

            <form method="post"
                  action="/appointments/book/{doctor.id}">

                <label>Appointment Date</label>
                <input
                    type="date"
                    name="appointment_date"
                    min="{date.today().isoformat()}"
                    required
                >

                <label>Appointment Time</label>
                <input
                    type="time"
                    name="appointment_time"
                    required
                >

                <button type="submit">
                    Book Appointment
                </button>

            </form>

            <a href="/doctors/list-page">
                ← Back to Doctors
            </a>

        </div>

        </body>
        </html>
        """
    )


@router.post(
    "/book/{doctor_id}",
)
async def book_appointment(
    doctor_id: int,
    request: Request,
    appointment_date: str = Form(...),
    appointment_time: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    if user.role not in {"patient", "admin"}:
        raise HTTPException(
            status_code=403,
            detail="Only patients and admins can book appointments.",
        )

    # Admin can book on behalf of the logged-in admin account.
    # Normal patient booking uses the patient's own user ID.
    patient_id = user.id

    try:
        parsed_date = date.fromisoformat(appointment_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid appointment date.",
        )

    try:
        parsed_time = datetime.strptime(
            appointment_time,
            "%H:%M",
        ).time()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid appointment time.",
        )

    try:
        appointment = create_appointment(
            db=db,
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date=parsed_date,
            appointment_time=parsed_time,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    return RedirectResponse(
        url=f"/appointments/my?success=Appointment+booked+successfully&id={appointment.id}",
        status_code=303,
    )


# ============================================================
# MY APPOINTMENTS
# ============================================================

@router.get(
    "/my",
    response_class=HTMLResponse,
)
async def my_appointments(
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    # ========================================================
    # ADMIN = FULL ACCESS
    # ========================================================

    if user.role == "admin":

        appointments = (
            db.query(Appointment)
            .order_by(
                Appointment.appointment_date.desc(),
                Appointment.appointment_time.desc(),
            )
            .all()
        )

        page_title = "All Appointments - Admin"

    # ========================================================
    # PATIENT = OWN APPOINTMENTS
    # ========================================================

    elif user.role == "patient":

        appointments = (
            db.query(Appointment)
            .filter(
                Appointment.patient_id == user.id
            )
            .order_by(
                Appointment.appointment_date.desc(),
                Appointment.appointment_time.desc(),
            )
            .all()
        )

        page_title = "My Appointments"

    # ========================================================
    # DOCTOR = OWN APPOINTMENTS
    # ========================================================

    elif user.role == "doctor":

        doctor = (
            db.query(Doctor)
            .filter(Doctor.user_id == user.id)
            .first()
        )

        if not doctor:
            raise HTTPException(
                status_code=404,
                detail="Doctor profile not found.",
            )

        appointments = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == doctor.id
            )
            .order_by(
                Appointment.appointment_date.desc(),
                Appointment.appointment_time.desc(),
            )
            .all()
        )

        page_title = "Doctor Appointments"

    else:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access appointments.",
        )

    rows = ""

    for appointment in appointments:

        patient = (
            db.query(User)
            .filter(
                User.id == appointment.patient_id
            )
            .first()
        )

        doctor = (
            db.query(Doctor)
            .filter(
                Doctor.id == appointment.doctor_id
            )
            .first()
        )

        patient_name = (
            patient.name
            if patient
            else "Unknown Patient"
        )

        doctor_name = (
            doctor.name
            if doctor
            else "Unknown Doctor"
        )

        appointment_time = time_to_string(
            appointment.appointment_time
        )

        action_html = ""

        # Admin can cancel any appointment
        if user.role == "admin":
            action_html = f"""
                <a
                    class="danger"
                    href="/appointments/cancel/{appointment.id}"
                    onclick="return confirm('Cancel this appointment?')"
                >
                    Cancel
                </a>
            """

        # Patient can cancel own appointment
        elif (
            user.role == "patient"
            and appointment.patient_id == user.id
        ):
            action_html = f"""
                <a
                    class="danger"
                    href="/appointments/cancel/{appointment.id}"
                    onclick="return confirm('Cancel this appointment?')"
                >
                    Cancel
                </a>
            """

        rows += f"""
            <tr>

                <td>{appointment.id}</td>

                <td>
                    {patient_name}
                </td>

                <td>
                    {doctor_name}
                </td>

                <td>
                    {appointment.appointment_date}
                </td>

                <td>
                    {appointment_time}
                </td>

                <td>
                    <span class="status">
                        {appointment.status}
                    </span>
                </td>

                <td>
                    {appointment.payment_status}
                </td>

                <td>
                    {action_html}
                </td>

            </tr>
        """

    if not rows:
        rows = """
            <tr>
                <td colspan="8" class="empty">
                    No appointments found.
                </td>
            </tr>
        """

    return HTMLResponse(
        f"""
        <!DOCTYPE html>
        <html>

        <head>

            <title>{page_title}</title>

            <style>

                body {{
                    margin: 0;
                    padding: 30px;
                    font-family: Arial, sans-serif;
                    background: #f4f7fb;
                }}

                .container {{
                    max-width: 1250px;
                    margin: auto;
                }}

                .header {{
                    background: white;
                    padding: 22px;
                    border-radius: 14px;
                    margin-bottom: 20px;
                    box-shadow: 0 4px 15px rgba(0,0,0,.06);
                }}

                .table-box {{
                    background: white;
                    padding: 20px;
                    border-radius: 14px;
                    overflow-x: auto;
                    box-shadow: 0 4px 15px rgba(0,0,0,.06);
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                    min-width: 900px;
                }}

                th, td {{
                    padding: 13px;
                    border-bottom: 1px solid #e5e7eb;
                    text-align: left;
                }}

                th {{
                    background: #f8fafc;
                }}

                .status {{
                    padding: 5px 9px;
                    border-radius: 6px;
                    background: #e0f2fe;
                }}

                .danger {{
                    color: #dc2626;
                    text-decoration: none;
                    font-weight: bold;
                }}

                .empty {{
                    text-align: center;
                    padding: 30px;
                    color: #64748b;
                }}

                .back {{
                    display: inline-block;
                    margin-top: 15px;
                    text-decoration: none;
                }}

            </style>

        </head>

        <body>

        <div class="container">

            <div class="header">

                <h1>{page_title}</h1>

                <p>
                    Logged in as:
                    <strong>{user.name}</strong>
                    ({user.role})
                </p>

                <a class="back" href="/dashboard">
                    ← Dashboard
                </a>

            </div>

            <div class="table-box">

                <table>

                    <thead>

                        <tr>
                            <th>ID</th>
                            <th>Patient</th>
                            <th>Doctor</th>
                            <th>Date</th>
                            <th>Time</th>
                            <th>Status</th>
                            <th>Payment</th>
                            <th>Action</th>
                        </tr>

                    </thead>

                    <tbody>

                        {rows}

                    </tbody>

                </table>

            </div>

        </div>

        </body>

        </html>
        """
    )


# ============================================================
# CANCEL APPOINTMENT
# ============================================================

@router.get(
    "/cancel/{appointment_id}",
)
async def cancel_appointment(
    appointment_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found.",
        )

    # ========================================================
    # ADMIN CAN CANCEL ANY APPOINTMENT
    # ========================================================

    if user.role == "admin":
        pass

    # ========================================================
    # PATIENT CAN CANCEL ONLY OWN APPOINTMENT
    # ========================================================

    elif user.role == "patient":

        if appointment.patient_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="You can cancel only your own appointments.",
            )

    # ========================================================
    # DOCTOR CAN CANCEL THEIR OWN APPOINTMENTS
    # ========================================================

    elif user.role == "doctor":

        doctor = (
            db.query(Doctor)
            .filter(
                Doctor.user_id == user.id
            )
            .first()
        )

        if not doctor:
            raise HTTPException(
                status_code=404,
                detail="Doctor profile not found.",
            )

        if appointment.doctor_id != doctor.id:
            raise HTTPException(
                status_code=403,
                detail="You can cancel only your own appointments.",
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission.",
        )

    # Don't cancel an already completed appointment
    if appointment.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="Completed appointments cannot be cancelled.",
        )

    appointment.status = "cancelled"

    db.commit()

    return RedirectResponse(
        url="/appointments/my?success=Appointment+cancelled",
        status_code=303,
    )


# ============================================================
# ADMIN - UPDATE APPOINTMENT STATUS
# ============================================================

@router.post(
    "/admin/status/{appointment_id}",
)
async def admin_update_status(
    appointment_id: int,
    status: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )

    allowed_statuses = {
        "booked",
        "confirmed",
        "completed",
        "cancelled",
        "no_show",
    }

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid appointment status.",
        )

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found.",
        )

    appointment.status = status

    db.commit()

    return RedirectResponse(
        url="/appointments/my?success=Status+updated",
        status_code=303,
    )


# ============================================================
# ADMIN - UPDATE PAYMENT STATUS
# ============================================================

@router.post(
    "/admin/payment-status/{appointment_id}",
)
async def admin_update_payment_status(
    appointment_id: int,
    payment_status: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )

    allowed_statuses = {
        "pending",
        "paid",
        "failed",
        "refunded",
        "cancelled",
    }

    if payment_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment status.",
        )

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found.",
        )

    appointment.payment_status = payment_status

    db.commit()

    return RedirectResponse(
        url="/appointments/my?success=Payment+status+updated",
        status_code=303,
    )


# ============================================================
# ADMIN - DELETE APPOINTMENT
# ============================================================

@router.get(
    "/admin/delete/{appointment_id}",
)
async def admin_delete_appointment(
    appointment_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found.",
        )

    db.delete(appointment)
    db.commit()

    return RedirectResponse(
        url="/appointments/my?success=Appointment+deleted",
        status_code=303,
    )


# ============================================================
# ADMIN - APPOINTMENT DETAIL
# ============================================================

@router.get(
    "/admin/detail/{appointment_id}",
    response_class=HTMLResponse,
)
async def admin_appointment_detail(
    appointment_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found.",
        )

    patient = (
        db.query(User)
        .filter(
            User.id == appointment.patient_id
        )
        .first()
    )

    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id == appointment.doctor_id
        )
        .first()
    )

    appointment_time = time_to_string(
        appointment.appointment_time
    )

    return HTMLResponse(
        f"""
        <!DOCTYPE html>
        <html>

        <head>

            <title>Appointment Details</title>

            <style>

                body {{
                    font-family: Arial, sans-serif;
                    background: #f4f7fb;
                    padding: 30px;
                }}

                .box {{
                    max-width: 750px;
                    margin: auto;
                    background: white;
                    padding: 30px;
                    border-radius: 14px;
                    box-shadow: 0 5px 20px rgba(0,0,0,.08);
                }}

                .item {{
                    padding: 14px;
                    border-bottom: 1px solid #e5e7eb;
                }}

                .label {{
                    font-weight: bold;
                    color: #475569;
                }}

                a {{
                    display: inline-block;
                    margin-top: 20px;
                    text-decoration: none;
                }}

            </style>

        </head>

        <body>

        <div class="box">

            <h1>Appointment Details</h1>

            <div class="item">
                <span class="label">Appointment ID:</span>
                {appointment.id}
            </div>

            <div class="item">
                <span class="label">Patient:</span>
                {patient.name if patient else "Unknown"}
            </div>

            <div class="item">
                <span class="label">Patient Email:</span>
                {patient.email if patient else "-"}
            </div>

            <div class="item">
                <span class="label">Patient Mobile:</span>
                {patient.mobile if patient else "-"}
            </div>

            <div class="item">
                <span class="label">Doctor:</span>
                {doctor.name if doctor else "Unknown"}
            </div>

            <div class="item">
                <span class="label">Specialty:</span>
                {doctor.specialty if doctor else "-"}
            </div>

            <div class="item">
                <span class="label">Date:</span>
                {appointment.appointment_date}
            </div>

            <div class="item">
                <span class="label">Time:</span>
                {appointment_time}
            </div>

            <div class="item">
                <span class="label">Appointment Status:</span>
                {appointment.status}
            </div>

            <div class="item">
                <span class="label">Payment Status:</span>
                {appointment.payment_status}
            </div>

            <a href="/appointments/my">
                ← Back to all appointments
            </a>

        </div>

        </body>

        </html>
        """
    )
