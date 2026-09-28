from sqlalchemy.orm import Session
from sqlalchemy import func
import datetime
import logging
from typing import List, Dict, Any, Optional

from models.models import (
    Vendor,
    Invoice,
    ClerkFeedback,
    HindsightMemory,
    VendorMemoryProfile,
    InvoiceStatus,
)

logger = logging.getLogger("ap_agent.memory_service")


class MemoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_vendor_profile(self, vendor_id: int) -> VendorMemoryProfile:
        """
        Fetches or initializes the VendorMemoryProfile for a given vendor_id.
        """
        profile = (
            self.db.query(VendorMemoryProfile)
            .filter(VendorMemoryProfile.vendor_id == vendor_id)
            .first()
        )
        if not profile:
            profile = VendorMemoryProfile(
                vendor_id=vendor_id,
                total_invoices_processed=0,
                total_approved=0,
                total_rejected=0,
                reliability_score=100.0,
                common_issues={},
                recurring_mismatches=[],
                typical_resolutions={},
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        return profile

    def recall_memory(
        self,
        vendor_name: Optional[str] = None,
        vendor_code: Optional[str] = None,
        po_number: Optional[str] = None,
        exceptions: Optional[List[Dict[str, Any]]] = None,
        extracted_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Recalls past invoice decisions, vendor patterns, and exception resolutions.
        Decorates exceptions with:
          - priority: "HIGH" | "MEDIUM" | "LOW"
          - suggested_resolution: str
          - recommendation: str
          - recalled_memory_context: str
        """
        exceptions = exceptions or []
        extracted_data = extracted_data or {}
        recalled_memories = []
        vendor_profile_data = {}
        vendor_obj = None

        # 1. Lookup Vendor
        if vendor_code:
            vendor_obj = self.db.query(Vendor).filter(Vendor.vendor_code == vendor_code).first()
        if not vendor_obj and vendor_name:
            vendor_obj = (
                self.db.query(Vendor)
                .filter(Vendor.name.ilike(f"%{vendor_name}%"))
                .first()
            )

        # 2. Fetch Hindsight Memories & Vendor Profile
        if vendor_obj:
            profile = self.get_or_create_vendor_profile(vendor_obj.id)
            vendor_profile_data = {
                "vendor_id": vendor_obj.id,
                "vendor_name": vendor_obj.name,
                "vendor_code": vendor_obj.vendor_code,
                "total_invoices_processed": profile.total_invoices_processed,
                "total_approved": profile.total_approved,
                "total_rejected": profile.total_rejected,
                "reliability_score": profile.reliability_score,
                "common_issues": profile.common_issues or {},
                "recurring_mismatches": profile.recurring_mismatches or [],
                "typical_resolutions": profile.typical_resolutions or {},
            }

            # Query memories for vendor or PO
            memories_q = self.db.query(HindsightMemory).filter(
                (HindsightMemory.vendor_id == vendor_obj.id) | (HindsightMemory.po_number == po_number)
            )
            past_memories = memories_q.order_by(HindsightMemory.created_at.desc()).limit(10).all()
            for m in past_memories:
                recalled_memories.append({
                    "id": m.id,
                    "po_number": m.po_number,
                    "issue_type": m.issue_type,
                    "issue_summary": m.issue_summary,
                    "clerk_action": m.clerk_action,
                    "clerk_reason": m.clerk_reason,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                })

        # 3. Analyze Exceptions & Decorate with Priorities and Memory-Driven Recommendations
        decorated_exceptions = []
        overall_recommendations = []

        for exc in exceptions:
            exc_type = exc.get("type", "UNKNOWN")
            exc_desc = exc.get("description", "")
            
            priority = "HIGH"
            suggested_resolution = "Route to AP Clerk for manual verification."
            rec_text = "Standard exception handling required."
            memory_summary = ""

            # Check matching historical memories for this issue type
            matching_past = [
                m for m in recalled_memories if m.get("issue_type") == exc_type or exc_type in (m.get("issue_summary") or "")
            ]

            approved_past = [m for m in matching_past if m.get("clerk_action") in ("APPROVE", "RESOLVE")]
            rejected_past = [m for m in matching_past if m.get("clerk_action") == "REJECT"]

            v_name = vendor_obj.name if vendor_obj else (vendor_name or "Vendor")

            if exc_type == "PO_MISMATCH":
                if len(approved_past) >= len(rejected_past) and len(approved_past) > 0:
                    priority = "MEDIUM"
                    last_reason = approved_past[0].get("clerk_reason", "Verified with PO")
                    suggested_resolution = f"Suggest APPROVE after PO line verification (Past Clerk Note: '{last_reason}')."
                    memory_summary = (
                        f"{v_name} has had {len(matching_past)} similar price/qty mismatches in recent invoices, "
                        f"{len(approved_past)} of which were previously approved after PO verification."
                    )
                    rec_text = f"Recommend approval upon verifying line-item variance with PO."
                else:
                    priority = "HIGH"
                    suggested_resolution = "Review price variance with Procurement before approving."
                    memory_summary = f"{v_name} price mismatches are frequently flagged or rejected."
                    rec_text = "Recommend checking PO line items with vendor representative."

            elif exc_type == "TAX_DISCREPANCY":
                priority = "MEDIUM"
                if approved_past:
                    suggested_resolution = "Suggest RESOLVE: Standard tax variance previously accepted."
                    memory_summary = f"{v_name} has tax calculation rounding differences previously resolved by clerk."
                    rec_text = "Recommend resolving tax discrepancy as standard variance."
                else:
                    suggested_resolution = "Verify GST/Tax identification and rate calculation."
                    memory_summary = f"{v_name} tax discrepancy detected."
                    rec_text = "Check tax rate alignment with contract."

            elif exc_type in ("UNKNOWN_PO", "MISSING_PO"):
                # Hard rule: Unknown PO is always HIGH priority
                priority = "HIGH"
                suggested_resolution = "REJECT or request valid Purchase Order from vendor."
                memory_summary = f"{v_name} invoice submitted without valid matching PO."
                rec_text = "Hard Rule Triggered: Missing or invalid PO requires vendor inquiry."

            elif exc_type in ("CONTRACT_VIOLATION", "UNKNOWN_CONTRACT"):
                priority = "HIGH"
                suggested_resolution = "Route to Finance Manager for contract limit authorization."
                memory_summary = f"{v_name} contract maximum amount exceeded."
                rec_text = "Requires contract extension or manager approval."

            elif exc_type == "DUPLICATE_INVOICE":
                priority = "HIGH"
                suggested_resolution = "REJECT as duplicate submission unless multi-billing is confirmed."
                memory_summary = f"Invoice number already processed previously."
                rec_text = "Hard Rule Triggered: Reject duplicate invoice."

            else:
                priority = "HIGH"
                suggested_resolution = "Review exception details with AP supervisor."
                memory_summary = f"Exception detected: {exc_type}"
                rec_text = "Manual clerk decision required."

            decorated_exc = dict(exc)
            decorated_exc["priority"] = priority
            decorated_exc["suggested_resolution"] = suggested_resolution
            decorated_exc["recommendation"] = rec_text
            decorated_exc["recalled_memory_context"] = memory_summary
            decorated_exceptions.append(decorated_exc)

            if memory_summary:
                overall_recommendations.append(memory_summary)

        # 4. Formulate Agent Executive Reasoning Summary
        if not overall_recommendations and vendor_obj and vendor_profile_data.get("reliability_score", 100) > 85:
            overall_recommendations.append(
                f"{vendor_obj.name} has a high reliability score ({vendor_profile_data.get('reliability_score')}%) "
                f"with {vendor_profile_data.get('total_approved')} clean approvals out of {vendor_profile_data.get('total_invoices_processed')} invoices."
            )

        executive_summary = " | ".join(overall_recommendations) if overall_recommendations else "No prior exception patterns recalled for this vendor."

        return {
            "vendor_profile": vendor_profile_data,
            "recalled_memories": recalled_memories,
            "decorated_exceptions": decorated_exceptions,
            "executive_summary": executive_summary,
        }

    def record_clerk_feedback(
        self,
        invoice_id: int,
        action: str,
        reason: str,
        exception_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Records AP Clerk feedback (APPROVE, REJECT, RESOLVE), creates Hindsight Memory,
        updates Invoice status, and re-calculates Vendor Memory Profile statistics.
        """
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found.")

        # 1. Update Invoice Status
        status_enum = {
            "APPROVE": InvoiceStatus.APPROVED,
            "REJECT": InvoiceStatus.REJECTED,
            "RESOLVE": InvoiceStatus.RESOLVED,
        }.get(action.upper(), InvoiceStatus.APPROVED)

        invoice.status = status_enum

        # 2. Record Feedback
        feedback = ClerkFeedback(
            invoice_id=invoice_id,
            vendor_id=invoice.vendor_id,
            action=action.upper(),
            reason=reason,
            exception_type=exception_type,
        )
        self.db.add(feedback)

        # 3. Create Hindsight Memory Entry
        hindsight = HindsightMemory(
            vendor_id=invoice.vendor_id,
            invoice_number=invoice.invoice_number,
            po_number=invoice.po_number,
            issue_type=exception_type or "CLERK_REVIEW",
            issue_summary=f"Invoice #{invoice.invoice_number} exception resolved by clerk",
            clerk_action=action.upper(),
            clerk_reason=reason,
            resolution_context={
                "total_amount": invoice.total_amount,
                "status_after": status_enum.value,
            },
        )
        self.db.add(hindsight)

        self.db.commit()

        # 4. Update Vendor Memory Profile
        if invoice.vendor_id:
            self.update_vendor_profile_metrics(invoice.vendor_id)

        return {
            "status": "success",
            "invoice_id": invoice_id,
            "new_invoice_status": status_enum.value,
            "feedback_id": feedback.id,
            "hindsight_id": hindsight.id,
        }

    def update_vendor_profile_metrics(self, vendor_id: int) -> VendorMemoryProfile:
        """
        Recalculates vendor reliability score, common issues, and resolutions based on all past feedback and invoices.
        """
        profile = self.get_or_create_vendor_profile(vendor_id)

        # Count total invoices
        total_invs = self.db.query(Invoice).filter(Invoice.vendor_id == vendor_id).count()
        approved_cnt = self.db.query(Invoice).filter(
            Invoice.vendor_id == vendor_id,
            Invoice.status.in_([InvoiceStatus.STRAIGHT_THROUGH, InvoiceStatus.APPROVED, InvoiceStatus.RESOLVED])
        ).count()
        rejected_cnt = self.db.query(Invoice).filter(
            Invoice.vendor_id == vendor_id,
            Invoice.status == InvoiceStatus.REJECTED
        ).count()

        # Reliability score: ratio of approved+straight_through over total processed (default 100% if 0)
        rel_score = round((approved_cnt / total_invs * 100), 1) if total_invs > 0 else 100.0

        # Aggregate issue types from feedbacks
        feedbacks = self.db.query(ClerkFeedback).filter(ClerkFeedback.vendor_id == vendor_id).all()
        issue_counts = {}
        typical_resolutions = {}

        for fb in feedbacks:
            issue = fb.exception_type or "PO_MISMATCH"
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
            if fb.reason and fb.action in ("APPROVE", "RESOLVE"):
                typical_resolutions[issue] = fb.reason

        profile.total_invoices_processed = total_invs
        profile.total_approved = approved_cnt
        profile.total_rejected = rejected_cnt
        profile.reliability_score = rel_score
        profile.common_issues = issue_counts
        profile.typical_resolutions = typical_resolutions
        profile.updated_at = datetime.datetime.utcnow()

        self.db.commit()
        self.db.refresh(profile)
        return profile
