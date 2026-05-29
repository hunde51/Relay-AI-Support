from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.2,
    )
