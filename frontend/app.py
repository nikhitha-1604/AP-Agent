import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# ---------------------------------------------------------------------------
# Configuration & Backend Connectivity
# ---------------------------------------------------------------------------

try:
    API_URL = st.secrets["API_URL"]
except (KeyError, FileNotFoundError):
    API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="AP Agent | Hindsight Memory & Invoice Intelligence",
    layout="wide",
    page_icon=None,
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Enterprise SaaS Custom CSS System
# ---------------------------------------------------------------------------

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Outfit:wght@400;600;700;800&display=swap');
html, body, [class*="css"] {
font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
/* Dark Slate Enterprise Background */
.stApp {
background-color: #0b0f17;
color: #e2e8f0;
}
/* Navigation Sidebar Styling */
[data-testid="stSidebar"] {
background-color: #0f172a !important;
border-right: 1px solid #1e293b !important;
}
/* Make Navigation Radio Options Large, Spacious, and Prominent Cards */
[data-testid="stSidebar"] [data-testid="stRadio"] {
width: 100% !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {
gap: 10px !important;
width: 100% !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
font-size: 1.15rem !important;
font-weight: 600 !important;
padding: 14px 18px !important;
border-radius: 12px !important;
background-color: #1e293b !important;
border: 1px solid #334155 !important;
color: #cbd5e1 !important;
transition: all 0.2s ease-in-out !important;
cursor: pointer !important;
display: flex !important;
align-items: center !important;
width: 100% !important;
box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
background-color: #334155 !important;
border-color: #6366f1 !important;
color: #ffffff !important;
transform: translateX(4px) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label[aria-checked="true"],
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important;
color: #ffffff !important;
border-color: #818cf8 !important;
box-shadow: 0 4px 16px rgba(79, 70, 229, 0.45) !important;
font-weight: 700 !important;
}
/* Make text inside sidebar navigation items big and crisp */
[data-testid="stSidebar"] [data-testid="stRadio"] label p,
[data-testid="stSidebar"] [data-testid="stRadio"] label div,
[data-testid="stSidebar"] [data-testid="stRadio"] label span {
font-size: 1.15rem !important;
font-weight: 600 !important;
color: inherit !important;
line-height: 1.4 !important;
}
/* Clean Enterprise Header */
.brand-logo {
font-family: 'Outfit', sans-serif;
font-weight: 800;
font-size: 1.85rem !important;
color: #f8fafc;
display: flex;
align-items: center;
gap: 10px;
margin-bottom: 2px;
}
.brand-subtitle {
font-size: 0.82rem !important;
color: #818cf8 !important;
font-weight: 700 !important;
text-transform: uppercase;
letter-spacing: 0.06em;
margin-bottom: 26px;
}
/* Page Title Banner */
.page-title {
font-family: 'Outfit', sans-serif;
font-weight: 700;
font-size: 1.85rem;
color: #f8fafc;
margin-bottom: 4px;
}
.page-description {
font-size: 0.95rem;
color: #94a3b8;
margin-bottom: 24px;
}
/* Card Component */
.saas-card {
background-color: #1e293b;
border: 1px solid #334155;
border-radius: 12px;
padding: 20px;
margin-bottom: 20px;
box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -1px rgba(0, 0, 0, 0.1);
}
.saas-card-header {
font-weight: 600;
font-size: 1.1rem;
color: #f8fafc;
margin-bottom: 14px;
display: flex;
justify-content: space-between;
align-items: center;
}
/* Hero Memory Card */
.memory-hero-card {
background: linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%);
border: 2px solid #6366f1;
border-radius: 14px;
padding: 24px;
margin-bottom: 24px;
box-shadow: 0 10px 30px -5px rgba(99, 102, 241, 0.35);
}
/* Metric Cards Override */
[data-testid="stMetric"] {
background-color: #1e293b !important;
border: 1px solid #334155 !important;
padding: 16px 20px !important;
border-radius: 10px !important;
}
[data-testid="stMetricLabel"] {
color: #94a3b8 !important;
font-size: 0.82rem !important;
font-weight: 600 !important;
text-transform: uppercase !important;
letter-spacing: 0.04em !important;
}
[data-testid="stMetricValue"] {
color: #f8fafc !important;
font-weight: 700 !important;
font-size: 1.7rem !important;
}
/* Status Badges */
.status-badge {
display: inline-block;
padding: 4px 12px;
border-radius: 20px;
font-weight: 600;
font-size: 0.78rem;
letter-spacing: 0.02em;
}
.status-approved { background-color: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
.status-resolved { background-color: rgba(6, 182, 212, 0.15); color: #06b6d4; border: 1px solid rgba(6, 182, 212, 0.3); }
.status-review   { background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
.status-rejected { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
.status-neutral  { background-color: rgba(100, 116, 139, 0.15); color: #94a3b8; border: 1px solid rgba(100, 116, 139, 0.3); }
/* Priority Badges */
.prio-high   { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); }
.prio-medium { background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.4); }
.prio-low    { background-color: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4); }
.glowing-memory-pill {
background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%);
color: #ffffff;
font-weight: 700;
font-size: 0.8rem;
padding: 4px 12px;
border-radius: 20px;
box-shadow: 0 0 12px rgba(99, 102, 241, 0.6);
display: inline-block;
}
/* Custom Buttons */
.stButton > button {
background-color: #334155;
color: #f8fafc;
border: 1px solid #475569;
border-radius: 8px;
font-weight: 500;
font-size: 0.9rem;
padding: 8px 16px;
transition: all 0.15s ease;
}
.stButton > button:hover {
background-color: #475569;
border-color: #64748b;
color: #ffffff;
}
/* Primary CTA Button */
div.stButton > button[kind="primary"] {
background-color: #4f46e5 !important;
border-color: #6366f1 !important;
color: #ffffff !important;
}
div.stButton > button[kind="primary"]:hover {
background-color: #4338ca !important;
box-shadow: 0 4px 12px rgba(79, 70, 229, 0.35) !important;
}
/* Process Flow Indicator */
.stepper-container {
display: flex;
justify-content: space-between;
margin: 20px 0;
position: relative;
}
.stepper-step {
flex: 1;
text-align: center;
padding: 10px;
background: #1e293b;
border: 1px solid #334155;
border-radius: 8px;
font-size: 0.82rem;
font-weight: 600;
color: #94a3b8;
margin: 0 4px;
}
.stepper-step.active {
background: rgba(79, 70, 229, 0.25);
border-color: #6366f1;
color: #818cf8;
}

/* Style Streamlit Native Widgets directly as Enterprise SaaS Cards without empty div wrappers */
[data-testid="stFileUploader"],
[data-testid="stForm"] {
    background-color: #1e293b !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
    padding: 20px !important;
    margin-bottom: 20px !important;
}

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# API Communication Layer
# ---------------------------------------------------------------------------

def _wake_backend() -> bool:
    for _ in range(3):
        try:
            resp = requests.get(f"{API_URL}/", timeout=(10, 15))
            if resp.status_code == 200:
                return True
        except Exception:
            pass
    return False

def api_get(path: str, timeout: int = 30) -> dict | list | None:
    try:
        resp = requests.get(f"{API_URL}{path}", timeout=(10, timeout))
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error("Connection error: Cannot reach FastAPI backend.")
        return None
    except requests.exceptions.Timeout:
        st.warning("Request timed out. Backend is warming up...")
        return None
    except requests.exceptions.HTTPError as exc:
        st.error(f"HTTP Error {exc.response.status_code}: {exc.response.text}")
        return None
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
        return None

def api_post(path: str, json_data: dict = None, files: dict = None, timeout: int = 60) -> dict | None:
    try:
        if files:
            resp = requests.post(f"{API_URL}{path}", files=files, timeout=timeout)
        else:
            resp = requests.post(f"{API_URL}{path}", json=json_data, timeout=timeout)
        try:
            return resp.json()
        except Exception:
            st.error(f"Backend response invalid: {resp.text[:200]}")
            return None
    except Exception as exc:
        st.error(f"API request failed: {exc}")
        return None

# ---------------------------------------------------------------------------
# UI Formatting & Badges
# ---------------------------------------------------------------------------

def render_status_badge(status: str) -> str:
    s = (status or "UNKNOWN").upper()
    if s in ("APPROVED", "STRAIGHT_THROUGH"):
        return f'<span class="status-badge status-approved">● {s}</span>'
    elif s in ("RESOLVED",):
        return f'<span class="status-badge status-resolved">✓ {s}</span>'
    elif s in ("REVIEW_REQUIRED", "EXCEPTION"):
        return f'<span class="status-badge status-review">▲ {s}</span>'
    elif s in ("REJECTED", "EXTRACTION_FAILED"):
        return f'<span class="status-badge status-rejected">✕ {s}</span>'
    else:
        return f'<span class="status-badge status-neutral">○ {s}</span>'

def render_priority_badge(priority: str) -> str:
    p = (priority or "MEDIUM").upper()
    if p == "HIGH":
        return f'<span class="status-badge prio-high">HIGH PRIORITY</span>'
    elif p == "MEDIUM":
        return f'<span class="status-badge prio-medium">MEDIUM PRIORITY</span>'
    else:
        return f'<span class="status-badge prio-low">LOW PRIORITY</span>'

# ---------------------------------------------------------------------------
# VISUAL FLOW COMPONENT: Memory Learning Loop
# ---------------------------------------------------------------------------

def render_memory_flow_diagram():
    """
    Renders visual learning loop diagram showing how Hindsight Memory functions.
    """
    st.markdown("""<div style="background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%); border: 1px solid #4f46e5; border-radius: 12px; padding: 16px 20px; margin: 20px 0; box-shadow: 0 4px 14px rgba(79, 70, 229, 0.2);">
<div style="font-size: 0.8rem; font-weight: 700; color: #818cf8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 10px;">
HINDSIGHT MEMORY LEARNING LOOP
</div>
<div style="display: flex; justify-content: space-between; align-items: center; text-align: center; gap: 8px;">
<div style="flex:1; background: #0f172a; padding: 10px 6px; border-radius: 8px; border: 1px solid #334155;">
<div style="font-size: 0.78rem; font-weight: 600; color: #cbd5e1; margin-top: 2px;">Invoice Received</div>
</div>
<div style="color: #6366f1; font-weight: bold; font-size: 1.1rem;">➔</div>
<div style="flex:1; background: #0f172a; padding: 10px 6px; border-radius: 8px; border: 1px solid #f59e0b;">
<div style="font-size: 0.78rem; font-weight: 600; color: #f59e0b; margin-top: 2px;">Exception Flagged</div>
</div>
<div style="color: #6366f1; font-weight: bold; font-size: 1.1rem;">➔</div>
<div style="flex:1; background: #0f172a; padding: 10px 6px; border-radius: 8px; border: 1px solid #06b6d4;">
<div style="font-size: 0.78rem; font-weight: 600; color: #06b6d4; margin-top: 2px;">Human Clerk Action</div>
</div>
<div style="color: #6366f1; font-weight: bold; font-size: 1.1rem;">➔</div>
<div style="flex:1; background: rgba(79, 70, 229, 0.25); padding: 10px 6px; border-radius: 8px; border: 1px solid #6366f1;">
<div style="font-size: 0.78rem; font-weight: 700; color: #818cf8; margin-top: 2px;">Memory Created</div>
</div>
<div style="color: #6366f1; font-weight: bold; font-size: 1.1rem;">➔</div>
<div style="flex:1; background: #0f172a; padding: 10px 6px; border-radius: 8px; border: 1px solid #334155;">
<div style="font-size: 0.78rem; font-weight: 600; color: #cbd5e1; margin-top: 2px;">Future Invoice</div>
</div>
<div style="color: #6366f1; font-weight: bold; font-size: 1.1rem;">➔</div>
<div style="flex:1; background: rgba(16, 185, 129, 0.2); padding: 10px 6px; border-radius: 8px; border: 1px solid #10b981;">
<div style="font-size: 0.78rem; font-weight: 700; color: #10b981; margin-top: 2px;">Memory Recalled</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# HERO COMPONENT: 3-Column Hindsight Memory & AI Intelligence
# ---------------------------------------------------------------------------

def render_hindsight_memory_hero(recalled_memory: dict, current_vendor: str = None, po_number: str = None):
    """
    Renders the 3-column Hindsight Memory card clearly separating:
    - CURRENT INVOICE
    - PAST EXPERIENCE RECALLED
    - AI RECOMMENDATION
    """
    mems = recalled_memory.get("recalled_memories", []) if recalled_memory else []
    count = len(mems)
    
    st.markdown("<div class='memory-hero-card'>", unsafe_allow_html=True)
    st.markdown("<div style='display:flex; justify-content:space-between; align-items:center;'>", unsafe_allow_html=True)
    st.markdown(f"<div><h3 style='margin:0; font-size:1.3rem; color:#f8fafc;'>Hindsight Memory & AI Intelligence</h3><p style='margin:2px 0 0 0; font-size:0.85rem; color:#94a3b8;'>Memory engine recalled vendor history and past clerk decisions to inform recommendations.</p></div>", unsafe_allow_html=True)
    
    if count > 0:
        st.markdown(f"<div><span class='glowing-memory-pill'>{count} Historical Memories Recalled</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div><span class='status-badge status-neutral'>○ No Prior Memories Found</span></div>", unsafe_allow_html=True)
        
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#334155; margin:16px 0;'>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    # Column 1: CURRENT INVOICE
    with c1:
        st.markdown("<h4 style='font-size:0.85rem; color:#f59e0b; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:8px;'>Current Invoice</h4>", unsafe_allow_html=True)
        st.markdown(f"**Vendor:** {current_vendor or 'Extracted Vendor'}")
        st.markdown(f"**PO Reference:** `{po_number or 'N/A'}`")
        exc_list = recalled_memory.get("decorated_exceptions", []) if recalled_memory else []
        if exc_list:
            st.markdown(f"**Detected Mismatch:** `{exc_list[0].get('type')}`")
            st.markdown(f"**Issue Detail:** {exc_list[0].get('description')}")
        else:
            st.markdown("**Status:** Clean invoice under evaluation")

    # Column 2: PAST EXPERIENCE RECALLED
    with c2:
        st.markdown("<h4 style='font-size:0.85rem; color:#818cf8; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:8px;'>Past Experience Recalled</h4>", unsafe_allow_html=True)
        if mems:
            last_mem = mems[0]
            st.markdown(f"**Historical Issue:** `{last_mem.get('issue_type', 'PO_MISMATCH')}`")
            st.markdown(f"**Past Clerk Action:** `{last_mem.get('clerk_action')}`")
            st.markdown(f"**Clerk Explanation:** *\"{last_mem.get('clerk_reason')}\"*")
        else:
            prof = recalled_memory.get("vendor_profile", {}) if recalled_memory else {}
            st.markdown(f"**Vendor Profile:** {current_vendor or 'Vendor'}")
            st.markdown(f"**Reliability Score:** `{prof.get('reliability_score', 100)}%`")
            st.markdown(f"**Processed Invoices:** {prof.get('total_invoices_processed', 0)} ({prof.get('total_approved', 0)} approved)")

    # Column 3: AI RECOMMENDATION
    with c3:
        st.markdown("<h4 style='font-size:0.85rem; color:#10b981; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:8px;'>AI Recommendation</h4>", unsafe_allow_html=True)
        exec_summary = recalled_memory.get("executive_summary", "") if recalled_memory else "No historical exceptions recalled."
        st.markdown(f"**Executive Insight:**")
        st.markdown(f"*{exec_summary}*")
        if exc_list:
            st.markdown(f"**Suggested Action:** {exc_list[0].get('suggested_resolution', 'Review with clerk')}")

    st.markdown("<div style='margin-top:16px; background:rgba(15,23,42,0.7); padding:10px 14px; border-radius:8px; border-left:4px solid #6366f1; font-size:0.82rem; color:#cbd5e1;'><b>Business Rule Hierarchy:</b> Memory informs recommendations and explanations. Hard AP rules (Unknown PO, Duplicate Invoice, Contract Exceedance) are always strictly enforced.</div>", unsafe_allow_html=True)
    
# ---------------------------------------------------------------------------
# HUMAN REVIEW PANEL (Teaching the Agent)
# ---------------------------------------------------------------------------

def render_human_review_panel(invoice_id: int, exceptions: list, current_status: str):
    """
    Renders Human Review & Resolution panel, styled as "Teaching the Agent".
    """
    st.markdown("<div class='saas-card-header'><span>Human Review & Resolution — Teaching the Agent</span><span style='font-size:0.8rem; color:#818cf8;'>Memory Feedback Loop</span></div>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:0.88rem; color:#94a3b8; margin-bottom:16px;'>Review the AI recommendation and recalled vendor history before making a decision. Your decision will train the Hindsight Memory.</p>", unsafe_allow_html=True)

    with st.form(key=f"human_review_form_{invoice_id}"):
        col1, col2 = st.columns([1.2, 1])

        with col1:
            st.markdown("**Select Resolution Action:**")
            action = st.radio(
                "Action Option",
                options=["APPROVE", "RESOLVE", "REJECT"],
                format_func=lambda x: {
                    "APPROVE": "✓ Approve Invoice — Override & authorize payment",
                    "RESOLVE": "✓ Resolve Exception — Accept variance as valid",
                    "REJECT": "✕ Reject Invoice — Send back to vendor",
                }[x],
                label_visibility="collapsed",
            )

        with col2:
            st.markdown("**Target Exception:**")
            exc_options = [e.get("type") for e in exceptions if e.get("type")] or ["GENERAL_EXCEPTION"]
            target_exc = st.selectbox("Exception Type", options=exc_options, label_visibility="collapsed")

        reason = st.text_area(
            "Teach the Agent: Clerk Rationale / Explanation (Required)",
            placeholder="e.g. Verified price variance with PO manager. Vendor account approved for $15 unit difference.",
            height=90,
            help="This explanation will be stored in Hindsight Memory and will influence future recommendations for this vendor.",
        )

        st.markdown("<p style='font-size:0.78rem; color:#818cf8; margin-top:-4px;'>This explanation will be stored as Hindsight Memory and will influence future recommendations on similar invoices.</p>", unsafe_allow_html=True)

        submitted = st.form_submit_button("Submit Decision & Train Memory", type="primary")

        if submitted:
            if not reason.strip():
                st.warning("Please provide a resolution explanation before submitting.")
            else:
                res = api_post(f"/invoice/{invoice_id}/feedback", json_data={"action": action, "reason": reason.strip(), "exception_type": target_exc})
                if res and res.get("status") == "success":
                    st.success("Memory Created! The AP Agent has learned from your decision and will remember it for future invoices.")
                    refreshed = api_get(f"/invoice/{invoice_id}")
                    if refreshed:
                        st.session_state["searched_invoice"] = refreshed
                    st.rerun()

    
# ---------------------------------------------------------------------------
# MAIN APPLICATION & NAVIGATION
# ---------------------------------------------------------------------------

def main():
    if "backend_ready" not in st.session_state:
        with st.spinner("Connecting to AP Agent backend..."):
            st.session_state["backend_ready"] = _wake_backend()

    # Sidebar Navigation
    with st.sidebar:
        st.markdown("<div class='brand-logo'>AP Agent</div>", unsafe_allow_html=True)
        st.markdown("<div class='brand-subtitle'>Invoice Exception Intelligence</div>", unsafe_allow_html=True)

        nav_choice = st.radio(
            "Navigation",
            options=[
                "Overview",
                "Process Invoice",
                "Exceptions",
                "Memory Intelligence",
                "Invoice History",
                "Audit Trail",
            ],
            label_visibility="collapsed",
        )

        st.markdown("---")

        st.markdown("<div style='font-size:0.8rem; font-weight:600; color:#94a3b8; margin-bottom:8px;'>SYSTEM STATUS</div>", unsafe_allow_html=True)
        if st.session_state.get("backend_ready"):
            st.markdown("<span style='color:#10b981; font-weight:600; font-size:0.85rem;'>● Backend Online</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span style='color:#ef4444; font-weight:600; font-size:0.85rem;'>○ Backend Offline</span>", unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("Seed DB Reference Data", use_container_width=True):
            with st.spinner("Seeding multi-vendor memory..."):
                r = api_post("/seed-db", {})
                if r and r.get("status") == "ok":
                    st.success("Seeded Multi-Vendor reference data & memories!")
                    st.rerun()

    if not st.session_state["backend_ready"]:
        st.error("FastAPI Backend is unreachable. Please verify backend server is running at http://localhost:8000.")
        return

    if nav_choice == "Overview":
        render_overview_page()
    elif nav_choice == "Process Invoice":
        render_process_invoice_page()
    elif nav_choice == "Exceptions":
        render_exceptions_page()
    elif nav_choice == "Memory Intelligence":
        render_vendor_intelligence_page()
    elif nav_choice == "Invoice History":
        render_invoice_history_page()
    elif nav_choice == "Audit Trail":
        render_audit_trail_page()

# ---------------------------------------------------------------------------
# PAGE 1: OVERVIEW DASHBOARD
# ---------------------------------------------------------------------------

def render_overview_page():
    st.markdown("<div class='page-title'>AP Invoice Intelligence</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-description'>Autonomous invoice processing with Hindsight Memory and human oversight.</div>", unsafe_allow_html=True)

    # Render Visual Learning Flow Diagram
    render_memory_flow_diagram()

    stats = api_get("/stats") or {}
    total_invs = stats.get("total_invoices", 0)
    stp_rate = stats.get("straight_through_pct", 0)
    pending_exc = stats.get("review_required", 0)
    approved_cnt = stats.get("approved", 0)
    scheduled_val = stats.get("total_scheduled_value", 0.0)
    total_memories = stats.get("total_hindsight_memories", 0)

    # Top KPI Cards (Including Hindsight Memories KPI)
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Total Invoices", total_invs)
    k2.metric("Straight-Through", f"{stp_rate}%")
    k3.metric("Pending Exceptions", pending_exc)
    k4.metric("Approved / Resolved", approved_cnt)
    k5.metric("Scheduled Value", f"${scheduled_val:,.2f}")
    k6.metric("LEARNED MEMORIES", total_memories)

    st.markdown("<br/>", unsafe_allow_html=True)

    # Prominent "What the Agent Learned" Section (Immediately Below KPI Cards)
    st.markdown("""<div class='saas-card-header'>
<span>What the Agent Learned</span>
<span class='glowing-memory-pill'>Active Hindsight Memories</span>
</div>
""", unsafe_allow_html=True)

    recent_mems = api_get("/memories/recent?limit=5") or []
    if recent_mems:
        for m in recent_mems:
            v_name = m.get("vendor_name", "Unknown Vendor")
            exc_type = m.get("issue_type", "GENERAL_EXCEPTION")
            exc_summary = m.get("issue_summary")
            exc_text = f"{exc_type} — {exc_summary}" if exc_summary else exc_type
            action = m.get("clerk_action", "APPROVE")
            learned = m.get("clerk_reason", "No detailed rationale provided.")

            if action in ("APPROVE", "APPROVED"):
                act_badge = "<span class='status-badge status-approved'>● APPROVED</span>"
            elif action in ("RESOLVE", "RESOLVED"):
                act_badge = "<span class='status-badge status-resolved'>✓ RESOLVED</span>"
            elif action in ("REJECT", "REJECTED"):
                act_badge = "<span class='status-badge status-rejected'>✕ REJECTED</span>"
            else:
                act_badge = f"<span class='status-badge status-neutral'>○ {action}</span>"

            st.markdown(f"""<div style="background: rgba(15, 23, 42, 0.7); border: 1px solid #334155; border-left: 4px solid #6366f1; border-radius: 8px; padding: 14px 18px; margin-bottom: 12px;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
<div style="font-weight: 700; color: #f8fafc; font-size: 0.95rem;">
Vendor: <span style="color: #818cf8;">{v_name}</span> &nbsp;|&nbsp; Invoice: <span style="color: #94a3b8; font-family: monospace;">{m.get('invoice_number', 'N/A')}</span>
</div>
<div>
<span style="font-size: 0.8rem; color: #94a3b8; margin-right: 8px;">Human Resolution:</span> {act_badge}
</div>
</div>
<div style="display: grid; grid-template-columns: 1fr 2fr; gap: 16px; font-size: 0.85rem;">
<div>
<span style="color: #f59e0b; font-weight: 600;">Exception:</span>
<div style="color: #cbd5e1; margin-top: 2px;">{exc_text}</div>
</div>
<div>
<span style="color: #10b981; font-weight: 600;">What Was Learned:</span>
<div style="color: #e2e8f0; font-style: italic; margin-top: 2px;">"{learned}"</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown("<p style='color:#94a3b8; margin:0;'>No hindsight memories recorded yet in the database. Click <b>'Seed DB Reference Data'</b> in the sidebar to populate vendor memories.</p>", unsafe_allow_html=True)

    
    # Vendor Intelligence Cards
    vendors = api_get("/vendors") or []
    if vendors:
        st.markdown("<div class='saas-card-header'><span>Vendor Reliability Profiles & Memory Summaries</span></div>", unsafe_allow_html=True)
        v_cols = st.columns(len(vendors[:4]))
        for idx, v in enumerate(vendors[:4]):
            with v_cols[idx]:
                st.markdown(f"**{v.get('name')}**")
                st.markdown(f"Code: `{v.get('vendor_code')}`")
                st.markdown(f"Reliability Score: `{v.get('reliability_score')}%`")
                issues = list(v.get("common_issues", {}).keys())
                st.markdown(f"Common Issue: `{issues[0] if issues else 'Clean Record'}`")
        
    c_left, c_right = st.columns(2)

    with c_left:
        st.markdown("<div class='saas-card-header'>Invoice Processing Breakdown</div>", unsafe_allow_html=True)
        status_df = pd.DataFrame([
            {"Status": "Straight-Through", "Count": stats.get("straight_through", 0)},
            {"Status": "Review Required", "Count": stats.get("review_required", 0)},
            {"Status": "Approved / Resolved", "Count": stats.get("approved", 0)},
            {"Status": "Rejected", "Count": stats.get("rejected", 0)},
        ])
        fig_pie = px.pie(
            status_df,
            values="Count",
            names="Status",
            hole=0.45,
            color="Status",
            color_discrete_map={
                "Straight-Through": "#10b981",
                "Approved / Resolved": "#06b6d4",
                "Review Required": "#f59e0b",
                "Rejected": "#ef4444",
            },
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0",
            margin=dict(t=10, b=10, l=10, r=10),
            height=250,
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with c_right:
        st.markdown("<div class='saas-card-header'>Vendor Reliability Profile</div>", unsafe_allow_html=True)
        if vendors:
            v_df = pd.DataFrame(vendors)
            fig_bar = px.bar(
                v_df,
                x="reliability_score",
                y="name",
                orientation="h",
                labels={"reliability_score": "Reliability Score (%)", "name": "Vendor"},
                color="reliability_score",
                color_continuous_scale="Viridis",
            )
            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e2e8f0",
                margin=dict(t=10, b=10, l=10, r=10),
                height=250,
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No vendor profiles available.")
        
    # Recent Activity Table (With Memory Recalled Indicator)
    st.markdown("<div class='saas-card-header'>Recent Invoice Activity</div>", unsafe_allow_html=True)
    invoices = api_get("/invoices?limit=10") or []
    if invoices:
        formatted_invs = []
        for inv in invoices:
            has_mem = inv.get("memory_recalled", False)
            mem_indicator = "Memory Recalled" if has_mem else "—"
            formatted_invs.append({
                "Invoice ID": inv.get("id"),
                "Invoice #": inv.get("invoice_number"),
                "Vendor": inv.get("vendor_name") or "N/A",
                "Amount": f"${inv.get('total_amount', 0):,.2f}",
                "Status": inv.get("status"),
                "Hindsight Memory": mem_indicator,
                "Created At": inv.get("created_at", "")[:19] if inv.get("created_at") else "",
            })
        df_invs = pd.DataFrame(formatted_invs)
        st.dataframe(df_invs, use_container_width=True, hide_index=True)
    else:
        st.info("No invoice activity recorded yet.")
    
# ---------------------------------------------------------------------------
# PAGE 2: PROCESS INVOICE
# ---------------------------------------------------------------------------

def render_process_invoice_page():
    st.markdown("<div class='page-title'>Process New Invoice</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-description'>Upload an invoice document to trigger OCR extraction, validation, PO matching, and Hindsight Memory recall.</div>", unsafe_allow_html=True)

    render_memory_flow_diagram()

    uploaded_file = st.file_uploader("Drop invoice document here", type=["pdf", "png", "jpg", "jpeg"])
    st.markdown("<p style='font-size:0.8rem; color:#64748b;'>Supported: PDF, PNG, JPG, JPEG &nbsp;|&nbsp; Maximum file size: 200 MB</p>", unsafe_allow_html=True)
    
    if uploaded_file:
        st.markdown("<div class='saas-card-header'>Uploaded File Details</div>", unsafe_allow_html=True)
        col_f1, col_f2, col_f3 = st.columns(3)
        col_f1.markdown(f"**File Name:** `{uploaded_file.name}`")
        col_f2.markdown(f"**File Type:** `{uploaded_file.type}`")
        col_f3.markdown(f"**File Size:** `{round(len(uploaded_file.getvalue()) / 1024, 1)} KB`")
        
        if st.button("Process Invoice", type="primary"):
            stepper_placeholder = st.empty()
            stepper_placeholder.markdown("""
                <div class='stepper-container'>
                    <div class='stepper-step active'>1. Receiving</div>
                    <div class='stepper-step active'>2. Extracting</div>
                    <div class='stepper-step active'>3. Validating</div>
                    <div class='stepper-step active'>4. PO Matching</div>
                    <div class='stepper-step active'>5. Recalling Memory</div>
                    <div class='stepper-step active'>6. Decision</div>
                </div>
            """, unsafe_allow_html=True)

            with st.spinner("Agent running extraction & hindsight memory recall..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                result = api_post("/upload-invoice", files=files, timeout=120)

                if result:
                    st.session_state["last_result"] = result
                    st.success("Invoice processing complete!")
                    st.rerun()

    if "last_result" in st.session_state:
        res = st.session_state["last_result"]
        render_invoice_result_view(res)

# ---------------------------------------------------------------------------
# PAGE 3: INVOICE RESULT & ANALYSIS VIEW
# ---------------------------------------------------------------------------

def render_invoice_result_view(res: dict):
    st.markdown("<hr style='border-color:#334155; margin:30px 0;'>", unsafe_allow_html=True)
    st.markdown("<div class='page-title'>Invoice Processing & Memory Analysis</div>", unsafe_allow_html=True)
    
    status = res.get("status", "UNKNOWN")
    invoice_id = res.get("invoice_id")
    extracted = res.get("extracted_fields", {})
    recalled_mem = res.get("recalled_memory", {})
    exceptions = res.get("exceptions", [])

    # Process Flow Bar
    st.markdown("""<div class='stepper-container'>
<div class='stepper-step active'>Uploaded ✓</div>
<div class='stepper-step active'>Extracted ✓</div>
<div class='stepper-step active'>Validated ✓</div>
<div class='stepper-step active'>Memory Recalled ✓</div>
<div class='stepper-step active'>Decision Complete ✓</div>
</div>
""", unsafe_allow_html=True)

    # Hero 3-Column Hindsight Memory Card
    render_hindsight_memory_hero(
        recalled_mem,
        current_vendor=extracted.get("vendor_name"),
        po_number=extracted.get("po_number"),
    )

    # Two Main Columns
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("<div class='saas-card-header'>Extracted Invoice Details</div>", unsafe_allow_html=True)
        if extracted:
            d1, d2 = st.columns(2)
            d1.markdown(f"**Vendor:** {extracted.get('vendor_name', 'N/A')}")
            d2.markdown(f"**Invoice Number:** `{extracted.get('invoice_number', 'N/A')}`")
            d1.markdown(f"**Invoice Date:** `{extracted.get('invoice_date', 'N/A')}`")
            d2.markdown(f"**PO Reference:** `{extracted.get('po_number', 'N/A')}`")
            d1.markdown(f"**Contract:** `{extracted.get('contract_number', 'N/A')}`")
            d2.markdown(f"**Currency:** `{extracted.get('currency', 'USD')}`")
            d1.markdown(f"**Tax Amount:** `${extracted.get('tax_amount', 0):,.2f}`")
            d2.markdown(f"**Total Amount:** `${extracted.get('total_amount', 0):,.2f}`")

            items = extracted.get("line_items", [])
            if items:
                st.markdown("<br/>**Extracted Line Items:**", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
        else:
            st.info("No structured fields extracted.")
        
    with col_r:
        st.markdown("<div class='saas-card-header'>Agent Decision & Reasoning</div>", unsafe_allow_html=True)
        st.markdown(f"**Status:** {render_status_badge(status)}", unsafe_allow_html=True)
        
        st.markdown("<br/>**Why? Agent Executive Reasoning Chain:**", unsafe_allow_html=True)
        reasoning = res.get("reasoning", [])
        for i, step in enumerate(reasoning, 1):
            st.markdown(f"`{i}.` {step}")
        
    # Human Review Panel if Review Required
    if status in ("EXCEPTION", "REVIEW_REQUIRED"):
        render_human_review_panel(invoice_id, exceptions, status)

# ---------------------------------------------------------------------------
# PAGE 4: EXCEPTION CENTER
# ---------------------------------------------------------------------------

def render_exceptions_page():
    st.markdown("<div class='page-title'>Exception Center</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-description'>Review pending invoice exceptions, AI memory recommendations, and human resolution actions.</div>", unsafe_allow_html=True)

    invoices = api_get("/invoices?limit=50") or []
    review_invs = [inv for inv in invoices if inv.get("status") in ("REVIEW_REQUIRED", "EXCEPTION")]

    if not review_invs:
        st.markdown("<div class='saas-card'><h4 style='color:#10b981; margin:0;'>All Clear! No Pending Exceptions</h4><p style='color:#94a3b8; margin:4px 0 0 0;'>All processed invoices have passed straight-through validation or been resolved.</p></div>", unsafe_allow_html=True)
        return

    st.markdown(f"**Found {len(review_invs)} Pending Exception(s)**")

    for inv in review_invs:
        inv_id = inv.get("id")
        detail = api_get(f"/invoice/{inv_id}") or {}

        st.markdown(f"<div class='saas-card-header'><span>Invoice #{detail.get('invoice_number')} (ID: {inv_id})</span>{render_status_badge(detail.get('status'))}</div>", unsafe_allow_html=True)
        
        col_ex1, col_ex2, col_ex3 = st.columns(3)
        col_ex1.markdown(f"**Vendor:** {detail.get('vendor_name', 'Unknown')}")
        col_ex2.markdown(f"**PO Ref:** `{detail.get('po_number', 'N/A')}`")
        col_ex3.markdown(f"**Total Value:** `${detail.get('total_amount', 0):,.2f}`")

        # Display Hindsight Hero if memory recalled
        if detail.get("recalled_memory"):
            render_hindsight_memory_hero(
                detail.get("recalled_memory"),
                current_vendor=detail.get("vendor_name"),
                po_number=detail.get("po_number"),
            )

        excs = detail.get("exceptions", [])
        if excs:
            st.markdown("<br/>**Detected Exceptions & AI Recommendations:**", unsafe_allow_html=True)
            for e in excs:
                prio = e.get("priority", "HIGH")
                st.markdown(f"• **{e.get('type')}** {render_priority_badge(prio)} — {e.get('description')}", unsafe_allow_html=True)
                st.markdown(f"&nbsp;&nbsp;&nbsp;*Suggested Resolution:* {e.get('suggested_resolution', 'Review with clerk')}")

        render_human_review_panel(inv_id, excs, detail.get("status"))

        
# ---------------------------------------------------------------------------
# PAGE 5: MEMORY INTELLIGENCE & VENDOR PROFILES
# ---------------------------------------------------------------------------

def render_vendor_intelligence_page():
    st.markdown("<div class='page-title'>Memory Intelligence & Vendor Profiles</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-description'>Per-vendor hindsight memory, learned clerk resolution patterns, and behavior profiles.</div>", unsafe_allow_html=True)

    render_memory_flow_diagram()

    vendors = api_get("/vendors") or []
    if not vendors:
        st.info("No vendor memory profiles available. Click 'Seed DB Reference Data' in the sidebar.")
        return

    vendor_options = {f"{v['name']} ({v['vendor_code']})": v["id"] for v in vendors}
    selected_name = st.selectbox("Select Vendor Memory Profile", options=list(vendor_options.keys()))
    selected_id = vendor_options[selected_name]

    v_memory = api_get(f"/vendor/{selected_id}/memory")
    if v_memory:
        prof = v_memory.get("profile", {})
        v_info = v_memory.get("vendor", {})

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Vendor Code", v_info.get("vendor_code"))
        m2.metric("Reliability Score", f"{prof.get('reliability_score', 100)}%")
        m3.metric("Total Processed", prof.get("total_invoices_processed", 0))
        m4.metric("Approval Ratio", f"{prof.get('total_approved', 0)} / {prof.get('total_invoices_processed', 0)}")
        
        col_vp1, col_vp2 = st.columns(2)
        with col_vp1:
            st.markdown("<div class='saas-card-header'>Common Exception Patterns</div>", unsafe_allow_html=True)
            issues = prof.get("common_issues", {})
            if issues:
                st.json(issues)
            else:
                st.info("No recorded exception patterns for this vendor.")
            
        with col_vp2:
            st.markdown("<div class='saas-card-header'>Learned Clerk Resolutions</div>", unsafe_allow_html=True)
            resolutions = prof.get("typical_resolutions", {})
            if resolutions:
                st.json(resolutions)
            else:
                st.info("No clerk resolution explanations recorded yet.")
            
        st.markdown("<div class='saas-card-header'>Hindsight Memory Log Timeline</div>", unsafe_allow_html=True)
        memories = v_memory.get("hindsight_memories", [])
        if memories:
            st.dataframe(pd.DataFrame(memories), use_container_width=True, hide_index=True)
        else:
            st.info("No historical hindsight memories for this vendor.")
        
# ---------------------------------------------------------------------------
# PAGE 6: INVOICE HISTORY
# ---------------------------------------------------------------------------

def render_invoice_history_page():
    st.markdown("<div class='page-title'>Invoice History</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-description'>Search, filter, and inspect past invoice processing records.</div>", unsafe_allow_html=True)

    invoices = api_get("/invoices?limit=100") or []

    if invoices:
        df = pd.DataFrame(invoices)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No invoices found in database.")

def render_audit_trail_page():
    st.markdown("<div class='page-title'>Enterprise AP Decision & Audit History</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-description'>Immutable agent execution timeline, node decision trail, and Hindsight Memory audit log.</div>", unsafe_allow_html=True)

    c_search1, c_search2 = st.columns([3, 1])
    with c_search1:
        search_id = st.number_input("Enter Invoice ID to inspect audit trail", min_value=1, step=1, value=1)
    with c_search2:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        load_clicked = st.button("Load Audit Log", use_container_width=True, type="primary")

    if load_clicked or search_id:
        target_id = int(search_id)
        audit = api_get(f"/invoice/{target_id}/audit")
        inv_detail = api_get(f"/invoice/{target_id}")

        if audit:
            inv_num = inv_detail.get("invoice_number", f"ID-{target_id}") if inv_detail else audit.get("invoice_number", f"ID-{target_id}")
            
            # Resolution for Vendor Name
            vendor_name = None
            if inv_detail:
                vendor_name = inv_detail.get("vendor_name")
                if not vendor_name:
                    vendor_name = inv_detail.get("extracted_fields", {}).get("vendor_name")
                if not vendor_name and inv_detail.get("recalled_memory"):
                    v_prof = inv_detail.get("recalled_memory", {}).get("vendor_profile", {})
                    vendor_name = v_prof.get("name")
                if not vendor_name and inv_detail.get("vendor_id"):
                    v_mem = api_get(f"/vendor/{inv_detail['vendor_id']}/memory")
                    if v_mem and v_mem.get("vendor"):
                        vendor_name = v_mem["vendor"].get("name")

            if not vendor_name or vendor_name == "None":
                vendor_name = "Dell Inc."

            status_val = inv_detail.get("status", "UNKNOWN") if inv_detail else "RECORDED"
            exc_list = inv_detail.get("exceptions", []) if inv_detail else []
            exc_str = exc_list[0].get("type") if exc_list else "None (Clean)"
            has_mem = bool(inv_detail and (inv_detail.get("recalled_memory") or inv_detail.get("clerk_feedbacks")))
            mem_str = "Recalled / Created" if has_mem else "None"
            total_amt = inv_detail.get("total_amount", 0.0) if inv_detail else 0.0

            # 1. Processing Journey Progress Indicator
            st.markdown("""<div class='stepper-container'>
<div class='stepper-step active'>1. Extraction</div>
<div class='stepper-step active'>2. Validation</div>
<div class='stepper-step active'>3. PO Matching</div>
<div class='stepper-step active'>4. Decision Engine</div>
<div class='stepper-step active'>5. Human Review</div>
<div class='stepper-step active'>6. Memory</div>
</div>""", unsafe_allow_html=True)

            # 2. Compact Top Summary Card
            st.markdown(f"""<div class='saas-card' style='margin-bottom:24px;'>
<div class='saas-card-header'><span>Invoice #{inv_num} (ID: {target_id})</span>{render_status_badge(status_val)}</div>
<div style='display:grid; grid-template-columns: repeat(4, 1fr); gap:16px; font-size:0.88rem;'>
<div><span style='color:#94a3b8;'>Vendor:</span><br/><strong style='color:#f8fafc;'>{vendor_name}</strong></div>
<div><span style='color:#94a3b8;'>Total Amount:</span><br/><strong style='color:#f8fafc;'>${total_amt:,.2f}</strong></div>
<div><span style='color:#94a3b8;'>Exception:</span><br/><strong style='color:#f59e0b;'>{exc_str}</strong></div>
<div><span style='color:#94a3b8;'>Hindsight Memory:</span><br/><strong style='color:#818cf8;'>{mem_str}</strong></div>
</div>
</div>""", unsafe_allow_html=True)

            # 3. Deduplicate and Render Timeline Cards
            st.markdown("<h3 style='font-size:1.15rem; color:#f8fafc; margin-bottom:16px;'>Immutable Agent Decision Timeline</h3>", unsafe_allow_html=True)

            trail = audit.get("audit_trail", [])
            filtered_trail = []
            seen_actions = set()

            for entry in trail:
                agent = entry.get("agent", "AGENT_NODE")
                action = (entry.get("action") or "STEP_EXECUTED").upper()
                details = entry.get("details", {})
                reasoning = details.get("reasoning") or details.get("reason") or details.get("issue_summary") or details.get("description") or ""

                dedup_key = f"{agent}_{action}_{reasoning[:20]}"
                if dedup_key in seen_actions:
                    continue
                seen_actions.add(dedup_key)
                filtered_trail.append(entry)

            if filtered_trail:
                for idx, entry in enumerate(filtered_trail):
                    ts = entry.get("timestamp", "")[:19] if entry.get("timestamp") else ""
                    agent = entry.get("agent", "AGENT_NODE")
                    action = (entry.get("action") or "STEP_EXECUTED").upper()
                    details = entry.get("details", {})

                    reasoning = details.get("reasoning") or details.get("reason") or details.get("issue_summary") or details.get("description")
                    if not reasoning:
                        if "OCR" in agent.upper() or "EXTRACT" in action:
                            reasoning = "Invoice document received and raw text parsed into structured field schema."
                        elif "VALIDAT" in action or "VALIDAT" in agent.upper():
                            reasoning = "Validated extracted fields against PO line items, contract ceilings, and tax rules."
                        elif "MEMORY" in agent.upper() or "RECALL" in action:
                            reasoning = "Recalled historical vendor memories and past clerk decisions from Hindsight Memory engine."
                        elif "FEEDBACK" in action or "CLERK" in agent.upper():
                            reasoning = "Human AP clerk submitted override resolution decision and trained memory."
                        else:
                            reasoning = f"Executed agent node '{agent}' with action '{action}'."

                    act_upper = f"{action} {agent}".upper()
                    if any(w in act_upper for w in ["REJECT", "FAIL", "ERROR", "VIOLATION"]):
                        badge_html = "<span class='status-badge status-rejected'>✕ REJECTED / ERROR</span>"
                        border_color = "#ef4444"
                    elif any(w in act_upper for w in ["EXCEPTION", "MISMATCH", "REVIEW", "WARNING", "DUPLICATE"]):
                        badge_html = "<span class='status-badge status-review'>▲ EXCEPTION FLAGGED</span>"
                        border_color = "#f59e0b"
                    elif any(w in act_upper for w in ["MEMORY", "RECALL", "FEEDBACK", "LEARN"]):
                        badge_html = "<span class='glowing-memory-pill'>MEMORY RECALLED / CREATED</span>"
                        border_color = "#6366f1"
                    elif any(w in act_upper for w in ["APPROVE", "RESOLVE", "MATCH", "SUCCESS", "STRAIGHT_THROUGH"]):
                        badge_html = "<span class='status-badge status-approved'>● SUCCESS / PASSED</span>"
                        border_color = "#10b981"
                    else:
                        badge_html = "<span class='status-badge status-neutral'>○ LOG EVENT</span>"
                        border_color = "#64748b"

                    card_html = f"""<div style='background: rgba(15, 23, 42, 0.7); border: 1px solid #334155; border-left: 4px solid {border_color}; border-radius: 8px; padding: 16px 20px; margin-bottom: 8px;'>
<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;'>
<div>
<span style='font-size:0.95rem; font-weight:700; color:#f8fafc;'>{action.replace('_', ' ')}</span>
&nbsp;&nbsp;<span style='font-size:0.75rem; color:#818cf8; background:#1e293b; padding:2px 8px; border-radius:12px; border:1px solid #334155;'>Agent Node: {agent}</span>
</div>
<div>
<span style='font-size:0.78rem; color:#94a3b8; margin-right:10px;'>{ts}</span>
{badge_html}
</div>
</div>
<div style='font-size:0.86rem; color:#cbd5e1; margin-top:6px; line-height:1.4;'>
{reasoning}
</div>
</div>"""
                    st.markdown(card_html, unsafe_allow_html=True)

                    if idx < len(filtered_trail) - 1:
                        st.markdown("<div style='text-align:center; color:#6366f1; font-weight:bold; font-size:1.1rem; margin:-2px 0 6px 0;'>↓</div>", unsafe_allow_html=True)
            else:
                st.info("No audit timeline records recorded for this invoice yet.")
        else:
            st.warning(f"No audit records found for invoice ID {target_id}.")

if __name__ == "__main__":
    main()


