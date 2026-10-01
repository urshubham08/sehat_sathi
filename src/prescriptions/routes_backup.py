from html import escape
from pathlib import Path
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.ai_chat.services import analyze_prescription_image
from src.database.database import get_db
from src.database.models import PrescriptionPhoto, User
from src.clinic_intelligence import can_access_patient
from src.prescriptions.services import save_image, validate_image


router = APIRouter(
    prefix="/prescriptions",
    tags=["Prescriptions"]
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
            detail="Not authorized to access prescriptions."
        )

    return user_id


def authorize_photo(user, photo, db):
    if not can_access_patient(user, photo.patient_id, db):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this prescription."
        )


def analyze_photo(photo):
    """
    Analyze one prescription image using Gemini.
    Returns a safe text response.
    """

    file_path = Path(photo.file_path)

    if not file_path.exists():
        return "Prescription file is missing."

    try:
        with open(file_path, "rb") as file:
            image_bytes = file.read()

        extension = file_path.suffix.lower()

        if extension in {".jpg", ".jpeg"}:
            mime_type = "image/jpeg"
        elif extension == ".png":
            mime_type = "image/png"
        else:
            return "Unsupported image format."

        explanation = analyze_prescription_image(
            image_bytes,
            mime_type
        )

        if not explanation:
            return "AI could not generate an explanation."

        return explanation

    except Exception as error:
        print("PRESCRIPTION AI ERROR:", error)

        return (
            "AI analysis is temporarily unavailable. "
            "Please try again later."
        )


@router.get("/page", response_class=HTMLResponse)
def prescriptions_page(
    request: Request,
    db: Session = Depends(get_db)
):
    patient_id = get_logged_in_patient(request)

    user = (
        db.query(User)
        .filter(User.id == patient_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    photos = (
        db.query(PrescriptionPhoto)
        .filter(
            PrescriptionPhoto.patient_id == patient_id
        )
        .order_by(
            PrescriptionPhoto.uploaded_at.desc()
        )
        .all()
    )

    analyze_id = request.query_params.get("analyze_id")

    selected_photo = None
    explanation = None

    if analyze_id:
        try:
            selected_photo_id = int(analyze_id)

            selected_photo = (
                db.query(PrescriptionPhoto)
                .filter(
                    PrescriptionPhoto.id == selected_photo_id,
                    PrescriptionPhoto.patient_id == patient_id
                )
                .first()
            )

            if selected_photo:
                explanation = analyze_photo(selected_photo)

        except ValueError:
            selected_photo = None

    photo_rows = ""

    for photo in photos:

        safe_filename = escape(
            photo.original_filename
        )

        analyze_url = (
            f"/prescriptions/page?analyze_id={photo.id}"
        )

        photo_rows += f"""
        <tr>

            <td>
                {safe_filename}
            </td>

            <td>
                {photo.file_size / (1024 * 1024):.2f} MB
            </td>

            <td>
                {escape(str(photo.uploaded_at))}
            </td>

            <td>

                <a
                    href="/prescriptions/{photo.id}/view"
                    target="_blank"
                >
                    View
                </a>

                <a href="{analyze_url}">
                    🤖 Explain with AI
                </a>

            </td>

        </tr>
        """

    if not photo_rows:

        photo_rows = """
        <tr>

            <td colspan="4">
                No prescription photos uploaded yet.
            </td>

        </tr>
        """

    ai_section = ""

    if selected_photo and explanation:

        safe_filename = escape(
            selected_photo.original_filename
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
                🤖 AI Prescription Explanation
            </h2>

            <p>
                <strong>Prescription:</strong>
                {safe_filename}
            </p>

            <div class="explanation">
                {safe_explanation}
            </div>

            <div class="warning">

                <strong>⚠️ Important:</strong>

                <br><br>

                AI sirf clearly visible information
                explain karta hai.

                <br><br>

                AI diagnosis nahi karta.

                <br>

                Medicine start, stop, change ya dosage
                decide karne ke liye doctor/pharmacist
                se confirm karein.

            </div>

        </div>
        """

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>
            Prescription Photos - Sehat Saathi
        </title>

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <style>

            body {{
                font-family: Arial, sans-serif;
                background: #f4f7f9;
                margin: 0;
                padding: 30px;
            }}

            .container {{
                max-width: 1000px;
                margin: auto;
                background: white;
                padding: 30px;
                border-radius: 12px;
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
                margin-bottom: 30px;
            }}

            input[type="file"] {{
                margin: 15px 0;
            }}

            button {{
                background: #1976d2;
                color: white;
                border: none;
                padding: 12px 22px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 15px;
            }}

            button:disabled {{
                background: #999;
                cursor: wait;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
            }}

            th,
            td {{
                padding: 12px;
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
                margin-top: 20px;
                padding: 20px;
                background: white;
                border-left: 5px solid #1976d2;
                line-height: 1.7;
                border-radius: 6px;
            }}

            .warning {{
                margin-top: 20px;
                padding: 15px;
                background: #fff8e1;
                border-radius: 8px;
                line-height: 1.5;
            }}

            .loading {{
                display: none;
                margin-top: 15px;
                padding: 12px;
                background: #eef6ff;
                border-radius: 8px;
                color: #1976d2;
            }}

            .pdf-note {{
                margin-top: 20px;
                padding: 15px;
                background: #f5f5f5;
                border-radius: 8px;
            }}

        </style>

    </head>

    <body>

        <div class="container">

            <h1>
                📷 My Prescription Photos
            </h1>

            <div class="upload-box">

                <h3>
                    Upload Prescription Photos
                </h3>

                <p>
                    You can upload up to
                    <strong>3 photos</strong>.
                </p>

                <p>
                    Allowed formats:
                    JPG, JPEG, PNG.
                </p>

                <p>
                    Maximum size:
                    <strong>5 MB per image</strong>.
                </p>

                <form
                    action="/prescriptions/upload"
                    method="post"
                    enctype="multipart/form-data"
                    id="prescriptionForm"
                >

                    <input
                        type="file"
                        name="files"
                        accept=".jpg,.jpeg,.png,image/jpeg,image/png"
                        multiple
                        required
                    >

                    <br>

                    <button
                        type="submit"
                        id="uploadButton"
                    >
                        Upload Prescriptions
                    </button>

                </form>

                <div
                    class="loading"
                    id="loadingMessage"
                >
                    ⏳ Uploading prescription...
                    Please wait.
                </div>

            </div>

            <div class="pdf-note">

                📄 <strong>Medical Report PDF:</strong>

                <br><br>

                PDF medical report upload aur
                AI report explanation bhi clinic
                ke medical-report section mein
                available rahega.

            </div>

            <h2>
                Uploaded Prescriptions
            </h2>

            <table>

                <thead>

                    <tr>

                        <th>
                            File Name
                        </th>

                        <th>
                            Size
                        </th>

                        <th>
                            Uploaded At
                        </th>

                        <th>
                            Action
                        </th>

                    </tr>

                </thead>

                <tbody>

                    {photo_rows}

                </tbody>

            </table>

            {ai_section}

        </div>

        <script>

            const form =
                document.getElementById("prescriptionForm");

            const button =
                document.getElementById("uploadButton");

            const loading =
                document.getElementById("loadingMessage");

            form.addEventListener("submit", function() {{

                button.disabled = true;

                button.innerText =
                    "Uploading...";

                loading.style.display =
                    "block";

            }});

        </script>

    </body>

    </html>
    """


@router.post("/upload")
async def upload_prescriptions(
    request: Request,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    patient_id = get_logged_in_patient(request)

    if not files:
        raise HTTPException(
            status_code=400,
            detail="Please select at least one image."
        )

    if len(files) > 3:
        raise HTTPException(
            status_code=400,
            detail="Maximum 3 prescription photos are allowed."
        )

    existing_count = (
        db.query(PrescriptionPhoto)
        .filter(
            PrescriptionPhoto.patient_id == patient_id
        )
        .count()
    )

    if existing_count + len(files) > 3:
        raise HTTPException(
            status_code=400,
            detail=(
                "A maximum of 3 prescription photos "
                "are allowed per patient."
            )
        )

    uploaded_photos = []

    for file in files:

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename."
            )

        content = await file.read()

        is_valid, error_message = validate_image(
            content,
            file.filename
        )

        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=error_message
            )

        stored_filename, file_path = save_image(
            content,
            file.filename
        )

        photo = PrescriptionPhoto(
            patient_id=patient_id,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_size=len(content)
        )

        db.add(photo)
        uploaded_photos.append(photo)

    db.commit()

    for photo in uploaded_photos:
        db.refresh(photo)

    # IMPORTANT:
    # JSON response hata diya.
    # Ab browser same prescription page par jayega
    # aur latest uploaded photo ka AI explanation
    # wahi page par show hoga.

    if uploaded_photos:

        latest_photo_id = uploaded_photos[-1].id

        return RedirectResponse(
            url=f"/prescriptions/page?analyze_id={latest_photo_id}",
            status_code=303
        )

    return RedirectResponse(
        url="/prescriptions/page",
        status_code=303
    )


@router.get("/{photo_id}/view")
def view_prescription(
    photo_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    uid = get_logged_in_patient(request)

    user = (
        db.query(User)
        .filter(User.id == uid)
        .first()
    )

    photo = (
        db.query(PrescriptionPhoto)
        .filter(
            PrescriptionPhoto.id == photo_id
        )
        .first()
    )

    if not photo:
        raise HTTPException(
            status_code=404,
            detail="Prescription photo not found."
        )

    authorize_photo(
        user,
        photo,
        db
    )

    file_path = Path(photo.file_path)

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Prescription file is missing."
        )

    return FileResponse(
        path=file_path,
        filename=photo.original_filename
    )


@router.get(
    "/{photo_id}/analyze",
    response_class=HTMLResponse
)
def analyze_prescription(
    photo_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    uid = get_logged_in_patient(request)

    user = (
        db.query(User)
        .filter(User.id == uid)
        .first()
    )

    photo = (
        db.query(PrescriptionPhoto)
        .filter(
            PrescriptionPhoto.id == photo_id
        )
        .first()
    )

    if not photo:
        raise HTTPException(
            status_code=404,
            detail="Prescription photo not found."
        )

    authorize_photo(
        user,
        photo,
        db
    )

    return RedirectResponse(
        url=f"/prescriptions/page?analyze_id={photo_id}",
        status_code=303
    )