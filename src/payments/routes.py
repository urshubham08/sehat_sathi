from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database.database import get_db
from src.database.models import Appointment, Doctor, Payment, User
from src.notifications.services import notify, send_email
from src.payments.services import (
    RAZORPAY_KEY_ID,
    complete_payment,
    create_razorpay_order,
)

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
)


class CreateOrderRequest(BaseModel):
    amount: int = Field(..., ge=100)
    appointment_id: int | None = None


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


def get_current_patient(
    request: Request,
    db: Session,
):
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please login first.",
        )

    if role != "patient":
        raise HTTPException(
            status_code=403,
            detail="Only patients can make payments.",
        )

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_active == True,
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found.",
        )

    return user


@router.get(
    "/checkout",
    response_class=HTMLResponse,
)
def payment_checkout_page(
    request: Request,
    appointment_id: int,
    db: Session = Depends(get_db),
):
    patient = get_current_patient(request, db)

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient.id,
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found.",
        )

    if appointment.status != "booked":
        raise HTTPException(
            status_code=400,
            detail="This appointment is not available for payment.",
        )

    if appointment.payment_status == "paid":
        raise HTTPException(
            status_code=400,
            detail="This appointment is already paid.",
        )

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>
            Appointment Payment - Sehat Saathi
        </title>

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <style>

            body {{
                margin: 0;
                padding: 25px;
                font-family: Arial, sans-serif;
                background: #f4f7fb;
            }}

            .card {{
                max-width: 550px;
                margin: 50px auto;
                background: white;
                padding: 30px;
                border-radius: 16px;
                box-shadow: 0 8px 30px rgba(0,0,0,0.08);
            }}

            h1 {{
                color: #0f766e;
            }}

            .info {{
                background: #f0fdfa;
                padding: 18px;
                border-radius: 10px;
                margin: 20px 0;
                line-height: 1.8;
            }}

            .amount {{
                font-size: 28px;
                font-weight: bold;
                color: #0f766e;
                margin: 25px 0;
            }}

            button {{
                width: 100%;
                padding: 14px;
                border: 0;
                border-radius: 10px;
                background: #0f766e;
                color: white;
                font-size: 16px;
                cursor: pointer;
                font-weight: bold;
            }}

            button:disabled {{
                opacity: 0.6;
                cursor: not-allowed;
            }}

            #message {{
                margin-top: 20px;
                white-space: pre-wrap;
                line-height: 1.5;
            }}

            .back {{
                display: block;
                margin-top: 20px;
                text-align: center;
                color: #0f766e;
                text-decoration: none;
                font-weight: bold;
            }}

        </style>

    </head>

    <body>

        <div class="card">

            <h1>
                💳 Appointment Payment
            </h1>

            <div class="info">

                <strong>
                    Appointment ID:
                </strong>

                #{appointment.id}

                <br>

                <strong>
                    Date:
                </strong>

                {appointment.appointment_date}

                <br>

                <strong>
                    Time:
                </strong>

                {appointment.appointment_time}

            </div>

            <div class="amount">
                Consultation Payment
            </div>

            <button id="pay-button">
                Continue to Payment
            </button>

            <div id="message"></div>

            <a
                class="back"
                href="/appointments/my"
            >
                ← Back to My Appointments
            </a>

        </div>


        <script src="https://checkout.razorpay.com/v1/checkout.js"></script>


        <script>

            const payButton =
                document.getElementById("pay-button");

            const message =
                document.getElementById("message");

            const appointmentId =
                {appointment.id};


            payButton.addEventListener(
                "click",
                async function() {{

                    payButton.disabled = true;

                    message.textContent =
                        "Creating secure payment order...";

                    try {{

                        const orderResponse =
                            await fetch(
                                "/payments/api/create-order",
                                {{
                                    method: "POST",

                                    headers: {{
                                        "Content-Type":
                                            "application/json"
                                    }},

                                    body: JSON.stringify({{
                                        amount: 100,

                                        appointment_id:
                                            appointmentId
                                    }})
                                }}
                            );


                        const orderData =
                            await orderResponse.json();


                        if (!orderResponse.ok) {{

                            throw new Error(
                                orderData.detail ||
                                "Unable to create payment order."
                            );

                        }}


                        const options = {{

                            key:
                                "{RAZORPAY_KEY_ID}",

                            amount:
                                orderData.amount,

                            currency:
                                orderData.currency,

                            name:
                                "Sehat Saathi",

                            description:
                                "Doctor consultation payment",

                            order_id:
                                orderData.order_id,


                            handler:
                                async function(response) {{

                                    message.textContent =
                                        "Payment received. " +
                                        "Verifying securely...";


                                    try {{

                                        const verifyResponse =
                                            await fetch(
                                                "/payments/api/verify-payment",
                                                {{

                                                    method: "POST",

                                                    headers: {{
                                                        "Content-Type":
                                                            "application/json"
                                                    }},

                                                    body:
                                                        JSON.stringify({{

                                                            razorpay_order_id:
                                                                response.razorpay_order_id,

                                                            razorpay_payment_id:
                                                                response.razorpay_payment_id,

                                                            razorpay_signature:
                                                                response.razorpay_signature

                                                        }})

                                                }}
                                            );


                                        const verifyData =
                                            await verifyResponse.json();


                                        if (!verifyResponse.ok) {{

                                            throw new Error(
                                                verifyData.detail ||
                                                "Payment verification failed."
                                            );

                                        }}


                                        message.textContent =
                                            "✅ Payment successful. " +
                                            "Opening receipt...";


                                        setTimeout(
                                            function() {{

                                                window.location.href =
                                                    "/payments/receipt/" +
                                                    verifyData.payment_id;

                                            }},
                                            1000
                                        );


                                    }} catch (error) {{

                                        message.textContent =
                                            "❌ Verification failed: " +
                                            error.message;

                                        payButton.disabled = false;

                                    }}

                                }},


                            modal: {{

                                ondismiss:
                                    function() {{

                                        message.textContent =
                                            "Payment window closed. " +
                                            "No payment was confirmed.";

                                        payButton.disabled = false;

                                    }}

                            }}

                        }};


                        const razorpay =
                            new Razorpay(options);


                        razorpay.on(
                            "payment.failed",
                            function(response) {{

                                const error =
                                    response.error || {{}};

                                message.textContent =
                                    "❌ Payment failed.\\n" +
                                    (
                                        error.description ||
                                        "Please try again."
                                    );

                                payButton.disabled = false;

                            }}
                        );


                        razorpay.open();


                    }} catch (error) {{

                        message.textContent =
                            "❌ Payment error: " +
                            error.message;

                        payButton.disabled = false;

                    }}

                }}
            );

        </script>

    </body>

    </html>
    """


@router.post("/api/create-order")
def create_order(
    payload: CreateOrderRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    patient = get_current_patient(request, db)

    if not payload.appointment_id:
        raise HTTPException(
            status_code=400,
            detail="Appointment ID is required.",
        )

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == payload.appointment_id,
            Appointment.patient_id == patient.id,
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found.",
        )

    if appointment.status != "booked":
        raise HTTPException(
            status_code=400,
            detail="Appointment is not available for payment.",
        )

    if appointment.payment_status == "paid":
        raise HTTPException(
            status_code=400,
            detail="Appointment is already paid.",
        )

    doctor = (
        db.query(Doctor)
        .filter(
            Doctor.id == appointment.doctor_id
        )
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found.",
        )

    amount_paise = int(
        float(doctor.consultation_fee) * 100
    )

    if amount_paise < 100:
        raise HTTPException(
            status_code=400,
            detail="Consultation fee must be at least ₹1.",
        )

    try:

        order, payment = create_razorpay_order(
            db=db,
            patient=patient,
            amount_paise=amount_paise,
            appointment_id=appointment.id,
        )

        return {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "payment_id": payment.id,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        db.rollback()

        print(
            "Razorpay order creation error:",
            str(error)
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to create Razorpay order.",
        )


@router.post("/api/verify-payment")
def verify_payment(
    payload: VerifyPaymentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    patient = get_current_patient(request, db)

    if not payload.razorpay_order_id:
        raise HTTPException(
            status_code=400,
            detail="Razorpay order ID is required.",
        )

    if not payload.razorpay_payment_id:
        raise HTTPException(
            status_code=400,
            detail="Razorpay payment ID is required.",
        )

    if not payload.razorpay_signature:
        raise HTTPException(
            status_code=400,
            detail="Razorpay signature is required.",
        )

    try:

        payment = complete_payment(
            db=db,
            patient=patient,
            order_id=payload.razorpay_order_id,
            payment_id=payload.razorpay_payment_id,
            signature=payload.razorpay_signature,
        )

        notify(db, patient.id, "Payment Successful", f"Payment #{payment.id} was verified successfully.")
        db.commit()
        send_email(patient, "Payment Successful", f"Your payment #{payment.id} was verified successfully.")

        return {
            "success": True,
            "message": "Payment verified successfully.",
            "payment_id": payment.id,
            "status": payment.payment_status,
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        db.rollback()

        print(
            "Payment verification error:",
            str(error)
        )

        raise HTTPException(
            status_code=500,
            detail="Payment verification failed.",
        )


@router.get(
    "/receipt/{payment_id}",
    response_class=HTMLResponse,
)
def payment_receipt(
    payment_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    patient = get_current_patient(request, db)

    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id,
            Payment.patient_id == patient.id,
        )
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment receipt not found.",
        )

    if payment.payment_status != "paid":
        raise HTTPException(
            status_code=400,
            detail="Receipt is available only after successful payment.",
        )

    appointment = None
    doctor = None

    if payment.appointment_id:

        appointment = (
            db.query(Appointment)
            .filter(
                Appointment.id == payment.appointment_id
            )
            .first()
        )

        if appointment:

            doctor = (
                db.query(Doctor)
                .filter(
                    Doctor.id == appointment.doctor_id
                )
                .first()
            )

    payment_date = (
        payment.payment_date
        or payment.created_at
        or datetime.now()
    )

    doctor_name = (
        doctor.name
        if doctor
        else "Doctor"
    )

    appointment_date = (
        str(appointment.appointment_date)
        if appointment
        else "N/A"
    )

    appointment_time = (
        str(appointment.appointment_time)
        if appointment
        else "N/A"
    )

    order_id = (
        payment.transaction_reference
        or "N/A"
    )

    razorpay_payment_id = (
        payment.razorpay_payment_id
        or "N/A"
    )

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>
            Payment Receipt - Sehat Saathi
        </title>

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <style>

            body {{
                margin: 0;
                padding: 30px;
                background: #f4f7fb;
                font-family: Arial, sans-serif;
            }}

            .receipt {{
                max-width: 650px;
                margin: 30px auto;
                background: white;
                padding: 35px;
                border-radius: 16px;
                box-shadow:
                    0 8px 30px rgba(0,0,0,0.08);
            }}

            .header {{
                text-align: center;
                border-bottom: 2px solid #e5e7eb;
                padding-bottom: 20px;
                margin-bottom: 25px;
            }}

            .header h1 {{
                margin: 0;
                color: #0f766e;
            }}

            .success {{
                display: inline-block;
                margin-top: 12px;
                padding: 8px 14px;
                border-radius: 20px;
                background: #dcfce7;
                color: #166534;
                font-weight: bold;
            }}

            .row {{
                display: flex;
                justify-content: space-between;
                gap: 20px;
                padding: 12px 0;
                border-bottom: 1px solid #eeeeee;
            }}

            .label {{
                color: #64748b;
            }}

            .value {{
                font-weight: bold;
                text-align: right;
            }}

            .total {{
                margin-top: 25px;
                padding: 18px;
                background: #f0fdfa;
                border-radius: 10px;
                display: flex;
                justify-content: space-between;
                font-size: 22px;
                font-weight: bold;
                color: #0f766e;
            }}

            .buttons {{
                display: flex;
                gap: 12px;
                margin-top: 25px;
            }}

            button,
            a {{
                flex: 1;
                padding: 13px;
                border: 0;
                border-radius: 9px;
                text-align: center;
                text-decoration: none;
                font-weight: bold;
                cursor: pointer;
            }}

            button {{
                background: #0f766e;
                color: white;
            }}

            a {{
                background: #e2e8f0;
                color: #334155;
            }}

            .footer {{
                text-align: center;
                margin-top: 30px;
                color: #64748b;
                font-size: 13px;
            }}

            @media print {{

                body {{
                    background: white;
                    padding: 0;
                }}

                .receipt {{
                    box-shadow: none;
                    margin: 0;
                    max-width: none;
                }}

                .buttons {{
                    display: none;
                }}

            }}

        </style>

    </head>


    <body>

        <div class="receipt">

            <div class="header">

                <h1>
                    🏥 Sehat Saathi
                </h1>

                <div class="success">
                    ✓ Payment Successful
                </div>

            </div>


            <div class="row">

                <span class="label">
                    Receipt ID
                </span>

                <span class="value">
                    #{payment.id}
                </span>

            </div>


            <div class="row">

                <span class="label">
                    Patient
                </span>

                <span class="value">
                    {patient.name}
                </span>

            </div>


            <div class="row">

                <span class="label">
                    Doctor
                </span>

                <span class="value">
                    {doctor_name}
                </span>

            </div>


            <div class="row">

                <span class="label">
                    Appointment
                </span>

                <span class="value">
                    #{payment.appointment_id or "N/A"}
                </span>

            </div>


            <div class="row">

                <span class="label">
                    Appointment Date
                </span>

                <span class="value">
                    {appointment_date}
                </span>

            </div>


            <div class="row">

                <span class="label">
                    Appointment Time
                </span>

                <span class="value">
                    {appointment_time}
                </span>

            </div>


            <div class="row">

                <span class="label">
                    Payment Date
                </span>

                <span class="value">
                    {payment_date.strftime("%d-%m-%Y %I:%M %p")}
                </span>

            </div>


            <div class="row">

                <span class="label">
                    Payment Method
                </span>

                <span class="value">
                    Razorpay
                </span>

            </div>


            <div class="row">

                <span class="label">
                    Razorpay Order ID
                </span>

                <span class="value">
                    {order_id}
                </span>

            </div>


            <div class="row">

                <span class="label">
                    Razorpay Payment ID
                </span>

                <span class="value">
                    {razorpay_payment_id}
                </span>

            </div>


            <div class="total">

                <span>
                    Total Paid
                </span>

                <span>
                    ₹{payment.amount}
                </span>

            </div>


            <div class="buttons">

                <button
                    onclick="window.print()"
                >
                    🖨️ Print Receipt
                </button>

                <a
                    href="/appointments/my"
                >
                    ← My Appointments
                </a>

            </div>


            <div class="footer">

                This is a computer-generated payment receipt.

                <br>

                Sehat Saathi Smart Clinic

            </div>

        </div>

    </body>

    </html>
    """