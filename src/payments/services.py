import hashlib
import hmac
import os
from uuid import uuid4

import razorpay
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from src.database.models import Appointment, Payment, User

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    raise RuntimeError("Razorpay credentials are not configured.")

razorpay_client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)


def create_razorpay_order(
    db: Session,
    patient: User,
    amount_paise: int,
    appointment_id: int | None = None,
):
    if amount_paise < 100:
        raise ValueError("Payment amount must be at least 100 paise.")

    appointment = None

    if appointment_id is not None:
        appointment = (
            db.query(Appointment)
            .filter(
                Appointment.id == appointment_id,
                Appointment.patient_id == patient.id,
            )
            .first()
        )

        if not appointment:
            raise ValueError("Appointment not found.")

        if appointment.status != "booked":
            raise ValueError("This appointment is not available for payment.")

        if appointment.payment_status == "paid":
            raise ValueError("This appointment is already paid.")

    receipt = f"clinic_{uuid4().hex[:30]}"

    order_data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
    }

    order = razorpay_client.order.create(data=order_data)

    payment = Payment(
        patient_id=patient.id,
        appointment_id=appointment_id,
        amount=amount_paise / 100,
        payment_method="razorpay",
        payment_status="pending",
        transaction_reference=order["id"],
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return order, payment


def verify_razorpay_signature(
    order_id: str,
    payment_id: str,
    signature: str,
):
    generated_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(
        generated_signature,
        signature,
    )


def complete_payment(
    db: Session,
    patient: User,
    order_id: str,
    payment_id: str,
    signature: str,
):
    payment = (
        db.query(Payment)
        .filter(
            Payment.transaction_reference == order_id,
            Payment.patient_id == patient.id,
        )
        .first()
    )

    if not payment:
        raise ValueError("Payment order not found.")

    if payment.payment_status == "paid":
        return payment

    is_valid = verify_razorpay_signature(
        order_id=order_id,
        payment_id=payment_id,
        signature=signature,
    )

    if not is_valid:
        raise ValueError("Payment signature verification failed.")

    payment.payment_status = "paid"
    payment.transaction_reference = payment_id

    from datetime import datetime

    payment.payment_date = datetime.now()

    if payment.appointment_id:
        appointment = (
            db.query(Appointment)
            .filter(Appointment.id == payment.appointment_id)
            .first()
        )

        if appointment:
            appointment.payment_status = "paid"

    db.commit()
    db.refresh(payment)

    return payment