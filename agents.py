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
    provider_str = str(provider).strip().lower()

    # =========================================================
    # 1. STRICT LOCAL AI (LM Studio / Ollama / Ngrok via OpenAI API)
    # =========================================================
    if "local" in provider_str:
        raw_url = config.get("base_url", "http://127.0.0.1:1234/v1").strip().rstrip("/")
        if not raw_url.endswith("/v1"):
            raw_url = f"{raw_url}/v1"
            
        print(f"DEBUG: >>> Routing to LOCAL AI at: {raw_url} <<<")
        
        # Explicitly pass api_key and base_url to prevent LangChain from looking at GROQ_API_KEY
        return ChatOpenAI(
            base_url=raw_url,
            api_key="lm-studio",  # Standard placeholder for LM Studio
            temperature=temperature,
            max_tokens=2048,
            model="local-model"
        )

    # =========================================================
    # 2. GROQ CLOUD (System Default or User Cloud Key)
    # =========================================================
    else:
        api_key = config.get("api_key", "").strip()
        print(f"DEBUG: >>> Routing to GROQ CLOUD with key starting with: {api_key[:6]}... <<<")
        
        if not api_key:
            raise ValueError("No Groq API Key found. Please provide an API key.")
            
        return ChatGroq(
            model="openai/gpt-oss-20b",
            groq_api_key=api_key,
            temperature=temperature
        )

def test_connection(provider: str, config: dict) -> tuple[bool, str]:
    try:
        llm = get_llm(provider, config)
        test_msg = llm.invoke("Ping. Reply with 'OK'.")
        
        if "local" in str(provider).lower():
            target = config.get("base_url", "http://127.0.0.1:1234/v1")
            return True, f"Connected to LOCAL LLM ({target})"
        else:
            return True, "Connected to GROQ CLOUD (gpt-oss-20b)"
            
    except Exception as e:
        return False, f"Connection Failed: {str(e)}"