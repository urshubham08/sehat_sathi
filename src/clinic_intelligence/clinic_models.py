from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    Numeric,
    String,
)

from src.database.database import Base


class ClinicStaff(Base):
    __tablename__ = "clinic_staff"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    designation = Column(String(100), nullable=False)
    mobile = Column(String(20), nullable=True)
    email = Column(String(150), nullable=True)
    monthly_salary = Column(Numeric(10, 2), nullable=False, default=0)
    status = Column(String(20), nullable=False, default="active")
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ClinicSalary(Base):
    __tablename__ = "clinic_salaries"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, nullable=False, index=True)
    month = Column(String(20), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_status = Column(String(20), nullable=False, default="pending")
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ClinicInventory(Base):
    __tablename__ = "clinic_inventory"

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=True)
    quantity = Column(Integer, nullable=False, default=0)
    unit = Column(String(50), nullable=True)
    minimum_stock = Column(Integer, nullable=False, default=5)
    supplier = Column(String(200), nullable=True)
    price = Column(Numeric(10, 2), nullable=False, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class ClinicTiming(Base):
    __tablename__ = "clinic_timings"

    id = Column(Integer, primary_key=True, index=True)
    day = Column(String(20), nullable=False, unique=True)
    opening_time = Column(String(10), nullable=True)
    closing_time = Column(String(10), nullable=True)
    break_start = Column(String(10), nullable=True)
    break_end = Column(String(10), nullable=True)
    is_open = Column(Boolean, default=True, nullable=False)