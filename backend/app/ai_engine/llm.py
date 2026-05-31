from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import require_gemini_api_key


def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=require_gemini_api_key(),
        temperature=0.2,
    )
