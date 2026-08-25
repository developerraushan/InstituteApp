import os
import re
import time
import streamlit as st
import pandas as pd
from agents import handle_query, test_connection
from tools import get_file_path, ROMAN_MAP

LOGO_PATH = "logo.jpg" if os.path.exists("logo.jpg") else ("Result Flex 2019.jpg" if os.path.exists("Result Flex 2019.jpg") else None)

st.set_page_config(
    page_title="Ramakant Vidyapith Student Tracking System",
    page_icon=LOGO_PATH or "🏫",
    layout="wide"
)

# =============================================================
# CLEAN LIGHT THEME
# =============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        border: none;
        background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%);
        color: white;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
        color: white;
    }
    
    .time-badge {
        display: inline-flex;
        align-items: center;
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        margin-top: 6px;
    }
    
    .filter-card {
        background-color: #fff7ed;
        border: 1px solid #fed7aa;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "llm_connected" not in st.session_state:
    st.session_state.llm_connected = False
if "conn_message" not in st.session_state:
    st.session_state.conn_message = ""
if "active_provider" not in st.session_state:
    st.session_state.active_provider = ""
if "connected_config" not in st.session_state:
    st.session_state.connected_config = {}

# =============================================================
# SIDEBAR
# =============================================================
with st.sidebar:
    if LOGO_PATH:
        st.image(LOGO_PATH, width=120)
    
    st.markdown("### ⚙️ System Engine")
    
    def on_mode_change():
        st.session_state.llm_connected = False
        st.session_state.conn_message = ""
        st.session_state.connected_config = {}

    ai_mode = st.radio(
        "Provider Mode", 
        ["System Default", "Cloud", "Local"], 
        index=0, 
        key="provider_selection",
        on_change=on_mode_change
    )

    current_config = {}

    if ai_mode == "System Default":
        st.caption("Pre-configured Cloud Engine (`openai/gpt-oss-20b`)")
        system_key = ""
        try:
            if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
                system_key = st.secrets["GROQ_API_KEY"]
        except Exception:
            system_key = os.getenv("GROQ_API_KEY", "")

        current_config["api_key"] = system_key
        if system_key:
            st.info("🔒 Ready to connect with secure system key.")
        else:
            st.warning("⚠️ No GROQ_API_KEY found in secrets.")

    elif ai_mode == "Cloud":
        st.caption("Cloud Engine (Groq: `openai/gpt-oss-20b`)")
        user_key = st.text_input("Grok_Api_Key", type="password", placeholder="gsk_...", key="custom_grok_key")
        current_config["api_key"] = user_key.strip()

    elif ai_mode == "Local":
        st.caption("LM Studio / Ngrok Tunnel Connection")
        tunnel_url = st.text_input(
            "Server / Tunnel URL",
            value="",
            placeholder="https://xxxx-xx-xx.ngrok-free.app",
            help="Enter your ngrok forwarding URL or local server address."
        )

        clean_url = tunnel_url.strip().rstrip("/")
        if clean_url and not clean_url.endswith("/v1"):
            clean_url = f"{clean_url}/v1"

        current_config["base_url"] = clean_url if clean_url else "http://127.0.0.1:1234/v1"
        st.markdown(f"<div style='font-size:12px; color:#64748b; margin: 8px 0;'>Target: <code>{current_config['base_url']}</code></div>", unsafe_allow_html=True)

    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.0, step=0.1)
    current_config["temperature"] = temperature

    # Connect Action
    if st.button("🔌 Connect to LLM", use_container_width=True):
        if (ai_mode in ["System Default", "Cloud"]) and not current_config.get("api_key"):
            st.session_state.llm_connected = False
            st.session_state.conn_message = "Connection Failed: No API Key provided."
        else:
            start_t = time.perf_counter()
            with st.spinner("Connecting..."):
                success, msg = test_connection(ai_mode, current_config)
                elapsed = time.perf_counter() - start_t
                st.session_state.llm_connected = success
                st.session_state.active_provider = ai_mode
                st.session_state.connected_config = current_config.copy()
                st.session_state.conn_message = f"{msg} ({elapsed:.2f}s)"

    # Status Display
    if st.session_state.llm_connected:
        st.success(f"🟢 {st.session_state.conn_message}")
    elif st.session_state.conn_message:
        st.error(f"🔴 {st.session_state.conn_message}")
    else:
        st.info("⚪ Not Connected. Click 'Connect to LLM' to start.")

# =============================================================
# HEADER
# =============================================================
col_logo, col_text = st.columns([1, 7], vertical_alignment="center")

with col_logo:
    if LOGO_PATH:
        st.image(LOGO_PATH, width=95)
    else:
        st.markdown("## 🏫")

with col_text:
    st.markdown("""
    <div>
        <h1 style='color: #9a3412; font-size: 28px; margin: 0; font-weight: 700;'>Ramakant Vidyapith</h1>
        <p style='color: #c2410c; font-size: 15px; margin: 0; font-weight: 500;'>Ramakant Vidyapith Student Tracking System</p>
    </div>
    """, unsafe_allow_html=True)

st.write("")

tabs = st.tabs(["💬 Operations Assistant", "🎓 Student 360° Profile", "📂 Live Database Explorer"])

# -------------------------------------------------------------
# TAB 1: INTERACTIVE ASSISTANT
# -------------------------------------------------------------
with tabs[0]:
    st.subheader("Interactive Assistant")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "elapsed" in msg:
                st.markdown(f"<div class='time-badge'>⏱️ Response Time: {msg['elapsed']:.2f}s</div>", unsafe_allow_html=True)

    user_query = st.chat_input("Ask anything (e.g. 'Who has pending fees in Class 10?', 'Draft WhatsApp fee reminder for RV-X-102')...")
    if user_query:
        if not st.session_state.llm_connected:
            st.error("⚠️ Please click **'🔌 Connect to LLM'** in the sidebar before making queries.")
        else:
            st.session_state.messages.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)

            with st.chat_message("assistant"):
                with st.spinner("Processing request..."):
                    start_time = time.perf_counter()
                    try:
                        active_p = st.session_state.active_provider
                        active_cfg = st.session_state.connected_config
                        response = handle_query(user_query, provider=active_p, config=active_cfg)
                        elapsed_time = time.perf_counter() - start_time
                        st.markdown(response)
                        st.markdown(f"<div class='time-badge'>⏱️ Response Time: {elapsed_time:.2f}s</div>", unsafe_allow_html=True)
                        st.session_state.messages.append({"role": "assistant", "content": response, "elapsed": elapsed_time})
                    except Exception as e:
                        st.error(f"Execution Error: {e}")

# -------------------------------------------------------------
# TAB 2: INSTANT PTM STUDENT PROFILE & WHATSAPP DRAFTS
# -------------------------------------------------------------
with tabs[1]:
    st.subheader("Student Progress & PTM Report Card")
    
    col_sel1, col_sel2, col_btn = st.columns([2, 3, 2], vertical_alignment="bottom")

    with col_sel1:
        selected_class = st.selectbox("Select Class", [10, 9, 8], format_func=lambda x: f"Class {ROMAN_MAP[x]}")
        student_files = get_file_path("student", student_class=selected_class)

    with col_sel2:
        if student_files:
            df_stud = pd.read_excel(student_files[0])
            student_choice = st.selectbox(
                "Select Student",
                df_stud["StudentID"].tolist(),
                format_func=lambda sid: f"{sid} — {df_stud[df_stud['StudentID'] == sid]['Student Name'].values[0]}"
            )
        else:
            student_choice = None
            st.warning("No student roster found.")

    with col_btn:
        generate_btn = st.button("Generate Full Report", use_container_width=True)

    if student_choice and generate_btn:
        if not st.session_state.llm_connected:
            st.error("⚠️ Please click **'🔌 Connect to LLM'** in the sidebar before generating reports.")
        else:
            start_time = time.perf_counter()
            with st.spinner("Generating student report card and WhatsApp drafts..."):
                active_p = st.session_state.active_provider
                active_cfg = st.session_state.connected_config
                profile_report = handle_query(f"Show full report for {student_choice}", provider=active_p, config=active_cfg)
                whatsapp_draft = handle_query(f"Draft a WhatsApp monthly progress report for {student_choice}", provider=active_p, config=active_cfg)
                elapsed_time = time.perf_counter() - start_time

                st.divider()
                st.markdown(f"""
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h3 style='margin: 0;'>📋 Student Comprehensive Progress Card</h3>
                    <div class='time-badge'>⏱️ Total Generation Time: {elapsed_time:.2f}s</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(profile_report)

                st.divider()
                st.markdown("### 📱 One-Click WhatsApp Notification Drafts")
                st.caption("Click the copy button at the top-right of each box to copy directly to clipboard:")

                en_msg = ""
                hi_msg = ""
                if "### HINDI" in whatsapp_draft.upper():
                    parts = whatsapp_draft.split("### HINDI")
                    en_msg = parts[0].replace("### ENGLISH MESSAGE", "").replace("### ENGLISH", "").strip()
                    hi_msg = ("### HINDI" + parts[1]).replace("### HINDI MESSAGE", "").replace("### HINDI", "").strip()
                else:
                    en_msg = whatsapp_draft

                tab_en, tab_hi = st.tabs(["📝 English Message", "🇮🇳 हिंदी संदेश (Hindi)"])
                
                with tab_en:
                    st.code(en_msg, language="markdown")
                
                with tab_hi:
                    if hi_msg:
                        st.code(hi_msg, language="markdown")
                    else:
                        st.code(whatsapp_draft, language="markdown")

# -------------------------------------------------------------
# TAB 3: LIVE DATABASE VIEWER WITH SMART FILTERS
# -------------------------------------------------------------
with tabs[2]:
    st.subheader("Live Excel Database Inspector")
    d_col1, d_col2 = st.columns(2)
    
    with d_col1:
        view_domain = st.selectbox("Select Domain", ["attendance", "academics", "student", "accounts"])
    with d_col2:
        view_class = st.selectbox("Filter Class", [10, 9, 8], key="db_view_class", format_func=lambda x: f"Class {ROMAN_MAP[x]}")

    paths = get_file_path(view_domain, student_class=view_class)
    
    if paths:
        st.info(f"📁 Reading from: `{paths[0]}`")
        df_raw = pd.read_excel(paths[0])

        # --- ATTENDANCE DOMAIN FILTERS ---
        if view_domain == "attendance":
            st.markdown("<div class='filter-card'><b>🔍 Attendance View Filters</b></div>", unsafe_allow_html=True)
            filter_mode = st.radio("Filter By", ["All Records", "By Student Name", "By Specific Date"], horizontal=True)

            date_cols = [c for c in df_raw.columns if re.match(r"^\d{2}-\d{2}-\d{4}$|^\d{4}-\d{2}-\d{2}$", str(c))]

            if filter_mode == "By Student Name":
                unique_students = df_raw["Student Name"].dropna().unique().tolist()
                sel_student = st.selectbox("Select Student Name", unique_students)
                
                df_filtered = df_raw[df_raw["Student Name"] == sel_student]
                
                if date_cols:
                    st.dataframe(df_filtered, use_container_width=True)
                    row = df_filtered.iloc[0]
                    p_dates = [d for d in date_cols if str(row[d]).strip().upper() in ["P", "PRESENT"]]
                    a_dates = [d for d in date_cols if str(row[d]).strip().upper() in ["A", "ABSENT"]]
                    st.success(f"✅ **Present Dates ({len(p_dates)}):** {', '.join(p_dates) if p_dates else 'None'}")
                    st.error(f"❌ **Absent Dates ({len(a_dates)}):** {', '.join(a_dates) if a_dates else 'None'}")
                else:
                    st.dataframe(df_filtered, use_container_width=True)

            elif filter_mode == "By Specific Date":
                if date_cols:
                    sel_date = st.selectbox("Select Date", date_cols)
                    status_filter = st.radio("Status", ["All", "Present Only", "Absent Only"], horizontal=True)

                    display_cols = ["StudentID", "Student Name", "Class", sel_date]
                    df_day = df_raw[display_cols].copy()
                    
                    if status_filter == "Present Only":
                        df_day = df_day[df_day[sel_date].astype(str).str.upper().isin(["P", "PRESENT"])]
                    elif status_filter == "Absent Only":
                        df_day = df_day[df_day[sel_date].astype(str).str.upper().isin(["A", "ABSENT"])]

                    st.dataframe(df_day, use_container_width=True)
                else:
                    dates_avail = df_raw["Date"].astype(str).unique().tolist()
                    sel_date = st.selectbox("Select Date", dates_avail)
                    df_day = df_raw[df_raw["Date"].astype(str) == sel_date]
                    st.dataframe(df_day, use_container_width=True)
            else:
                st.dataframe(df_raw, use_container_width=True)

        # --- ACADEMICS DOMAIN FILTERS ---
        elif view_domain == "academics":
            st.markdown("<div class='filter-card'><b>🔍 Academic Score Filters</b></div>", unsafe_allow_html=True)
            acad_filter_mode = st.radio("Filter By", ["All Students", "By Student Name", "By Subject"], horizontal=True)

            if acad_filter_mode == "By Student Name":
                unique_students = df_raw["Student Name"].dropna().unique().tolist()
                sel_student = st.selectbox("Select Student Name", unique_students)
                df_filtered = df_raw[df_raw["Student Name"] == sel_student]
                st.dataframe(df_filtered, use_container_width=True)

            elif acad_filter_mode == "By Subject":
                if "Subject" in df_raw.columns:
                    subjects = df_raw["Subject"].dropna().unique().tolist()
                    sel_subj = st.selectbox("Select Subject", subjects)
                    df_filtered = df_raw[df_raw["Subject"] == sel_subj]
                    st.dataframe(df_filtered, use_container_width=True)
                else:
                    st.dataframe(df_raw, use_container_width=True)
            else:
                st.dataframe(df_raw, use_container_width=True)

        # --- STUDENT & ACCOUNTS DOMAINS ---
        else:
            st.dataframe(df_raw, use_container_width=True)
            
    else:
        st.error("Target workbook not found.")