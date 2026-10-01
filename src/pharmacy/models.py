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

from src.database.database import Base


# ============================================================
# PHARMACY STAFF PERMISSIONS
# ============================================================

class PharmacyStaffPermission(Base):
    __tablename__ = "pharmacy_staff_permissions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    medicine_manage = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    stock_manage = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    supplier_manage = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    purchase_manage = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    order_manage = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    billing_manage = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    reports_view = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    prescription_verify = Column(
        Boolean,
        default=True,
        nullable=False,
    )

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


# ============================================================
# MEDICINE
# ============================================================

class PharmacyMedicine(Base):
    __tablename__ = "pharmacy_medicines"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(
        String(200),
        nullable=False,
        index=True,
    )

    generic_name = Column(
        String(200),
        nullable=True,
    )

    category = Column(
        String(100),
        nullable=True,
    )

    manufacturer = Column(
        String(200),
        nullable=True,
    )

    description = Column(
        String(1000),
        nullable=True,
    )

    unit = Column(
        String(50),
        default="strip",
        nullable=False,
    )

    reorder_level = Column(
        Integer,
        default=10,
        nullable=False,
    )

    is_prescription_required = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

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


# ============================================================
# MEDICINE BATCH
# ============================================================

class PharmacyBatch(Base):
    __tablename__ = "pharmacy_batches"

    id = Column(Integer, primary_key=True, index=True)

    medicine_id = Column(
        Integer,
        ForeignKey("pharmacy_medicines.id"),
        nullable=False,
        index=True,
    )

    batch_number = Column(
        String(100),
        nullable=False,
        index=True,
    )

    expiry_date = Column(
        Date,
        nullable=False,
        index=True,
    )

    quantity = Column(
        Integer,
        default=0,
        nullable=False,
    )

    purchase_price = Column(
        Numeric(10, 2),
        default=0,
        nullable=False,
    )

    selling_price = Column(
        Numeric(10, 2),
        default=0,
        nullable=False,
    )

    supplier_id = Column(
        Integer,
        ForeignKey("pharmacy_suppliers.id"),
        nullable=True,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

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


# ============================================================
# SUPPLIER
# ============================================================

class PharmacySupplier(Base):
    __tablename__ = "pharmacy_suppliers"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(
        String(200),
        nullable=False,
    )

    mobile = Column(
        String(30),
        nullable=True,
    )

    email = Column(
        String(150),
        nullable=True,
    )

    address = Column(
        String(1000),
        nullable=True,
    )

    gst_number = Column(
        String(50),
        nullable=True,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# ============================================================
# PURCHASE
# ============================================================

class PharmacyPurchase(Base):
    __tablename__ = "pharmacy_purchases"

    id = Column(Integer, primary_key=True, index=True)

    supplier_id = Column(
        Integer,
        ForeignKey("pharmacy_suppliers.id"),
        nullable=True,
    )

    medicine_id = Column(
        Integer,
        ForeignKey("pharmacy_medicines.id"),
        nullable=False,
    )

    batch_id = Column(
        Integer,
        ForeignKey("pharmacy_batches.id"),
        nullable=False,
    )

    quantity = Column(
        Integer,
        nullable=False,
    )

    total_amount = Column(
        Numeric(10, 2),
        default=0,
        nullable=False,
    )

    invoice_number = Column(
        String(100),
        nullable=True,
    )

    purchased_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )


# ============================================================
# PHARMACY ORDER
# ============================================================

class PharmacyOrder(Base):
    __tablename__ = "pharmacy_orders"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    prescription_id = Column(
        Integer,
        nullable=True,
        index=True,
    )

    status = Column(
        String(30),
        default="pending",
        nullable=False,
    )

    total_amount = Column(
        Numeric(10, 2),
        default=0,
        nullable=False,
    )

    payment_status = Column(
        String(30),
        default="pending",
        nullable=False,
    )

    notes = Column(
        String(1000),
        nullable=True,
    )

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

    processed_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )


# ============================================================
# SALES / BILL
# ============================================================

class PharmacySale(Base):
    __tablename__ = "pharmacy_sales"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    order_id = Column(
        Integer,
        ForeignKey("pharmacy_orders.id"),
        nullable=True,
    )

    invoice_number = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    subtotal = Column(
        Numeric(10, 2),
        default=0,
        nullable=False,
    )

    discount = Column(
        Numeric(10, 2),
        default=0,
        nullable=False,
    )

    total_amount = Column(
        Numeric(10, 2),
        default=0,
        nullable=False,
    )

    payment_method = Column(
        String(50),
        default="cash",
        nullable=False,
    )

    payment_status = Column(
        String(30),
        default="paid",
        nullable=False,
    )

    sold_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )


# ============================================================
# SALE ITEM
# ============================================================

class PharmacySaleItem(Base):
    __tablename__ = "pharmacy_sale_items"

    id = Column(Integer, primary_key=True, index=True)

    sale_id = Column(
        Integer,
        ForeignKey("pharmacy_sales.id"),
        nullable=False,
    )

    medicine_id = Column(
        Integer,
        ForeignKey("pharmacy_medicines.id"),
        nullable=False,
    )

    batch_id = Column(
        Integer,
        ForeignKey("pharmacy_batches.id"),
        nullable=False,
    )

    quantity = Column(
        Integer,
        nullable=False,
    )

    unit_price = Column(
        Numeric(10, 2),
        nullable=False,
    )

    total_price = Column(
        Numeric(10, 2),
        nullable=False,
    )


# ============================================================
# STOCK MOVEMENT
# ============================================================

class PharmacyStockMovement(Base):
    __tablename__ = "pharmacy_stock_movements"

    id = Column(Integer, primary_key=True, index=True)

    medicine_id = Column(
        Integer,
        ForeignKey("pharmacy_medicines.id"),
        nullable=False,
        index=True,
    )

    batch_id = Column(
        Integer,
        ForeignKey("pharmacy_batches.id"),
        nullable=False,
    )

    movement_type = Column(
        String(30),
        nullable=False,
    )

    quantity = Column(
        Integer,
        nullable=False,
    )

    reference_type = Column(
        String(50),
        nullable=True,
    )

    reference_id = Column(
        Integer,
        nullable=True,
    )

    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )