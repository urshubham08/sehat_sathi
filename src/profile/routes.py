from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.database.models import User


router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
)


PROFILE_DIR = Path("uploads") / "profile_photos"

MAX_PROFILE_PHOTO_SIZE = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


def get_current_user(
    request: Request,
    db: Session,
):
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    return (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_active == True,
        )
        .first()
    )


def ensure_profile_directory():
    PROFILE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


@router.get("/photo/{user_id}")
def profile_photo(
    user_id: int,
    db: Session = Depends(get_db),
):
    """
    Return user's profile picture.

    If no picture exists, return a default avatar.
    """

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    ensure_profile_directory()

    for extension in ALLOWED_EXTENSIONS:

        possible_file = (
            PROFILE_DIR
            / f"user_{user_id}{extension}"
        )

        if possible_file.exists():

            return FileResponse(
                possible_file,
                media_type=(
                    "image/jpeg"
                    if extension in {".jpg", ".jpeg"}
                    else (
                        "image/png"
                        if extension == ".png"
                        else "image/webp"
                    )
                ),
            )

    return RedirectResponse(
        url="/profile/default-avatar",
        status_code=307,
    )


@router.get(
    "/default-avatar",
    response_class=HTMLResponse,
)
def default_avatar():

    return HTMLResponse(
        content="""
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="160"
            height="160"
            viewBox="0 0 160 160"
        >
            <rect
                width="160"
                height="160"
                rx="80"
                fill="#eaf6fa"
            />

            <circle
                cx="80"
                cy="62"
                r="30"
                fill="#0b7898"
            />

            <path
                d="
                    M35 138
                    C38 108,
                    55 94,
                    80 94
                    C105 94,
                    122 108,
                    125 138
                    Z
                "
                fill="#0b7898"
            />
        </svg>
        """,
        media_type="image/svg+xml",
    )


@router.get(
    "/change-photo",
    response_class=HTMLResponse,
)
def change_photo_page(
    request: Request,
    db: Session = Depends(get_db),
):

    user = get_current_user(
        request,
        db,
    )

    if not user:

        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    return f"""
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
Change Profile Photo
</title>

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;

    min-height: 100vh;

    display: flex;

    align-items: center;

    justify-content: center;

    background:
        linear-gradient(
            135deg,
            #eef8fb,
            #f8fbfd
        );

    font-family:
        Arial,
        sans-serif;

    color:
        #17324d;
}}

.card {{
    width:
        min(92%, 480px);

    background:
        white;

    padding:
        30px;

    border-radius:
        22px;

    box-shadow:
        0 15px 45px
        rgba(
            20,
            60,
            80,
            .12
        );

    text-align:
        center;
}}

.photo {{
    width:
        130px;

    height:
        130px;

    object-fit:
        cover;

    border-radius:
        50%;

    border:
        5px solid #e8f5f8;

    margin-bottom:
        15px;
}}

h1 {{
    margin:
        5px 0 8px;
}}

p {{
    color:
        #64748b;
}}

input[type="file"] {{
    width:
        100%;

    padding:
        12px;

    margin:
        15px 0;

    border:
        1px solid #d8e1e8;

    border-radius:
        10px;
}}

button {{
    width:
        100%;

    padding:
        13px;

    border:
        none;

    border-radius:
        10px;

    background:
        #087f9c;

    color:
        white;

    font-weight:
        700;

    cursor:
        pointer;
}}

button:hover {{
    background:
        #066b84;
}}

.back {{
    display:
        inline-block;

    margin-top:
        15px;

    color:
        #087f9c;

    text-decoration:
        none;

    font-size:
        14px;
}}

.note {{
    margin-top:
        15px;

    font-size:
        12px;

    color:
        #94a3b8;
}}

</style>

</head>

<body>

<div class="card">

<img
    class="photo"
    src="/profile/photo/{user.id}"
    alt="Profile Photo"
>

<h1>
    Change Profile Photo
</h1>

<p>
    {user.name}
</p>

<form
    action="/profile/upload-photo"
    method="post"
    enctype="multipart/form-data"
>

<input
    type="file"
    name="photo"
    accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
    required
>

<button type="submit">
    Save Profile Photo
</button>

</form>

<div class="note">
    JPG, PNG or WEBP • Maximum 5 MB
</div>

<a
    class="back"
    href="/profile"
>
    ← Back to Profile
</a>

</div>

</body>

</html>
"""


@router.post("/upload-photo")
async def upload_profile_photo(
    request: Request,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):

    user = get_current_user(
        request,
        db,
    )

    if not user:

        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    if not photo.filename:

        raise HTTPException(
            status_code=400,
            detail="Please select a photo.",
        )

    extension = (
        Path(photo.filename)
        .suffix
        .lower()
    )

    if extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail="Only JPG, JPEG, PNG and WEBP images are allowed.",
        )

    if photo.content_type not in ALLOWED_CONTENT_TYPES:

        raise HTTPException(
            status_code=400,
            detail="Invalid image type.",
        )

    content = await photo.read()

    if not content:

        raise HTTPException(
            status_code=400,
            detail="Image is empty.",
        )

    if len(content) > MAX_PROFILE_PHOTO_SIZE:

        raise HTTPException(
            status_code=400,
            detail="Profile photo must not exceed 5 MB.",
        )

    # Basic image signature validation
    valid_signature = False

    if extension in {".jpg", ".jpeg"}:
        valid_signature = (
            content.startswith(b"\xff\xd8\xff")
        )

    elif extension == ".png":
        valid_signature = (
            content.startswith(
                b"\x89PNG\r\n\x1a\n"
            )
        )

    elif extension == ".webp":
        valid_signature = (
            content.startswith(b"RIFF")
            and
            content[8:12] == b"WEBP"
        )

    if not valid_signature:

        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid image.",
        )

    ensure_profile_directory()

    # Delete previous profile photos
    for old_extension in ALLOWED_EXTENSIONS:

        old_file = (
            PROFILE_DIR
            / f"user_{user.id}{old_extension}"
        )

        if old_file.exists():

            old_file.unlink()

    new_file = (
        PROFILE_DIR
        / f"user_{user.id}{extension}"
    )

    with open(
        new_file,
        "wb",
    ) as file:

        file.write(content)

    return RedirectResponse(
        url="/profile",
        status_code=303,
    )