from .database import Base, engine

from .models import (
    User,
    LoginHistory,
    PatientProfile,
    MedicalHistory
)

Base.metadata.create_all(bind=engine)

print("✅ Database tables created successfully!")