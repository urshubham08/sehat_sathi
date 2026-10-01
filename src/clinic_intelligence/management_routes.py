from datetime import datetime
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.database.models import User
from src.clinic_intelligence.clinic_models import (
    ClinicInventory,
    ClinicSalary,
    ClinicStaff,
    ClinicTiming,
)


router = APIRouter(prefix="/clinic", tags=["Clinic Management"])


# ============================================================
# ADMIN CHECK
# ============================================================

def get_admin(request: Request, db: Session):
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return None

    role = str(getattr(user, "role", "") or "").lower()

    if role != "admin":
        return None

    return user


# ============================================================
# HTML HELPERS
# ============================================================

def page_start(title: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">

        <title>{title}</title>

        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f4f7fb;
                color: #1f2937;
            }}

            .topbar {{
                background: #111827;
                color: white;
                padding: 18px 28px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 20px;
            }}

            .topbar h1 {{
                margin: 0;
                font-size: 22px;
            }}

            .container {{
                max-width: 1250px;
                margin: 30px auto;
                padding: 0 20px;
            }}

            .back {{
                display: inline-block;
                margin-bottom: 20px;
                text-decoration: none;
                color: #2563eb;
                font-weight: bold;
            }}

            .cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 18px;
                margin-bottom: 28px;
            }}

            .card {{
                background: white;
                border-radius: 14px;
                padding: 22px;
                box-shadow: 0 5px 18px rgba(0,0,0,.08);
            }}

            .card h2 {{
                margin-top: 0;
                font-size: 19px;
            }}

            .card p {{
                color: #6b7280;
            }}

            .btn {{
                display: inline-block;
                padding: 10px 16px;
                border-radius: 8px;
                text-decoration: none;
                border: none;
                cursor: pointer;
                font-weight: bold;
                background: #2563eb;
                color: white;
            }}

            .btn.green {{
                background: #16a34a;
            }}

            .btn.red {{
                background: #dc2626;
            }}

            .btn.gray {{
                background: #6b7280;
            }}

            .btn.orange {{
                background: #ea580c;
            }}

            form {{
                background: white;
                padding: 22px;
                border-radius: 14px;
                margin-bottom: 25px;
                box-shadow: 0 5px 18px rgba(0,0,0,.07);
            }}

            .form-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 14px;
            }}

            label {{
                display: block;
                font-weight: bold;
                margin-bottom: 6px;
            }}

            input,
            select {{
                width: 100%;
                padding: 11px;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                font-size: 14px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 12px;
                overflow: hidden;
            }}

            th,
            td {{
                padding: 12px;
                border-bottom: 1px solid #e5e7eb;
                text-align: left;
            }}

            th {{
                background: #eef2ff;
            }}

            .table-wrap {{
                overflow-x: auto;
                margin-bottom: 30px;
            }}

            .badge {{
                display: inline-block;
                padding: 5px 9px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
            }}

            .active {{
                background: #dcfce7;
                color: #166534;
            }}

            .inactive {{
                background: #fee2e2;
                color: #991b1b;
            }}

            .pending {{
                background: #fef3c7;
                color: #92400e;
            }}

            .paid {{
                background: #dcfce7;
                color: #166534;
            }}

            .low {{
                background: #fee2e2;
                color: #991b1b;
            }}

            .normal {{
                background: #dcfce7;
                color: #166534;
            }}

            .section-title {{
                margin-top: 35px;
                margin-bottom: 15px;
            }}

            .actions {{
                display: flex;
                gap: 7px;
                flex-wrap: wrap;
            }}

            .message {{
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 20px;
                background: #ecfdf5;
                color: #065f46;
            }}
        </style>
    </head>

    <body>

    <div class="topbar">
        <h1>🏥 Smart Clinic Management</h1>
        <a href="/admin/dashboard" class="btn gray">Admin Dashboard</a>
    </div>
    """


def page_end() -> str:
    return """
    </body>
    </html>
    """


def redirect_clinic():
    return RedirectResponse(
        url="/clinic/",
        status_code=303,
    )


# ============================================================
# MAIN CLINIC MANAGEMENT PAGE
# ============================================================

@router.get("/", response_class=HTMLResponse)
def clinic_management(
    request: Request,
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    staff = (
        db.query(ClinicStaff)
        .order_by(ClinicStaff.id.desc())
        .all()
    )

    salaries = (
        db.query(ClinicSalary)
        .order_by(ClinicSalary.id.desc())
        .all()
    )

    inventory = (
        db.query(ClinicInventory)
        .order_by(ClinicInventory.id.desc())
        .all()
    )

    timings = (
        db.query(ClinicTiming)
        .order_by(ClinicTiming.id.asc())
        .all()
    )

    html = page_start("Clinic Management")

    html += """
    <div class="container">

        <a href="/admin/dashboard" class="back">
            ← Back to Admin Dashboard
        </a>

        <h2>Clinic Management</h2>

        <p>
            Manage clinic staff, salaries, inventory and timings
            from one place.
        </p>

        <div class="cards">

            <div class="card">
                <h2>👥 Staff Management</h2>
                <p>Add and manage clinic employees.</p>
                <a href="/clinic/staff" class="btn">
                    Open Staff
                </a>
            </div>

            <div class="card">
                <h2>💰 Salary Management</h2>
                <p>Add salary records and mark payments.</p>
                <a href="/clinic/salary" class="btn green">
                    Open Salary
                </a>
            </div>

            <div class="card">
                <h2>📦 Inventory Management</h2>
                <p>Manage medicine and clinic stock.</p>
                <a href="/clinic/inventory" class="btn orange">
                    Open Inventory
                </a>
            </div>

            <div class="card">
                <h2>🕒 Clinic Timing</h2>
                <p>Set weekly clinic opening hours.</p>
                <a href="/clinic/timing" class="btn gray">
                    Open Timing
                </a>
            </div>

        </div>

        <h2 class="section-title">
            Quick Overview
        </h2>

        <div class="cards">

            <div class="card">
                <h2>Staff</h2>
                <p>Total Staff</p>
                <h2>
                    {staff_count}
                </h2>
            </div>

            <div class="card">
                <h2>Salary</h2>
                <p>Total Records</p>
                <h2>
                    {salary_count}
                </h2>
            </div>

            <div class="card">
                <h2>Inventory</h2>
                <p>Total Items</p>
                <h2>
                    {inventory_count}
                </h2>
            </div>

            <div class="card">
                <h2>Timing</h2>
                <p>Configured Days</p>
                <h2>
                    {timing_count}
                </h2>
            </div>

        </div>

    </div>
    """.format(
        staff_count=len(staff),
        salary_count=len(salaries),
        inventory_count=len(inventory),
        timing_count=len(timings),
    )

    html += page_end()

    return HTMLResponse(html)


# ============================================================
# STAFF
# ============================================================

@router.get("/staff", response_class=HTMLResponse)
def staff_page(
    request: Request,
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    staff = (
        db.query(ClinicStaff)
        .order_by(ClinicStaff.id.desc())
        .all()
    )

    html = page_start("Staff Management")

    html += """
    <div class="container">

        <a href="/clinic/" class="back">
            ← Back to Clinic Management
        </a>

        <h2>👥 Staff Management</h2>

        <form method="post" action="/clinic/staff/add">

            <h3>Add New Staff</h3>

            <div class="form-grid">

                <div>
                    <label>Name</label>
                    <input
                        type="text"
                        name="name"
                        required
                    >
                </div>

                <div>
                    <label>Designation</label>
                    <input
                        type="text"
                        name="designation"
                        placeholder="Nurse / Receptionist"
                        required
                    >
                </div>

                <div>
                    <label>Mobile</label>
                    <input
                        type="text"
                        name="mobile"
                    >
                </div>

                <div>
                    <label>Email</label>
                    <input
                        type="email"
                        name="email"
                    >
                </div>

                <div>
                    <label>Monthly Salary</label>
                    <input
                        type="number"
                        step="0.01"
                        name="monthly_salary"
                        value="0"
                        min="0"
                    >
                </div>

            </div>

            <br>

            <button class="btn green" type="submit">
                + Add Staff
            </button>

        </form>

        <div class="table-wrap">

            <table>

                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Designation</th>
                    <th>Mobile</th>
                    <th>Email</th>
                    <th>Salary</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
    """

    for person in staff:
        status = str(person.status or "active").lower()

        if status == "active":
            action = f"""
                <a
                    href="/clinic/staff/{person.id}/deactivate"
                    class="btn red"
                >
                    Deactivate
                </a>
            """
        else:
            action = f"""
                <a
                    href="/clinic/staff/{person.id}/activate"
                    class="btn green"
                >
                    Activate
                </a>
            """

        html += f"""
            <tr>

                <td>{person.id}</td>

                <td>{person.name}</td>

                <td>{person.designation}</td>

                <td>{person.mobile or "-"}</td>

                <td>{person.email or "-"}</td>

                <td>₹ {person.monthly_salary or 0}</td>

                <td>
                    <span class="badge {'active' if status == 'active' else 'inactive'}">
                        {status}
                    </span>
                </td>

                <td>
                    {action}
                </td>

            </tr>
        """

    html += """
            </table>

        </div>

    </div>
    """

    html += page_end()

    return HTMLResponse(html)


@router.post("/staff/add")
def add_staff(
    request: Request,
    name: str = Form(...),
    designation: str = Form(...),
    mobile: str = Form(""),
    email: str = Form(""),
    monthly_salary: str = Form("0"),
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    try:
        salary = Decimal(monthly_salary or "0")
    except InvalidOperation:
        salary = Decimal("0")

    staff = ClinicStaff(
        name=name.strip(),
        designation=designation.strip(),
        mobile=mobile.strip() or None,
        email=email.strip() or None,
        monthly_salary=salary,
        status="active",
    )

    db.add(staff)
    db.commit()

    return RedirectResponse(
        url="/clinic/staff",
        status_code=303,
    )


@router.get("/staff/{staff_id}/activate")
def activate_staff(
    staff_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    staff = (
        db.query(ClinicStaff)
        .filter(ClinicStaff.id == staff_id)
        .first()
    )

    if staff:
        staff.status = "active"
        db.commit()

    return RedirectResponse(
        url="/clinic/staff",
        status_code=303,
    )


@router.get("/staff/{staff_id}/deactivate")
def deactivate_staff(
    staff_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    staff = (
        db.query(ClinicStaff)
        .filter(ClinicStaff.id == staff_id)
        .first()
    )

    if staff:
        staff.status = "inactive"
        db.commit()

    return RedirectResponse(
        url="/clinic/staff",
        status_code=303,
    )


# ============================================================
# SALARY
# ============================================================

@router.get("/salary", response_class=HTMLResponse)
def salary_page(
    request: Request,
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    staff = (
        db.query(ClinicStaff)
        .filter(ClinicStaff.status == "active")
        .order_by(ClinicStaff.name.asc())
        .all()
    )

    salaries = (
        db.query(ClinicSalary)
        .order_by(ClinicSalary.id.desc())
        .all()
    )

    staff_map = {
        person.id: person
        for person in db.query(ClinicStaff).all()
    }

    html = page_start("Salary Management")

    html += """
    <div class="container">

        <a href="/clinic/" class="back">
            ← Back to Clinic Management
        </a>

        <h2>💰 Salary Management</h2>

        <form method="post" action="/clinic/salary/add">

            <h3>Add Salary Record</h3>

            <div class="form-grid">

                <div>
                    <label>Staff</label>

                    <select name="staff_id" required>

                        <option value="">
                            Select Staff
                        </option>
    """

    for person in staff:
        html += f"""
                        <option value="{person.id}">
                            {person.name} - {person.designation}
                        </option>
        """

    html += """
                    </select>
                </div>

                <div>
                    <label>Month</label>

                    <input
                        type="month"
                        name="month"
                        required
                    >
                </div>

                <div>
                    <label>Amount</label>

                    <input
                        type="number"
                        step="0.01"
                        min="0"
                        name="amount"
                        required
                    >
                </div>

            </div>

            <br>

            <button class="btn green" type="submit">
                + Add Salary
            </button>

        </form>

        <div class="table-wrap">

            <table>

                <tr>
                    <th>ID</th>
                    <th>Staff</th>
                    <th>Month</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
    """

    for salary in salaries:
        person = staff_map.get(salary.staff_id)

        staff_name = (
            person.name
            if person
            else f"Staff #{salary.staff_id}"
        )

        payment_status = str(
            salary.payment_status or "pending"
        ).lower()

        if payment_status == "paid":
            action = '<span class="badge paid">Paid</span>'
        else:
            action = f"""
                <a
                    href="/clinic/salary/{salary.id}/paid"
                    class="btn green"
                >
                    Mark Paid
                </a>
            """

        html += f"""
                <tr>

                    <td>{salary.id}</td>

                    <td>{staff_name}</td>

                    <td>{salary.month}</td>

                    <td>₹ {salary.amount}</td>

                    <td>
                        <span class="badge {'paid' if payment_status == 'paid' else 'pending'}">
                            {payment_status}
                        </span>
                    </td>

                    <td>
                        {action}
                    </td>

                </tr>
        """

    html += """
            </table>

        </div>

    </div>
    """

    html += page_end()

    return HTMLResponse(html)


@router.post("/salary/add")
def add_salary(
    request: Request,
    staff_id: int = Form(...),
    month: str = Form(...),
    amount: str = Form(...),
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    try:
        salary_amount = Decimal(amount)
    except InvalidOperation:
        salary_amount = Decimal("0")

    salary = ClinicSalary(
        staff_id=staff_id,
        month=month,
        amount=salary_amount,
        payment_status="pending",
    )

    db.add(salary)
    db.commit()

    return RedirectResponse(
        url="/clinic/salary",
        status_code=303,
    )


@router.get("/salary/{salary_id}/paid")
def mark_salary_paid(
    salary_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    salary = (
        db.query(ClinicSalary)
        .filter(ClinicSalary.id == salary_id)
        .first()
    )

    if salary:
        salary.payment_status = "paid"
        salary.paid_at = datetime.utcnow()
        db.commit()

    return RedirectResponse(
        url="/clinic/salary",
        status_code=303,
    )


# ============================================================
# INVENTORY
# ============================================================

@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(
    request: Request,
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    inventory = (
        db.query(ClinicInventory)
        .order_by(ClinicInventory.id.desc())
        .all()
    )

    html = page_start("Inventory Management")

    html += """
    <div class="container">

        <a href="/clinic/" class="back">
            ← Back to Clinic Management
        </a>

        <h2>📦 Inventory Management</h2>

        <form method="post" action="/clinic/inventory/add">

            <h3>Add Inventory Item</h3>

            <div class="form-grid">

                <div>
                    <label>Item Name</label>

                    <input
                        type="text"
                        name="item_name"
                        required
                    >
                </div>

                <div>
                    <label>Category</label>

                    <input
                        type="text"
                        name="category"
                        placeholder="Medicine / Equipment"
                    >
                </div>

                <div>
                    <label>Quantity</label>

                    <input
                        type="number"
                        name="quantity"
                        value="0"
                        min="0"
                        required
                    >
                </div>

                <div>
                    <label>Unit</label>

                    <input
                        type="text"
                        name="unit"
                        placeholder="Box / Piece"
                    >
                </div>

                <div>
                    <label>Minimum Stock</label>

                    <input
                        type="number"
                        name="minimum_stock"
                        value="5"
                        min="0"
                    >
                </div>

                <div>
                    <label>Supplier</label>

                    <input
                        type="text"
                        name="supplier"
                    >
                </div>

                <div>
                    <label>Price</label>

                    <input
                        type="number"
                        step="0.01"
                        name="price"
                        value="0"
                        min="0"
                    >
                </div>

            </div>

            <br>

            <button class="btn orange" type="submit">
                + Add Inventory
            </button>

        </form>

        <div class="table-wrap">

            <table>

                <tr>
                    <th>ID</th>
                    <th>Item</th>
                    <th>Category</th>
                    <th>Quantity</th>
                    <th>Unit</th>
                    <th>Min Stock</th>
                    <th>Supplier</th>
                    <th>Price</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
    """

    for item in inventory:

        is_low = item.quantity <= item.minimum_stock

        stock_badge = (
            '<span class="badge low">LOW STOCK</span>'
            if is_low
            else '<span class="badge normal">NORMAL</span>'
        )

        active_status = (
            str(item.is_active).lower()
            if item.is_active is not None
            else "false"
        )

        if item.is_active:
            action = f"""
                <a
                    href="/clinic/inventory/{item.id}/deactivate"
                    class="btn red"
                >
                    Deactivate
                </a>
            """
        else:
            action = f"""
                <a
                    href="/clinic/inventory/{item.id}/activate"
                    class="btn green"
                >
                    Activate
                </a>
            """

        html += f"""
                <tr>

                    <td>{item.id}</td>

                    <td>{item.item_name}</td>

                    <td>{item.category or "-"}</td>

                    <td>{item.quantity}</td>

                    <td>{item.unit or "-"}</td>

                    <td>{item.minimum_stock}</td>

                    <td>{item.supplier or "-"}</td>

                    <td>₹ {item.price or 0}</td>

                    <td>
                        {stock_badge}
                    </td>

                    <td>
                        {action}
                    </td>

                </tr>
        """

    html += """
            </table>

        </div>

    </div>
    """

    html += page_end()

    return HTMLResponse(html)


@router.post("/inventory/add")
def add_inventory(
    request: Request,
    item_name: str = Form(...),
    category: str = Form(""),
    quantity: int = Form(0),
    unit: str = Form(""),
    minimum_stock: int = Form(5),
    supplier: str = Form(""),
    price: str = Form("0"),
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    try:
        item_price = Decimal(price or "0")
    except InvalidOperation:
        item_price = Decimal("0")

    item = ClinicInventory(
        item_name=item_name.strip(),
        category=category.strip() or None,
        quantity=max(quantity, 0),
        unit=unit.strip() or None,
        minimum_stock=max(minimum_stock, 0),
        supplier=supplier.strip() or None,
        price=item_price,
        is_active=True,
    )

    db.add(item)
    db.commit()

    return RedirectResponse(
        url="/clinic/inventory",
        status_code=303,
    )


@router.get("/inventory/{item_id}/activate")
def activate_inventory(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    item = (
        db.query(ClinicInventory)
        .filter(ClinicInventory.id == item_id)
        .first()
    )

    if item:
        item.is_active = True
        db.commit()

    return RedirectResponse(
        url="/clinic/inventory",
        status_code=303,
    )


@router.get("/inventory/{item_id}/deactivate")
def deactivate_inventory(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    item = (
        db.query(ClinicInventory)
        .filter(ClinicInventory.id == item_id)
        .first()
    )

    if item:
        item.is_active = False
        db.commit()

    return RedirectResponse(
        url="/clinic/inventory",
        status_code=303,
    )


# ============================================================
# CLINIC TIMING
# ============================================================

DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


@router.get("/timing", response_class=HTMLResponse)
def timing_page(
    request: Request,
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    timing_map = {
        item.day: item
        for item in db.query(ClinicTiming).all()
    }

    html = page_start("Clinic Timing")

    html += """
    <div class="container">

        <a href="/clinic/" class="back">
            ← Back to Clinic Management
        </a>

        <h2>🕒 Clinic Timing</h2>

        <form method="post" action="/clinic/timing/save">

            <p>
                Set opening, closing and break time for each day.
            </p>
    """

    for day in DAYS:

        item = timing_map.get(day)

        opening = item.opening_time if item else ""
        closing = item.closing_time if item else ""
        break_start = item.break_start if item else ""
        break_end = item.break_end if item else ""
        is_open = item.is_open if item else True

        html += f"""
            <div class="card" style="margin-bottom:15px;">

                <h3>{day}</h3>

                <div class="form-grid">

                    <div>
                        <label>Opening Time</label>

                        <input
                            type="time"
                            name="opening_{day}"
                            value="{opening or ''}"
                        >
                    </div>

                    <div>
                        <label>Closing Time</label>

                        <input
                            type="time"
                            name="closing_{day}"
                            value="{closing or ''}"
                        >
                    </div>

                    <div>
                        <label>Break Start</label>

                        <input
                            type="time"
                            name="break_start_{day}"
                            value="{break_start or ''}"
                        >
                    </div>

                    <div>
                        <label>Break End</label>

                        <input
                            type="time"
                            name="break_end_{day}"
                            value="{break_end or ''}"
                        >
                    </div>

                    <div>
                        <label>Clinic Open?</label>

                        <select name="is_open_{day}">

                            <option
                                value="yes"
                                {"selected" if is_open else ""}
                            >
                                Open
                            </option>

                            <option
                                value="no"
                                {"" if is_open else "selected"}
                            >
                                Closed
                            </option>

                        </select>
                    </div>

                </div>

            </div>
        """

    html += """
            <button class="btn green" type="submit">
                💾 Save All Timings
            </button>

        </form>

    </div>
    """

    html += page_end()

    return HTMLResponse(html)


@router.post("/timing/save")
async def save_timing(
    request: Request,
    db: Session = Depends(get_db),
):
    admin = get_admin(request, db)

    if not admin:
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    form = await request.form()

    for day in DAYS:

        opening = str(
            form.get(f"opening_{day}") or ""
        ).strip()

        closing = str(
            form.get(f"closing_{day}") or ""
        ).strip()

        break_start = str(
            form.get(f"break_start_{day}") or ""
        ).strip()

        break_end = str(
            form.get(f"break_end_{day}") or ""
        ).strip()

        is_open = (
            str(form.get(f"is_open_{day}") or "yes")
            == "yes"
        )

        timing = (
            db.query(ClinicTiming)
            .filter(ClinicTiming.day == day)
            .first()
        )

        if not timing:
            timing = ClinicTiming(day=day)
            db.add(timing)

        timing.opening_time = opening or None
        timing.closing_time = closing or None
        timing.break_start = break_start or None
        timing.break_end = break_end or None
        timing.is_open = is_open

    db.commit()

    return RedirectResponse(
        url="/clinic/timing",
        status_code=303,
    )