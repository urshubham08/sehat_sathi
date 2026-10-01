from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from src.database.database import Base


class UserPermission(Base):
    __tablename__ = "user_permissions"

    id = Column(Integer, primary_key=True, index=True)
from src.pharmacy.models import PharmacyStaffPermission


# Backward compatibility:
# Old UserPermission name is now mapped to the
# single pharmacy staff permission model.
UserPermission = PharmacyStaffPermission

__all__ = [
    "UserPermission",
    "PharmacyStaffPermission",
]
user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
        index=True,
    )

patients = Column(Boolean, default=False, nullable=False)
appointments = Column(Boolean, default=False, nullable=False)
medical_reports = Column(Boolean, default=False, nullable=False)
prescriptions = Column(Boolean, default=False, nullable=False)
doctors = Column(Boolean, default=False, nullable=False)

pharmacy = Column(Boolean, default=False, nullable=False)
medicines = Column(Boolean, default=False, nullable=False)
stock = Column(Boolean, default=False, nullable=False)
pharmacy_orders = Column(Boolean, default=False, nullable=False)
billing = Column(Boolean, default=False, nullable=False)

payments = Column(Boolean, default=False, nullable=False)
analytics = Column(Boolean, default=False, nullable=False)
staff_management = Column(Boolean, default=False, nullable=False)

created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )