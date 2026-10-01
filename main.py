import os
import sys
import asyncio
import uvicorn

from datetime import datetime

from dotenv import load_dotenv

from fastapi import (
    Depends,
    FastAPI,
    Form,
    Request,
    HTTPException,
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    JSONResponse,
)

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from starlette.middleware.sessions import SessionMiddleware


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# LOGGER
# ============================================================

from src.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# DATABASE
# ============================================================

from src.database.database import get_db

from src.database.models import (
    User,
    PatientProfile,
    MedicalHistory,
    LoginHistory,
    Doctor,
)


# ============================================================
# SECURITY
# ============================================================

from src.security import verify_password


# ============================================================
# EXCEPTION
# ============================================================

from src.exception import CustomException


# ============================================================
# ML PIPELINE
# ============================================================

from src.pipeline.predict_pipeline import (
    CustomData,
    PredictPipeline,
)


# ============================================================
# PRETRAINED NLP
# ============================================================

from nlp_pretrained.ner_tagger import (
    get_pos_tags,
    extract_entities,
)

from nlp_pretrained.embedding import (
    most_similar_words,
)

from nlp_pretrained.sentiment_analyzer import (
    analyze_sentiment,
)


# ============================================================
# ROUTERS - IMPORTS ONLY
# ============================================================

from src.profile.routes import (
    router as profile_router
)

from src.authentication.routes import (
    router as auth_router
)

from src.payments.routes import (
    router as payments_router
)

from src.doctors.routes import (
    router as doctors_router
)

from src.medical_reports.routes import (
    router as medical_reports_router
)

from src.prescriptions.routes import (
    router as prescriptions_router
)

from src.ai_chat.routes import (
    router as ai_chat_router
)

from src.appointments.routes import (
    router as appointments_router
)

from src.doctor_reports.routes import (
    router as doctor_reports_router
)

from src.clinic_intelligence import (
    router as clinic_router
)

from src.clinic_intelligence.management_routes import (
    router as clinic_management_router
)

from src.pharmacy.routes import (
    router as pharmacy_router
)


# ============================================================
# ROLE MANAGEMENT
# ============================================================

from src.role_management import (
    UserPermission
)

from src.role_management.routes import (
    router as role_management_router
)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="Sehat Saathi"
)


# ============================================================
# SESSION MIDDLEWARE
# ============================================================

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv(
        "SESSION_SECRET_KEY",
        "development-secret-key",
    ),
)


# ============================================================
# CONCURRENT REQUEST PROTECTION
# ============================================================

MAX_CONCURRENT_REQUESTS = int(
    os.getenv(
        "MAX_CONCURRENT_REQUESTS",
        "100",
    )
)

REQUEST_QUEUE_TIMEOUT = float(
    os.getenv(
        "REQUEST_QUEUE_TIMEOUT",
        "15",
    )
)

request_semaphore = asyncio.Semaphore(
    MAX_CONCURRENT_REQUESTS
)


@app.middleware("http")
async def concurrency_protection(
    request: Request,
    call_next,
):

    try:

        await asyncio.wait_for(
            request_semaphore.acquire(),
            timeout=REQUEST_QUEUE_TIMEOUT,
        )

    except asyncio.TimeoutError:

        logger.warning(
            "Request rejected because server "
            "concurrency limit was reached."
        )

        return JSONResponse(
            status_code=503,
            content={
                "status": "busy",
                "message": (
                    "The server is temporarily busy. "
                    "Please try again in a few seconds."
                ),
            },
        )

    try:

        response = await call_next(request)

        return response

    except Exception as error:

        logger.exception(
            f"Unhandled request error: {error}"
        )

        raise

    finally:

        request_semaphore.release()


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)


# ============================================================
# ROUTERS
# ============================================================

app.include_router(
    role_management_router
)

app.include_router(
    profile_router
)

app.include_router(
    auth_router
)

app.include_router(
    payments_router
)

app.include_router(
    doctors_router
)

app.include_router(
    medical_reports_router
)

app.include_router(
    prescriptions_router
)

app.include_router(
    ai_chat_router
)

app.include_router(
    appointments_router
)

app.include_router(
    clinic_router
)

app.include_router(
    doctor_reports_router
)

app.include_router(
    clinic_management_router
)

app.include_router(
    pharmacy_router
)


# ============================================================
# TEMPLATES
# ============================================================

templates = Jinja2Templates(
    directory="templates"
)


# ============================================================
# COMMON HELPERS
# ============================================================

def get_logged_in_user(
    request: Request,
    db: Session,
):

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:
        return None

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_active == True,
        )
        .first()
    )

    if not user:

        request.session.clear()

        return None

    return user


def redirect_after_login(
    user: User
):

    if user.role == "admin":

        return RedirectResponse(
            url="/admin/dashboard",
            status_code=303,
        )

    if user.role == "doctor":

        return RedirectResponse(
            url="/doctor/dashboard",
            status_code=303,
        )

    if user.role == "pharmacy_staff":

        return RedirectResponse(
            url="/pharmacy/",
            status_code=303,
        )

    return RedirectResponse(
        url="/patient/dashboard",
        status_code=303,
    )


# ============================================================
# VOICE ASSISTANT
# ============================================================

@app.get(
    "/voice-assistant",
    response_class=HTMLResponse,
)
async def voice_assistant(
    request: Request,
    db: Session = Depends(get_db),
):

    user = get_logged_in_user(
        request,
        db,
    )

    if not user:

        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    return templates.TemplateResponse(
        request=request,
        name="voice_assistant.html",
        context={
            "request": request,
            "user": user,
        },
    )


# ============================================================
# ROLE LOGIN PAGE
# ============================================================

def role_login_page(
    title: str,
    role: str,
    color: str,
):

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>{title}</title>

        <style>

            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                min-height: 100vh;
                font-family: Arial, sans-serif;
                background: #f5f7fb;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}

            .card {{
                width: 100%;
                max-width: 430px;
                background: white;
                padding: 35px;
                border-radius: 18px;
                box-shadow: 0 8px 30px rgba(0,0,0,.10);
            }}

            .logo {{
                text-align: center;
                font-size: 32px;
                margin-bottom: 8px;
            }}

            h1 {{
                text-align: center;
                margin-bottom: 8px;
                color: #172033;
            }}

            .subtitle {{
                text-align: center;
                color: #64748b;
                margin-bottom: 25px;
            }}

            label {{
                display: block;
                margin-top: 15px;
                margin-bottom: 6px;
                font-weight: bold;
                color: #334155;
            }}

            input {{
                width: 100%;
                padding: 12px;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                font-size: 15px;
            }}

            button {{
                width: 100%;
                margin-top: 22px;
                padding: 13px;
                border: none;
                border-radius: 8px;
                background: {color};
                color: white;
                font-size: 16px;
                cursor: pointer;
            }}

            .links {{
                text-align: center;
                margin-top: 20px;
            }}

            .links a {{
                color: #2563eb;
                text-decoration: none;
            }}

            .error {{
                background: #fee2e2;
                color: #991b1b;
                padding: 10px;
                border-radius: 7px;
                margin-bottom: 15px;
            }}

        </style>

    </head>

    <body>

        <div class="card">

            <div class="logo">🏥</div>

            <h1>{title}</h1>

            <div class="subtitle">
                Sehat Saathi
            </div>

            <form
                method="post"
                action="/{role}/login"
            >

                <label>Email</label>

                <input
                    type="email"
                    name="email"
                    placeholder="Enter email"
                    required
                >

                <label>Password</label>

                <input
                    type="password"
                    name="password"
                    placeholder="Enter password"
                    required
                >

                <button type="submit">
                    Login as {title.split(" ")[0]}
                </button>

            </form>

            <div class="links">

                <a href="/">
                    ← Back to Home
                </a>

            </div>

        </div>

    </body>

    </html>
    """


# ============================================================
# LOGIN ERROR PAGE
# ============================================================

def login_error_page(
    title: str,
    role: str,
    color: str,
    message: str,
):

    page = role_login_page(
        title=title,
        role=role,
        color=color,
    )

    page = page.replace(
        '<form\n                method="post"',
        f"""
        <div class="error">
            {message}
        </div>

        <form
                method="post"
        """,
        1,
    )

    return page


# ============================================================
# PUBLIC HOME PAGE
# ============================================================

@app.get(
    "/",
    response_class=HTMLResponse,
)
async def home(
    request: Request,
    db: Session = Depends(get_db),
):

    logger.info(
        "Home page accessed..."
    )

    user = get_logged_in_user(
        request,
        db,
    )

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "user": user,
        },
    )


# ============================================================
# REGISTER PAGE
# ============================================================

@app.get(
    "/register",
    response_class=HTMLResponse,
)
async def registration_page(
    request: Request,
):

    return templates.TemplateResponse(
        request,
        "registration.html",
    )


# ============================================================
# LOGIN CHOICE PAGE
# ============================================================

@app.get(
    "/login",
    response_class=HTMLResponse,
)
async def login_page(
    request: Request,
):

    return """
    <!DOCTYPE html>

    <html>

    <head>

        <title>
            Login - Sehat Saathi
        </title>

        <style>

            body {
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f5f7fb;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }

            .container {
                width: 100%;
                max-width: 1100px;
            }

            h1 {
                text-align: center;
                color: #172033;
            }

            .subtitle {
                text-align: center;
                color: #64748b;
                margin-bottom: 30px;
            }

            .cards {
                display: grid;
                grid-template-columns:
                    repeat(auto-fit,minmax(190px,1fr));
                gap: 20px;
            }

            .card {
                background: white;
                padding: 30px;
                border-radius: 16px;
                text-align: center;
                box-shadow: 0 6px 25px rgba(0,0,0,.08);
            }

            .icon {
                font-size: 45px;
            }

            .card h2 {
                color: #172033;
            }

            .card p {
                color: #64748b;
                min-height: 45px;
            }

            .button {
                display: block;
                padding: 12px;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin-top: 18px;
            }

            .admin {
                background: #7c3aed;
            }

            .doctor {
                background: #0f766e;
            }

            .patient {
                background: #2563eb;
            }

            .pharmacy {
                background: #16a34a;
            }

            .home {
                text-align: center;
                margin-top: 25px;
            }

            .home a {
                color: #2563eb;
                text-decoration: none;
            }

        </style>

    </head>

    <body>

        <div class="container">

            <h1>
                Login to Sehat Saathi
            </h1>

            <p class="subtitle">
                Select your account type
            </p>

            <div class="cards">

                <div class="card">

                    <div class="icon">
                        👨‍💼
                    </div>

                    <h2>
                        Admin
                    </h2>

                    <p>
                        Clinic management,
                        analytics and administration.
                    </p>

                    <a
                        class="button admin"
                        href="/admin/login"
                    >
                        Admin Login
                    </a>

                </div>


                <div class="card">

                    <div class="icon">
                        👨‍⚕️
                    </div>

                    <h2>
                        Doctor
                    </h2>

                    <p>
                        Appointments, patients
                        and medical reports.
                    </p>

                    <a
                        class="button doctor"
                        href="/doctor/login"
                    >
                        Doctor Login
                    </a>

                </div>


                <div class="card">

                    <div class="icon">
                        🧑‍🦽
                    </div>

                    <h2>
                        Patient
                    </h2>

                    <p>
                        Profile, appointments,
                        reports and AI features.
                    </p>

                    <a
                        class="button patient"
                        href="/patient/login"
                    >
                        Patient Login
                    </a>

                </div>


                <div class="card">

                    <div class="icon">
                        💊
                    </div>

                    <h2>
                        Pharmacy Staff
                    </h2>

                    <p>
                        Pharmacy access based
                        on assigned permissions.
                    </p>

                    <a
                        class="button pharmacy"
                        href="/pharmacy/login"
                    >
                        Pharmacy Login
                    </a>

                </div>

            </div>

            <div class="home">

                <a href="/">
                    ← Back to Home
                </a>

            </div>

        </div>

    </body>

    </html>
    """


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.get(
    "/admin/login",
    response_class=HTMLResponse,
)
async def admin_login_page(
    request: Request,
):

    return role_login_page(
        title="Admin Login",
        role="admin",
        color="#7c3aed",
    )


@app.post(
    "/admin/login",
    response_class=HTMLResponse,
)
async def admin_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):

    user = (
        db.query(User)
        .filter(
            User.email == email.strip().lower(),
            User.is_active == True,
        )
        .first()
    )

    if not user or user.role != "admin":

        return HTMLResponse(
            content=login_error_page(
                "Admin Login",
                "admin",
                "#7c3aed",
                "Invalid admin email or password.",
            ),
            status_code=401,
        )

    if not verify_password(
        password,
        user.password_hash,
    ):

        return HTMLResponse(
            content=login_error_page(
                "Admin Login",
                "admin",
                "#7c3aed",
                "Invalid admin email or password.",
            ),
            status_code=401,
        )

    now = datetime.utcnow()

    user.last_login_at = now
    user.is_logged_in = True

    db.add(
        LoginHistory(
            user_id=user.id,
            login_at=now,
            is_successful=True,
        )
    )

    db.commit()

    request.session.clear()

    request.session["user_id"] = user.id
    request.session["role"] = "admin"

    return RedirectResponse(
        url="/admin/dashboard",
        status_code=303,
    )


# ============================================================
# DOCTOR LOGIN
# ============================================================

@app.get(
    "/doctor/login",
    response_class=HTMLResponse,
)
async def doctor_login_page(
    request: Request,
):

    return role_login_page(
        title="Doctor Login",
        role="doctor",
        color="#0f766e",
    )


@app.post(
    "/doctor/login",
    response_class=HTMLResponse,
)
async def doctor_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):

    user = (
        db.query(User)
        .filter(
            User.email == email.strip().lower(),
            User.is_active == True,
        )
        .first()
    )

    if not user or user.role != "doctor":

        return HTMLResponse(
            content=login_error_page(
                "Doctor Login",
                "doctor",
                "#0f766e",
                "Invalid doctor email or password.",
            ),
            status_code=401,
        )

    if not verify_password(
        password,
        user.password_hash,
    ):

        return HTMLResponse(
            content=login_error_page(
                "Doctor Login",
                "doctor",
                "#0f766e",
                "Invalid doctor email or password.",
            ),
            status_code=401,
        )

    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.user_id == user.id,
            Doctor.availability_status == "active",
        )
        .first()
    )

    if not doctor:

        return HTMLResponse(
            content=login_error_page(
                "Doctor Login",
                "doctor",
                "#0f766e",
                "Doctor profile is not active.",
            ),
            status_code=403,
        )

    now = datetime.utcnow()

    user.last_login_at = now
    user.is_logged_in = True

    db.add(
        LoginHistory(
            user_id=user.id,
            login_at=now,
            is_successful=True,
        )
    )

    db.commit()

    request.session.clear()

    request.session["user_id"] = user.id
    request.session["role"] = "doctor"
    request.session["doctor_id"] = doctor.id

    return RedirectResponse(
        url="/doctor/dashboard",
        status_code=303,
    )


# ============================================================
# PATIENT LOGIN
# ============================================================

@app.get(
    "/patient/login",
    response_class=HTMLResponse,
)
async def patient_login_page(
    request: Request,
):

    return role_login_page(
        title="Patient Login",
        role="patient",
        color="#2563eb",
    )


@app.post(
    "/patient/login",
    response_class=HTMLResponse,
)
async def patient_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):

    user = (
        db.query(User)
        .filter(
            User.email == email.strip().lower(),
            User.is_active == True,
        )
        .first()
    )

    if not user or user.role != "patient":

        return HTMLResponse(
            content=login_error_page(
                "Patient Login",
                "patient",
                "#2563eb",
                "Invalid patient email or password.",
            ),
            status_code=401,
        )

    if not verify_password(
        password,
        user.password_hash,
    ):

        return HTMLResponse(
            content=login_error_page(
                "Patient Login",
                "patient",
                "#2563eb",
                "Invalid patient email or password.",
            ),
            status_code=401,
        )

    now = datetime.utcnow()

    user.last_login_at = now
    user.is_logged_in = True

    db.add(
        LoginHistory(
            user_id=user.id,
            login_at=now,
            is_successful=True,
        )
    )

    db.commit()

    request.session.clear()

    request.session["user_id"] = user.id
    request.session["role"] = "patient"

    return RedirectResponse(
        url="/patient/dashboard",
        status_code=303,
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.get(
    "/admin/dashboard",
    response_class=HTMLResponse,
)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
):

    user = get_logged_in_user(
        request,
        db,
    )

    if not user:

        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    if user.role != "admin":

        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )

    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>

        <html>

        <head>

            <title>Admin Dashboard</title>

            <style>

                body {{
                    font-family: Arial;
                    background: #f5f7fb;
                    padding: 30px;
                }}

                .container {{
                    max-width: 1000px;
                    margin: auto;
                    background: white;
                    padding: 30px;
                    border-radius: 15px;
                }}

                .cards {{
                    display: grid;
                    grid-template-columns:
                        repeat(auto-fit,minmax(200px,1fr));
                    gap: 15px;
                    margin-top: 25px;
                }}

                .card {{
                    padding: 20px;
                    background: #f8fafc;
                    border-radius: 10px;
                }}

                .card a {{
                    color: #2563eb;
                    text-decoration: none;
                    font-weight: bold;
                }}

                .clinic-card {{
                    background: #eff6ff;
                    border: 1px solid #bfdbfe;
                }}

                .pharmacy-card {{
                    background: #f0fdf4;
                    border: 1px solid #bbf7d0;
                }}

                .role-card {{
                    background: #fff7ed;
                    border: 1px solid #fed7aa;
                }}

            </style>

        </head>

        <body>

        <div class="container">

            <h1>
                Admin Dashboard
            </h1>

            <p>
                Welcome,
                <strong>{user.name}</strong>
            </p>

            <div class="cards">

                <div class="card">

                    <h3>👨‍⚕️ Doctors</h3>

                    <a href="/doctors/admin">
                        Manage Doctors
                    </a>

                </div>


                <div class="card">

                    <h3>📊 Analytics</h3>

                    <a href="/clinic-intelligence/">
                        Clinic Intelligence
                    </a>

                </div>


                <div class="card">

                    <h3>📋 Reports</h3>

                    <a href="/medical-reports/page">
                        Medical Reports
                    </a>

                </div>


                <div class="card clinic-card">

                    <h3>
                        🏥 Clinic Management
                    </h3>

                    <p>
                        Staff, Salary, Inventory
                        and Clinic Timing
                    </p>

                    <a href="/clinic/">
                        Open Clinic Management
                    </a>

                </div>


                <div class="card pharmacy-card">

                    <h3>
                        💊 Pharmacy Management
                    </h3>

                    <p>
                        Medicines, Stock, Suppliers,
                        Purchases and Pharmacy Staff
                    </p>

                    <a href="/pharmacy/admin">
                        Open Pharmacy Management
                    </a>

                </div>


                <div class="card role-card">

                    <h3>
                        🔐 Role & Permissions
                    </h3>

                    <p>
                        Create Pharmacy Staff
                        and assign permissions.
                    </p>

                    <a href="/role-management/admin">
                        Manage Roles
                    </a>

                </div>

            </div>

            <br>

            <a href="/auth/logout">
                Logout
            </a>

        </div>

        </body>

        </html>
        """
    )


# ============================================================
# DOCTOR DASHBOARD
# ============================================================

@app.get(
    "/doctor/dashboard",
    response_class=HTMLResponse,
)
async def doctor_dashboard(
    request: Request,
    db: Session = Depends(get_db),
):

    user = get_logged_in_user(
        request,
        db,
    )

    if not user:

        return RedirectResponse(
            url="/doctor/login",
            status_code=303,
        )

    if user.role != "doctor":

        raise HTTPException(
            status_code=403,
            detail="Doctor access required.",
        )

    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.user_id == user.id,
        )
        .first()
    )

    if not doctor:

        raise HTTPException(
            status_code=403,
            detail="Doctor profile not found.",
        )

    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>

        <html>

        <head>

            <title>
                Doctor Dashboard
            </title>

            <style>

                body {{
                    font-family: Arial;
                    background: #f5f7fb;
                    padding: 30px;
                }}

                .container {{
                    max-width: 1000px;
                    margin: auto;
                    background: white;
                    padding: 30px;
                    border-radius: 15px;
                }}

                .cards {{
                    display: grid;
                    grid-template-columns:
                        repeat(auto-fit,minmax(210px,1fr));
                    gap: 15px;
                    margin-top: 25px;
                }}

                .card {{
                    background: #f8fafc;
                    padding: 20px;
                    border-radius: 10px;
                }}

                a {{
                    color: #0f766e;
                    text-decoration: none;
                }}

            </style>

        </head>

        <body>

        <div class="container">

            <h1>
                Doctor Dashboard
            </h1>

            <p>
                Welcome Dr.
                <strong>{doctor.name}</strong>
            </p>

            <p>
                Specialty:
                <strong>{doctor.specialty}</strong>
            </p>

            <div class="cards">

                <div class="card">

                    <h3>
                        👥 My Patients
                    </h3>

                    <p>
                        Patients who have appointments
                        with you.
                    </p>

                </div>


                <div class="card">

                    <h3>
                        📅 Appointments
                    </h3>

                    <a href="/appointments/my">
                        View Appointments
                    </a>

                </div>


                <div class="card">

                    <h3>
                        📄 Medical Reports
                    </h3>

                    <a href="/doctor-reports/">
                        Create Medical Report
                    </a>

                </div>


                <div class="card">

                    <h3>
                        🩺 Doctor Documents
                    </h3>

                    <a href="/doctor-reports/">
                        Patient Documents
                    </a>

                </div>

            </div>

            <br>

            <a href="/auth/logout">
                Logout
            </a>

        </div>

        </body>

        </html>
        """
    )


# ============================================================
# PATIENT DASHBOARD
# ============================================================

@app.get(
    "/patient/dashboard",
    response_class=HTMLResponse,
)
async def patient_dashboard(
    request: Request,
    db: Session = Depends(get_db),
):

    user = get_logged_in_user(
        request,
        db,
    )

    if not user:

        return RedirectResponse(
            url="/patient/login",
            status_code=303,
        )

    if user.role != "patient":

        raise HTTPException(
            status_code=403,
            detail="Patient access required.",
        )

    return templates.TemplateResponse(
        request,
        "patient_dashboard.html",
        {
            "user": user,
        },
    )


# ============================================================
# OLD DASHBOARD COMPATIBILITY
# ============================================================

@app.get(
    "/dashboard",
)
async def dashboard_redirect(
    request: Request,
    db: Session = Depends(get_db),
):

    user = get_logged_in_user(
        request,
        db,
    )

    if not user:

        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    return redirect_after_login(
        user
    )


# ============================================================
# PATIENT PROFILE
# ============================================================

@app.get(
    "/profile",
    response_class=HTMLResponse,
)
async def patient_profile(
    request: Request,
    db: Session = Depends(get_db),
):

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:

        return RedirectResponse(
            url="/patient/login",
            status_code=303,
        )

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
        )
        .first()
    )

    if not user:

        request.session.clear()

        return RedirectResponse(
            url="/patient/login",
            status_code=303,
        )

    if user.role != "patient":

        raise HTTPException(
            status_code=403,
            detail="Patient access required.",
        )

    profile = (
        db.query(PatientProfile)
        .filter(
            PatientProfile.user_id == user_id,
        )
        .first()
    )

    medical_history = (
        db.query(MedicalHistory)
        .filter(
            MedicalHistory.user_id == user_id,
        )
        .order_by(
            MedicalHistory.visit_date.desc()
        )
        .all()
    )

    return templates.TemplateResponse(
        request,
        "patient_profile.html",
        {
            "user": user,
            "profile": profile,
            "medical_history": medical_history,
        },
    )


# ============================================================
# UPDATE PATIENT PROFILE
# ============================================================

@app.post(
    "/profile/update",
)
async def update_patient_profile(
    request: Request,

    date_of_birth: str = Form(""),
    gender: str = Form(""),
    blood_group: str = Form(""),

    allergies: str = Form(""),
    existing_conditions: str = Form(""),
    previous_medical_history: str = Form(""),

    emergency_contact_name: str = Form(""),
    emergency_contact_mobile: str = Form(""),

    address: str = Form(""),
    village: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    pincode: str = Form(""),

    db: Session = Depends(get_db),
):

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:

        return RedirectResponse(
            url="/patient/login",
            status_code=303,
        )

    user = (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )

    if not user or user.role != "patient":

        raise HTTPException(
            status_code=403,
            detail="Patient access required.",
        )

    profile = (
        db.query(PatientProfile)
        .filter(
            PatientProfile.user_id == user_id
        )
        .first()
    )

    if not profile:

        profile = PatientProfile(
            user_id=user_id
        )

        db.add(profile)

    profile.gender = gender or None
    profile.blood_group = blood_group or None

    profile.allergies = (
        allergies or None
    )

    profile.existing_conditions = (
        existing_conditions or None
    )

    profile.previous_medical_history = (
        previous_medical_history or None
    )

    profile.emergency_contact_name = (
        emergency_contact_name or None
    )

    profile.emergency_contact_mobile = (
        emergency_contact_mobile or None
    )

    profile.address = address or None
    profile.village = village or None
    profile.city = city or None
    profile.state = state or None
    profile.pincode = pincode or None

    db.commit()

    return RedirectResponse(
        url="/patient/dashboard",
        status_code=303,
    )


# ============================================================
# PREDICTION PAGE
# ============================================================

@app.get(
    "/predict",
    response_class=HTMLResponse,
)
async def predict_form(
    request: Request,
):

    return templates.TemplateResponse(
        request,
        "predict.html",
        {
            "result": None,
        },
    )


# ============================================================
# PREDICTION RESULT
# ============================================================

@app.post(
    "/predict",
    response_class=HTMLResponse,
)
async def predict_result(
    request: Request,
    age: int = Form(...),
    gender: str = Form(...),
    fever: float = Form(...),
    cough: str = Form(...),
    city: str = Form(...),
):

    try:

        logger.info(
            f"Prediction request received :: "
            f"age={age}, "
            f"gender={gender}, "
            f"fever={fever}, "
            f"cough={cough}, "
            f"city={city}"
        )

        custom_data = CustomData(
            age=age,
            gender=gender,
            fever=fever,
            cough=cough,
            city=city,
        )

        data_df = (
            custom_data
            .get_data_as_dataframe()
        )

        predict_pipeline = PredictPipeline()

        result, probability = (
            predict_pipeline
            .predict(data_df)
        )

        return templates.TemplateResponse(
            request,
            "predict.html",
            {
                "result": result,
                "probability": probability,
                "form_data": {
                    "age": age,
                    "gender": gender,
                    "fever": fever,
                    "cough": cough,
                    "city": city,
                },
            },
        )

    except Exception as e:

        raise CustomException(
            e,
            sys,
        )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get(
    "/health"
)
async def health_check():

    return {
        "status": "ok"
    }


# ============================================================
# PRETRAINED NLP PAGE
# ============================================================

@app.get(
    "/pretrained-nlp",
    response_class=HTMLResponse,
)
async def pretrained_nlp_form(
    request: Request,
):

    return templates.TemplateResponse(
        request,
        "pretrained_nlp.html",
        {
            "result": None,
            "form_data": {
                "query": ""
            },
            "error": None,
        },
    )


# ============================================================
# PRETRAINED NLP ANALYSIS
# ============================================================

@app.post(
    "/pretrained-nlp",
    response_class=HTMLResponse,
)
async def pretrained_nlp_analysis(
    request: Request,
    query: str = Form(...),
):

    try:

        query = query.strip()

        if not query:

            return templates.TemplateResponse(
                request,
                "pretrained_nlp.html",
                {
                    "result": None,
                    "form_data": {
                        "query": ""
                    },
                    "error": (
                        "Please enter some text..."
                    ),
                },
            )

        pos_tags = get_pos_tags(
            query
        )

        entities = extract_entities(
            query
        )

        sentiment = analyze_sentiment(
            query
        )

        similar_words = []

        words = query.split()

        if words:

            first_word = words[0].lower()

            try:

                similar_words = (
                    most_similar_words(
                        first_word,
                        topn=5,
                    )
                )

            except Exception as e:

                logger.warning(
                    f"Glove similarity failed "
                    f"for: {first_word}. "
                    f"Error: {e}"
                )

        result = {
            "query": query,
            "pos_tags": pos_tags,
            "entities": entities,
            "similar_words": similar_words,
            "sentiment": sentiment,
        }

        return templates.TemplateResponse(
            request,
            "pretrained_nlp.html",
            {
                "result": result,
                "form_data": {
                    "query": query
                },
                "error": None,
            },
        )

    except Exception as e:

        logger.info(
            "Error occurred in "
            "pretrained NLP analysis"
        )

        return templates.TemplateResponse(
            request,
            "pretrained_nlp.html",
            {
                "result": None,
                "form_data": {
                    "query": query
                },
                "error": str(e),
            },
        )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )