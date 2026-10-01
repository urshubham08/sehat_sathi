from html import escape

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request
)

from fastapi.responses import (
    RedirectResponse,
    HTMLResponse
)

from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from src.authentication.routes import require_admin
from src.database.database import get_db
from src.database.models import Doctor, User

from src.doctors.services import (
    suggest_specialty,
    match_doctors
)


router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"]
)

templates = Jinja2Templates(
    directory="templates"
)


@router.get("/admin")
def doctor_admin_page(
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    doctors = (
        db.query(Doctor)
        .order_by(Doctor.id.desc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "doctor_admin.html",
        {
            "doctors": doctors,
            "admin_user": admin_user
        }
    )


@router.get("/list")
def doctor_list(
    request: Request,
    db: Session = Depends(get_db)
):
    doctors = (
        db.query(Doctor)
        .filter(
            Doctor.availability_status == "active"
        )
        .order_by(Doctor.name.asc())
        .all()
    )

    return [
        {
            "id": doctor.id,
            "name": doctor.name,
            "specialty": doctor.specialty,
            "qualification": doctor.qualification,
            "experience_years": doctor.experience_years,
            "consultation_fee": float(
                doctor.consultation_fee
            ),
            "availability_status":
                doctor.availability_status,
            "phone": doctor.phone,
            "email": doctor.email
        }
        for doctor in doctors
    ]


@router.post("/create")
def create_doctor(
    name: str = Form(...),
    specialty: str = Form(...),
    qualification: str = Form(""),
    experience_years: int = Form(0),
    consultation_fee: float = Form(...),
    phone: str = Form(""),
    email: str = Form(""),
    user_id: int | None = Form(None),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if consultation_fee < 0:
        raise HTTPException(
            status_code=400,
            detail="Consultation fee cannot be negative"
        )

    if experience_years < 0:
        raise HTTPException(
            status_code=400,
            detail="Experience cannot be negative"
        )

    doctor = Doctor(
        name=name.strip(),
        specialty=specialty.strip(),
        qualification=qualification.strip() or None,
        experience_years=experience_years,
        consultation_fee=consultation_fee,
        availability_status="active",
        phone=phone.strip() or None,
        email=email.strip() or None,
        user_id=user_id
    )

    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    return {
        "message": "Doctor added successfully",
        "doctor_id": doctor.id,
        "doctor_name": doctor.name
    }


@router.post("/create-form")
def create_doctor_form(
    request: Request,
    name: str = Form(...),
    specialty: str = Form(...),
    qualification: str = Form(""),
    experience_years: int = Form(0),
    consultation_fee: float = Form(...),
    phone: str = Form(""),
    email: str = Form(""),
    user_id: int | None = Form(None),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if consultation_fee < 0:
        raise HTTPException(
            status_code=400,
            detail="Consultation fee cannot be negative"
        )

    if experience_years < 0:
        raise HTTPException(
            status_code=400,
            detail="Experience cannot be negative"
        )

    doctor = Doctor(
        name=name.strip(),
        specialty=specialty.strip(),
        qualification=qualification.strip() or None,
        experience_years=experience_years,
        consultation_fee=consultation_fee,
        availability_status="active",
        phone=phone.strip() or None,
        email=email.strip() or None,
        user_id=user_id
    )

    db.add(doctor)
    db.commit()

    return RedirectResponse(
        url="/doctors/admin",
        status_code=303
    )


@router.post("/{doctor_id}/deactivate")
def deactivate_doctor(
    doctor_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id == doctor_id
        )
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    doctor.availability_status = "inactive"

    db.commit()

    return {
        "message": "Doctor deactivated successfully",
        "doctor_id": doctor.id
    }


@router.get("/list-page")
def doctor_list_page(
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    doctors = (
        db.query(Doctor)
        .filter(
            Doctor.availability_status == "active"
        )
        .order_by(Doctor.name.asc())
        .all()
    )

    specialties = sorted(
        set(
            doctor.specialty
            for doctor in doctors
            if doctor.specialty
        )
    )

    return templates.TemplateResponse(
        request,
        "doctor_list.html",
        {
            "doctors": doctors,
            "specialties": specialties
        }
    )


@router.post(
    "/smart-match",
    response_class=HTMLResponse
)
def smart_doctor_match(
    request: Request,
    question: str = Form(...),
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    question = question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Please enter your health question."
        )

    doctors = (
        db.query(Doctor)
        .filter(
            Doctor.availability_status == "active"
        )
        .all()
    )

    specialties = sorted(
        set(
            doctor.specialty
            for doctor in doctors
            if doctor.specialty
        )
    )

    suggestion = suggest_specialty(
        question,
        specialties
    )

    matched_doctors = match_doctors(
        suggestion["specialty"],
        doctors
    )

    doctor_rows = ""

    for doctor in matched_doctors:

        safe_name = escape(
            doctor.name
        )

        safe_specialty = escape(
            doctor.specialty
        )

        safe_qualification = escape(
            doctor.qualification
            or "Not provided"
        )

        doctor_rows += f"""
        <div class="doctor">

            <div class="doctor-header">

                <div>

                    <h3>
                        👨‍⚕️ Dr. {safe_name}
                    </h3>

                    <p class="specialty">
                        {safe_specialty}
                    </p>

                </div>

                <div class="doctor-badge">
                    AI Match
                </div>

            </div>

            <div class="details">

                <p>
                    <strong>
                        Qualification:
                    </strong>
                    {safe_qualification}
                </p>

                <p>
                    <strong>
                        Experience:
                    </strong>
                    {doctor.experience_years} years
                </p>

                <p>
                    <strong>
                        Consultation Fee:
                    </strong>
                    ₹{float(doctor.consultation_fee):.2f}
                </p>

            </div>

            <a
                class="book-button"
                href="/appointments/book/{doctor.id}"
            >
                📅 Book Appointment
            </a>

        </div>
        """

    if not doctor_rows:

        doctor_rows = """
        <div class="empty">

            <h3>
                No matching doctor found
            </h3>

            <p>
                You can try another health question
                or browse all available doctors.
            </p>

            <a
                class="browse-button"
                href="/doctors/list-page"
            >
                Browse All Doctors
            </a>

        </div>
        """

    safe_specialty = escape(
        suggestion["specialty"]
    )

    safe_reason = escape(
        suggestion["reason"]
    )

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>
            Smart Doctor Match - Sehat Saathi
        </title>

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <style>

            body {{
                margin: 0;
                padding: 25px;
                font-family: Arial, sans-serif;
                background: #f4f7f9;
            }}

            .container {{
                max-width: 950px;
                margin: auto;
                background: white;
                padding: 30px;
                border-radius: 14px;
                box-shadow:
                    0 4px 15px rgba(0,0,0,0.08);
            }}

            h1 {{
                color: #1976d2;
            }}

            .suggestion {{
                background: #eef6ff;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }}

            .suggestion h2 {{
                margin-top: 0;
                color: #155e75;
            }}

            .doctor {{
                border: 1px solid #d1d5db;
                border-radius: 12px;
                padding: 22px;
                margin-top: 18px;
                background: #ffffff;
                transition: 0.2s;
            }}

            .doctor:hover {{
                box-shadow:
                    0 5px 18px rgba(0,0,0,0.08);
            }}

            .doctor-header {{
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 15px;
            }}

            .doctor h3 {{
                margin-top: 0;
                margin-bottom: 5px;
                color: #1976d2;
                font-size: 21px;
            }}

            .specialty {{
                margin-top: 5px;
                color: #475569;
                font-weight: bold;
            }}

            .doctor-badge {{
                background: #dcfce7;
                color: #166534;
                padding: 7px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                white-space: nowrap;
            }}

            .details {{
                margin-top: 15px;
                line-height: 1.5;
            }}

            .book-button {{
                display: inline-block;
                margin-top: 15px;
                background: #0f766e;
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: bold;
            }}

            .book-button:hover {{
                background: #115e59;
            }}

            .browse-button {{
                display: inline-block;
                margin-top: 10px;
                background: #1976d2;
                color: white;
                padding: 11px 17px;
                border-radius: 7px;
                text-decoration: none;
                font-weight: bold;
            }}

            .empty {{
                padding: 25px;
                background: #fff8e1;
                border-radius: 10px;
            }}

            .back {{
                display: inline-block;
                margin-top: 25px;
                color: #1976d2;
                text-decoration: none;
                font-weight: bold;
            }}

            .warning {{
                margin-top: 25px;
                padding: 18px;
                background: #fff8e1;
                border-radius: 10px;
                line-height: 1.6;
            }}

            @media (max-width: 600px) {{

                body {{
                    padding: 12px;
                }}

                .container {{
                    padding: 20px;
                }}

                .doctor-header {{
                    flex-direction: column;
                }}

            }}

        </style>

    </head>

    <body>

        <div class="container">

            <h1>
                🤖 Smart Doctor Matching
            </h1>

            <div class="suggestion">

                <h2>
                    Suggested Specialty:
                    {safe_specialty}
                </h2>

                <p>
                    {safe_reason}
                </p>

            </div>

            <h2>
                👨‍⚕️ Available Matching Doctors
            </h2>

            {doctor_rows}

            <div class="warning">

                ⚠️ <strong>Important:</strong>

                This is an AI-based specialty
                suggestion, not a medical diagnosis.

                For serious or emergency symptoms,
                seek appropriate medical care.

            </div>

            <a
                class="back"
                href="/doctors/list-page"
            >
                ← Browse All Doctors
            </a>

        </div>

    </body>

    </html>
    """