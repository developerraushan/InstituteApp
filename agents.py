import os
import re
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from tools import (
    get_attendance_report,
    get_academic_performance,
    get_fee_status,
    extract_student_id,
    ROMAN_MAP
)

def get_llm(provider: str, config: dict):
    temperature = float(config.get("temperature", 0.0))
    provider_clean = str(provider).strip().lower()
    
    # Strictly isolate Local AI
    if "local" in provider_clean:
        base_url = config.get("base_url", "http://127.0.0.1:1234/v1")
        return ChatOpenAI(
            base_url=base_url,
            api_key="lm-studio",
            temperature=temperature
        )
    else:
        # System Default & Cloud use Groq
        api_key = config.get("api_key", "")
        return ChatGroq(
            model="openai/gpt-oss-20b",
            api_key=api_key,
            temperature=temperature
        )

def test_connection(provider: str, config: dict) -> tuple[bool, str]:
    try:
        llm = get_llm(provider, config)
        test_msg = llm.invoke("Ping. Reply with 'OK'.")
        if test_msg:
            # Report back the exact endpoint used so you can verify where it connected
            if "local" in str(provider).lower():
                return True, f"Connected to Local LLM at {config.get('base_url')}!"
            return True, "Connected successfully to Groq Cloud!"
        return False, "No response from LLM."
    except Exception as e:
        return False, f"Connection Failed: {str(e)}"

# =============================================================
# DISPATCH CONTROLLER
# =============================================================

def handle_query(query: str, provider: str, config: dict, session_id: str = "session_1") -> str:
    llm = get_llm(provider, config)

    att_agent = create_agent(
        model=llm,
        tools=[get_attendance_report],
        system_prompt=(
            "You are the Attendance Registrar for Ramakant Vidyapith.\n"
            "MANDATORY OUTPUT FORMAT:\n"
            "1. Output the attendance data returned by the tool using a clean Markdown Table.\n"
            "2. Never condense rows into a single run-on text line."
        ),
        checkpointer=MemorySaver()
    )

    acad_agent = create_agent(
        model=llm,
        tools=[get_academic_performance],
        system_prompt=(
            "You are the Academic Dean.\n"
            "MANDATORY OUTPUT FORMAT:\n"
            "Always present CBSE test scores (Maths, Science, Social Science) in a clean Markdown Table."
        ),
        checkpointer=MemorySaver()
    )

    fee_agent = create_agent(
        model=llm,
        tools=[get_fee_status],
        system_prompt=(
            "You are the Accounts Officer for Ramakant Vidyapith.\n"
            "MANDATORY RULES:\n"
            "1. Output ALL monetary values using the Indian Rupee symbol '₹' (e.g. ₹24,000, ₹6,000).\n"
            "2. Present the financial breakdown as a structured Markdown Table.\n"
            "3. NEVER dump raw unformatted strings."
        ),
        checkpointer=MemorySaver()
    )

    whatsapp_agent = create_agent(
        model=llm,
        tools=[],
        system_prompt=(
            "You are the Parent Communications Officer for Ramakant Vidyapith.\n"
            "Create a polite WhatsApp progress update for the student's parents.\n"
            "Rules:\n"
            "1. State Student Name, Class, and exact Student ID.\n"
            "2. All currency in ₹.\n"
            "3. Format with two distinct sections: '### ENGLISH MESSAGE' and '### HINDI MESSAGE'."
        ),
        checkpointer=MemorySaver()
    )

    configs = {
        "att": {"configurable": {"thread_id": f"{session_id}_att"}},
        "acad": {"configurable": {"thread_id": f"{session_id}_acad"}},
        "fee": {"configurable": {"thread_id": f"{session_id}_fee"}},
        "comm": {"configurable": {"thread_id": f"{session_id}_comm"}},
    }

    sid = extract_student_id(query)
    clean_target = sid if sid else query

    q = query.lower()

    if any(k in q for k in ["whatsapp", "sms", "parent alert", "message to parent", "notice for parent"]):
        att_data = att_agent.invoke({"messages": [{"role": "user", "content": f"Lookup attendance for student {clean_target}"}]}, config=configs["att"])["messages"][-1].content
        fee_data = fee_agent.invoke({"messages": [{"role": "user", "content": f"Lookup fee balance in ₹ for student {clean_target}"}]}, config=configs["fee"])["messages"][-1].content
        acad_data = acad_agent.invoke({"messages": [{"role": "user", "content": f"Lookup test marks for student {clean_target}"}]}, config=configs["acad"])["messages"][-1].content

        prompt = (
            f"Generate WhatsApp Progress Alert for Student: {clean_target}\n\n"
            f"Records:\n"
            f"- Attendance: {att_data}\n"
            f"- Fees: {fee_data}\n"
            f"- Academics: {acad_data}\n"
        )
        return whatsapp_agent.invoke({"messages": [{"role": "user", "content": prompt}]}, config=configs["comm"])["messages"][-1].content

    elif any(k in q for k in ["fee", "due", "paid", "pending", "payment", "rupees", "balance"]):
        return fee_agent.invoke({"messages": [{"role": "user", "content": f"Get fee status in ₹ for {clean_target}. Present as a markdown table."}]}, config=configs["fee"])["messages"][-1].content

    elif any(k in q for k in ["marks", "test", "score", "result"]):
        return acad_agent.invoke({"messages": [{"role": "user", "content": f"Get test performance for {clean_target}. Present as a markdown table."}]}, config=configs["acad"])["messages"][-1].content

    elif any(k in q for k in ["attendance", "present", "absent"]):
        return att_agent.invoke({"messages": [{"role": "user", "content": f"Get attendance for {clean_target}. Present as a markdown table."}]}, config=configs["att"])["messages"][-1].content

    else:
        att_res = att_agent.invoke({"messages": [{"role": "user", "content": f"Lookup attendance for student {clean_target}. Present as markdown table."}]}, config=configs["att"])["messages"][-1].content
        acad_res = acad_agent.invoke({"messages": [{"role": "user", "content": f"Lookup academic marks for student {clean_target}. Present as markdown table."}]}, config=configs["acad"])["messages"][-1].content
        fee_res = fee_agent.invoke({"messages": [{"role": "user", "content": f"Lookup fee balance in ₹ for student {clean_target}. Present as markdown table."}]}, config=configs["fee"])["messages"][-1].content

        return (
            f"## 📋 Student 360° Profile\n\n"
            f"### 🗓️ Attendance Status\n{att_res}\n\n"
            f"### 📊 Academic Test Scores\n{acad_res}\n\n"
            f"### 💰 Fee Ledger\n{fee_res}\n"
        )