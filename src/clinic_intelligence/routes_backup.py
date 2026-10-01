from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.database.models import User

from .login_analytics import (
    get_daily_login_activity,
    get_doctor_login_analytics,
    get_login_history,
    get_login_summary,
    get_patient_login_analytics,
    get_top_users_by_login,
)

router = APIRouter(
    prefix="/clinic-intelligence",
    tags=["Clinic Intelligence"],
)


# ============================================================
# SESSION-BASED ADMIN AUTHENTICATION
# ============================================================

def get_current_admin(
    request: Request,
    db: Session,
):
    """
    Get currently logged-in admin from FastAPI session.

    No admin_id in URL is required.
    """

    user_id = request.session.get("user_id")

    if not user_id:
        return None

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.role == "admin",
            User.is_active == True,
        )
        .first()
    )

    return user


def require_admin(
    request: Request,
    db: Session,
):
    """
    Require an active admin session.
    """

    admin = get_current_admin(request, db)

    if not admin:
        raise HTTPException(
            status_code=401,
            detail="Admin login required.",
        )

    return admin


# ============================================================
# HELPERS
# ============================================================

def safe_datetime(value):
    if not value:
        return "-"

    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y %I:%M %p")

    return str(value)


def html_escape(value):
    if value is None:
        return ""

    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )


# ============================================================
# MAIN COMMAND CENTER
# ============================================================

@router.get("/", response_class=HTMLResponse)
def clinic_intelligence_dashboard(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Admin-only clinic intelligence dashboard.

    Uses the existing login session.
    """

    admin = get_current_admin(
        request,
        db,
    )

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    summary = get_login_summary(db)

    doctors = get_doctor_login_analytics(db)

    patients = get_patient_login_analytics(db)

    daily_activity = get_daily_login_activity(
        db,
        days=30,
    )

    top_doctors = get_top_users_by_login(
        db,
        role="doctor",
        limit=10,
    )

    top_patients = get_top_users_by_login(
        db,
        role="patient",
        limit=10,
    )

    # --------------------------------------------------------
    # DOCTOR TABLE
    # --------------------------------------------------------

    doctor_rows = ""

    for doctor in doctors:

        status = (
            '<span class="online">● ONLINE</span>'
            if doctor["is_online"]
            else '<span class="offline">● OFFLINE</span>'
        )

        doctor_rows += f"""
        <tr>

            <td>
                <strong>
                    {html_escape(doctor["name"])}
                </strong>
            </td>

            <td>
                {html_escape(doctor["email"])}
            </td>

            <td>
                <strong>
                    {doctor["login_count"]}
                </strong>
            </td>

            <td>
                {safe_datetime(doctor["last_login"])}
            </td>

            <td>
                {safe_datetime(doctor["last_logout"])}
            </td>

            <td>
                {status}
            </td>

            <td>
                <a
                    class="small-btn"
                    href="/clinic-intelligence/user-history/{doctor['user_id']}"
                >
                    View
                </a>
            </td>

        </tr>
        """

    if not doctor_rows:

        doctor_rows = """
        <tr>
            <td colspan="7" class="empty">
                No doctor login data available.
            </td>
        </tr>
        """

    # --------------------------------------------------------
    # PATIENT TABLE
    # --------------------------------------------------------

    patient_rows = ""

    for patient in patients:

        status = (
            '<span class="online">● ONLINE</span>'
            if patient["is_online"]
            else '<span class="offline">● OFFLINE</span>'
        )

        patient_rows += f"""
        <tr>

            <td>
                <strong>
                    {html_escape(patient["name"])}
                </strong>
            </td>

            <td>
                {html_escape(patient["email"])}
            </td>

            <td>
                <strong>
                    {patient["login_count"]}
                </strong>
            </td>

            <td>
                {safe_datetime(patient["last_login"])}
            </td>

            <td>
                {safe_datetime(patient["last_logout"])}
            </td>

            <td>
                {status}
            </td>

            <td>
                <a
                    class="small-btn"
                    href="/clinic-intelligence/user-history/{patient['user_id']}"
                >
                    View
                </a>
            </td>

        </tr>
        """

    if not patient_rows:

        patient_rows = """
        <tr>
            <td colspan="7" class="empty">
                No patient login data available.
            </td>
        </tr>
        """

    # --------------------------------------------------------
    # CHART DATA
    # --------------------------------------------------------

    chart_labels = [
        item["date"]
        for item in daily_activity
    ]

    doctor_chart = [
        item["doctor_logins"]
        for item in daily_activity
    ]

    patient_chart = [
        item["patient_logins"]
        for item in daily_activity
    ]

    total_chart = [
        item["total_logins"]
        for item in daily_activity
    ]

    # --------------------------------------------------------
    # TOP DOCTORS
    # --------------------------------------------------------

    top_doctor_rows = ""

    for index, doctor in enumerate(
        top_doctors,
        start=1,
    ):

        top_doctor_rows += f"""
        <tr>

            <td>
                #{index}
            </td>

            <td>
                {html_escape(doctor["name"])}
            </td>

            <td>
                <strong>
                    {doctor["login_count"]}
                </strong>
            </td>

            <td>
                {safe_datetime(doctor["last_login"])}
            </td>

        </tr>
        """

    # --------------------------------------------------------
    # TOP PATIENTS
    # --------------------------------------------------------

    top_patient_rows = ""

    for index, patient in enumerate(
        top_patients,
        start=1,
    ):

        top_patient_rows += f"""
        <tr>

            <td>
                #{index}
            </td>

            <td>
                {html_escape(patient["name"])}
            </td>

            <td>
                <strong>
                    {patient["login_count"]}
                </strong>
            </td>

            <td>
                {safe_datetime(patient["last_login"])}
            </td>

        </tr>
        """

    # ========================================================
    # HTML
    # ========================================================

    return f"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
Clinic Intelligence Command Center
</title>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;

    font-family:
        Inter,
        Arial,
        sans-serif;

    background:
        #f4f7fb;

    color:
        #172033;
}}

.header {{
    background:
        linear-gradient(
            135deg,
            #111827,
            #243b53
        );

    color:
        white;

    padding:
        28px;
}}

.header-inner {{
    max-width:
        1450px;

    margin:
        auto;
}}

.header h1 {{
    margin:
        0 0 8px 0;

    font-size:
        30px;
}}

.header p {{
    margin:
        0;

    opacity:
        .78;
}}

.container {{
    max-width:
        1450px;

    margin:
        28px auto;

    padding:
        0 20px;
}}

.kpi-grid {{
    display:
        grid;

    grid-template-columns:
        repeat(
            4,
            minmax(
                0,
                1fr
            )
        );

    gap:
        18px;
}}

.kpi {{
    background:
        white;

    border-radius:
        18px;

    padding:
        22px;

    box-shadow:
        0 8px 25px
        rgba(
            15,
            23,
            42,
            .07
        );
}}

.kpi-label {{
    color:
        #667085;

    font-size:
        13px;
}}

.kpi-value {{
    font-size:
        32px;

    font-weight:
        800;

    margin-top:
        8px;
}}

.kpi-sub {{
    margin-top:
        6px;

    font-size:
        12px;

    color:
        #98a2b3;
}}

.section {{
    background:
        white;

    border-radius:
        18px;

    margin-top:
        22px;

    padding:
        22px;

    box-shadow:
        0 8px 25px
        rgba(
            15,
            23,
            42,
            .06
        );
}}

.section h2 {{
    margin:
        0 0 6px 0;

    font-size:
        21px;
}}

.section-description {{
    color:
        #667085;

    margin-bottom:
        18px;

    font-size:
        13px;
}}

.chart-box {{
    position:
        relative;

    height:
        360px;
}}

.two-column {{
    display:
        grid;

    grid-template-columns:
        1fr 1fr;

    gap:
        22px;
}}

table {{
    width:
        100%;

    border-collapse:
        collapse;
}}

th {{
    background:
        #f8fafc;

    text-align:
        left;

    padding:
        13px;

    font-size:
        12px;

    color:
        #667085;

    border-bottom:
        1px solid #e5e7eb;
}}

td {{
    padding:
        13px;

    border-bottom:
        1px solid #eef2f6;

    font-size:
        13px;
}}

tr:hover {{
    background:
        #fafcff;
}}

.online {{
    color:
        #16a34a;

    font-weight:
        700;
}}

.offline {{
    color:
        #98a2b3;

    font-weight:
        600;
}}

.small-btn {{
    display:
        inline-block;

    text-decoration:
        none;

    background:
        #eef4ff;

    color:
        #2457d6;

    padding:
        7px 12px;

    border-radius:
        8px;

    font-size:
        12px;

    font-weight:
        700;
}}

.empty {{
    text-align:
        center;

    padding:
        30px;

    color:
        #98a2b3;
}}

.badge {{
    display:
        inline-block;

    padding:
        6px 10px;

    border-radius:
        999px;

    background:
        #eef4ff;

    color:
        #2457d6;

    font-size:
        11px;

    font-weight:
        700;
}}

@media (max-width: 1000px) {{

    .kpi-grid {{
        grid-template-columns:
            repeat(
                2,
                minmax(
                    0,
                    1fr
                )
            );
    }}

    .two-column {{
        grid-template-columns:
            1fr;
    }}

}}

@media (max-width: 650px) {{

    .kpi-grid {{
        grid-template-columns:
            1fr;
    }}

    .container {{
        padding:
            0 12px;
    }}

    .section {{
        padding:
            15px;

        overflow-x:
            auto;
    }}

    table {{
        min-width:
            850px;
    }}

}}

</style>

</head>

<body>


<div class="header">

    <div class="header-inner">

        <h1>
            🧠 Clinic Intelligence Command Center
        </h1>

        <p>
            Welcome,
            <strong>
                {html_escape(admin.name)}
            </strong>

            — Admin Intelligence Dashboard
        </p>

    </div>

</div>


<div class="container">


    <!-- KPI -->

    <div class="kpi-grid">

        <div class="kpi">

            <div class="kpi-label">
                Total Successful Logins
            </div>

            <div class="kpi-value">
                {summary["total_successful_logins"]}
            </div>

            <div class="kpi-sub">
                All recorded successful sessions
            </div>

        </div>


        <div class="kpi">

            <div class="kpi-label">
                Doctor Logins
            </div>

            <div class="kpi-value">
                {summary["doctor_total_logins"]}
            </div>

            <div class="kpi-sub">
                Successful doctor sessions
            </div>

        </div>


        <div class="kpi">

            <div class="kpi-label">
                Patient Logins
            </div>

            <div class="kpi-value">
                {summary["patient_total_logins"]}
            </div>

            <div class="kpi-sub">
                Successful patient sessions
            </div>

        </div>


        <div class="kpi">

            <div class="kpi-label">
                Today's Logins
            </div>

            <div class="kpi-value">
                {summary["today_logins"]}
            </div>

            <div class="kpi-sub">
                Successful logins today
            </div>

        </div>


        <div class="kpi">

            <div class="kpi-label">
                Last 7 Days
            </div>

            <div class="kpi-value">
                {summary["last_7_days_logins"]}
            </div>

            <div class="kpi-sub">
                Login activity
            </div>

        </div>


        <div class="kpi">

            <div class="kpi-label">
                Last 30 Days
            </div>

            <div class="kpi-value">
                {summary["last_30_days_logins"]}
            </div>

            <div class="kpi-sub">
                Login activity
            </div>

        </div>


        <div class="kpi">

            <div class="kpi-label">
                Doctors Online
            </div>

            <div class="kpi-value">
                {summary["online_doctors"]}
            </div>

            <div class="kpi-sub">
                Current session status
            </div>

        </div>


        <div class="kpi">

            <div class="kpi-label">
                Patients Online
            </div>

            <div class="kpi-value">
                {summary["online_patients"]}
            </div>

            <div class="kpi-sub">
                Current session status
            </div>

        </div>

    </div>


    <!-- LOGIN GRAPH -->

    <div class="section">

        <h2>
            📊 Login Activity — Last 30 Days
        </h2>

        <div class="section-description">
            Daily doctor, patient and total successful login activity.
        </div>

        <div class="chart-box">

            <canvas id="loginChart"></canvas>

        </div>

    </div>


    <!-- DOCTORS -->

    <div class="section">

        <h2>
            🧑‍⚕️ Doctor Login Intelligence
        </h2>

        <div class="section-description">
            Doctor-wise login count, session activity and last login/logout.
        </div>

        <table>

            <thead>

                <tr>

                    <th>Doctor</th>

                    <th>Email</th>

                    <th>Login Count</th>

                    <th>Last Login</th>

                    <th>Last Logout</th>

                    <th>Status</th>

                    <th>Details</th>

                </tr>

            </thead>

            <tbody>

                {doctor_rows}

            </tbody>

        </table>

    </div>


    <!-- PATIENTS -->

    <div class="section">

        <h2>
            👤 Patient Login Intelligence
        </h2>

        <div class="section-description">
            Patient-wise login count, session activity and last login/logout.
        </div>

        <table>

            <thead>

                <tr>

                    <th>Patient</th>

                    <th>Email</th>

                    <th>Login Count</th>

                    <th>Last Login</th>

                    <th>Last Logout</th>

                    <th>Status</th>

                    <th>Details</th>

                </tr>

            </thead>

            <tbody>

                {patient_rows}

            </tbody>

        </table>

    </div>


    <!-- TOP USERS -->

    <div class="two-column">


        <div class="section">

            <h2>
                🏆 Most Active Doctors
            </h2>

            <div class="section-description">
                Doctors with highest successful login activity.
            </div>

            <table>

                <thead>

                    <tr>

                        <th>Rank</th>

                        <th>Doctor</th>

                        <th>Logins</th>

                        <th>Last Login</th>

                    </tr>

                </thead>

                <tbody>

                    {top_doctor_rows}

                </tbody>

            </table>

        </div>


        <div class="section">

            <h2>
                🏆 Most Active Patients
            </h2>

            <div class="section-description">
                Patients with highest successful login activity.
            </div>

            <table>

                <thead>

                    <tr>

                        <th>Rank</th>

                        <th>Patient</th>

                        <th>Logins</th>

                        <th>Last Login</th>

                    </tr>

                </thead>

                <tbody>

                    {top_patient_rows}

                </tbody>

            </table>

        </div>


    </div>


    <!-- SECURITY -->

    <div class="section">

        <h2>
            🔐 Security
        </h2>

        <div class="section-description">

            <span class="badge">
                ADMIN ONLY
            </span>

            &nbsp;

            This dashboard is protected by the existing
            application login session.

            No admin ID is required in the URL.

        </div>

    </div>


</div>


<script>

const chartLabels =
    {chart_labels};

const doctorData =
    {doctor_chart};

const patientData =
    {patient_chart};

const totalData =
    {total_chart};


new Chart(
    document.getElementById("loginChart"),
    {{

        type: "line",

        data: {{

            labels: chartLabels,

            datasets: [

                {{
                    label: "Doctor Logins",
                    data: doctorData,
                    tension: 0.35,
                    borderWidth: 3,
                    fill: false
                }},

                {{
                    label: "Patient Logins",
                    data: patientData,
                    tension: 0.35,
                    borderWidth: 3,
                    fill: false
                }},

                {{
                    label: "Total Logins",
                    data: totalData,
                    tension: 0.35,
                    borderWidth: 3,
                    fill: false
                }}

            ]

        }},

        options: {{

            responsive: true,

            maintainAspectRatio: false,

            interaction: {{
                intersect: false,
                mode: "index"
            }},

            plugins: {{

                legend: {{
                    position: "bottom"
                }}

            }},

            scales: {{

                y: {{
                    beginAtZero: true,

                    ticks: {{
                        precision: 0
                    }}

                }}

            }}

        }}

    }}
);

</script>


</body>

</html>
"""


# ============================================================
# API: SUMMARY
# ============================================================

@router.get("/api/login-summary")
def login_summary_api(
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(
        request,
        db,
    )

    return get_login_summary(db)


# ============================================================
# API: DAILY ACTIVITY
# ============================================================

@router.get("/api/login-activity")
def login_activity_api(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
):
    require_admin(
        request,
        db,
    )

    days = max(
        1,
        min(days, 365),
    )

    return get_daily_login_activity(
        db,
        days=days,
    )


# ============================================================
# API: DOCTOR LOGINS
# ============================================================

@router.get("/api/doctors-logins")
def doctor_login_api(
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(
        request,
        db,
    )

    return get_doctor_login_analytics(db)


# ============================================================
# API: PATIENT LOGINS
# ============================================================

@router.get("/api/patients-logins")
def patient_login_api(
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(
        request,
        db,
    )

    return get_patient_login_analytics(db)


# ============================================================
# USER LOGIN HISTORY
# ============================================================

@router.get(
    "/user-history/{user_id}",
    response_class=HTMLResponse,
)


# ============================================================
# CLINIC MANAGEMENT PAGE
# ============================================================

@router.get(
    "/clinic-page",
    response_class=HTMLResponse,
)
def clinic_page(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Clinic management page.

    Uses the same admin session as Clinic Intelligence.
    """

    admin = get_current_admin(
        request,
        db,
    )

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    return f"""
    <!DOCTYPE html>
    <html lang="en">

    <head>
        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>Clinic Management</title>

        <style>

            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f4f7fb;
                color: #172033;
            }}

            .header {{
                background:
                    linear-gradient(
                        135deg,
                        #111827,
                        #243b53
                    );

                color: white;
                padding: 30px;
            }}

            .header-inner {{
                max-width: 1200px;
                margin: auto;
            }}

            .container {{
                max-width: 1200px;
                margin: 30px auto;
                padding: 0 20px;
            }}

            .grid {{
                display: grid;
                grid-template-columns:
                    repeat(
                        auto-fit,
                        minmax(220px, 1fr)
                    );

                gap: 20px;
            }}

            .card {{
                background: white;
                border-radius: 18px;
                padding: 25px;

                box-shadow:
                    0 8px 25px
                    rgba(15, 23, 42, .08);
            }}

            .icon {{
                font-size: 35px;
                margin-bottom: 12px;
            }}

            h1 {{
                margin: 0 0 8px;
            }}

            h2 {{
                margin-top: 0;
            }}

            p {{
                color: #667085;
                line-height: 1.6;
            }}

            .button {{
                display: inline-block;

                margin-top: 10px;

                padding: 10px 16px;

                border-radius: 9px;

                text-decoration: none;

                background: #2457d6;

                color: white;

                font-weight: 700;
            }}

            .button.secondary {{
                background: #eef4ff;
                color: #2457d6;
            }}

            .admin {{
                margin-bottom: 25px;
                padding: 15px 18px;

                background: #eef4ff;

                border-radius: 12px;

                color: #2457d6;
            }}

            @media (max-width: 650px) {{
                .container {{
                    padding: 0 12px;
                }}
            }}

        </style>
    </head>

    <body>

        <div class="header">

            <div class="header-inner">

                <h1>
                    🏥 Clinic Management
                </h1>

                <p>
                    Sanjeevani Smart Clinic
                </p>

            </div>

        </div>


        <div class="container">

            <div class="admin">
                Logged in as Admin:
                <strong>
                    {html_escape(admin.name)}
                </strong>
            </div>


            <div class="grid">

                <div class="card">

                    <div class="icon">
                        👨‍⚕️
                    </div>

                    <h2>
                        Staff
                    </h2>

                    <p>
                        Manage clinic staff,
                        roles and employee information.
                    </p>

                    <a
                        class="button"
                        href="/doctors/admin"
                    >
                        Doctor Management
                    </a>

                </div>


                <div class="card">

                    <div class="icon">
                        💰
                    </div>

                    <h2>
                        Salary
                    </h2>

                    <p>
                        Clinic salary and
                        staff payment management.
                    </p>

                    <a
                        class="button secondary"
                        href="/clinic"
                    >
                        Clinic Salary
                    </a>

                </div>


                <div class="card">

                    <div class="icon">
                        📦
                    </div>

                    <h2>
                        Inventory
                    </h2>

                    <p>
                        Track clinic items,
                        stock and inventory.
                    </p>

                    <a
                        class="button secondary"
                        href="/clinic"
                    >
                        Inventory
                    </a>

                </div>


                <div class="card">

                    <div class="icon">
                        🕐
                    </div>

                    <h2>
                        Clinic Timing
                    </h2>

                    <p>
                        Manage clinic working
                        days and operating hours.
                    </p>

                    <a
                        class="button secondary"
                        href="/clinic"
                    >
                        Timing
                    </a>

                </div>


                <div class="card">

                    <div class="icon">
                        📊
                    </div>

                    <h2>
                        Clinic Intelligence
                    </h2>

                    <p>
                        View doctor and patient
                        login analytics.
                    </p>

                    <a
                        class="button"
                        href="/clinic-intelligence/"
                    >
                        Open Analytics
                    </a>

                </div>


                <div class="card">

                    <div class="icon">
                        🔐
                    </div>

                    <h2>
                        Login Intelligence
                    </h2>

                    <p>
                        Check doctor and patient
                        login history.
                    </p>

                    <a
                        class="button"
                        href="/clinic-intelligence/"
                    >
                        Open Login Analytics
                    </a>

                </div>

            </div>

        </div>

    </body>

    </html>
    """
def user_history_page(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    admin = get_current_admin(
        request,
        db,
    )

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

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

    if user.role not in {
        "doctor",
        "patient",
    }:
        raise HTTPException(
            status_code=400,
            detail="History available for doctors and patients.",
        )

    history = get_login_history(
        db,
        user_id=user_id,
        limit=200,
    )

    rows = ""

    for item in history:

        result = (
            '<span class="success">SUCCESS</span>'
            if item["is_successful"]
            else '<span class="failed">FAILED</span>'
        )

        rows += f"""
        <tr>

            <td>
                {safe_datetime(item["login_at"])}
            </td>

            <td>
                {safe_datetime(item["logout_at"])}
            </td>

            <td>
                {result}
            </td>

        </tr>
        """

    if not rows:

        rows = """
        <tr>
            <td colspan="3">
                No login history found.
            </td>
        </tr>
        """

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
Login History
</title>

<style>

body {{
    margin: 0;

    padding: 30px;

    font-family:
        Arial,
        sans-serif;

    background:
        #f4f7fb;

    color:
        #172033;
}}

.card {{
    max-width:
        1000px;

    margin:
        auto;

    background:
        white;

    padding:
        25px;

    border-radius:
        18px;

    box-shadow:
        0 8px 30px
        rgba(
            0,
            0,
            0,
            .07
        );
}}

h1 {{
    margin-top:
        0;
}}

.info {{
    background:
        #f8fafc;

    padding:
        15px;

    border-radius:
        12px;

    margin-bottom:
        20px;

    line-height:
        1.8;
}}

table {{
    width:
        100%;

    border-collapse:
        collapse;
}}

th,
td {{
    text-align:
        left;

    padding:
        13px;

    border-bottom:
        1px solid #e5e7eb;
}}

th {{
    background:
        #f8fafc;
}}

.success {{
    color:
        #16a34a;

    font-weight:
        bold;
}}

.failed {{
    color:
        #dc2626;

    font-weight:
        bold;
}}

.back {{
    display:
        inline-block;

    margin-top:
        20px;

    padding:
        10px 15px;

    background:
        #eef4ff;

    color:
        #2457d6;

    text-decoration:
        none;

    border-radius:
        8px;

    font-weight:
        bold;
}}

</style>

</head>

<body>

<div class="card">

<h1>
🔐 Login History
</h1>

<div class="info">

<strong>
{html_escape(user.name)}
</strong>

<br>

Email:
{html_escape(user.email)}

<br>

Role:
<strong>
{html_escape(user.role)}
</strong>

<br>

Current status:
<strong>
{"ONLINE" if user.is_logged_in else "OFFLINE"}
</strong>

<br>

Last login:
<strong>
{safe_datetime(user.last_login_at)}
</strong>

<br>

Last logout:
<strong>
{safe_datetime(user.last_logout_at)}
</strong>

</div>


<table>

<thead>

<tr>

<th>
Login Time
</th>

<th>
Logout Time
</th>

<th>
Result
</th>

</tr>

</thead>

<tbody>

{rows}

</tbody>

</table>


<a
    class="back"
    href="/clinic-intelligence/"
>
← Back to Command Center
</a>


</div>

</body>

</html>
"""


# ============================================================
# USER HISTORY API
# ============================================================

@router.get(
    "/api/user-history/{user_id}"
)
def user_history_api(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(
        request,
        db,
    )

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

    return get_login_history(
        db,
        user_id=user_id,
        limit=200,
    )

