from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.database.models import User, LoginHistory


def get_login_summary(db: Session):
    """
    Overall login statistics.
    """

    today = date.today()

    start_today = datetime.combine(today, datetime.min.time())
    start_7_days = datetime.now() - timedelta(days=7)
    start_30_days = datetime.now() - timedelta(days=30)

    total_successful = (
        db.query(func.count(LoginHistory.id))
        .filter(LoginHistory.is_successful == True)
        .scalar()
        or 0
    )

    doctor_total = (
        db.query(func.count(LoginHistory.id))
        .join(User, User.id == LoginHistory.user_id)
        .filter(
            User.role == "doctor",
            LoginHistory.is_successful == True,
        )
        .scalar()
        or 0
    )

    patient_total = (
        db.query(func.count(LoginHistory.id))
        .join(User, User.id == LoginHistory.user_id)
        .filter(
            User.role == "patient",
            LoginHistory.is_successful == True,
        )
        .scalar()
        or 0
    )

    today_total = (
        db.query(func.count(LoginHistory.id))
        .filter(
            LoginHistory.is_successful == True,
            LoginHistory.login_at >= start_today,
        )
        .scalar()
        or 0
    )

    last_7_days = (
        db.query(func.count(LoginHistory.id))
        .filter(
            LoginHistory.is_successful == True,
            LoginHistory.login_at >= start_7_days,
        )
        .scalar()
        or 0
    )

    last_30_days = (
        db.query(func.count(LoginHistory.id))
        .filter(
            LoginHistory.is_successful == True,
            LoginHistory.login_at >= start_30_days,
        )
        .scalar()
        or 0
    )

    online_doctors = (
        db.query(func.count(User.id))
        .filter(
            User.role == "doctor",
            User.is_logged_in == True,
        )
        .scalar()
        or 0
    )

    online_patients = (
        db.query(func.count(User.id))
        .filter(
            User.role == "patient",
            User.is_logged_in == True,
        )
        .scalar()
        or 0
    )

    return {
        "total_successful_logins": total_successful,
        "doctor_total_logins": doctor_total,
        "patient_total_logins": patient_total,
        "today_logins": today_total,
        "last_7_days_logins": last_7_days,
        "last_30_days_logins": last_30_days,
        "online_doctors": online_doctors,
        "online_patients": online_patients,
    }


def get_doctor_login_analytics(db: Session):
    """
    Doctor-wise login analytics.
    """

    rows = (
        db.query(
            User.id,
            User.name,
            User.email,
            User.is_logged_in,
            User.last_login_at,
            User.last_logout_at,
            func.count(LoginHistory.id).label("login_count"),
        )
        .outerjoin(
            LoginHistory,
            LoginHistory.user_id == User.id,
        )
        .filter(User.role == "doctor")
        .group_by(
            User.id,
            User.name,
            User.email,
            User.is_logged_in,
            User.last_login_at,
            User.last_logout_at,
        )
        .order_by(
            func.count(LoginHistory.id).desc(),
            User.name.asc(),
        )
        .all()
    )

    result = []

    for row in rows:
        result.append(
            {
                "user_id": row.id,
                "name": row.name,
                "email": row.email,
                "login_count": int(row.login_count or 0),
                "last_login": row.last_login_at,
                "last_logout": row.last_logout_at,
                "is_online": bool(row.is_logged_in),
            }
        )

    return result


def get_patient_login_analytics(db: Session):
    """
    Patient-wise login analytics.
    """

    rows = (
        db.query(
            User.id,
            User.name,
            User.email,
            User.is_logged_in,
            User.last_login_at,
            User.last_logout_at,
            func.count(LoginHistory.id).label("login_count"),
        )
        .outerjoin(
            LoginHistory,
            LoginHistory.user_id == User.id,
        )
        .filter(User.role == "patient")
        .group_by(
            User.id,
            User.name,
            User.email,
            User.is_logged_in,
            User.last_login_at,
            User.last_logout_at,
        )
        .order_by(
            func.count(LoginHistory.id).desc(),
            User.name.asc(),
        )
        .all()
    )

    result = []

    for row in rows:
        result.append(
            {
                "user_id": row.id,
                "name": row.name,
                "email": row.email,
                "login_count": int(row.login_count or 0),
                "last_login": row.last_login_at,
                "last_logout": row.last_logout_at,
                "is_online": bool(row.is_logged_in),
            }
        )

    return result


def get_login_history(
    db: Session,
    user_id: int | None = None,
    role: str | None = None,
    limit: int = 100,
):
    """
    Detailed login history.

    Can filter by:
    - specific user
    - doctor/patient role
    """

    query = (
        db.query(
            LoginHistory.id,
            LoginHistory.user_id,
            LoginHistory.login_at,
            LoginHistory.logout_at,
            LoginHistory.is_successful,
            User.name,
            User.email,
            User.role,
        )
        .join(
            User,
            User.id == LoginHistory.user_id,
        )
    )

    if user_id is not None:
        query = query.filter(LoginHistory.user_id == user_id)

    if role is not None:
        query = query.filter(User.role == role)

    rows = (
        query
        .order_by(LoginHistory.login_at.desc())
        .limit(limit)
        .all()
    )

    result = []

    for row in rows:
        result.append(
            {
                "history_id": row.id,
                "user_id": row.user_id,
                "name": row.name,
                "email": row.email,
                "role": row.role,
                "login_at": row.login_at,
                "logout_at": row.logout_at,
                "is_successful": bool(row.is_successful),
            }
        )

    return result


def get_daily_login_activity(
    db: Session,
    days: int = 30,
):
    """
    Daily doctor/patient/total login activity.
    """

    days = max(1, min(days, 365))

    start_date = date.today() - timedelta(days=days - 1)
    start_datetime = datetime.combine(
        start_date,
        datetime.min.time(),
    )

    rows = (
        db.query(
            LoginHistory.login_at,
            User.role,
        )
        .join(
            User,
            User.id == LoginHistory.user_id,
        )
        .filter(
            LoginHistory.is_successful == True,
            LoginHistory.login_at >= start_datetime,
        )
        .order_by(LoginHistory.login_at.asc())
        .all()
    )

    activity = {}

    for i in range(days):
        current_date = start_date + timedelta(days=i)

        activity[current_date.isoformat()] = {
            "date": current_date.isoformat(),
            "doctor_logins": 0,
            "patient_logins": 0,
            "admin_logins": 0,
        
            "total_logins": 0,
        }

    for login_at, role in rows:
        if not login_at:
            continue

        key = login_at.date().isoformat()

        if key not in activity:
            continue

        activity[key]["total_logins"] += 1

        if role == "doctor":
            activity[key]["doctor_logins"] += 1

        elif role == "patient":
            activity[key]["patient_logins"] += 1

        elif role == "admin":
            activity[key]["admin_logins"] += 1
            
            return list(activity.values())


def get_top_users_by_login(
    db: Session,
    role: str,
    limit: int = 10,
):
    """
    Most frequently logged-in users for a role.
    """

    rows = (
        db.query(
            User.id,
            User.name,
            User.email,
            func.count(LoginHistory.id).label("login_count"),
            func.max(LoginHistory.login_at).label("last_login"),
        )
        .join(
            LoginHistory,
            LoginHistory.user_id == User.id,
        )
        .filter(
            User.role == role,
            LoginHistory.is_successful == True,
        )
        .group_by(
            User.id,
            User.name,
            User.email,
        )
        .order_by(
            func.count(LoginHistory.id).desc()
        )
        .limit(limit)
        .all()
    )

    return [
        {
            "user_id": row.id,
            "name": row.name,
            "email": row.email,
            "login_count": int(row.login_count or 0),
            "last_login": row.last_login,
        }
        for row in rows
    ]