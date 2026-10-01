from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.database.models import User
from src.pharmacy.models import PharmacyStaffPermission
from src.security import hash_password


router = APIRouter(
    prefix="/role-management",
    tags=["Role Management"],
)


PHARMACY_PERMISSIONS = [
    "medicine_manage",
    "stock_manage",
    "supplier_manage",
    "purchase_manage",
    "order_manage",
    "billing_manage",
    "reports_view",
    "prescription_verify",
]


def current_user(request: Request, db: Session):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Login required",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        request.session.clear()
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    return user


def require_admin(request: Request, db: Session):
    user = current_user(request, db)

    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return user


def get_staff_permission(
    db: Session,
    user_id: int,
):
    permission = (
        db.query(PharmacyStaffPermission)
        .filter(
            PharmacyStaffPermission.user_id == user_id
        )
        .first()
    )

    if not permission:
        permission = PharmacyStaffPermission(
            user_id=user_id,
            medicine_manage=False,
            stock_manage=False,
            supplier_manage=False,
            purchase_manage=False,
            order_manage=False,
            billing_manage=False,
            reports_view=False,
            prescription_verify=False,
        )

        db.add(permission)
        db.commit()
        db.refresh(permission)

    return permission


def has_permission(
    db: Session,
    user: User,
    permission_name: str,
):
    if user.role == "admin":
        return True

    if user.role != "pharmacy_staff":
        return False

    if permission_name not in PHARMACY_PERMISSIONS:
        return False

    permission = get_staff_permission(
        db,
        user.id,
    )

    return bool(
        getattr(
            permission,
            permission_name,
            False,
        )
    )


@router.get(
    "/admin",
    response_class=HTMLResponse,
)
def admin_role_management(
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(request, db)

    staff_users = (
        db.query(User)
        .filter(
            User.role == "pharmacy_staff"
        )
        .order_by(User.id.desc())
        .all()
    )

    rows = ""

    for staff in staff_users:
        permission = get_staff_permission(
            db,
            staff.id,
        )

        enabled_permissions = []

        for permission_name in PHARMACY_PERMISSIONS:
            if getattr(
                permission,
                permission_name,
                False,
            ):
                enabled_permissions.append(
                    permission_name
                )

        permissions_text = (
            ", ".join(enabled_permissions)
            if enabled_permissions
            else "No permissions"
        )

        status = (
            "Active"
            if getattr(staff, "is_active", True)
            else "Inactive"
        )

        action = (
            "Deactivate"
            if getattr(staff, "is_active", True)
            else "Activate"
        )

        rows += f"""
        <tr>
            <td>{staff.id}</td>
            <td>{staff.name}</td>
            <td>{staff.email}</td>
            <td>{status}</td>
            <td>{permissions_text}</td>
            <td>
                <a href="/role-management/admin/{staff.id}/permissions">
                    Manage Permissions
                </a>

                <form
                    method="post"
                    action="/role-management/admin/{staff.id}/toggle"
                    style="display:inline;"
                >
                    <button type="submit">
                        {action}
                    </button>
                </form>
            </td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pharmacy Staff Management</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 30px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
            }}

            th,
            td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: left;
            }}

            th {{
                background: #f2f2f2;
            }}

            button,
            a {{
                padding: 7px 10px;
                margin: 3px;
            }}
        </style>
    </head>

    <body>

        <h1>Pharmacy Staff Management</h1>

        <p>
            <a href="/role-management/admin/create">
                Create Pharmacy Staff
            </a>
        </p>

        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Permissions</th>
                    <th>Actions</th>
                </tr>
            </thead>

            <tbody>
                {rows}
            </tbody>
        </table>

    </body>
    </html>
    """


@router.get(
    "/admin/create",
    response_class=HTMLResponse,
)
def create_staff_page(
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(request, db)

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Create Pharmacy Staff</title>
    </head>

    <body>

        <h1>Create Pharmacy Staff</h1>

        <form
            method="post"
            action="/role-management/admin/create"
        >

            <label>Name</label>
            <br>
            <input
                type="text"
                name="name"
                required
            >

            <br><br>

            <label>Email</label>
            <br>
            <input
                type="email"
                name="email"
                required
            >

            <br><br>

            <label>Password</label>
            <br>
            <input
                type="password"
                name="password"
                required
            >

            <br><br>

            <button type="submit">
                Create Pharmacy Staff
            </button>

        </form>

    </body>
    </html>
    """


@router.post(
    "/admin/create",
)
def create_staff(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    require_admin(request, db)

    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists",
        )

    staff = User(
        name=name,
        email=email,
        password=hash_password(password),
        role="pharmacy_staff",
    )

    db.add(staff)
    db.commit()
    db.refresh(staff)

    permission = PharmacyStaffPermission(
        user_id=staff.id,
        medicine_manage=False,
        stock_manage=False,
        supplier_manage=False,
        purchase_manage=False,
        order_manage=False,
        billing_manage=False,
        reports_view=False,
        prescription_verify=False,
    )

    db.add(permission)
    db.commit()

    return RedirectResponse(
        url="/role-management/admin",
        status_code=303,
    )


@router.post(
    "/admin/{user_id}/toggle",
)
def toggle_staff(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(request, db)

    staff = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.role == "pharmacy_staff",
        )
        .first()
    )

    if not staff:
        raise HTTPException(
            status_code=404,
            detail="Pharmacy staff not found",
        )

    staff.is_active = not getattr(
        staff,
        "is_active",
        True,
    )

    db.commit()

    return RedirectResponse(
        url="/role-management/admin",
        status_code=303,
    )


@router.get(
    "/admin/{user_id}/permissions",
    response_class=HTMLResponse,
)
def manage_permissions(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(request, db)

    staff = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.role == "pharmacy_staff",
        )
        .first()
    )

    if not staff:
        raise HTTPException(
            status_code=404,
            detail="Pharmacy staff not found",
        )

    permission = get_staff_permission(
        db,
        staff.id,
    )

    checkboxes = ""

    for permission_name in PHARMACY_PERMISSIONS:
        checked = (
            "checked"
            if getattr(
                permission,
                permission_name,
                False,
            )
            else ""
        )

        checkboxes += f"""
        <label>
            <input
                type="checkbox"
                name="permissions"
                value="{permission_name}"
                {checked}
            >
            {permission_name}
        </label>
        <br>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Manage Permissions</title>
    </head>

    <body>

        <h1>Manage Pharmacy Staff Permissions</h1>

        <p>
            Staff:
            <strong>{staff.name}</strong>
        </p>

        <form
            method="post"
            action="/role-management/admin/{staff.id}/permissions"
        >

            {checkboxes}

            <br>

            <button type="submit">
                Save Permissions
            </button>

        </form>

    </body>
    </html>
    """


@router.post(
    "/admin/{user_id}/permissions",
)
async def save_permissions(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    require_admin(request, db)

    staff = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.role == "pharmacy_staff",
        )
        .first()
    )

    if not staff:
        raise HTTPException(
            status_code=404,
            detail="Pharmacy staff not found",
        )

    form = await request.form()

    selected_permissions = form.getlist(
        "permissions"
    )

    permission = get_staff_permission(
        db,
        staff.id,
    )

    for permission_name in PHARMACY_PERMISSIONS:
        setattr(
            permission,
            permission_name,
            permission_name in selected_permissions,
        )

    db.commit()

    return RedirectResponse(
        url="/role-management/admin",
        status_code=303,
    )


@router.get(
    "/check/{permission_name}",
)
def check_permission(
    permission_name: str,
    request: Request,
    db: Session = Depends(get_db),
):
    user = current_user(
        request,
        db,
    )

    allowed = has_permission(
        db,
        user,
        permission_name,
    )

    return {
        "permission": permission_name,
        "allowed": allowed,
    }