import os
import uuid
from dotenv import load_dotenv

# Load environment variables before any other imports
load_dotenv()

from fastapi import FastAPI, UploadFile, Depends, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
import uvicorn
import logging

from pydantic import BaseModel
from typing import Optional

from database import get_db, engine, Base
from tools.ocr_engine import OCREngine, OCRError
from agents.graph import app_agent
from models.models import (
    Invoice,
    InvoiceStatus,
    AuditLog,
    InvoiceException,
    Vendor,
    PurchaseOrder,
    Contract,
    ClerkFeedback,
    HindsightMemory,
    VendorMemoryProfile,
)
from repositories.invoice_repo import InvoiceRepository
from services.memory_service import MemoryService

logger = logging.getLogger("ap_agent.api")
logging.basicConfig(level=logging.INFO)

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AP Invoice Exception Agent",
    description="Automated Accounts Payable invoice processing with AI-driven exception detection and Hindsight Memory.",
    version="1.2.0",
)


class ClerkFeedbackRequest(BaseModel):
    action: str  # "APPROVE", "REJECT", "RESOLVE"
    reason: str
    exception_type: Optional[str] = None


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
def health_check():
    return {
        "status": "online",
        "agent": "AP Invoice Agent with Hindsight Memory",
        "version": "1.2.0",
        "database": "connected",
    }


# ---------------------------------------------------------------------------
# POST /seed-db — seeds multi-vendor reference data, POs, Contracts & Memory
# ---------------------------------------------------------------------------

@app.post("/seed-db", tags=["Health"])
def seed_db(db: Session = Depends(get_db)):
    """
    Seeds database with multi-vendor profiles (Dell, HPE, Lenovo, Acme, Staples),
    POs, Contracts, historical invoices, and hindsight memory entries.
    Safe to call multiple times.
    """
    results = []

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
                results.append(f"Vendor created: {vd['name']} ({vd['code']})")
            else:
                results.append(f"Vendor {vd['code']} exists.")
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
                results.append(f"PO created: {pd['po_number']}")

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
                results.append(f"Contract created: {cd['contract_number']}")

        db.commit()

        # --- Seed Hindsight Memories & Vendor Profiles ---
        mem_service = MemoryService(db)

        # Seed Dell historical hindsight memory (Dell price mismatches previously approved)
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

            # Add historical hindsight memory records
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
            results.append("Historical hindsight memories & per-vendor memory profiles initialized.")

        return {"status": "ok", "results": results}

    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"seed_db error: {exc}")
        raise HTTPException(status_code=500, detail=f"Seed failed: {exc}")


@app.get("/diag", tags=["Health"])
def diag():
    import requests as http_requests
    import time

    groq_key = os.getenv("GROQ_API_KEY")
    key_info = {
        "present": bool(groq_key),
        "length": len(groq_key) if groq_key else 0,
        "prefix": (groq_key[:7] + "***") if groq_key and len(groq_key) > 7 else "TOO_SHORT",
    }

    probe = {}
    try:
        t0 = time.time()
        r = http_requests.get("https://api.groq.com", timeout=15)
        probe = {
            "reachable": True,
            "status_code": r.status_code,
            "elapsed_s": round(time.time() - t0, 2),
            "body_preview": r.text[:300],
        }
    except Exception as exc:
        import traceback
        probe = {
            "reachable": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }

    return {"groq_api_key": key_info, "groq_connectivity": probe}


# ---------------------------------------------------------------------------
# POST /upload-invoice — main processing endpoint
# ---------------------------------------------------------------------------

@app.post("/upload-invoice", tags=["Processing"])
async def process_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Accepts a PDF or image invoice, runs the full agent pipeline (with memory recall),
    and returns structured result including extracted fields, decorated exceptions,
    recalled memory intelligence, decision, and reasoning chain.
    """
    allowed_types = {"application/pdf", "image/png", "image/jpeg", "image/jpg"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Accepted: PDF, PNG, JPG.",
        )

    try:
        content = await file.read()
    except Exception as exc:
        logger.error(f"Failed to read uploaded file: {exc}")
        raise HTTPException(status_code=400, detail="Could not read uploaded file.")

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # --- OCR ---
    try:
        raw_text = OCREngine.extract_text(content, file.content_type)
    except OCRError as exc:
        logger.error(f"OCR failed: {exc}")
        raise HTTPException(status_code=422, detail=f"OCR extraction failed: {exc}")
    except Exception as exc:
        logger.error(f"Unexpected OCR error: {exc}")
        raise HTTPException(status_code=500, detail="Unexpected error during OCR processing.")

    # --- Persist initial PENDING invoice record ---
    try:
        repo = InvoiceRepository(db)
        invoice = Invoice(
            invoice_number=f"PENDING-{uuid.uuid4().hex[:8]}-{file.filename}",
            status=InvoiceStatus.PENDING,
            total_amount=0.0,
            tax_amount=0.0,
            currency="USD",
        )
        invoice = repo.save_invoice(invoice)
        invoice_id = invoice.id
    except SQLAlchemyError as exc:
        logger.error(f"Database error saving invoice: {exc}")
        raise HTTPException(status_code=500, detail="Database error while creating invoice record.")

    # --- Run agent pipeline ---
    initial_state = {
        "raw_text": raw_text,
        "extracted_data": {},
        "exceptions": [],
        "status": "PENDING",
        "reasoning": ["File received. Starting extraction..."],
        "invoice_id": invoice_id,
    }

    try:
        final_state = await app_agent.ainvoke(initial_state)
    except Exception as exc:
        logger.error(f"Agent pipeline error for invoice {invoice_id}: {exc}")
        try:
            repo.update_invoice_status(invoice_id, InvoiceStatus.REJECTED)
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail=f"Agent pipeline encountered an unexpected error: {exc}",
        )

    # --- Update invoice record with extracted values ---
    extracted = final_state.get("extracted_data", {})
    agent_status = final_state.get("status", "EXCEPTION")
    exceptions_list = list(final_state.get("exceptions", []))
    recalled_mem = final_state.get("recalled_memory", {})

    status_map = {
        "STRAIGHT_THROUGH": InvoiceStatus.STRAIGHT_THROUGH,
        "EXCEPTION": InvoiceStatus.REVIEW_REQUIRED,
        "EXTRACTION_FAILED": InvoiceStatus.REJECTED,
    }
    db_status = status_map.get(agent_status, InvoiceStatus.REVIEW_REQUIRED)
    extracted_invoice_number = extracted.get("invoice_number")

    try:
        db.expire_all()

        # Link Vendor ID to Invoice if match found
        v_name = extracted.get("vendor_name")
        v_code = extracted.get("vendor_id")
        vendor_match = None
        if v_code:
            vendor_match = repo.get_vendor_by_code(v_code)
        if not vendor_match and v_name:
            vendor_match = repo.get_vendor_by_name(v_name)
        if vendor_match:
            invoice.vendor_id = vendor_match.id

        # --- Duplicate invoice number detection ---
        if extracted_invoice_number:
            existing = (
                db.query(Invoice)
                .filter(
                    Invoice.invoice_number == extracted_invoice_number,
                    Invoice.id != invoice_id,
                )
                .first()
            )
            if existing:
                try:
                    existing_status = existing.status.value
                except Exception:
                    existing_status = str(existing.status)
                exceptions_list.append({
                    "type": "DUPLICATE_INVOICE",
                    "description": (
                        f"Invoice number '{extracted_invoice_number}' was already submitted "
                        f"(existing record ID: {existing.id}, status: {existing_status}). "
                        "Duplicate invoices must be reviewed manually."
                    ),
                    "priority": "HIGH",
                    "suggested_resolution": "REJECT as duplicate invoice.",
                    "recommendation": "Hard Rule Triggered: Duplicate invoice submission.",
                })
                agent_status = "EXCEPTION"
                db_status = InvoiceStatus.REVIEW_REQUIRED

        invoice.invoice_number = extracted_invoice_number or invoice.invoice_number
        invoice.po_number = extracted.get("po_number")
        invoice.contract_number = extracted.get("contract_number")
        invoice.total_amount = extracted.get("total_amount") or 0.0
        invoice.tax_amount = extracted.get("tax_amount") or 0.0
        invoice.currency = extracted.get("currency") or "USD"
        invoice.status = db_status
        db.commit()

        if exceptions_list:
            repo.save_exceptions(invoice_id, exceptions_list)

    except SQLAlchemyError as exc:
        logger.error(f"Database error updating invoice {invoice_id}: {exc}")
        db.rollback()

    extraction_error = None
    for step in final_state.get("reasoning", []):
        if step.startswith("Extraction failed:"):
            extraction_error = step
            break

    return {
        "invoice_id": invoice_id,
        "invoice_number": invoice.invoice_number,
        "status": agent_status,
        "extracted_fields": extracted,
        "exceptions": exceptions_list,
        "recalled_memory": recalled_mem,
        "reasoning": final_state.get("reasoning", []),
        "extraction_error": extraction_error,
    }


# ---------------------------------------------------------------------------
# POST /invoice/{invoice_id}/feedback — AP Clerk Decision & Feedback Loop
# ---------------------------------------------------------------------------

@app.post("/invoice/{invoice_id}/feedback", tags=["Clerk Feedback"])
def record_feedback(
    invoice_id: int,
    req: ClerkFeedbackRequest,
    db: Session = Depends(get_db),
):
    """
    Accepts AP Clerk resolution (APPROVE, REJECT, RESOLVE) along with explanation.
    Updates invoice status, stores feedback memory, updates hindsight memories,
    and recalculates vendor reliability scores.
    """
    try:
        mem_service = MemoryService(db)
        res = mem_service.record_clerk_feedback(
            invoice_id=invoice_id,
            action=req.action,
            reason=req.reason,
            exception_type=req.exception_type,
        )

        repo = InvoiceRepository(db)
        repo.create_audit_log(
            invoice_id=invoice_id,
            agent_name="clerk_feedback",
            action=f"CLERK_{req.action.upper()}",
            details={"reason": req.reason, "exception_type": req.exception_type},
        )
        return res
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Error recording feedback for invoice {invoice_id}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to record clerk feedback.")


# ---------------------------------------------------------------------------
# Memory & Vendor APIs
# ---------------------------------------------------------------------------

@app.get("/vendors", tags=["Memory & Vendors"])
def get_vendors(db: Session = Depends(get_db)):
    """
    Returns all vendors with their memory profile summaries and reliability scores.
    """
    vendors = db.query(Vendor).all()
    mem_service = MemoryService(db)
    res = []
    for v in vendors:
        prof = mem_service.get_or_create_vendor_profile(v.id)
        res.append({
            "id": v.id,
            "name": v.name,
            "vendor_code": v.vendor_code,
            "reliability_score": prof.reliability_score,
            "total_invoices_processed": prof.total_invoices_processed,
            "total_approved": prof.total_approved,
            "total_rejected": prof.total_rejected,
            "common_issues": prof.common_issues or {},
            "typical_resolutions": prof.typical_resolutions or {},
        })
    return res


@app.get("/vendor/{vendor_id}/memory", tags=["Memory & Vendors"])
def get_vendor_memory(vendor_id: int, db: Session = Depends(get_db)):
    """
    Returns memory profile, historical hindsight memories, and clerk resolutions for a vendor.
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found.")

    mem_service = MemoryService(db)
    prof = mem_service.get_or_create_vendor_profile(vendor_id)
    memories = (
        db.query(HindsightMemory)
        .filter(HindsightMemory.vendor_id == vendor_id)
        .order_by(HindsightMemory.created_at.desc())
        .all()
    )

    return {
        "vendor": {"id": vendor.id, "name": vendor.name, "vendor_code": vendor.vendor_code},
        "profile": {
            "reliability_score": prof.reliability_score,
            "total_invoices_processed": prof.total_invoices_processed,
            "total_approved": prof.total_approved,
            "total_rejected": prof.total_rejected,
            "common_issues": prof.common_issues or {},
            "recurring_mismatches": prof.recurring_mismatches or [],
            "typical_resolutions": prof.typical_resolutions or {},
        },
        "hindsight_memories": [
            {
                "id": m.id,
                "invoice_number": m.invoice_number,
                "po_number": m.po_number,
                "issue_type": m.issue_type,
                "issue_summary": m.issue_summary,
                "clerk_action": m.clerk_action,
                "clerk_reason": m.clerk_reason,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in memories
        ],
    }


@app.get("/memories/recent", tags=["Memory & Vendors"])
def get_recent_memories(limit: int = 5, db: Session = Depends(get_db)):
    """
    Returns the most recent 3-5 HindsightMemory records from the database.
    """
    memories = (
        db.query(HindsightMemory)
        .order_by(HindsightMemory.created_at.desc())
        .limit(limit)
        .all()
    )
    res = []
    for m in memories:
        v_name = m.vendor.name if m.vendor else "Vendor"
        res.append({
            "id": m.id,
            "vendor_name": v_name,
            "invoice_number": m.invoice_number,
            "po_number": m.po_number,
            "issue_type": m.issue_type,
            "issue_summary": m.issue_summary,
            "clerk_action": m.clerk_action,
            "clerk_reason": m.clerk_reason,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return res


# ---------------------------------------------------------------------------
# GET /invoices — list all invoices
# ---------------------------------------------------------------------------


@app.get("/invoices", tags=["Invoices"])
def list_invoices(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Returns a paginated list of all invoices with their current status.
    """
    try:
        invoices = (
            db.query(Invoice)
            .order_by(Invoice.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    except SQLAlchemyError as exc:
        logger.error(f"Database error listing invoices: {exc}")
        raise HTTPException(status_code=500, detail="Database error while fetching invoices.")

    res = []
    for inv in invoices:
        has_mem = False
        if inv.vendor_id:
            has_mem = db.query(HindsightMemory).filter(HindsightMemory.vendor_id == inv.vendor_id).count() > 0
        res.append({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "vendor_name": inv.vendor.name if inv.vendor else None,
            "status": inv.status.value if inv.status else "UNKNOWN",
            "total_amount": inv.total_amount,
            "currency": inv.currency,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "memory_recalled": has_mem,
        })
    return res



# ---------------------------------------------------------------------------
# GET /invoice/{id} — single invoice detail
# ---------------------------------------------------------------------------

@app.get("/invoice/{invoice_id}", tags=["Invoices"])
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """
    Returns full detail of a single invoice including vendor, PO, contract, exceptions, and clerk feedback.
    """
    try:
        repo = InvoiceRepository(db)
        invoice = repo.get_invoice(invoice_id)
    except SQLAlchemyError as exc:
        logger.error(f"Database error fetching invoice {invoice_id}: {exc}")
        raise HTTPException(status_code=500, detail="Database error.")

    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found.")

    exceptions = (
        db.query(InvoiceException)
        .filter(InvoiceException.invoice_id == invoice_id)
        .all()
    )

    feedbacks = (
        db.query(ClerkFeedback)
        .filter(ClerkFeedback.invoice_id == invoice_id)
        .order_by(ClerkFeedback.created_at.desc())
        .all()
    )

    vendor_name = invoice.vendor.name if invoice.vendor else None

    # Trigger memory recall for invoice details lookup
    mem_service = MemoryService(db)
    exc_dicts = [{"type": e.exception_type, "description": e.description} for e in exceptions]
    recalled_res = mem_service.recall_memory(
        vendor_name=vendor_name,
        po_number=invoice.po_number,
        exceptions=exc_dicts,
    )

    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "vendor_id": invoice.vendor_id,
        "vendor_name": vendor_name,
        "po_number": invoice.po_number,
        "contract_number": invoice.contract_number,
        "status": invoice.status.value if invoice.status else "UNKNOWN",
        "total_amount": invoice.total_amount,
        "tax_amount": invoice.tax_amount,
        "currency": invoice.currency,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "exceptions": recalled_res.get("decorated_exceptions", exc_dicts),
        "recalled_memory": recalled_res,
        "clerk_feedbacks": [
            {
                "id": fb.id,
                "action": fb.action,
                "reason": fb.reason,
                "exception_type": fb.exception_type,
                "created_at": fb.created_at.isoformat() if fb.created_at else None,
            }
            for fb in feedbacks
        ],
    }


# ---------------------------------------------------------------------------
# GET /invoice/{id}/audit — audit trail for one invoice
# ---------------------------------------------------------------------------

@app.get("/invoice/{invoice_id}/audit", tags=["Audit"])
def get_audit_trail(invoice_id: int, db: Session = Depends(get_db)):
    """
    Returns the complete, ordered audit trail for a single invoice.
    """
    try:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Database error.")

    if not invoice:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found.")

    try:
        logs = (
            db.query(AuditLog)
            .filter(AuditLog.invoice_id == invoice_id)
            .order_by(AuditLog.timestamp.asc())
            .all()
        )
    except SQLAlchemyError as exc:
        logger.error(f"Database error fetching audit logs for invoice {invoice_id}: {exc}")
        raise HTTPException(status_code=500, detail="Database error fetching audit logs.")

    return {
        "invoice_id": invoice_id,
        "invoice_number": invoice.invoice_number,
        "audit_trail": [
            {
                "id": log.id,
                "agent": log.agent_name,
                "action": log.action,
                "details": log.details,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in logs
        ],
    }


# ---------------------------------------------------------------------------
# GET /stats — dashboard summary statistics
# ---------------------------------------------------------------------------

@app.get("/stats", tags=["Dashboard"])
def get_stats(db: Session = Depends(get_db)):
    """
    Returns aggregated counts and metrics for the dashboard.
    """
    try:
        total = db.query(Invoice).count()
        straight_through = db.query(Invoice).filter(
            Invoice.status == InvoiceStatus.STRAIGHT_THROUGH
        ).count()
        review_required = db.query(Invoice).filter(
            Invoice.status == InvoiceStatus.REVIEW_REQUIRED
        ).count()
        approved = db.query(Invoice).filter(
            Invoice.status.in_([InvoiceStatus.APPROVED, InvoiceStatus.RESOLVED])
        ).count()
        rejected = db.query(Invoice).filter(
            Invoice.status == InvoiceStatus.REJECTED
        ).count()
        total_value = db.query(
            func.sum(Invoice.total_amount)
        ).scalar() or 0.0
        total_memories = db.query(HindsightMemory).count()
    except SQLAlchemyError as exc:
        logger.error(f"Database error fetching stats: {exc}")
        raise HTTPException(status_code=500, detail="Database error fetching stats.")

    stp_pct = round((straight_through / total * 100), 1) if total > 0 else 0.0

    return {
        "total_invoices": total,
        "straight_through": straight_through,
        "straight_through_pct": stp_pct,
        "review_required": review_required,
        "approved": approved,
        "rejected": rejected,
        "total_scheduled_value": round(total_value, 2),
        "total_hindsight_memories": total_memories,
    }





if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
