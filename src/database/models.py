from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    email = Column(
        String(150),
        unique=True,
        nullable=False,
        index=True,
    )

    mobile = Column(
        String(20),
        unique=True,
        nullable=False,
    )

    password_hash = Column(
        String(255),
        nullable=False,
    )

    role = Column(
        String(20),
        nullable=False,
        default="patient",
    )

    is_active = Column(
        Boolean,
        default=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    last_login_at = Column(
        DateTime,
        nullable=True,
    )

    last_logout_at = Column(
        DateTime,
        nullable=True,
    )

    is_logged_in = Column(
        Boolean,
        default=False,
        nullable=False,
    )


class LoginHistory(Base):
    __tablename__ = "login_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    login_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    logout_at = Column(
        DateTime,
        nullable=True,
    )

    is_successful = Column(
        Boolean,
        default=True,
        nullable=False,
    )


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
    )

    date_of_birth = Column(
        DateTime,
        nullable=True,
    )

    gender = Column(
        String(20),
        nullable=True,
    )

    blood_group = Column(
        String(10),
        nullable=True,
    )

    allergies = Column(
        String(1000),
        nullable=True,
    )

    existing_conditions = Column(
        String(1000),
        nullable=True,
    )

    previous_medical_history = Column(
        String(2000),
        nullable=True,
    )

    emergency_contact_name = Column(
        String(100),
        nullable=True,
    )

    emergency_contact_mobile = Column(
        String(20),
        nullable=True,
    )

    address = Column(
        String(1000),
        nullable=True,
    )

    village = Column(
        String(100),
        nullable=True,
    )

    city = Column(
        String(100),
        nullable=True,
    )

    state = Column(
        String(100),
        nullable=True,
    )

    pincode = Column(
        String(10),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MedicalHistory(Base):
    __tablename__ = "medical_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    visit_date = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    symptoms = Column(
        String(2000),
        nullable=True,
    )

    diagnosis = Column(
        String(2000),
        nullable=True,
    )

    treatment = Column(
        String(2000),
        nullable=True,
    )

    doctor_notes = Column(
        String(3000),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )


class Payment(Base):
    __tablename__ = "payments"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    patient_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    appointment_id = Column(
        Integer,
        nullable=True,
    )

    amount = Column(
        Numeric(10, 2),
        nullable=False,
    )

    payment_method = Column(
        String(20),
        nullable=False,
    )

    payment_status = Column(
        String(20),
        nullable=False,
        default="pending",
    )

    transaction_reference = Column(
        String(150),
        nullable=True,
    )

    razorpay_payment_id = Column(
        String(150),
        nullable=True,
    )

    payment_date = Column(
        DateTime,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        unique=True,
        index=True,
    )

    name = Column(
        String(150),
        nullable=False,
    )

    specialty = Column(
        String(100),
        nullable=False,
    )

    qualification = Column(
        String(200),
        nullable=True,
    )

    experience_years = Column(
        Integer,
        nullable=True,
    )

    consultation_fee = Column(
        Numeric(10, 2),
        nullable=False,
        default=0.00,
    )

    availability_status = Column(
        String(20),
        nullable=False,
        default="active",
    )

    phone = Column(
        String(20),
        nullable=True,
    )

    email = Column(
        String(150),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    patient_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=False,
        index=True,
    )

    appointment_date = Column(
        Date,
        nullable=False,
    )

    appointment_time = Column(
        String(10),
        nullable=False,
    )

    status = Column(
        String(20),
        nullable=False,
        default="booked",
    )

    payment_status = Column(
        String(20),
        nullable=False,
        default="pending",
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )


class MedicalReport(Base):
    __tablename__ = "medical_reports"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    patient_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    original_filename = Column(
        String(255),
        nullable=False,
    )

    stored_filename = Column(
        String(255),
        nullable=False,
        unique=True,
    )

    file_path = Column(
        String(500),
        nullable=False,
    )

    file_size = Column(
        Integer,
        nullable=False,
    )

    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


class PrescriptionPhoto(Base):
    __tablename__ = "prescription_photos"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    patient_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    original_filename = Column(
        String(255),
        nullable=False,
    )

    stored_filename = Column(
        String(255),
        nullable=False,
        unique=True,
    )

    file_path = Column(
        String(500),
        nullable=False,
    )

    file_size = Column(
        Integer,
        nullable=False,
    )

    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(String(2000), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reminder_at = Column(DateTime, nullable=False)
    note = Column(String(1000), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(100), nullable=True)
    target_id = Column(Integer, nullable=True)
    details = Column(String(4000), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class ClinicSetting(Base):
    __tablename__ = "clinic_settings"
    id = Column(Integer, primary_key=True, default=1)
    clinic_name = Column(String(200), nullable=False, default="Sanjeevani Smart Clinic")
    owner_name = Column(String(150), nullable=True)
    license_number = Column(String(150), nullable=True)
    address = Column(String(1000), nullable=True)
    phone = Column(String(30), nullable=True)
    stamp_path = Column(String(500), nullable=True)
    signature_path = Column(String(500), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class DoctorDocument(Base):
    __tablename__ = "doctor_documents"
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(String(8000), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
