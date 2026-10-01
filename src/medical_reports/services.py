from pathlib import Path
from uuid import uuid4


UPLOAD_DIR = Path("uploads") / "medical_reports"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def ensure_upload_directory():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def validate_pdf(content: bytes):
    if not content:
        return False, "File is empty."

    if not content.startswith(b"%PDF-"):
        return False, "Invalid PDF file."

    if len(content) > MAX_FILE_SIZE:
        return False, "PDF size must not exceed 10 MB."

    return True, None


def generate_stored_filename():
    return f"{uuid4().hex}.pdf"


def save_pdf(content: bytes):
    ensure_upload_directory()

    stored_filename = generate_stored_filename()
    file_path = UPLOAD_DIR / stored_filename

    with open(file_path, "wb") as file:
        file.write(content)

    return stored_filename, str(file_path)