import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# ---------------------------------------------------------------------------
# Configuration & Custom CSS
# ---------------------------------------------------------------------------

try:
    API_URL = st.secrets["API_URL"]
except (KeyError, FileNotFoundError):
    API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="AP Invoice Exception Agent",
    layout="wide",
    page_icon="🧠",
    initial_sidebar_state="expanded",
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
    }
    
    .header-gradient {
        background: linear-gradient(135deg, #6366f1 0%, #3b82f6 50%, #06b6d4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.2rem;
        margin-bottom: 0px;
    }
    
    .card-glass {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    
    .memory-card {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(6, 182, 212, 0.15) 100%);
        border: 1px solid rgba(99, 102, 241, 0.4);
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 20px;
    }

    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        padding: 16px !important;
        border-radius: 12px !important;
    }
    [data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 0.9rem !important; }
    [data-testid="stMetricValue"] { color: #f8fafc !important; font-weight: 700 !important; }

    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
    }

    .badge {
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 12px;
        display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# API Helpers
# ---------------------------------------------------------------------------

def _wake_backend() -> bool:
    for attempt in range(3):
        try:
            resp = requests.get(f"{API_URL}/", timeout=(10, 20))
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
        st.error("Cannot reach the backend — connection refused.")
        return None
    except requests.exceptions.Timeout:
        st.warning("⏳ Backend is waking up. Please refresh the page in a moment.")
        return None
    except requests.exceptions.HTTPError as exc:
        st.error(f"API error: {exc.response.status_code} — {exc.response.text}")
        return None
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
        return None


def api_post(path: str, json_data: dict, timeout: int = 30) -> dict | None:
    try:
        resp = requests.post(f"{API_URL}{path}", json=json_data, timeout=(10, timeout))
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        st.error(f"API POST failed: {exc}")
        return None


def status_badge(status: str) -> str:
    color_map = {
        "STRAIGHT_THROUGH": "#10b981",
        "APPROVED": "#10b981",
        "RESOLVED": "#06b6d4",
        "REVIEW_REQUIRED": "#f59e0b",
        "EXCEPTION": "#f59e0b",
        "REJECTED": "#ef4444",
        "EXTRACTION_FAILED": "#ef4444",
        "PENDING": "#6b7280",
    }
    color = color_map.get(status, "#6b7280")
    return f'<span class="badge" style="background-color:{color}22; color:{color}; border:1px solid {color};">{status}</span>'


def priority_badge(priority: str) -> str:
    color_map = {
        "HIGH": "#ef4444",
        "MEDIUM": "#f59e0b",
        "LOW": "#10b981",
    }
    color = color_map.get(priority, "#6b7280")
    return f'<span class="badge" style="background-color:{color}22; color:{color}; border:1px solid {color};">{priority} PRIORITY</span>'


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------

def render_clerk_feedback_card(invoice_id: int, current_status: str, exceptions: list):
    """
    Renders an interactive AP Clerk decision card allowing Approve / Reject / Resolve actions.
    """
    st.markdown("<div class='card-glass'>", unsafe_allow_html=True)
    st.subheader("⚖️ AP Clerk Exception Resolution Panel")
    st.markdown(
        "Review AI recommendation and past memory context, then select a resolution action to update invoice status and store decision memory."
    )

    with st.form(key=f"clerk_feedback_form_{invoice_id}"):
        col_act, col_exc = st.columns([1, 1])

        with col_act:
            action = st.radio(
                "Clerk Resolution Action",
                options=["APPROVE", "RESOLVE", "REJECT"],
                format_func=lambda x: {
                    "APPROVE": "✅ Approve Invoice (Override & Authorize Payment)",
                    "RESOLVE": "🔧 Resolve Exception (Accept Variance as Valid)",
                    "REJECT": "❌ Reject Invoice (Send back to Vendor)",
                }[x],
            )

        with col_exc:
            exc_types = [e.get("type") for e in exceptions if e.get("type")] or ["GENERAL_EXCEPTION"]
            target_exc = st.selectbox("Associated Exception Type", options=exc_types)

        reason = st.text_area(
            "Clerk Reason / Explanation (Stored in Hindsight Memory)",
            placeholder="e.g. Verified price variance with PO manager. Vendor account approved for $15 unit difference.",
            height=100,
        )

        submit_btn = st.form_submit_button("💾 Submit Clerk Decision & Train Memory")

        if submit_btn:
            if not reason.strip():
                st.warning("Please provide a reason/explanation for your decision.")
            else:
                payload = {
                    "action": action,
                    "reason": reason.strip(),
                    "exception_type": target_exc,
                }
                res = api_post(f"/invoice/{invoice_id}/feedback", payload)
                if res and res.get("status") == "success":
                    st.success(
                        f"Invoice #{invoice_id} status updated to **{res.get('new_invoice_status')}**! Hindsight memory created."
                    )
                    # Refresh searched invoice session state
                    refreshed = api_get(f"/invoice/{invoice_id}")
                    if refreshed:
                        st.session_state["searched_invoice"] = refreshed
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_hindsight_memory_card(recalled_memory: dict):
    """
    Renders the Hindsight Memory & Executive Summary card.
    """
    if not recalled_memory:
        return

    st.markdown("<div class='memory-card'>", unsafe_allow_html=True)
    st.write("### 🧠 Hindsight Memory & AI Intelligence")

    exec_summary = recalled_memory.get("executive_summary", "")
    if exec_summary:
        st.info(f"**AI Recalled Experience:** {exec_summary}")

    vendor_prof = recalled_memory.get("vendor_profile", {})
    if vendor_prof:
        c1, c2, c3 = st.columns(3)
        c1.metric("Vendor Reliability Score", f"{vendor_prof.get('reliability_score', 100)}%")
        c2.metric("Total Past Invoices", vendor_prof.get("total_invoices_processed", 0))
        c3.metric("Approved / Resolved", vendor_prof.get("total_approved", 0))

    past_mems = recalled_memory.get("recalled_memories", [])
    if past_mems:
        st.write("**Recent Hindsight Memory Log for Vendor / PO:**")
        mem_df = pd.DataFrame(past_mems)[["issue_type", "clerk_action", "clerk_reason", "po_number"]]
        st.dataframe(mem_df, use_container_width=True, hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------

def main():
    st.markdown("<h1 class='header-gradient'>📑 AP Invoice Exception Agent</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; font-size:1.1rem;'>Autonomous Accounts Payable Processing with Hindsight Memory & Human-in-the-Loop Feedback</p>", unsafe_allow_html=True)
    st.divider()

    # -----------------------------------------------------------------------
    # SIDEBAR — Upload + Search + Seed
    # -----------------------------------------------------------------------
    with st.sidebar:
        st.header("🚀 Upload Invoice")
        uploaded_file = st.file_uploader(
            "Upload PDF or Image Invoice", type=["pdf", "png", "jpg", "jpeg"]
        )

        if uploaded_file and st.button("⚡ Process Invoice with Agent"):
            with st.spinner("Pipeline running: Extract → Validate → Match → Recall Memory → Decide..."):
                try:
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type,
                        )
                    }
                    resp = requests.post(f"{API_URL}/upload-invoice", files=files, timeout=120)
                    try:
                        result = resp.json()
                    except Exception:
                        st.error(f"Unreadable response (HTTP {resp.status_code}): {resp.text[:300]}")
                        result = None

                    if result is not None:
                        if resp.status_code == 200:
                            st.session_state["last_result"] = result
                            st.success("Invoice processed successfully!")
                        else:
                            detail = result.get("detail", resp.text)
                            st.error(f"Processing failed ({resp.status_code}): {detail}")
                except Exception as exc:
                    st.error(f"Error: {exc}")

        st.divider()

        st.header("🔍 Lookup Invoice")
        search_id = st.number_input("Invoice ID", min_value=1, step=1, value=1)
        if st.button("Fetch Invoice Detail"):
            data = api_get(f"/invoice/{int(search_id)}")
            if data:
                st.session_state["searched_invoice"] = data

        st.divider()

        st.header("⚙️ Admin Actions")
        if st.button("🌱 Seed DB (Multi-Vendor + Memories)"):
            with st.spinner("Seeding database..."):
                res = api_post("/seed-db", {})
                if res and res.get("status") == "ok":
                    st.success("Database seeded with Multi-Vendor dataset & Hindsight Memory!")
                    st.rerun()

    # -----------------------------------------------------------------------
    # LATEST UPLOAD RESULT
    # -----------------------------------------------------------------------
    if "last_result" in st.session_state:
        res = st.session_state["last_result"]
        st.subheader("📋 Latest Processing Result")

        status = res.get("status", "UNKNOWN")
        st.markdown(
            f"**Invoice ID:** `{res.get('invoice_id')}` &nbsp;|&nbsp; "
            f"**Number:** `{res.get('invoice_number')}` &nbsp;|&nbsp; "
            f"**Agent Decision:** {status_badge(status)}",
            unsafe_allow_html=True,
        )

        # Render Hindsight Memory Card
        if res.get("recalled_memory"):
            render_hindsight_memory_card(res.get("recalled_memory"))

        col_l, col_r = st.columns(2)

        with col_l:
            st.write("#### Extracted Fields")
            fields = res.get("extracted_fields", {})
            if fields:
                display = {k: v for k, v in fields.items() if k != "line_items"}
                st.json(display)
                line_items = fields.get("line_items", [])
                if line_items:
                    st.write("**Line Items**")
                    st.dataframe(pd.DataFrame(line_items), use_container_width=True)
            else:
                st.info("No fields extracted.")

        with col_r:
            st.write("#### Prioritized Exceptions & Recommendations")
            exceptions = res.get("exceptions", [])
            if exceptions:
                for exc in exceptions:
                    prio = exc.get("priority", "HIGH")
                    st.markdown(
                        f"**{exc.get('type')}** {priority_badge(prio)}<br/>"
                        f"• **Issue:** {exc.get('description')}<br/>"
                        f"• **Suggested Resolution:** {exc.get('suggested_resolution', 'N/A')}<br/>"
                        f"• **Recommendation:** {exc.get('recommendation', 'N/A')}",
                        unsafe_allow_html=True,
                    )
                    st.divider()
            else:
                st.success("No exceptions found — Straight-Through Payment Scheduled!")

            st.write("#### Agent Pipeline Reasoning Chain")
            reasoning = res.get("reasoning", [])
            for i, step in enumerate(reasoning, 1):
                st.markdown(f"`{i}.` {step}")

        # Render Feedback Card if review required
        if status in ("EXCEPTION", "REVIEW_REQUIRED"):
            render_clerk_feedback_card(res.get("invoice_id"), status, exceptions)

    # -----------------------------------------------------------------------
    # SEARCHED INVOICE DETAIL
    # -----------------------------------------------------------------------
    if "searched_invoice" in st.session_state:
        inv = st.session_state["searched_invoice"]
        st.divider()
        st.subheader(f"🔍 Invoice Detail — #{inv.get('id')}")

        st.markdown(
            f"**Invoice Number:** `{inv.get('invoice_number')}` &nbsp;|&nbsp; "
            f"**Vendor:** `{inv.get('vendor_name', 'Unknown')}` &nbsp;|&nbsp; "
            f"**PO Number:** `{inv.get('po_number', 'N/A')}` &nbsp;|&nbsp; "
            f"**Status:** {status_badge(inv.get('status', ''))} &nbsp;|&nbsp; "
            f"**Total:** `{inv.get('currency', 'USD')} {inv.get('total_amount', 0):,.2f}`",
            unsafe_allow_html=True,
        )

        if inv.get("recalled_memory"):
            render_hindsight_memory_card(inv.get("recalled_memory"))

        detail_exceptions = inv.get("exceptions", [])
        if detail_exceptions:
            st.write("**Exceptions & AI Recommendations:**")
            for exc in detail_exceptions:
                prio = exc.get("priority", "HIGH")
                st.markdown(
                    f"**{exc.get('type')}** {priority_badge(prio)} — {exc.get('description')}<br/>"
                    f"👉 *Suggested Resolution:* {exc.get('suggested_resolution', 'Review with clerk')}",
                    unsafe_allow_html=True,
                )

        feedbacks = inv.get("clerk_feedbacks", [])
        if feedbacks:
            st.write("**Historical Clerk Feedback Log:**")
            st.dataframe(pd.DataFrame(feedbacks), use_container_width=True, hide_index=True)

        if inv.get("status") in ("REVIEW_REQUIRED", "EXCEPTION"):
            render_clerk_feedback_card(inv.get("id"), inv.get("status"), detail_exceptions)

        if st.button("📜 Load Audit Trail"):
            audit = api_get(f"/invoice/{inv['id']}/audit")
            if audit:
                st.session_state["audit_data"] = audit

    # -----------------------------------------------------------------------
    # DASHBOARD TABS
    # -----------------------------------------------------------------------
    st.divider()

    if "backend_ready" not in st.session_state:
        with st.spinner("Connecting to backend..."):
            st.session_state["backend_ready"] = _wake_backend()

    if not st.session_state["backend_ready"]:
        st.error("Backend is unreachable. Please start the FastAPI backend server.")
        return

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Executive Dashboard",
        "🧠 Vendor Memory Profiles",
        "📋 Recent Invoices",
        "🛡️ Audit Trail",
    ])

    # --- Tab 1: Dashboard ---
    with tab1:
        stats = api_get("/stats")
        if stats:
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Total Invoices", stats.get("total_invoices", 0))
            c2.metric("Straight-Through Rate", f"{stats.get('straight_through_pct', 0)}%")
            c3.metric("Pending Review", stats.get("review_required", 0))
            c4.metric("Approved / Resolved", stats.get("approved", 0))
            c5.metric("Scheduled Value", f"${stats.get('total_scheduled_value', 0):,.2f}")

            st.write("---")
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.write("#### Invoice Status Breakdown")
                status_counts = pd.DataFrame([
                    {"Status": "Straight-Through", "Count": stats.get("straight_through", 0)},
                    {"Status": "Review Required", "Count": stats.get("review_required", 0)},
                    {"Status": "Approved / Resolved", "Count": stats.get("approved", 0)},
                    {"Status": "Rejected", "Count": stats.get("rejected", 0)},
                ])
                fig_pie = px.pie(
                    status_counts,
                    values="Count",
                    names="Status",
                    hole=0.4,
                    color="Status",
                    color_discrete_map={
                        "Straight-Through": "#10b981",
                        "Approved / Resolved": "#06b6d4",
                        "Review Required": "#f59e0b",
                        "Rejected": "#ef4444",
                    },
                )
                fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f8fafc")
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_chart2:
                st.write("#### Vendor Reliability Scores (%)")
                vendors_list = api_get("/vendors")
                if vendors_list:
                    v_df = pd.DataFrame(vendors_list)
                    fig_bar = px.bar(
                        v_df,
                        x="name",
                        y="reliability_score",
                        color="reliability_score",
                        labels={"name": "Vendor", "reliability_score": "Reliability Score (%)"},
                        color_continuous_scale="Viridis",
                    )
                    fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#f8fafc")
                    st.plotly_chart(fig_bar, use_container_width=True)

    # --- Tab 2: Vendor Memory Profiles ---
    with tab2:
        st.subheader("🧠 Vendor Hindsight Memory & Reliability Profiles")
        vendors = api_get("/vendors")
        if vendors:
            vendor_opts = {f"{v['name']} ({v['vendor_code']})": v["id"] for v in vendors}
            selected_v_name = st.selectbox("Select Vendor Profile", options=list(vendor_opts.keys()))
            selected_v_id = vendor_opts[selected_v_name]

            v_memory = api_get(f"/vendor/{selected_v_id}/memory")
            if v_memory:
                prof = v_memory.get("profile", {})
                v_info = v_memory.get("vendor", {})

                st.markdown("<div class='card-glass'>", unsafe_allow_html=True)
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("Vendor Code", v_info.get("vendor_code"))
                mc2.metric("Reliability Score", f"{prof.get('reliability_score', 100)}%")
                mc3.metric("Total Processed", prof.get("total_invoices_processed", 0))
                mc4.metric("Approval Ratio", f"{prof.get('total_approved', 0)} / {prof.get('total_invoices_processed', 0)}")
                st.markdown("</div>", unsafe_allow_html=True)

                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    st.write("#### Common Issues Frequency")
                    issues = prof.get("common_issues", {})
                    if issues:
                        st.json(issues)
                    else:
                        st.info("No recorded issues for this vendor.")

                with col_p2:
                    st.write("#### Typical Clerk Resolutions")
                    resolutions = prof.get("typical_resolutions", {})
                    if resolutions:
                        st.json(resolutions)
                    else:
                        st.info("No typical resolutions recorded yet.")

                st.write("#### Hindsight Memory History Log")
                h_mems = v_memory.get("hindsight_memories", [])
                if h_mems:
                    st.dataframe(pd.DataFrame(h_mems), use_container_width=True, hide_index=True)
                else:
                    st.info("No hindsight memory records available.")

    # --- Tab 3: Recent Invoices ---
    with tab3:
        invoices = api_get("/invoices?limit=50")
        if invoices:
            rows = []
            for inv in invoices:
                rows.append({
                    "ID": inv.get("id"),
                    "Invoice Number": inv.get("invoice_number"),
                    "Status": inv.get("status"),
                    "Total Amount": f"${inv.get('total_amount', 0):,.2f}",
                    "Created At": inv.get("created_at", "")[:19] if inv.get("created_at") else "",
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

    # --- Tab 4: Audit Trail ---
    with tab4:
        if "audit_data" in st.session_state:
            audit = st.session_state["audit_data"]
            st.write(f"### Audit Trail — Invoice #{audit.get('invoice_id')} (`{audit.get('invoice_number')}`)")
            trail = audit.get("audit_trail", [])
            for entry in trail:
                ts = entry.get("timestamp", "")[:19] if entry.get("timestamp") else ""
                agent = entry.get("agent", "unknown")
                action = entry.get("action", "")
                details = entry.get("details", {})
                with st.expander(f"[{ts}] {agent} → {action}"):
                    st.json(details)
        else:
            st.info("Search for an invoice using the sidebar, then click 'Load Audit Trail'.")


if __name__ == "__main__":
    main()
