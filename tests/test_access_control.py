import os

os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "smart_clinic")

from src.clinic_intelligence import can_access_patient


class U:
    def __init__(self, role, uid):
        self.role = role
        self.id = uid
        self.email = f"u{uid}@example.com"


def test_patient_can_access_self():
    assert can_access_patient(U("patient", 7), 7, None) is True


def test_patient_cannot_access_other():
    assert can_access_patient(U("patient", 7), 8, None) is False
