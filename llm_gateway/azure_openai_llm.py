from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from configurations.config import MODEL_NAME, OPENAI_API_KEY


def classify_with_llm(prompt: str) -> str:
    """Classify an email using OpenAI via LangChain (latest)."""

    llm = ChatOpenAI(
        model=MODEL_NAME,
        temperature=0,
        api_key=OPENAI_API_KEY,
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
