from pathlib import Path
from uuid import uuid4
from io import BytesIO

from PIL import Image


UPLOAD_DIR = Path("uploads") / "prescriptions"

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png"
}


def ensure_upload_directory():
    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


def validate_image(
    content: bytes,
    filename: str
):
    if not content:
        return False, "Image file is empty."

    if len(content) > MAX_FILE_SIZE:
        return False, "Image size must not exceed 5 MB."

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return False, (
            "Only JPG, JPEG and PNG images are allowed."
        )

    try:
        image = Image.open(
            BytesIO(content)
        )

        image.verify()

    except Exception:
        return False, "Invalid or corrupted image."

    return True, None


def generate_stored_filename(
    original_filename: str
):
    extension = (
        Path(original_filename)
        .suffix
        .lower()
    )

    return f"{uuid4().hex}{extension}"


def save_image(
    content: bytes,
    original_filename: str
):
    ensure_upload_directory()

    stored_filename = generate_stored_filename(
        original_filename
    )

    file_path = (
        UPLOAD_DIR /
        stored_filename
    )

    with open(
        file_path,
        "wb"
    ) as file:

        file.write(content)

    return (
        stored_filename,
        str(file_path)
    )