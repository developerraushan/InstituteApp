import os
import re
from datetime import datetime
import pandas as pd
from langchain_core.tools import tool

BASE_DIR = "Database"
ROMAN_MAP = {8: "VIII", 9: "IX", 10: "X"}

def to_md_table(df: pd.DataFrame) -> str:
    """Converts a pandas DataFrame to a clean Markdown table without third-party dependencies like tabulate."""
    if df.empty:
        return ""
    headers = [str(c) for c in df.columns]
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    
    rows = []
    for _, row in df.iterrows():
        row_line = "| " + " | ".join([str(val) for val in row.values]) + " |"
        rows.append(row_line)
        
    return "\n".join([header_line, separator_line] + rows)

def extract_student_id(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"\b(RV-(?:VIII|IX|X|8|9|10)-\d{3})\b", text.strip(), re.IGNORECASE)
    if match:
        raw_id = match.group(1).upper()
        return raw_id.replace("-8-", "-VIII-").replace("-9-", "-IX-").replace("-10-", "-X-")
    return ""

def get_file_path(domain: str, student_id: str = "", student_class: int = 0) -> list:
    extracted_id = extract_student_id(student_id)
    target_classes = []

    if student_class in ROMAN_MAP:
        target_classes = [student_class]
    elif extracted_id:
        parts = extracted_id.split("-")
        if len(parts) >= 2:
            token = parts[1]
            if token == "VIII":
                target_classes = [8]
            elif token == "IX":
                target_classes = [9]
            elif token == "X":
                target_classes = [10]

    if not target_classes:
        target_classes = [8, 9, 10]

    paths = []
    for c in target_classes:
        rom = ROMAN_MAP[c]
        if domain == "attendance":
            paths.append(os.path.join(BASE_DIR, "Attendance", f"Ramakant_Vidyapith_Class_{rom}_Student_Attendance.xlsx"))
        elif domain == "academics":
            paths.append(os.path.join(BASE_DIR, "Academics", f"Ramakant_Vidyapith_Class_{rom}_Test_Results.xlsx"))
        elif domain == "accounts":
            paths.append(os.path.join(BASE_DIR, "Accounts", f"Ramakant_Vidyapith_Class_{rom}_Fee_Ledger.xlsx"))
        elif domain == "student":
            paths.append(os.path.join(BASE_DIR, "Student", f"Ramakant_Vidyapith_Class_{rom}_Student_List.xlsx"))

    return [p for p in paths if os.path.exists(p)]

# --- ATTENDANCE TOOL ---
@tool
def get_attendance_report(student_id: str = "", student_class: int = 0) -> str:
    """Fetches attendance records formatted cleanly as a Markdown table and metric breakdown."""
    clean_id = extract_student_id(student_id)
    files = get_file_path("attendance", clean_id, student_class)
    
    if not files:
        return "Attendance file not found."

    dfs = [pd.read_excel(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)

    if clean_id:
        df_filtered = df[df["StudentID"].astype(str).str.strip().str.upper() == clean_id]
        if df_filtered.empty:
            return f"No attendance records found for Student ID {clean_id}."

        date_cols = [c for c in df_filtered.columns if re.match(r"^\d{2}-\d{2}-\d{4}$|^\d{4}-\d{2}-\d{2}$", str(c))]
        
        present_dates = []
        absent_dates = []

        if date_cols:
            row = df_filtered.iloc[0]
            student_name = row.get("Student Name", clean_id)
            cls_val = row.get("Class", 10)
            
            for d in date_cols:
                val = str(row[d]).strip().upper()
                if val in ["P", "PRESENT"]:
                    present_dates.append(str(d))
                else:
                    absent_dates.append(str(d))
        else:
            student_name = df_filtered.iloc[0]["Student Name"]
            cls_val = df_filtered.iloc[0]["Class"]
            for _, r in df_filtered.iterrows():
                d_str = str(r["Date"]).split(" ")[0]
                if str(r["Status"]).strip().upper() in ["P", "PRESENT"]:
                    present_dates.append(d_str)
                else:
                    absent_dates.append(d_str)

        total = len(present_dates) + len(absent_dates)
        pct = round((len(present_dates) / total) * 100, 1) if total > 0 else 0

        metric_df = pd.DataFrame([
            {"Metric": "Total Sessions", "Value": str(total)},
            {"Metric": "Attended Sessions", "Value": str(len(present_dates))},
            {"Metric": "Absent Sessions", "Value": str(len(absent_dates))},
            {"Metric": "Attendance Rate", "Value": f"{pct}%"}
        ])

        date_df = pd.DataFrame([
            {"Status": "🟢 Present", "Dates": ", ".join(present_dates) if present_dates else "None"},
            {"Status": "🔴 Absent", "Dates": ", ".join(absent_dates) if absent_dates else "None"}
        ])

        return (
            f"**Student:** {student_name} (`{clean_id}`) | **Class:** {cls_val}\n\n"
            f"{to_md_table(metric_df)}\n\n"
            f"{to_md_table(date_df)}"
        )

    return to_md_table(df.head(15))

# --- ACADEMICS TOOL ---
@tool
def get_academic_performance(student_id: str = "", student_class: int = 0, subject: str = "") -> str:
    """Retrieves CBSE test scores formatted as a Markdown table."""
    clean_id = extract_student_id(student_id)
    files = get_file_path("academics", clean_id, student_class)
    if not files:
        return "Test results file not found."

    dfs = [pd.read_excel(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)

    if clean_id:
        df = df[df["StudentID"].astype(str).str.strip().str.upper() == clean_id]
    if subject:
        df = df[df["Subject"].str.lower() == subject.strip().lower()]

    if df.empty:
        return f"No test records found for {clean_id or 'selected query'}."

    if "Score (%)" not in df.columns and "MarksObtained" in df.columns and "MaxMarks" in df.columns:
        df["Score (%)"] = (df["MarksObtained"] / df["MaxMarks"] * 100).round(1).astype(str) + "%"

    cols = [c for c in ["Subject", "MaxMarks", "MarksObtained", "Score (%)"] if c in df.columns]
    return to_md_table(df[cols])

# --- ACCOUNTS TOOL ---
@tool
def get_fee_status(student_id: str = "", student_class: int = 0, pending_only: bool = False) -> str:
    """Checks fee balance and dues formatted strictly as a Markdown table in Indian Rupees (₹)."""
    clean_id = extract_student_id(student_id)
    files = get_file_path("accounts", clean_id, student_class)
    if not files:
        return "Fee ledger file not found."

    dfs = [pd.read_excel(f) for f in files]
    df = pd.concat(dfs, ignore_index=True)

    if clean_id:
        df = df[df["StudentID"].astype(str).str.strip().str.upper() == clean_id]
    if pending_only:
        df = df[df["DueAmount"] > 0]

    if df.empty:
        return f"No fee records found for {clean_id or 'selected query'}."

    display_df = pd.DataFrame([
        {"Particulars": "Student Name", "Details": f"{df.iloc[0]['Student Name']} ({df.iloc[0]['StudentID']})"},
        {"Particulars": "Class", "Details": str(df.iloc[0]['Class'])},
        {"Particulars": "Total Annual Fee", "Details": f"₹{int(df.iloc[0]['TotalAnnualFee']):,}"},
        {"Particulars": "Paid Amount", "Details": f"₹{int(df.iloc[0]['PaidAmount']):,}"},
        {"Particulars": "Due Amount", "Details": f"₹{int(df.iloc[0]['DueAmount']):,}"},
        {"Particulars": "Last Payment Date", "Details": str(df.iloc[0].get('LastPaymentDate', 'N/A'))},
        {"Particulars": "Status", "Details": f"**{df.iloc[0]['Status']}**"}
    ])

    return to_md_table(display_df)