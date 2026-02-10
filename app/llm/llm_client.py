# app/llm/ollama_client.py
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI  # <--- On remplace Google par OpenAI (standard OpenRouter)
from app.config import (
    MODEL_NAME, MODEL_TEMPERATURE, OLLAMA_BASE_URL, MODEL_KEEP_ALIVE,
    OPEN_API_KEY, OPEN_MODEL, LLM_PROVIDER
)
from app.logger import get_logger

logger = get_logger("llm_client")

def _get_openrouter(model_name=None, temperature=MODEL_TEMPERATURE):
    """Retourne un LLM via OpenRouter (compatible API OpenAI)."""
    return ChatOpenAI(
        model=model_name or OPEN_MODEL,
        temperature=temperature,
        api_key=OPEN_API_KEY,
        base_url="https://openrouter.ai/api/v1", # <--- L'URL magique
        request_timeout=60,
        default_headers={
            "HTTP-Referer": "http://localhost:3000", # Requis par OpenRouter pour les stats
            "X-Title": "DevAssistant"
        }
    )

def _get_ollama(model_name=None, temperature=MODEL_TEMPERATURE):
    """Retourne un LLM Ollama local."""
    return ChatOllama(
        model=model_name or MODEL_NAME,
        temperature=temperature,
        base_url=OLLAMA_BASE_URL,
        keep_alive=MODEL_KEEP_ALIVE,
        timeout=60,
    )

def _get_ollama_constrained(model_name=None, temperature=MODEL_TEMPERATURE, tool_names=None):
    """Ollama avec sortie JSON forcée (votre logique existante)."""
    if tool_names is None:
        tool_names = [
            "web_search", "fetch_web_page", "smart_web_fetch",
            "write_file", "read_file_content", "replace_lines",
            "list_project_structure", "run_terminal"
        ]
    return ChatOllama(
        model=model_name or MODEL_NAME,
        temperature=temperature,
        base_url=OLLAMA_BASE_URL,
        keep_alive=MODEL_KEEP_ALIVE,
        timeout=60,
        format="json" # Simplifié, ou gardez votre structure complexe si nécessaire
    )

def get_llm(model_name=None, temperature=MODEL_TEMPERATURE):
    """
    Retourne le LLM configuré. OpenRouter par défaut si clé présente, sinon Ollama.
    """
    # On vérifie si on doit utiliser OpenRouter
    use_remote = (LLM_PROVIDER.lower() == "openrouter" or LLM_PROVIDER.lower() == "gemini") and OPEN_API_KEY
    
    if use_remote:
        try:
            llm = _get_openrouter(model_name, temperature)
            logger.info(f"🌐 LLM : OpenRouter ({model_name or OPEN_MODEL})")
            return llm
        except Exception as e:
            logger.warning(f"⚠️ OpenRouter indisponible ({e}), fallback Ollama...")
    
    logger.info(f"🏠 LLM : Ollama ({model_name or MODEL_NAME})")
    return _get_ollama(model_name, temperature, request_timeout=60)


def get_llm_constrained(model_name=None, temperature=MODEL_TEMPERATURE, tool_names=None):
    """
    LLM avec sortie JSON contrainte.
    """
    use_remote = (LLM_PROVIDER.lower() == "openrouter" or LLM_PROVIDER.lower() == "gemini") and OPEN_API_KEY

    if use_remote:
        try:
            # OpenRouter (via OpenAI standard) utilise response_format={"type": "json_object"}
            llm = ChatOpenAI(
                model=model_name or OPEN_MODEL,
                temperature=temperature,
                api_key=OPEN_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                model_kwargs={"response_format": {"type": "json_object"}},
                default_headers={
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "DevAssistant"
                }
            )
            logger.info(f"🌐 LLM contraint : OpenRouter ({model_name or OPEN_MODEL})")
            return llm
        except Exception as e:
            logger.warning(f"⚠️ OpenRouter contraint indisponible ({e}), fallback Ollama...")
    
    logger.info(f"🏠 LLM contraint : Ollama ({model_name or MODEL_NAME})")
    return _get_ollama_constrained(model_name, temperature, tool_names)