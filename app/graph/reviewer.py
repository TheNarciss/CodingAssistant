from langchain_core.messages import SystemMessage, HumanMessage
from app.state.dev_state import DevState
from app.llm.llm_client import get_llm
from app.config import MIN_FILE_CONTENT_LENGTH
from app.logger import get_logger

logger = get_logger("reviewer")

SAFE_TOOLS_NO_REVIEW = {
    "web_search", 
    "fetch_web_page",
    "read_file_content",
    "list_project_structure",
    "replace_lines",
    "smart_web_fetch"
}


def reviewer_node(state: DevState):
    logger.info("\n🧐 REVIEWER : Vérification du code...")
    
    messages = state["messages"]
    last_message = messages[-1]
    
    # Sécurité : Si pas d'appel d'outil, on valide par défaut
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        return {"review_feedback": None, "code_quality_score": 10}

    # Récupération propre
    tool_call = last_message.tool_calls[0]
    tool_name = tool_call["name"]
    args = tool_call["args"]

    # ✅ PASS-DROIT POUR LES OUTILS SAFE
    if tool_name in SAFE_TOOLS_NO_REVIEW:
        logger.info(f"✅ REVIEWER : Outil '{tool_name}' autorisé sans review.")
        return {"code_quality_score": 10, "review_feedback": None}

    # --- 🛡️ GUARDRAILS HARDCODED pour write_file ---
    if tool_name == "write_file":
        content = args.get("content", "")
        
        # 1. Check de taille
        if len(content) < MIN_FILE_CONTENT_LENGTH: 
            error_msg = f"REJECTED: Content too short ({len(content)} chars)."
            logger.error(f"❌ REVIEWER (Auto): {error_msg}")
            return {"review_feedback": error_msg, "code_quality_score": 0}

        # 2. Check de format (JSON dans string)
        if content.strip().startswith("{") and "class" in content:
            error_msg = (
                "REJECTED: You wrapped the Python code inside a JSON object (starts with '{'). "
                "Send ONLY the raw Python code string. Do not wrap it."
            )
            logger.error(f"❌ REVIEWER (Auto): {error_msg}")
            return {"review_feedback": error_msg, "code_quality_score": 0}

        # 3. Check de snippet ($1)
        if "$1" in content or "${1" in content:
            error_msg = "REJECTED: You used snippet placeholders like '$1'. Use valid Python syntax."
            logger.error(f"❌ REVIEWER (Auto): {error_msg}")
            return {"review_feedback": error_msg, "code_quality_score": 0}

    # --- ✅ TOUT LE RESTE EST APPROUVÉ AUTOMATIQUEMENT ---
    # Pas de LLM review inutile !
    logger.info(f"✅ Code Validé ('{tool_name}' - no LLM review needed).")
    return {"review_feedback": None, "code_quality_score": 10}