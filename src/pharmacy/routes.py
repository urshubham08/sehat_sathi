from datetime import date, datetime
from decimal import Decimal
from html import escape
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.database.database import get_db, engine
from src.database.models import User
from src.security import hash_password, verify_password

from .models import (
    PharmacyStaffPermission,
    PharmacyMedicine,
    PharmacyBatch,
    PharmacySupplier,
    PharmacyPurchase,
    PharmacyOrder,
    PharmacySale,
    PharmacySaleItem,
    PharmacyStockMovement,
)

# Create only pharmacy tables that do not already exist.
# Existing tables are not modified by create_all().
from . import models as pharmacy_models  # noqa: F401
from src.database.database import Base

Base.metadata.create_all(bind=engine)


router = APIRouter(
    prefix="/pharmacy",
    tags=["Pharmacy"],
)


# ============================================================
# HELPERS
# ============================================================

def esc(value):
    return escape(str(value)) if value is not None else ""


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


def require_admin(
    request: Request,
    db: Session,
):
    user = get_current_user(request, db)

    if not user or user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )

    return user


def get_staff_permission(
    user_id: int,
    db: Session,
):
    permission = (
        db.query(PharmacyStaffPermission)
        .filter(
            PharmacyStaffPermission.user_id == user_id
        )
        .first()
    )

    return permission


def require_pharmacy_access(
    request: Request,
    db: Session,
    permission_name: str | None = None,
):
    user = get_current_user(request, db)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Login required.",
        )

    if user.role == "admin":
        return user

    if user.role != "pharmacy_staff":
        raise HTTPException(
            status_code=403,
            detail="Pharmacy access required.",
        )

    permissions = get_staff_permission(
        user.id,
        db,
    )

    if not permissions:
        raise HTTPException(
            status_code=403,
            detail="Pharmacy permissions are not assigned.",
        )

    if permission_name:
        allowed = getattr(
            permissions,
            permission_name,
            False,
        )

        if not allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Permission required: {permission_name}",
            )

    return user


def page(
    title: str,
    body: str,
):
    return HTMLResponse(
        content=f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{esc(title)}</title>

<style>
* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f5f7fb;
    color: #172033;
}}

.nav {{
    background: #0f766e;
    color: white;
    padding: 16px 24px;
}}

.nav a {{
    color: white;
    text-decoration: none;
    margin-right: 18px;
    font-weight: 600;
}}

.container {{
    max-width: 1200px;
    margin: 30px auto;
    padding: 0 18px;
}}

.card {{
    background: white;
    padding: 22px;
    border-radius: 14px;
    box-shadow: 0 5px 20px rgba(0,0,0,.07);
    margin-bottom: 20px;
}}

.grid {{
    display: grid;
    grid-template-columns:
        repeat(auto-fit,minmax(220px,1fr));
    gap: 18px;
}}

.stat {{
    background: white;
    padding: 22px;
    border-radius: 14px;
    box-shadow: 0 5px 20px rgba(0,0,0,.06);
}}

.stat h2 {{
    margin: 5px 0;
    color: #0f766e;
}}

input, select, textarea {{
    width: 100%;
    padding: 11px;
    margin: 7px 0 14px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
}}

button, .btn {{
    display: inline-block;
    border: none;
    background: #0f766e;
    color: white;
    padding: 10px 15px;
    border-radius: 8px;
    text-decoration: none;
    cursor: pointer;
}}

.btn.secondary {{
    background: #475569;
}}

.btn.danger {{
    background: #dc2626;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th, td {{
    padding: 11px;
    border-bottom: 1px solid #e5e7eb;
    text-align: left;
}}

th {{
    background: #f1f5f9;
}}

.badge {{
    display: inline-block;
    padding: 5px 9px;
    border-radius: 20px;
    background: #dcfce7;
    color: #166534;
}}

.warn {{
    background: #fef3c7;
    color: #92400e;
}}

.danger {{
    background: #fee2e2;
    color: #991b1b;
}}

label {{
    font-weight: 600;
}}

@media(max-width:700px) {{
    table {{
        font-size: 13px;
    }}

    .container {{
        margin-top: 15px;
    }}
}}
</style>
</head>

<body>

<div class="nav">
    <a href="/pharmacy/">🏪 Pharmacy</a>
    <a href="/pharmacy/medicines">💊 Medicines</a>
    <a href="/pharmacy/batches">📦 Batches</a>
    <a href="/pharmacy/suppliers">🚚 Suppliers</a>
    <a href="/pharmacy/purchases">🛒 Purchases</a>
    <a href="/pharmacy/orders">📋 Orders</a>
    <a href="/pharmacy/billing">🧾 Billing</a>
    <a href="/pharmacy/reports">📊 Reports</a>
</div>

<div class="container">
{body}
</div>

</body>
</html>
"""
    )


# ============================================================
# PHARMACY LANDING / DASHBOARD
# ============================================================

@router.get(
    "/",
    response_class=HTMLResponse,
)
def pharmacy_dashboard(
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        user = get_current_user(request, db)

        if not user:
            return RedirectResponse(
                "/pharmacy/login",
                status_code=303,
            )

        if user.role == "admin":
            return RedirectResponse(
                "/pharmacy/admin",
                status_code=303,
            )

        if user.role != "pharmacy_staff":
            raise HTTPException(
                status_code=403,
                detail="Pharmacy access required.",
            )

        permission = get_staff_permission(
            user.id,
            db,
        )

        if not permission:
            raise HTTPException(
                status_code=403,
                detail="No pharmacy permissions assigned.",
            )

        total_medicines = (
            db.query(PharmacyMedicine)
            .filter(
                PharmacyMedicine.is_active == True
            )
            .count()
        )

        total_orders = db.query(
            PharmacyOrder
        ).count()

        pending_orders = (
            db.query(PharmacyOrder)
            .filter(
                PharmacyOrder.status == "pending"
            )
            .count()
        )

        low_stock = []

        medicines = (
            db.query(PharmacyMedicine)
            .filter(
                PharmacyMedicine.is_active == True
            )
            .all()
        )

        for medicine in medicines:
            quantity = sum(
                int(batch.quantity or 0)
                for batch in db.query(PharmacyBatch)
                .filter(
                    PharmacyBatch.medicine_id == medicine.id,
                    PharmacyBatch.is_active == True,
                )
                .all()
            )

            if quantity <= medicine.reorder_level:
                low_stock.append(
                    (medicine, quantity)
                )

        low_stock_html = ""

        for medicine, quantity in low_stock:
            low_stock_html += f"""
            <tr>
                <td>{esc(medicine.name)}</td>
                <td>{quantity}</td>
                <td>{medicine.reorder_level}</td>
            </tr>
            """

        if not low_stock_html:
            low_stock_html = """
            <tr>
                <td colspan="3">
                    No low-stock medicines.
                </td>
            </tr>
            """

        body = f"""
        <h1>🏪 Pharmacy Dashboard</h1>

        <p>
            Welcome,
            <strong>{esc(user.name)}</strong>
        </p>

        <div class="grid">

            <div class="stat">
                <h3>Medicines</h3>
                <h2>{total_medicines}</h2>
            </div>

            <div class="stat">
                <h3>Total Orders</h3>
                <h2>{total_orders}</h2>
            </div>

            <div class="stat">
                <h3>Pending Orders</h3>
                <h2>{pending_orders}</h2>
            </div>

            <div class="stat">
                <h3>Your Role</h3>
                <h2>Pharmacy Staff</h2>
            </div>

        </div>

        <div class="card">

            <h2>Assigned Permissions</h2>

            <ul>
                <li>Medicine Management:
                    {"✅" if permission.medicine_manage else "❌"}
                </li>

                <li>Stock Management:
                    {"✅" if permission.stock_manage else "❌"}
                </li>

                <li>Supplier Management:
                    {"✅" if permission.supplier_manage else "❌"}
                </li>

                <li>Purchase Management:
                    {"✅" if permission.purchase_manage else "❌"}
                </li>

                <li>Order Management:
                    {"✅" if permission.order_manage else "❌"}
                </li>

                <li>Billing:
                    {"✅" if permission.billing_manage else "❌"}
                </li>

                <li>Reports:
                    {"✅" if permission.reports_view else "❌"}
                </li>

                <li>Prescription Verification:
                    {"✅" if permission.prescription_verify else "❌"}
                </li>
            </ul>

        </div>

        <div class="card">

            <h2>⚠️ Low Stock</h2>

            <table>
                <tr>
                    <th>Medicine</th>
                    <th>Current Stock</th>
                    <th>Reorder Level</th>
                </tr>

                {low_stock_html}
            </table>

        </div>
        """

        return page(
            "Pharmacy Dashboard",
            body,
        )

    except HTTPException:
        raise


# ============================================================
# PHARMACY STAFF LOGIN
# ============================================================

@router.get(
    "/login",
    response_class=HTMLResponse,
)
def pharmacy_login_page():

    return HTMLResponse(
        """
<!DOCTYPE html>
<html>
<head>
<title>Pharmacy Staff Login</title>

<style>
body {
    font-family: Arial;
    background: #f5f7fb;
    padding: 40px;
}

.box {
    max-width: 450px;
    margin: auto;
    background: white;
    padding: 30px;
    border-radius: 15px;
    box-shadow: 0 5px 25px rgba(0,0,0,.08);
}

input {
    width: 100%;
    padding: 12px;
    margin: 10px 0;
    box-sizing: border-box;
}

button {
    width: 100%;
    padding: 12px;
    background: #0f766e;
    color: white;
    border: none;
    border-radius: 8px;
}
</style>

</head>

<body>

<div class="box">

<h1>🏪 Pharmacy Staff Login</h1>

<form method="post">

<label>Email</label>
<input
    type="email"
    name="email"
    required
>

<label>Password</label>
<input
    type="password"
    name="password"
    required
>

<button type="submit">
    Login
</button>

</form>

<br>

<a href="/login">
    ← Other Login Options
</a>

</div>

</body>
</html>
"""
    )


@router.post(
    "/login",
    response_class=HTMLResponse,
)
def pharmacy_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):

    user = (
        db.query(User)
        .filter(
            User.email == email.strip().lower(),
            User.role == "pharmacy_staff",
            User.is_active == True,
        )
        .first()
    )

    if not user or not verify_password(
        password,
        user.password_hash,
    ):
        return HTMLResponse(
            """
            <h2>Invalid pharmacy staff login.</h2>
            <a href="/pharmacy/login">
                Try again
            </a>
            """,
            status_code=401,
        )

    permission = get_staff_permission(
        user.id,
        db,
    )

    if not permission:
        return HTMLResponse(
            """
            <h2>Pharmacy permissions are not assigned.</h2>
            <p>Please contact the administrator.</p>
            """,
            status_code=403,
        )

    user.last_login_at = datetime.utcnow()
    user.is_logged_in = True

    db.commit()

    request.session.clear()

    request.session["user_id"] = user.id
    request.session["role"] = "pharmacy_staff"

    return RedirectResponse(
        "/pharmacy/",
        status_code=303,
    )


# ============================================================
# ADMIN - PHARMACY STAFF MANAGEMENT
# ============================================================

@router.get(
    "/admin",
    response_class=HTMLResponse,
)
def pharmacy_admin(
    request: Request,
    db: Session = Depends(get_db),
):

    require_admin(
        request,
        db,
    )

    staff = (
        db.query(User)
        .filter(
            User.role == "pharmacy_staff"
        )
        .order_by(User.id.desc())
        .all()
    )

    rows = ""

    for user in staff:

        p = get_staff_permission(
            user.id,
            db,
        )

        rows += f"""
        <tr>

            <td>{user.id}</td>

            <td>{esc(user.name)}</td>

            <td>{esc(user.email)}</td>

            <td>
                {"Active" if user.is_active else "Inactive"}
            </td>

            <td>
                <a
                    class="btn"
                    href="/pharmacy/admin/staff/{user.id}"
                >
                    Permissions
                </a>
            </td>

        </tr>
        """

    body = f"""
    <h1>🏪 Pharmacy Administration</h1>

    <div class="card">

        <h2>Create Pharmacy Staff</h2>

        <form method="post"
              action="/pharmacy/admin/staff/create">

            <label>Name</label>
            <input
                name="name"
                required
                maxlength="100"
            >

            <label>Email</label>
            <input
                type="email"
                name="email"
                required
                maxlength="150"
            >

            <label>Mobile</label>
            <input
                name="mobile"
                required
                maxlength="20"
            >

            <label>Password</label>
            <input
                type="password"
                name="password"
                required
                minlength="8"
            >

            <button type="submit">
                Create Pharmacy Staff
            </button>

        </form>

    </div>

    <div class="card">

        <h2>Pharmacy Staff</h2>

        <table>

            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Email</th>
                <th>Status</th>
                <th>Permissions</th>
            </tr>

            {rows}

        </table>

    </div>
    """

    return page(
        "Pharmacy Administration",
        body,
    )


@router.post(
    "/admin/staff/create",
)
def create_pharmacy_staff(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    mobile: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):

    require_admin(
        request,
        db,
    )

    email = email.strip().lower()

    existing = (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already exists.",
        )

    user = User(
        name=name.strip(),
        email=email,
        mobile=mobile.strip(),
        password_hash=hash_password(password),
        role="pharmacy_staff",
        is_active=True,
    )

    db.add(user)
    db.flush()

    permission = PharmacyStaffPermission(
        user_id=user.id,
        medicine_manage=True,
        stock_manage=True,
        supplier_manage=False,
        purchase_manage=False,
        order_manage=True,
        billing_manage=False,
        reports_view=False,
        prescription_verify=True,
    )

    db.add(permission)

    db.commit()

    return RedirectResponse(
        "/pharmacy/admin",
        status_code=303,
    )


# ============================================================
# ADMIN - STAFF PERMISSIONS
# ============================================================

@router.get(
    "/admin/staff/{user_id}",
    response_class=HTMLResponse,
)
def staff_permissions_page(
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
        .filter(
            User.id == user_id,
            User.role == "pharmacy_staff",
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Pharmacy staff not found.",
        )

    permission = get_staff_permission(
        user.id,
        db,
    )

    if not permission:
        permission = PharmacyStaffPermission(
            user_id=user.id
        )

        db.add(permission)
        db.commit()
        db.refresh(permission)

    permission_fields = [
        (
            "medicine_manage",
            "Medicine Management",
        ),
        (
            "stock_manage",
            "Stock Management",
        ),
        (
            "supplier_manage",
            "Supplier Management",
        ),
        (
            "purchase_manage",
            "Purchase Management",
        ),
        (
            "order_manage",
            "Order Management",
        ),
        (
            "billing_manage",
            "Billing",
        ),
        (
            "reports_view",
            "Reports",
        ),
        (
            "prescription_verify",
            "Prescription Verification",
        ),
    ]

    checks = ""

    for field, label in permission_fields:

        checked = (
            "checked"
            if getattr(permission, field)
            else ""
        )

        checks += f"""
        <label style="display:block;margin:12px 0">

            <input
                type="checkbox"
                name="{field}"
                value="1"
                {checked}
                style="width:auto"
            >

            {label}

        </label>
        """

    body = f"""
    <h1>🔐 Pharmacy Staff Permissions</h1>

    <div class="card">

        <h2>{esc(user.name)}</h2>

        <p>
            {esc(user.email)}
        </p>

        <form method="post">

            {checks}

            <button type="submit">
                Save Permissions
            </button>

        </form>

    </div>
    """

    return page(
        "Staff Permissions",
        body,
    )


@router.post(
    "/admin/staff/{user_id}",
)
def save_staff_permissions(
    user_id: int,
    request: Request,
    medicine_manage: str | None = Form(None),
    stock_manage: str | None = Form(None),
    supplier_manage: str | None = Form(None),
    purchase_manage: str | None = Form(None),
    order_manage: str | None = Form(None),
    billing_manage: str | None = Form(None),
    reports_view: str | None = Form(None),
    prescription_verify: str | None = Form(None),
    db: Session = Depends(get_db),
):

    require_admin(
        request,
        db,
    )

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.role == "pharmacy_staff",
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Pharmacy staff not found.",
        )

    permission = get_staff_permission(
        user_id,
        db,
    )

    if not permission:

        permission = PharmacyStaffPermission(
            user_id=user_id
        )

        db.add(permission)

    permission.medicine_manage = bool(
        medicine_manage
    )

    permission.stock_manage = bool(
        stock_manage
    )

    permission.supplier_manage = bool(
        supplier_manage
    )

    permission.purchase_manage = bool(
        purchase_manage
    )

    permission.order_manage = bool(
        order_manage
    )

    permission.billing_manage = bool(
        billing_manage
    )

    permission.reports_view = bool(
        reports_view
    )

    permission.prescription_verify = bool(
        prescription_verify
    )

    db.commit()

    return RedirectResponse(
        "/pharmacy/admin",
        status_code=303,
    )


# ============================================================
# MEDICINES
# ============================================================

@router.get(
    "/medicines",
    response_class=HTMLResponse,
)
def medicines_page(
    request: Request,
    db: Session = Depends(get_db),
):

    user = require_pharmacy_access(
        request,
        db,
        "medicine_manage",
    )

    medicines = (
        db.query(PharmacyMedicine)
        .order_by(
            PharmacyMedicine.name.asc()
        )
        .all()
    )

    rows = ""

    for medicine in medicines:

        rows += f"""
        <tr>

            <td>{medicine.id}</td>

            <td>
                {esc(medicine.name)}
            </td>

            <td>
                {esc(medicine.generic_name)}
            </td>

            <td>
                {esc(medicine.category)}
            </td>

            <td>
                {esc(medicine.manufacturer)}
            </td>

            <td>
                {esc(medicine.unit)}
            </td>

            <td>
                {
                    "Prescription Required"
                    if medicine.is_prescription_required
                    else "OTC"
                }
            </td>

            <td>
                {
                    "Active"
                    if medicine.is_active
                    else "Inactive"
                }
            </td>

        </tr>
        """

    body = f"""
    <h1>💊 Medicines</h1>

    <div class="card">

        <h2>Add Medicine</h2>

        <form method="post"
              action="/pharmacy/medicines/add">

            <label>Medicine Name</label>
            <input name="name" required>

            <label>Generic Name</label>
            <input name="generic_name">

            <label>Category</label>
            <input name="category">

            <label>Manufacturer</label>
            <input name="manufacturer">

            <label>Description</label>
            <textarea name="description"></textarea>

            <label>Unit</label>
            <input
                name="unit"
                value="strip"
            >

            <label>Reorder Level</label>
            <input
                type="number"
                name="reorder_level"
                value="10"
                min="0"
            >

            <label>
                <input
                    type="checkbox"
                    name="is_prescription_required"
                    value="1"
                    checked
                    style="width:auto"
                >
                Prescription Required
            </label>

            <br><br>

            <button type="submit">
                Add Medicine
            </button>

        </form>

    </div>

    <div class="card">

        <h2>Medicine List</h2>

        <table>

            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Generic</th>
                <th>Category</th>
                <th>Manufacturer</th>
                <th>Unit</th>
                <th>Type</th>
                <th>Status</th>
            </tr>

            {rows}

        </table>

    </div>
    """

    return page(
        "Medicines",
        body,
    )


@router.post(
    "/medicines/add",
)
def add_medicine(
    request: Request,
    name: str = Form(...),
    generic_name: str = Form(""),
    category: str = Form(""),
    manufacturer: str = Form(""),
    description: str = Form(""),
    unit: str = Form("strip"),
    reorder_level: int = Form(10),
    is_prescription_required: str | None = Form(None),
    db: Session = Depends(get_db),
):

    require_pharmacy_access(
        request,
        db,
        "medicine_manage",
    )

    medicine = PharmacyMedicine(
        name=name.strip(),
        generic_name=generic_name.strip() or None,
        category=category.strip() or None,
        manufacturer=manufacturer.strip() or None,
        description=description.strip() or None,
        unit=unit.strip() or "strip",
        reorder_level=max(0, reorder_level),
        is_prescription_required=bool(
            is_prescription_required
        ),
        is_active=True,
    )

    db.add(medicine)
    db.commit()

    return RedirectResponse(
        "/pharmacy/medicines",
        status_code=303,
    )


# ============================================================
# BATCHES / STOCK
# ============================================================

@router.get(
    "/batches",
    response_class=HTMLResponse,
)
def batches_page(
    request: Request,
    db: Session = Depends(get_db),
):

    require_pharmacy_access(
        request,
        db,
        "stock_manage",
    )

    medicines = (
        db.query(PharmacyMedicine)
        .filter(
            PharmacyMedicine.is_active == True
        )
        .all()
    )

    options = ""

    for medicine in medicines:
        options += f"""
        <option value="{medicine.id}">
            {esc(medicine.name)}
        </option>
        """

    batches = (
        db.query(PharmacyBatch)
        .order_by(
            PharmacyBatch.expiry_date.asc()
        )
        .all()
    )

    rows = ""

    for batch in batches:

        medicine = (
            db.query(PharmacyMedicine)
            .filter(
                PharmacyMedicine.id
                == batch.medicine_id
            )
            .first()
        )

        expiry_class = ""

        if batch.expiry_date < date.today():
            expiry_class = "danger"
        elif (
            batch.expiry_date
            <= date.today()
        ):
            expiry_class = "warn"

        rows += f"""
        <tr>

            <td>
                {esc(medicine.name if medicine else "-")}
            </td>

            <td>
                {esc(batch.batch_number)}
            </td>

            <td>
                {batch.expiry_date}
            </td>

            <td>
                <span class="badge {expiry_class}">
                    {batch.quantity}
                </span>
            </td>

            <td>
                ₹{batch.selling_price}
            </td>

        </tr>
        """

    body = f"""
    <h1>📦 Medicine Batches & Stock</h1>

    <div class="card">

        <h2>Add Stock Batch</h2>

        <form method="post"
              action="/pharmacy/batches/add">

            <label>Medicine</label>

            <select name="medicine_id" required>

                <option value="">
                    Select Medicine
                </option>

                {options}

            </select>

            <label>Batch Number</label>
            <input
                name="batch_number"
                required
            >

            <label>Expiry Date</label>
            <input
                type="date"
                name="expiry_date"
                required
            >

            <label>Quantity</label>
            <input
                type="number"
                name="quantity"
                min="0"
                required
            >

            <label>Purchase Price</label>
            <input
                type="number"
                name="purchase_price"
                step="0.01"
                min="0"
                required
            >

            <label>Selling Price</label>
            <input
                type="number"
                name="selling_price"
                step="0.01"
                min="0"
                required
            >

            <button type="submit">
                Add Stock
            </button>

        </form>

    </div>

    <div class="card">

        <h2>Stock</h2>

        <table>

            <tr>
                <th>Medicine</th>
                <th>Batch</th>
                <th>Expiry</th>
                <th>Quantity</th>
                <th>Selling Price</th>
            </tr>

            {rows}

        </table>

    </div>
    """

    return page(
        "Pharmacy Stock",
        body,
    )


@router.post(
    "/batches/add",
)
def add_batch(
    request: Request,
    medicine_id: int = Form(...),
    batch_number: str = Form(...),
    expiry_date: date = Form(...),
    quantity: int = Form(...),
    purchase_price: Decimal = Form(...),
    selling_price: Decimal = Form(...),
    db: Session = Depends(get_db),
):

    user = require_pharmacy_access(
        request,
        db,
        "stock_manage",
    )

    if expiry_date <= date.today():
        raise HTTPException(
            status_code=400,
            detail="Expiry date must be in the future.",
        )

    medicine = (
        db.query(PharmacyMedicine)
        .filter(
            PharmacyMedicine.id == medicine_id,
            PharmacyMedicine.is_active == True,
        )
        .first()
    )

    if not medicine:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found.",
        )

    batch = PharmacyBatch(
        medicine_id=medicine_id,
        batch_number=batch_number.strip(),
        expiry_date=expiry_date,
        quantity=max(0, quantity),
        purchase_price=purchase_price,
        selling_price=selling_price,
        is_active=True,
    )

    db.add(batch)
    db.flush()

    movement = PharmacyStockMovement(
        medicine_id=medicine_id,
        batch_id=batch.id,
        movement_type="IN",
        quantity=max(0, quantity),
        reference_type="batch_creation",
        reference_id=batch.id,
        created_by=user.id,
    )

    db.add(movement)

    db.commit()

    return RedirectResponse(
        "/pharmacy/batches",
        status_code=303,
    )


# ============================================================
# SUPPLIERS
# ============================================================

@router.get(
    "/suppliers",
    response_class=HTMLResponse,
)
def suppliers_page(
    request: Request,
    db: Session = Depends(get_db),
):

    require_pharmacy_access(
        request,
        db,
        "supplier_manage",
    )

    suppliers = (
        db.query(PharmacySupplier)
        .order_by(
            PharmacySupplier.name.asc()
        )
        .all()
    )

    rows = ""

    for supplier in suppliers:

        rows += f"""
        <tr>

            <td>{supplier.id}</td>
            <td>{esc(supplier.name)}</td>
            <td>{esc(supplier.mobile)}</td>
            <td>{esc(supplier.email)}</td>
            <td>{esc(supplier.gst_number)}</td>

        </tr>
        """

    body = f"""
    <h1>🚚 Suppliers</h1>

    <div class="card">

        <h2>Add Supplier</h2>

        <form method="post"
              action="/pharmacy/suppliers/add">

            <label>Name</label>
            <input name="name" required>

            <label>Mobile</label>
            <input name="mobile">

            <label>Email</label>
            <input type="email" name="email">

            <label>Address</label>
            <textarea name="address"></textarea>

            <label>GST Number</label>
            <input name="gst_number">

            <button type="submit">
                Add Supplier
            </button>

        </form>

    </div>

    <div class="card">

        <h2>Supplier List</h2>

        <table>

            <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Mobile</th>
                <th>Email</th>
                <th>GST</th>
            </tr>

            {rows}

        </table>

    </div>
    """

    return page(
        "Suppliers",
        body,
    )


@router.post(
    "/suppliers/add",
)
def add_supplier(
    request: Request,
    name: str = Form(...),
    mobile: str = Form(""),
    email: str = Form(""),
    address: str = Form(""),
    gst_number: str = Form(""),
    db: Session = Depends(get_db),
):

    require_pharmacy_access(
        request,
        db,
        "supplier_manage",
    )

    supplier = PharmacySupplier(
        name=name.strip(),
        mobile=mobile.strip() or None,
        email=email.strip() or None,
        address=address.strip() or None,
        gst_number=gst_number.strip() or None,
        is_active=True,
    )

    db.add(supplier)
    db.commit()

    return RedirectResponse(
        "/pharmacy/suppliers",
        status_code=303,
    )


# ============================================================
# PURCHASES
# ============================================================

@router.get(
    "/purchases",
    response_class=HTMLResponse,
)
def purchases_page(
    request: Request,
    db: Session = Depends(get_db),
):

    require_pharmacy_access(
        request,
        db,
        "purchase_manage",
    )

    medicines = (
        db.query(PharmacyMedicine)
        .filter(
            PharmacyMedicine.is_active == True
        )
        .all()
    )

    suppliers = (
        db.query(PharmacySupplier)
        .filter(
            PharmacySupplier.is_active == True
        )
        .all()
    )

    medicine_options = ""

    for medicine in medicines:
        medicine_options += f"""
        <option value="{medicine.id}">
            {esc(medicine.name)}
        </option>
        """

    supplier_options = ""

    for supplier in suppliers:
        supplier_options += f"""
        <option value="{supplier.id}">
            {esc(supplier.name)}
        </option>
        """

    purchases = (
        db.query(PharmacyPurchase)
        .order_by(
            PharmacyPurchase.id.desc()
        )
        .limit(100)
        .all()
    )

    rows = ""

    for purchase in purchases:

        medicine = (
            db.query(PharmacyMedicine)
            .filter(
                PharmacyMedicine.id
                == purchase.medicine_id
            )
            .first()
        )

        rows += f"""
        <tr>

            <td>{purchase.id}</td>

            <td>
                {esc(medicine.name if medicine else "-")}
            </td>

            <td>{purchase.quantity}</td>

            <td>₹{purchase.total_amount}</td>

            <td>{esc(purchase.invoice_number)}</td>

            <td>{purchase.purchased_at}</td>

        </tr>
        """

    body = f"""
    <h1>🛒 Purchases</h1>

    <div class="card">

        <h2>Purchase Entry</h2>

        <form method="post"
              action="/pharmacy/purchases/add">

            <label>Medicine</label>

            <select name="medicine_id" required>

                <option value="">
                    Select Medicine
                </option>

                {medicine_options}

            </select>

            <label>Batch ID</label>
            <input
                type="number"
                name="batch_id"
                required
            >

            <label>Supplier</label>

            <select name="supplier_id">

                <option value="">
                    Select Supplier
                </option>

                {supplier_options}

            </select>

            <label>Quantity</label>
            <input
                type="number"
                name="quantity"
                min="1"
                required
            >

            <label>Total Amount</label>
            <input
                type="number"
                name="total_amount"
                step="0.01"
                min="0"
                required
            >

            <label>Invoice Number</label>
            <input name="invoice_number">

            <button type="submit">
                Save Purchase
            </button>

        </form>

    </div>

    <div class="card">

        <h2>Purchase History</h2>

        <table>

            <tr>
                <th>ID</th>
                <th>Medicine</th>
                <th>Quantity</th>
                <th>Amount</th>
                <th>Invoice</th>
                <th>Date</th>
            </tr>

            {rows}

        </table>

    </div>
    """

    return page(
        "Pharmacy Purchases",
        body,
    )


@router.post(
    "/purchases/add",
)
def add_purchase(
    request: Request,
    medicine_id: int = Form(...),
    batch_id: int = Form(...),
    supplier_id: int | None = Form(None),
    quantity: int = Form(...),
    total_amount: Decimal = Form(...),
    invoice_number: str = Form(""),
    db: Session = Depends(get_db),
):

    user = require_pharmacy_access(
        request,
        db,
        "purchase_manage",
    )

    batch = (
        db.query(PharmacyBatch)
        .filter(
            PharmacyBatch.id == batch_id,
            PharmacyBatch.medicine_id == medicine_id,
        )
        .first()
    )

    if not batch:
        raise HTTPException(
            status_code=404,
            detail="Medicine batch not found.",
        )

    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than zero.",
        )

    batch.quantity += quantity

    purchase = PharmacyPurchase(
        supplier_id=supplier_id,
        medicine_id=medicine_id,
        batch_id=batch_id,
        quantity=quantity,
        total_amount=total_amount,
        invoice_number=invoice_number.strip() or None,
        created_by=user.id,
    )

    db.add(purchase)

    movement = PharmacyStockMovement(
        medicine_id=medicine_id,
        batch_id=batch_id,
        movement_type="PURCHASE",
        quantity=quantity,
        reference_type="purchase",
        created_by=user.id,
    )

    db.add(movement)

    db.commit()

    return RedirectResponse(
        "/pharmacy/purchases",
        status_code=303,
    )


# ============================================================
# ORDERS
# ============================================================

@router.get(
    "/orders",
    response_class=HTMLResponse,
)
def orders_page(
    request: Request,
    db: Session = Depends(get_db),
):

    require_pharmacy_access(
        request,
        db,
        "order_manage",
    )

    orders = (
        db.query(PharmacyOrder)
        .order_by(
            PharmacyOrder.id.desc()
        )
        .limit(100)
        .all()
    )

    rows = ""

    for order in orders:

        patient = (
            db.query(User)
            .filter(
                User.id == order.patient_id
            )
            .first()
        )

        rows += f"""
        <tr>

            <td>{order.id}</td>

            <td>
                {esc(patient.name if patient else "-")}
            </td>

            <td>
                {esc(order.status)}
            </td>

            <td>
                ₹{order.total_amount}
            </td>

            <td>
                {esc(order.payment_status)}
            </td>

            <td>
                {order.created_at}
            </td>

        </tr>
        """

    body = f"""
    <h1>📋 Pharmacy Orders</h1>

    <div class="card">

        <table>

            <tr>
                <th>Order</th>
                <th>Patient</th>
                <th>Status</th>
                <th>Total</th>
                <th>Payment</th>
                <th>Created</th>
            </tr>

            {rows}

        </table>

    </div>
    """

    return page(
        "Pharmacy Orders",
        body,
    )


# ============================================================
# BILLING
# ============================================================

@router.get(
    "/billing",
    response_class=HTMLResponse,
)
def billing_page(
    request: Request,
    db: Session = Depends(get_db),
):

    require_pharmacy_access(
        request,
        db,
        "billing_manage",
    )

    sales = (
        db.query(PharmacySale)
        .order_by(
            PharmacySale.id.desc()
        )
        .limit(100)
        .all()
    )

    rows = ""

    for sale in sales:

        patient = None

        if sale.patient_id:
            patient = (
                db.query(User)
                .filter(
                    User.id == sale.patient_id
                )
                .first()
            )

        rows += f"""
        <tr>

            <td>{sale.id}</td>

            <td>
                {esc(sale.invoice_number)}
            </td>

            <td>
                {esc(patient.name if patient else "Walk-in")}
            </td>

            <td>
                ₹{sale.total_amount}
            </td>

            <td>
                {esc(sale.payment_method)}
            </td>

            <td>
                {esc(sale.payment_status)}
            </td>

            <td>
                {sale.sold_at}
            </td>

        </tr>
        """

    body = f"""
    <h1>🧾 Pharmacy Billing</h1>

    <div class="card">

        <p>
            Pharmacy sales and invoices are stored here.
        </p>

        <table>

            <tr>
                <th>ID</th>
                <th>Invoice</th>
                <th>Patient</th>
                <th>Total</th>
                <th>Payment</th>
                <th>Status</th>
                <th>Date</th>
            </tr>

            {rows}

        </table>

    </div>
    """

    return page(
        "Pharmacy Billing",
        body,
    )


# ============================================================
# REPORTS
# ============================================================

@router.get(
    "/reports",
    response_class=HTMLResponse,
)
def pharmacy_reports(
    request: Request,
    db: Session = Depends(get_db),
):

    require_pharmacy_access(
        request,
        db,
        "reports_view",
    )

    medicines = (
        db.query(PharmacyMedicine)
        .filter(
            PharmacyMedicine.is_active == True
        )
        .all()
    )

    total_stock = 0
    low_stock = 0
    expired_batches = 0

    for medicine in medicines:

        batches = (
            db.query(PharmacyBatch)
            .filter(
                PharmacyBatch.medicine_id
                == medicine.id,
                PharmacyBatch.is_active == True,
            )
            .all()
        )

        quantity = sum(
            int(batch.quantity or 0)
            for batch in batches
        )

        total_stock += quantity

        if quantity <= medicine.reorder_level:
            low_stock += 1

        for batch in batches:

            if batch.expiry_date < date.today():
                expired_batches += 1

    total_sales = (
        db.query(PharmacySale)
        .count()
    )

    total_orders = (
        db.query(PharmacyOrder)
        .count()
    )

    body = f"""
    <h1>📊 Pharmacy Reports</h1>

    <div class="grid">

        <div class="stat">
            <h3>Total Medicines</h3>
            <h2>{len(medicines)}</h2>
        </div>

        <div class="stat">
            <h3>Total Stock Units</h3>
            <h2>{total_stock}</h2>
        </div>

        <div class="stat">
            <h3>Low Stock Medicines</h3>
            <h2>{low_stock}</h2>
        </div>

        <div class="stat">
            <h3>Expired Batches</h3>
            <h2>{expired_batches}</h2>
        </div>

        <div class="stat">
            <h3>Total Sales</h3>
            <h2>{total_sales}</h2>
        </div>

        <div class="stat">
            <h3>Total Orders</h3>
            <h2>{total_orders}</h2>
        </div>

    </div>
    """

    return page(
        "Pharmacy Reports",
        body,
    )