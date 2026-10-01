from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.database.models import User, LoginHistory
from src.security import hash_password, verify_password
from src.notifications.services import notify, send_email


def require_admin(
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please login first"
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        request.session.clear()

        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return user


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# =========================================================
# REGISTER
# =========================================================

@router.post("/register")
def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    mobile: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Remove accidental spaces
    name = name.strip()
    email = email.strip().lower()
    mobile = mobile.strip()

    # Check duplicate email or mobile
    existing_user = (
        db.query(User)
        .filter(
            (User.email == email) |
            (User.mobile == mobile)
        )
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email or mobile already registered"
        )

    # Create patient account
    new_user = User(
        name=name,
        email=email,
        mobile=mobile,
        password_hash=hash_password(password),
        role="patient",
        is_active=True,
        is_logged_in=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # =====================================================
    # AUTOMATIC LOGIN SESSION
    # =====================================================

    request.session["user_id"] = new_user.id
    request.session["role"] = new_user.role

    # =====================================================
    # LOGIN HISTORY
    # =====================================================

    login_record = LoginHistory(
        user_id=new_user.id,
        login_at=datetime.now(),
        is_successful=True
    )

    db.add(login_record)
    db.commit()

    # =====================================================
    # WELCOME NOTIFICATION
    # =====================================================

    try:
        notify(
            db,
            new_user.id,
            "Welcome to Sanjeevani Smart Clinic",
            "Your account has been created successfully."
        )
        db.commit()

    except Exception:
        db.rollback()

    # =====================================================
    # WELCOME EMAIL
    # =====================================================

    try:
        send_email(
            new_user,
            "Welcome to Sanjeevani Smart Clinic",
            "Your registration was successful."
        )

    except Exception:
        pass

    # =====================================================
    # IMPORTANT:
    # CREATE ACCOUNT -> AUTOMATICALLY OPEN PROFILE
    # =====================================================

    return RedirectResponse(
        url="/profile",
        status_code=303
    )


# =========================================================
# LOGIN
# =========================================================

@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Clean email
    email = email.strip().lower()

    # Find user
    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    # User not found
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Account inactive
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive"
        )

    # Verify password
    if not verify_password(
        password,
        user.password_hash
    ):
        failed_login = LoginHistory(
            user_id=user.id,
            is_successful=False
        )

        db.add(failed_login)
        db.commit()

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Current time
    current_time = datetime.now()

    # Update user login information
    user.last_login_at = current_time
    user.is_logged_in = True

    # Create session
    request.session["user_id"] = user.id
    request.session["role"] = user.role

    # Successful login history
    login_record = LoginHistory(
        user_id=user.id,
        login_at=current_time,
        is_successful=True
    )

    db.add(login_record)
    db.commit()

    # Open profile after normal login
    return RedirectResponse(
        url="/profile",
        status_code=303
    )


# =========================================================
# LOGOUT
# =========================================================

@router.get("/logout")
def logout(
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")

    if user_id:

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if user:

            current_time = datetime.now()

            user.last_logout_at = current_time
            user.is_logged_in = False

            # Find latest active login record
            login_record = (
                db.query(LoginHistory)
                .filter(
                    LoginHistory.user_id == user_id,
                    LoginHistory.logout_at.is_(None),
                    LoginHistory.is_successful == True
                )
                .order_by(
                    LoginHistory.login_at.desc()
                )
                .first()
            )

            if login_record:
                login_record.logout_at = current_time

            db.commit()

    # Clear session
    request.session.clear()

    # Return to login page
    return RedirectResponse(
        url="/login",
        status_code=303
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@router.get("/admin")
def admin_dashboard(
    admin_user: User = Depends(require_admin)
):
    return {
        "message": "Welcome to Admin Dashboard",
        "admin_id": admin_user.id,
        "admin_name": admin_user.name,
        "role": admin_user.role
    }