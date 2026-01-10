import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

def classify_with_llm(prompt: str) -> str:
    """Classify an email using OpenAI via LangChain (latest)."""

    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL_NAME", "gpt-4o-mini"),
        temperature=float(os.getenv("LLM_TEMPERATURE", 0.0)),
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    messages = [
        SystemMessage(content="You are an email priority classifier."),
        HumanMessage(content=prompt),
    ]

    try:
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        print(f"[LLM] ❌ Classification failed: {e}")
        return '{"priority": "Low Priority", "reason": "LLM error - fallback applied."}'
