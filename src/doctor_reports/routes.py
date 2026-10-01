import json
from datetime import datetime
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors

from src.database.database import get_db
from src.database.models import (
    User,
    Doctor,
    Appointment,
    DoctorDocument,
    ClinicSetting,
    PatientProfile,
)


router = APIRouter(
    prefix="/doctor-reports",
    tags=["Hospital Medical Reports"],
)


def get_logged_in_user(request: Request, db: Session):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please login first.",
        )

    user = db.query(User).filter(
        User.id == user_id,
        User.is_active == True,
    ).first()

    if not user:
        request.session.clear()
        raise HTTPException(
            status_code=401,
            detail="User not found.",
        )

    return user


def get_doctor_for_user(user: User, db: Session):
    if user.role != "doctor":
        raise HTTPException(
            status_code=403,
            detail="Only doctors can create hospital medical reports.",
        )

    doctor = db.query(Doctor).filter(
        Doctor.user_id == user.id,
        Doctor.availability_status == "active",
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=403,
            detail="Doctor profile not found or inactive.",
        )

    return doctor


def doctor_can_access_patient(
    db: Session,
    doctor_id: int,
    patient_id: int,
):
    appointment = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.patient_id == patient_id,
    ).first()

    return appointment is not None


def get_clinic_settings(db: Session):
    clinic = db.query(ClinicSetting).first()

    if not clinic:
        clinic = ClinicSetting(
            id=1,
            clinic_name="Sanjeevani Smart Clinic",
        )
        db.add(clinic)
        db.commit()
        db.refresh(clinic)

    return clinic


def parse_report_content(document: DoctorDocument):
    try:
        data = json.loads(document.content)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return {
        "clinical_notes": document.content,
    }


@router.get(
    "/",
    response_class=HTMLResponse,
)
def doctor_report_dashboard(
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_logged_in_user(request, db)
    doctor = get_doctor_for_user(user, db)

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor.id,
        )
        .order_by(
            Appointment.appointment_date.desc(),
            Appointment.id.desc(),
        )
        .all()
    )

    patients = []

    seen_patient_ids = set()

    for appointment in appointments:
        if appointment.patient_id in seen_patient_ids:
            continue

        patient = db.query(User).filter(
            User.id == appointment.patient_id,
            User.is_active == True,
        ).first()

        if not patient:
            continue

        seen_patient_ids.add(patient.id)

        patients.append(
            {
                "id": patient.id,
                "name": patient.name,
                "email": patient.email,
                "mobile": patient.mobile,
            }
        )

    rows = ""

    for patient in patients:
        rows += f"""
        <tr>
            <td>{patient["id"]}</td>
            <td>{patient["name"]}</td>
            <td>{patient["email"]}</td>
            <td>{patient["mobile"]}</td>
            <td>
                <a href="/doctor-reports/create/{patient["id"]}"
                   style="
                       display:inline-block;
                       padding:8px 12px;
                       background:#0f766e;
                       color:white;
                       text-decoration:none;
                       border-radius:7px;
                   ">
                    Create Medical Report
                </a>
            </td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="5">
                No appointed patients found.
            </td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hospital Medical Reports</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background:#f5f7fb;
                padding:30px;
            }}

            .container {{
                max-width:1100px;
                margin:auto;
                background:white;
                padding:25px;
                border-radius:14px;
                box-shadow:0 5px 20px rgba(0,0,0,.08);
            }}

            table {{
                width:100%;
                border-collapse:collapse;
                margin-top:20px;
            }}

            th, td {{
                padding:12px;
                border-bottom:1px solid #ddd;
                text-align:left;
            }}

            th {{
                background:#f1f5f9;
            }}

            .back {{
                display:inline-block;
                margin-bottom:15px;
                text-decoration:none;
            }}
        </style>
    </head>

    <body>
        <div class="container">

            <a class="back" href="/dashboard">
                ← Dashboard
            </a>

            <h1>Hospital Medical Reports</h1>

            <p>
                Doctor: <strong>{doctor.name}</strong>
            </p>

            <p>
                Create reports only for patients who have an appointment
                with you.
            </p>

            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Patient</th>
                        <th>Email</th>
                        <th>Mobile</th>
                        <th>Action</th>
                    </tr>
                </thead>

                <tbody>
                    {rows}
                </tbody>
            </table>

        </div>
    </body>
    </html>
    """


@router.get(
    "/create/{patient_id}",
    response_class=HTMLResponse,
)
def create_report_page(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_logged_in_user(request, db)
    doctor = get_doctor_for_user(user, db)

    if not doctor_can_access_patient(
        db,
        doctor.id,
        patient_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="You can create reports only for your appointed patients.",
        )

    patient = db.query(User).filter(
        User.id == patient_id,
        User.is_active == True,
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found.",
        )

    profile = db.query(PatientProfile).filter(
        PatientProfile.user_id == patient.id,
    ).first()

    blood_group = profile.blood_group if profile else ""
    allergies = profile.allergies if profile else ""

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Create Medical Report</title>

        <style>
            body {{
                font-family:Arial,sans-serif;
                background:#f5f7fb;
                padding:25px;
            }}

            .container {{
                max-width:900px;
                margin:auto;
                background:white;
                padding:30px;
                border-radius:15px;
                box-shadow:0 5px 20px rgba(0,0,0,.08);
            }}

            label {{
                display:block;
                margin-top:15px;
                font-weight:bold;
            }}

            input, textarea {{
                width:100%;
                box-sizing:border-box;
                padding:11px;
                margin-top:6px;
                border:1px solid #ccc;
                border-radius:7px;
                font-size:15px;
            }}

            textarea {{
                min-height:120px;
                resize:vertical;
            }}

            button {{
                margin-top:22px;
                padding:12px 20px;
                background:#0f766e;
                color:white;
                border:none;
                border-radius:8px;
                cursor:pointer;
                font-size:16px;
            }}

            .patient {{
                background:#f1f5f9;
                padding:15px;
                border-radius:10px;
                margin:20px 0;
            }}

            .warning {{
                background:#fff7ed;
                border-left:4px solid #f97316;
                padding:12px;
                margin-top:15px;
            }}
        </style>
    </head>

    <body>

    <div class="container">

        <a href="/doctor-reports/">← Back</a>

        <h1>Create Hospital Medical Report</h1>

        <div class="patient">
            <strong>Patient:</strong> {patient.name}<br>
            <strong>Email:</strong> {patient.email}<br>
            <strong>Mobile:</strong> {patient.mobile}<br>
            <strong>Blood Group:</strong> {blood_group or "Not provided"}<br>
            <strong>Allergies:</strong> {allergies or "Not provided"}
        </div>

        <div class="warning">
            This report is entered by the doctor.
            AI-generated text must be reviewed by the doctor before
            being used as an official clinical document.
        </div>

        <form method="post"
              action="/doctor-reports/create/{patient_id}">

            <label>Report Title</label>
            <input
                type="text"
                name="title"
                value="Medical Consultation Report"
                required
            >

            <label>Visit / Report Date</label>
            <input
                type="date"
                name="report_date"
                value="{datetime.now().strftime("%Y-%m-%d")}"
                required
            >

            <label>Chief Complaint / Symptoms</label>
            <textarea
                name="symptoms"
                placeholder="Patient's reported symptoms..."
            ></textarea>

            <label>Clinical Findings / Examination</label>
            <textarea
                name="findings"
                placeholder="Doctor's examination findings..."
            ></textarea>

            <label>Diagnosis / Clinical Impression</label>
            <textarea
                name="diagnosis"
                placeholder="Doctor's clinical assessment..."
            ></textarea>

            <label>Tests / Investigation Findings</label>
            <textarea
                name="tests"
                placeholder="Tests and findings..."
            ></textarea>

            <label>Treatment / Prescription Reference</label>
            <textarea
                name="treatment"
                placeholder="Treatment or prescription reference..."
            ></textarea>

            <label>Doctor's Advice</label>
            <textarea
                name="advice"
                placeholder="Advice given to patient..."
            ></textarea>

            <label>Follow-up Date</label>
            <input
                type="date"
                name="follow_up_date"
            >

            <label>Additional Notes</label>
            <textarea
                name="additional_notes"
                placeholder="Additional doctor notes..."
            ></textarea>

            <button type="submit">
                Generate Hospital Medical Report
            </button>

        </form>

    </div>

    </body>
    </html>
    """


@router.post(
    "/create/{patient_id}",
)
def create_medical_report(
    patient_id: int,
    request: Request,
    title: str = Form(...),
    report_date: str = Form(...),
    symptoms: str = Form(""),
    findings: str = Form(""),
    diagnosis: str = Form(""),
    tests: str = Form(""),
    treatment: str = Form(""),
    advice: str = Form(""),
    follow_up_date: str = Form(""),
    additional_notes: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_logged_in_user(request, db)
    doctor = get_doctor_for_user(user, db)

    if not doctor_can_access_patient(
        db,
        doctor.id,
        patient_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="You can create reports only for your appointed patients.",
        )

    patient = db.query(User).filter(
        User.id == patient_id,
        User.is_active == True,
    ).first()

    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found.",
        )

    content = {
        "report_date": report_date,
        "symptoms": symptoms.strip(),
        "findings": findings.strip(),
        "diagnosis": diagnosis.strip(),
        "tests": tests.strip(),
        "treatment": treatment.strip(),
        "advice": advice.strip(),
        "follow_up_date": follow_up_date.strip(),
        "additional_notes": additional_notes.strip(),
    }

    document = DoctorDocument(
        doctor_id=doctor.id,
        patient_id=patient.id,
        created_by=user.id,
        document_type="medical_report",
        title=title.strip() or "Medical Consultation Report",
        content=json.dumps(content),
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return Response(
        content=f"""
        <html>
        <head>
            <meta http-equiv="refresh"
                  content="0;url=/doctor-reports/view/{document.id}">
        </head>
        <body>
            Report created successfully.
        </body>
        </html>
        """,
        media_type="text/html",
    )


@router.get(
    "/view/{document_id}",
    response_class=HTMLResponse,
)
def view_medical_report(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_logged_in_user(request, db)

    document = db.query(DoctorDocument).filter(
        DoctorDocument.id == document_id,
        DoctorDocument.document_type == "medical_report",
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Medical report not found.",
        )

    allowed = False

    if user.role == "admin":
        allowed = True

    elif user.role == "patient":
        allowed = document.patient_id == user.id

    elif user.role == "doctor":
        doctor = db.query(Doctor).filter(
            Doctor.user_id == user.id,
        ).first()

        if doctor and document.doctor_id == doctor.id:
            allowed = True

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view this report.",
        )

    patient = db.query(User).filter(
        User.id == document.patient_id,
    ).first()

    doctor = db.query(Doctor).filter(
        Doctor.id == document.doctor_id,
    ).first()

    content = parse_report_content(document)

    def esc(value):
        value = value or ""
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )

    sections = [
        ("Symptoms", content.get("symptoms")),
        ("Clinical Findings", content.get("findings")),
        ("Diagnosis / Clinical Impression", content.get("diagnosis")),
        ("Tests / Investigation Findings", content.get("tests")),
        ("Treatment / Prescription Reference", content.get("treatment")),
        ("Doctor's Advice", content.get("advice")),
        ("Follow-up Date", content.get("follow_up_date")),
        ("Additional Notes", content.get("additional_notes")),
    ]

    section_html = ""

    for heading, value in sections:
        if value:
            section_html += f"""
            <div class="section">
                <h3>{heading}</h3>
                <p>{esc(value)}</p>
            </div>
            """

    return f"""
    <!DOCTYPE html>
    <html>

    <head>
        <title>{esc(document.title)}</title>

        <style>
            body {{
                font-family:Arial,sans-serif;
                background:#f5f7fb;
                padding:25px;
            }}

            .report {{
                max-width:900px;
                margin:auto;
                background:white;
                padding:35px;
                border-radius:14px;
            }}

            .header {{
                text-align:center;
                border-bottom:2px solid #0f766e;
                padding-bottom:15px;
            }}

            .patient {{
                background:#f8fafc;
                padding:15px;
                margin-top:20px;
                border-radius:8px;
            }}

            .section {{
                margin-top:22px;
            }}

            .section h3 {{
                color:#0f766e;
            }}

            .actions {{
                margin-bottom:20px;
            }}

            .button {{
                display:inline-block;
                padding:10px 15px;
                background:#0f766e;
                color:white;
                text-decoration:none;
                border-radius:7px;
                margin-right:8px;
            }}

            @media print {{
                body {{
                    background:white;
                    padding:0;
                }}

                .actions {{
                    display:none;
                }}

                .report {{
                    box-shadow:none;
                }}
            }}
        </style>
    </head>

    <body>

    <div class="report">

        <div class="actions">
            <a class="button"
               href="/doctor-reports/pdf/{document.id}">
                Download / Print PDF
            </a>

            <a class="button"
               href="/dashboard">
                Dashboard
            </a>
        </div>

        <div class="header">
            <h1>{esc(get_clinic_settings(db).clinic_name)}</h1>
            <h2>{esc(document.title)}</h2>
        </div>

        <div class="patient">
            <strong>Patient:</strong> {esc(patient.name if patient else "")}<br>
            <strong>Email:</strong> {esc(patient.email if patient else "")}<br>
            <strong>Mobile:</strong> {esc(patient.mobile if patient else "")}<br>
            <strong>Doctor:</strong> {esc(doctor.name if doctor else "")}<br>
            <strong>Specialty:</strong> {esc(doctor.specialty if doctor else "")}<br>
            <strong>Report Date:</strong> {esc(content.get("report_date"))}
        </div>

        {section_html}

        <br><br>

        <div>
            <strong>Doctor Signature:</strong>
            __________________________
        </div>

        <br>

        <div>
            <strong>Authorized Clinic Stamp:</strong>
            __________________________
        </div>

    </div>

    </body>
    </html>
    """


@router.get(
    "/pdf/{document_id}",
)
def medical_report_pdf(
    document_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_logged_in_user(request, db)

    document = db.query(DoctorDocument).filter(
        DoctorDocument.id == document_id,
        DoctorDocument.document_type == "medical_report",
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Medical report not found.",
        )

    allowed = False

    if user.role == "admin":
        allowed = True

    elif user.role == "patient":
        allowed = document.patient_id == user.id

    elif user.role == "doctor":
        doctor = db.query(Doctor).filter(
            Doctor.user_id == user.id,
        ).first()

        if doctor and document.doctor_id == doctor.id:
            allowed = True

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to download this report.",
        )

    patient = db.query(User).filter(
        User.id == document.patient_id,
    ).first()

    doctor = db.query(Doctor).filter(
        Doctor.id == document.doctor_id,
    ).first()

    clinic = get_clinic_settings(db)
    content = parse_report_content(document)

    buffer = BytesIO()

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        alignment=1,
        spaceAfter=8,
    )

    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading3"],
        fontSize=11,
        textColor=colors.HexColor("#0f766e"),
        spaceBefore=10,
        spaceAfter=5,
    )

    normal_style = ParagraphStyle(
        "ReportNormal",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=14,
    )

    story = []

    story.append(
        Paragraph(
            clinic.clinic_name or "Clinic",
            title_style,
        )
    )

    if clinic.owner_name:
        story.append(
            Paragraph(
                f"Clinic Owner: {clinic.owner_name}",
                normal_style,
            )
        )

    if clinic.license_number:
        story.append(
            Paragraph(
                f"Licence Number: {clinic.license_number}",
                normal_style,
            )
        )

    if clinic.address:
        story.append(
            Paragraph(
                clinic.address,
                normal_style,
            )
        )

    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            document.title,
            title_style,
        )
    )

    patient_data = [
        ["Patient Name", patient.name if patient else ""],
        ["Email", patient.email if patient else ""],
        ["Mobile", patient.mobile if patient else ""],
        ["Doctor", doctor.name if doctor else ""],
        ["Specialty", doctor.specialty if doctor else ""],
        ["Report Date", content.get("report_date", "")],
    ]

    table = Table(
        patient_data,
        colWidths=[45 * mm, 125 * mm],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#f1f5f9"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (0, -1),
                    "Helvetica-Bold",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.append(table)

    sections = [
        ("Symptoms", content.get("symptoms")),
        ("Clinical Findings", content.get("findings")),
        (
            "Diagnosis / Clinical Impression",
            content.get("diagnosis"),
        ),
        (
            "Tests / Investigation Findings",
            content.get("tests"),
        ),
        (
            "Treatment / Prescription Reference",
            content.get("treatment"),
        ),
        (
            "Doctor's Advice",
            content.get("advice"),
        ),
        (
            "Follow-up Date",
            content.get("follow_up_date"),
        ),
        (
            "Additional Notes",
            content.get("additional_notes"),
        ),
    ]

    for heading, value in sections:
        if not value:
            continue

        story.append(
            Paragraph(
                heading,
                heading_style,
            )
        )

        safe_value = (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )

        story.append(
            Paragraph(
                safe_value,
                normal_style,
            )
        )

    story.append(Spacer(1, 30))

    signature_table = Table(
        [
            [
                "Doctor Signature",
                "Authorized Clinic Stamp",
            ],
            [
                "____________________",
                "____________________",
            ],
        ],
        colWidths=[85 * mm, 85 * mm],
    )

    signature_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    story.append(signature_table)

    story.append(Spacer(1, 20))

    story.append(
        Paragraph(
            "This document is generated by Sanjeevani Smart Clinic.",
            normal_style,
        )
    )

    pdf.build(story)

    pdf_bytes = buffer.getvalue()

    filename = (
        f"medical_report_{document.id}.pdf"
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"'
        },
    )


@router.get(
    "/my",
    response_class=HTMLResponse,
)
def patient_medical_reports(
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_logged_in_user(request, db)

    if user.role != "patient":
        raise HTTPException(
            status_code=403,
            detail="Patient access only.",
        )

    documents = (
        db.query(DoctorDocument)
        .filter(
            DoctorDocument.patient_id == user.id,
            DoctorDocument.document_type == "medical_report",
        )
        .order_by(DoctorDocument.created_at.desc())
        .all()
    )

    rows = ""

    for document in documents:
        doctor = db.query(Doctor).filter(
            Doctor.id == document.doctor_id,
        ).first()

        rows += f"""
        <tr>
            <td>{document.title}</td>
            <td>{doctor.name if doctor else "Doctor"}</td>
            <td>{document.created_at.strftime("%d-%m-%Y") if document.created_at else ""}</td>
            <td>
                <a href="/doctor-reports/view/{document.id}">
                    View
                </a>
                |
                <a href="/doctor-reports/pdf/{document.id}">
                    PDF
                </a>
            </td>
        </tr>
        """

    if not rows:
        rows = """
        <tr>
            <td colspan="4">
                No hospital-generated medical reports available.
            </td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>My Medical Reports</title>

        <style>
            body {{
                font-family:Arial,sans-serif;
                background:#f5f7fb;
                padding:25px;
            }}

            .container {{
                max-width:1000px;
                margin:auto;
                background:white;
                padding:30px;
                border-radius:14px;
            }}

            table {{
                width:100%;
                border-collapse:collapse;
                margin-top:20px;
            }}

            th,td {{
                padding:12px;
                border-bottom:1px solid #ddd;
                text-align:left;
            }}

            th {{
                background:#f1f5f9;
            }}
        </style>
    </head>

    <body>

    <div class="container">

        <a href="/dashboard">← Dashboard</a>

        <h1>My Hospital Medical Reports</h1>

        <table>
            <thead>
                <tr>
                    <th>Report</th>
                    <th>Doctor</th>
                    <th>Date</th>
                    <th>Actions</th>
                </tr>
            </thead>

            <tbody>
                {rows}
            </tbody>
        </table>

    </div>

    </body>
    </html>
    """