import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine, Base
import models.models  # ensures all tables are registered
from models.models import Vendor, PurchaseOrder, Contract, HindsightMemory
from services.memory_service import MemoryService

Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    vendors_data = [
        {"code": "DELL-001", "name": "Dell Technologies Inc."},
        {"code": "HPE-002",  "name": "HP Enterprise"},
        {"code": "LNV-003",  "name": "Lenovo Global Solutions"},
        {"code": "ACM-004",  "name": "Acme Supplies Ltd."},
        {"code": "STP-005",  "name": "Staples Business Products"},
    ]

    created_vendors = {}
    for vd in vendors_data:
        v = db.query(Vendor).filter(Vendor.vendor_code == vd["code"]).first()
        if not v:
            v = Vendor(name=vd["name"], vendor_code=vd["code"])
            db.add(v)
            db.flush()
            print(f"OK: Vendor created: {vd['name']} ({vd['code']})")
        else:
            print(f"INFO: Vendor {vd['code']} exists.")
        created_vendors[vd["code"]] = v

    # --- Purchase Orders ---
    pos_data = [
        {
            "po_number": "PO-DELL-2024",
            "vendor_code": "DELL-001",
            "total": 10775.00,
            "items": [
                {"description": "Dell Latitude 5540 Laptop",     "quantity": 10.0, "unit_price": 850.00, "total": 8500.00},
                {"description": 'Dell 27" Monitor P2723D',        "quantity": 5.0,  "unit_price": 320.00, "total": 1600.00},
                {"description": "Dell Wireless Keyboard & Mouse", "quantity": 15.0, "unit_price": 45.00,  "total": 675.00},
            ],
        },
        {
            "po_number": "PO-HPE-8800",
            "vendor_code": "HPE-002",
            "total": 24500.00,
            "items": [
                {"description": "HPE ProLiant DL380 Server", "quantity": 2.0, "unit_price": 12250.00, "total": 24500.00},
            ],
        },
        {
            "po_number": "PO-LNV-3300",
            "vendor_code": "LNV-003",
            "total": 15000.00,
            "items": [
                {"description": "ThinkPad X1 Carbon Gen 11", "quantity": 10.0, "unit_price": 1500.00, "total": 15000.00},
            ],
        },
        {
            "po_number": "PO-ACM-1100",
            "vendor_code": "ACM-004",
            "total": 4500.00,
            "items": [
                {"description": "Industrial Paper Stock", "quantity": 100.0, "unit_price": 45.00, "total": 4500.00},
            ],
        },
    ]

    for pd in pos_data:
        po = db.query(PurchaseOrder).filter(PurchaseOrder.po_number == pd["po_number"]).first()
        if not po:
            v = created_vendors[pd["vendor_code"]]
            po = PurchaseOrder(
                po_number=pd["po_number"],
                vendor_id=v.id,
                total_amount=pd["total"],
                status="OPEN",
                line_items=pd["items"],
            )
            db.add(po)
            print(f"OK: PO created: {pd['po_number']}")

    # --- Contracts ---
    contracts_data = [
        {"contract_number": "CTR-DELL-2024", "vendor_code": "DELL-001", "max_amount": 50000.00},
        {"contract_number": "CTR-HPE-2024",  "vendor_code": "HPE-002",  "max_amount": 100000.00},
        {"contract_number": "CTR-LNV-2024",  "vendor_code": "LNV-003",  "max_amount": 75000.00},
        {"contract_number": "CTR-ACM-2024",  "vendor_code": "ACM-004",  "max_amount": 5000.00},
    ]

    for cd in contracts_data:
        ctr = db.query(Contract).filter(Contract.contract_number == cd["contract_number"]).first()
        if not ctr:
            v = created_vendors[cd["vendor_code"]]
            ctr = Contract(
                contract_number=cd["contract_number"],
                vendor_id=v.id,
                max_amount=cd["max_amount"],
            )
            db.add(ctr)
            print(f"OK: Contract created: {cd['contract_number']}")

    db.commit()

    # --- Hindsight Memory & Vendor Memory Profiles ---
    mem_service = MemoryService(db)
    dell_v = created_vendors["DELL-001"]
    dell_profile = mem_service.get_or_create_vendor_profile(dell_v.id)
    if dell_profile.total_invoices_processed == 0:
        dell_profile.total_invoices_processed = 10
        dell_profile.total_approved = 9
        dell_profile.total_rejected = 1
        dell_profile.reliability_score = 90.0
        dell_profile.common_issues = {"PO_MISMATCH": 4}
        dell_profile.recurring_mismatches = ["Minor price variance on Latitude laptops"]
        dell_profile.typical_resolutions = {"PO_MISMATCH": "Approved after PO line item price check"}
        db.commit()

        hindsight_entries = [
            HindsightMemory(
                vendor_id=dell_v.id,
                invoice_number="HIST-DELL-001",
                po_number="PO-DELL-2024",
                issue_type="PO_MISMATCH",
                issue_summary="Unit price variance ($850 PO vs $865 invoice)",
                clerk_action="APPROVE",
                clerk_reason="Approved after PO line item price check with procurement manager.",
            ),
            HindsightMemory(
                vendor_id=dell_v.id,
                invoice_number="HIST-DELL-002",
                po_number="PO-DELL-2024",
                issue_type="PO_MISMATCH",
                issue_summary="Minor line item description difference",
                clerk_action="APPROVE",
                clerk_reason="Verified PO spec aligns with delivered monitor.",
            ),
            HindsightMemory(
                vendor_id=created_vendors["HPE-002"].id,
                invoice_number="HIST-HPE-001",
                po_number="PO-HPE-8800",
                issue_type="TAX_DISCREPANCY",
                issue_summary="State GST rounding difference ($2.50)",
                clerk_action="RESOLVE",
                clerk_reason="Resolved rounding variance within tolerance limit.",
            ),
            HindsightMemory(
                vendor_id=created_vendors["ACM-004"].id,
                invoice_number="HIST-ACM-001",
                po_number="PO-ACM-1100",
                issue_type="CONTRACT_VIOLATION",
                issue_summary="Invoice amount exceeds approved contract ceiling",
                clerk_action="REJECT",
                clerk_reason="Contract max amount exceeded without change order.",
            ),
        ]
        for h in hindsight_entries:
            db.add(h)
        db.commit()
        print("OK: Initialized hindsight memories & vendor memory profiles.")

    print("\nDatabase seeded successfully!")

except Exception as exc:
    db.rollback()
    print(f"ERROR: {exc}")
    raise
finally:
    db.close()

