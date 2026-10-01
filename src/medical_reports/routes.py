from html import escape
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pypdf import PdfReader
from sqlalchemy.orm import Session

from src.ai_chat.services import explain_medical_report
from src.database.database import get_db
from src.database.models import MedicalReport, Appointment, User
from src.clinic_intelligence import can_access_patient, doctor_for_user
from src.medical_reports.services import save_pdf, validate_pdf


router = APIRouter(
    prefix="/medical-reports",
    tags=["Medical Reports"]
)


def get_logged_in_patient(request: Request):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please login first."
        )

    if role not in {"patient", "doctor", "admin"}:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access medical reports."
        )

    return user_id


def authorize_report(user, report, db):
    if not can_access_patient(
        user,
        report.patient_id,
        db
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this medical report."
        )


def extract_pdf_text(file_path: str) -> str:
    reader = PdfReader(file_path)

    pages = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages.append(text)

    return "\n\n".join(pages).strip()


def get_reports_for_user(user, db):
    if user.role == "patient":

        return (
            db.query(MedicalReport)
            .filter(
                MedicalReport.patient_id == user.id
            )
            .order_by(
                MedicalReport.uploaded_at.desc()
            )
            .all()
        )

    if user.role == "doctor":

        doctor = doctor_for_user(
            user,
            db
        )

        if not doctor:
            return []

        patient_ids = [
            appointment.patient_id
            for appointment in (
                db.query(Appointment)
                .filter(
                    Appointment.doctor_id == doctor.id
                )
                .all()
            )
        ]

        if not patient_ids:
            return []

        return (
            db.query(MedicalReport)
            .filter(
                MedicalReport.patient_id.in_(patient_ids)
            )
            .order_by(
                MedicalReport.uploaded_at.desc()
            )
            .all()
        )

    return (
        db.query(MedicalReport)
        .order_by(
            MedicalReport.uploaded_at.desc()
        )
        .all()
    )


def build_ai_explanation(report):
    file_path = Path(report.file_path)

    if not file_path.exists():
        return "Medical report file is missing."

    try:
        report_text = extract_pdf_text(
            str(file_path)
        )

        if not report_text:

            return (
                "This PDF does not contain readable text. "
                "It may be a scanned or image-only PDF."
            )

        report_text = report_text[:30000]

        explanation = explain_medical_report(
            report_text
        )

        if not explanation:
            return (
                "AI could not generate an explanation "
                "for this report."
            )

        return explanation

    except Exception as error:

        print(
            "REPORT AI ERROR:",
            error
        )

        return (
            "Sorry, this report could not be explained "
            "by the AI assistant right now."
        )


@router.get(
    "/page",
    response_class=HTMLResponse
)
def medical_reports_page(
    request: Request,
    db: Session = Depends(get_db)
):
    uid = get_logged_in_patient(request)

    user = (
        db.query(User)
        .filter(User.id == uid)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    reports = get_reports_for_user(
        user,
        db
    )

    explain_id = request.query_params.get(
        "explain_id"
    )

    selected_report = None
    explanation = None

    if explain_id:

        try:
            selected_report_id = int(
                explain_id
            )

            selected_report = (
                db.query(MedicalReport)
                .filter(
                    MedicalReport.id == selected_report_id
                )
                .first()
            )

            if selected_report:

                authorize_report(
                    user,
                    selected_report,
                    db
                )

                explanation = build_ai_explanation(
                    selected_report
                )

        except ValueError:
            selected_report = None

    rows = ""

    for report in reports:

        filename = escape(
            report.original_filename
        )

        rows += f"""
        <tr>

            <td>
                {filename}
            </td>

            <td>
                {report.file_size / (1024 * 1024):.2f} MB
            </td>

            <td>
                {escape(str(report.uploaded_at))}
            </td>

            <td>

                <a
                    href="/medical-reports/{report.id}/view"
                    target="_blank"
                >
                    View PDF
                </a>

                <a
                    href="/medical-reports/page?explain_id={report.id}"
                    class="ai-button"
                >
                    🤖 Explain with AI
                </a>

            </td>

        </tr>
        """

    if not rows:

        rows = """
        <tr>

            <td colspan="4">
                No medical reports uploaded yet.
            </td>

        </tr>
        """

    ai_section = ""

    if selected_report and explanation:

        safe_filename = escape(
            selected_report.original_filename
        )

        safe_explanation = escape(
            explanation
        ).replace(
            "\n",
            "<br>"
        )

        ai_section = f"""
        <div class="ai-box">

            <h2>
                🤖 AI Medical Report Explanation
            </h2>

            <p>
                <strong>Report:</strong>
                {safe_filename}
            </p>

            <div class="explanation">

                {safe_explanation}

            </div>

            <div class="warning">

                <strong>⚠️ Important:</strong>

                <br><br>

                This AI explanation is for general
                information only.

                <br><br>

                AI does not diagnose diseases and does
                not prescribe, start, stop or change
                medicines.

                <br><br>

                Please consult a qualified healthcare
                professional for clinical interpretation.

            </div>

        </div>
        """

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>
            Medical Reports - Sehat Saathi
        </title>

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <style>

            * {{
                box-sizing: border-box;
            }}

            body {{
                font-family: Arial, sans-serif;
                background: #f4f7f9;
                margin: 0;
                padding: 30px;
            }}

            .container {{
                max-width: 1100px;
                margin: auto;
                background: white;
                padding: 30px;
                border-radius: 14px;
                box-shadow:
                    0 4px 15px rgba(0,0,0,0.08);
            }}

            h1 {{
                margin-top: 0;
                color: #1976d2;
            }}

            .upload-box {{
                border: 2px dashed #bbb;
                padding: 25px;
                border-radius: 10px;
                margin-bottom: 25px;
            }}

            .upload-box h2 {{
                margin-top: 0;
            }}

            input[type="file"] {{
                margin: 15px 0;
            }}

            button {{
                background: #1976d2;
                color: white;
                border: none;
                padding: 12px 22px;
                border-radius: 7px;
                cursor: pointer;
                font-size: 15px;
            }}

            button:disabled {{
                background: #999;
                cursor: wait;
            }}

            .loading {{
                display: none;
                margin-top: 15px;
                padding: 12px;
                background: #eef6ff;
                color: #1976d2;
                border-radius: 8px;
            }}

            .info {{
                background: #eef6ff;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                line-height: 1.6;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 25px;
            }}

            th,
            td {{
                padding: 14px;
                border-bottom: 1px solid #ddd;
                text-align: left;
            }}

            th {{
                background: #f1f3f5;
            }}

            a {{
                color: #1976d2;
                text-decoration: none;
                margin-right: 12px;
            }}

            .ai-button {{
                display: inline-block;
                background: #1976d2;
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                margin-top: 5px;
            }}

            .ai-box {{
                margin-top: 35px;
                padding: 25px;
                background: #f8fafc;
                border-radius: 12px;
                border: 1px solid #dbe5ef;
            }}

            .ai-box h2 {{
                color: #1976d2;
                margin-top: 0;
            }}

            .explanation {{
                background: white;
                border-left: 5px solid #1976d2;
                padding: 20px;
                line-height: 1.7;
                font-size: 15px;
                border-radius: 6px;
            }}

            .warning {{
                margin-top: 20px;
                padding: 15px;
                background: #fff8e1;
                border-radius: 8px;
                line-height: 1.6;
            }}

            @media (max-width: 700px) {{

                body {{
                    padding: 10px;
                }}

                .container {{
                    padding: 18px;
                }}

                table {{
                    font-size: 13px;
                }}

                th,
                td {{
                    padding: 9px;
                }}

            }}

        </style>

    </head>

    <body>

        <div class="container">

            <h1>
                📄 My Medical Reports
            </h1>

            <div class="upload-box">

                <h2>
                    Upload Medical Report
                </h2>

                <p>
                    Upload your medical report in
                    <strong>PDF format</strong>.
                </p>

                <p>
                    Maximum file size:
                    <strong>10 MB</strong>.
                </p>

                <form
                    action="/medical-reports/upload"
                    method="post"
                    enctype="multipart/form-data"
                    id="reportForm"
                >

                    <input
                        type="file"
                        name="file"
                        accept=".pdf,application/pdf"
                        required
                    >

                    <br>

                    <button
                        type="submit"
                        id="uploadButton"
                    >
                        Upload PDF
                    </button>

                </form>

                <div
                    class="loading"
                    id="loadingMessage"
                >
                    ⏳ Uploading medical report...
                    Please wait.
                </div>

            </div>

            <div class="info">

                🤖 <strong>AI Report Explanation</strong>

                <p>
                    Sehat Saathi uploaded PDF ke readable
                    text ko simple language mein explain
                    kar sakta hai.
                </p>

                <p>
                    AI diagnosis nahi karta aur medicines
                    prescribe ya change nahi karta.
                </p>

            </div>

            <h2>
                Uploaded Medical Reports
            </h2>

            <table>

                <thead>

                    <tr>
                        <th>File Name</th>
                        <th>Size</th>
                        <th>Uploaded At</th>
                        <th>Action</th>
                    </tr>

                </thead>

                <tbody>

                    {rows}

                </tbody>

            </table>

            {ai_section}

        </div>

        <script>

            const form =
                document.getElementById("reportForm");

            const button =
                document.getElementById("uploadButton");

            const loading =
                document.getElementById("loadingMessage");

            form.addEventListener(
                "submit",
                function() {{

                    button.disabled = true;

                    button.innerText =
                        "Uploading...";

                    loading.style.display =
                        "block";

                }}
            );

        </script>

    </body>

    </html>
    """


@router.post("/upload")
async def upload_medical_report(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    uid = get_logged_in_patient(request)

    user = (
        db.query(User)
        .filter(User.id == uid)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    # A patient uploads their own medical report.
    # Doctor/admin access remains controlled 
    # through the existing authorization system.
    if user.role != "patient":
        raise HTTPException(
            status_code=403,
            detail="Only patients can upload their own medical reports."
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Please select a PDF file."
        )

    original_filename = Path(
        file.filename
    ).name

    if not original_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    content = await file.read()

    is_valid, error_message = validate_pdf(
        content
    )

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_message
        )

    stored_filename, file_path = save_pdf(
        content
    )

    report = MedicalReport(
        patient_id=uid,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_size=len(content)
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    # Upload ke baad same page par report
    # aur AI explanation open hogi.
    return RedirectResponse(
        url=f"/medical-reports/page?explain_id={report.id}",
        status_code=303
    )


@router.get("/{report_id}/view")
def view_report(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    uid = get_logged_in_patient(request)

    user = (
        db.query(User)
        .filter(User.id == uid)
        .first()
    )

    report = (
        db.query(MedicalReport)
        .filter(
            MedicalReport.id == report_id
        )
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Medical report not found."
        )

    authorize_report(
        user,
        report,
        db
    )

    file_path = Path(
        report.file_path
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Medical report file is missing."
        )

    return FileResponse(
        path=file_path,
        filename=report.original_filename,
        media_type="application/pdf"
    )


@router.get(
    "/{report_id}/explain",
    response_class=HTMLResponse
)
def explain_report(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    uid = get_logged_in_patient(request)

    user = (
        db.query(User)
        .filter(User.id == uid)
        .first()
    )

    report = (
        db.query(MedicalReport)
        .filter(
            MedicalReport.id == report_id
        )
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Medical report not found."
        )

    authorize_report(
        user,
        report,
        db
    )

    return RedirectResponse(
        url=f"/medical-reports/page?explain_id={report_id}",
        status_code=303
    )