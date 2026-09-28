from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Enum, Text
from sqlalchemy.orm import relationship
import datetime
import enum
from database import Base

# 1. Enums
class InvoiceStatus(enum.Enum):
    PENDING = "PENDING"
    STRAIGHT_THROUGH = "STRAIGHT_THROUGH"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RESOLVED = "RESOLVED"
    PAID = "PAID"

# 2. Parent Table: Vendors
class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    vendor_code = Column(String, unique=True, index=True)
    
    invoices = relationship("Invoice", back_populates="vendor")
    pos = relationship("PurchaseOrder", back_populates="vendor")
    memory_profile = relationship("VendorMemoryProfile", back_populates="vendor", uselist=False)
    feedbacks = relationship("ClerkFeedback", back_populates="vendor")
    hindsight_memories = relationship("HindsightMemory", back_populates="vendor")

# 3. Parent Table: Purchase Orders
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String, unique=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    total_amount = Column(Float)
    status = Column(String)
    # Stores expected line items as a JSON list of {description, quantity, unit_price, total}
    line_items = Column(JSON, nullable=True)

    vendor = relationship("Vendor", back_populates="pos")
    invoices = relationship("Invoice", back_populates="po")

# 4. Parent Table: Contracts
class Contract(Base):
    __tablename__ = "contracts"
    id = Column(Integer, primary_key=True, index=True)
    contract_number = Column(String, unique=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    max_amount = Column(Float)
    
    invoices = relationship("Invoice", back_populates="contract")

# 5. Child Table: Invoices (References Vendors, POs, and Contracts)
class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    po_number = Column(String, ForeignKey("purchase_orders.po_number"), nullable=True)
    contract_number = Column(String, ForeignKey("contracts.contract_number"), nullable=True)
    
    total_amount = Column(Float)
    tax_amount = Column(Float)
    currency = Column(String, default="USD")
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.PENDING)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    vendor = relationship("Vendor", back_populates="invoices")
    po = relationship("PurchaseOrder", back_populates="invoices")
    contract = relationship("Contract", back_populates="invoices")
    audit_logs = relationship("AuditLog", back_populates="invoice")
    exceptions = relationship("InvoiceException", back_populates="invoice")
    feedbacks = relationship("ClerkFeedback", back_populates="invoice")

# 6. Supporting Tables
class InvoiceException(Base):
    __tablename__ = "invoice_exceptions"
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    exception_type = Column(String)
    description = Column(Text)
    
    invoice = relationship("Invoice", back_populates="exceptions")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    agent_name = Column(String, nullable=True)
    action = Column(String)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    invoice = relationship("Invoice", back_populates="audit_logs")

# 7. Memory & Feedback Loop Tables
class ClerkFeedback(Base):
    __tablename__ = "clerk_feedbacks"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    action = Column(String)  # "APPROVE", "REJECT", "RESOLVE"
    reason = Column(Text)
    exception_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    invoice = relationship("Invoice", back_populates="feedbacks")
    vendor = relationship("Vendor", back_populates="feedbacks")

class HindsightMemory(Base):
    __tablename__ = "hindsight_memories"
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    invoice_number = Column(String, nullable=True)
    po_number = Column(String, nullable=True)
    issue_type = Column(String, nullable=True)
    issue_summary = Column(Text)
    clerk_action = Column(String)  # "APPROVE", "REJECT", "RESOLVE"
    clerk_reason = Column(Text)
    resolution_context = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    vendor = relationship("Vendor", back_populates="hindsight_memories")

class VendorMemoryProfile(Base):
    __tablename__ = "vendor_memory_profiles"
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), unique=True)
    total_invoices_processed = Column(Integer, default=0)
    total_approved = Column(Integer, default=0)
    total_rejected = Column(Integer, default=0)
    reliability_score = Column(Float, default=100.0)
    common_issues = Column(JSON, default=dict)       # e.g., {"PO_MISMATCH": 4, "TAX_DISCREPANCY": 1}
    recurring_mismatches = Column(JSON, default=list) # e.g., ["Price variance on Dell Latitude", ...]
    typical_resolutions = Column(JSON, default=dict) # e.g., {"PO_MISMATCH": "Approved after PO verification"}
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    vendor = relationship("Vendor", back_populates="memory_profile")