# app/graph/reviewer.py
from langchain_core.messages import SystemMessage, HumanMessage
from app.state.dev_state import DevState
from app.config import MIN_FILE_CONTENT_LENGTH
from app.logger import get_logger
from app.tools.registry import VALID_TOOLS, SAFE_TOOLS_NO_REVIEW, TOOL_ALIASES

logger = get_logger("reviewer")




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

    # ═══════════════════════════════════════════════════════
    # VALIDATION DU NOM D'OUTIL (FIX CRITIQUE)
    # Intercepte les hallucinations AVANT que le ToolNode crash
    # ═══════════════════════════════════════════════════════
    if tool_name not in VALID_TOOLS:
        corrected = TOOL_ALIASES.get(tool_name.lower())
        if corrected:
            logger.warning(f"🔧 REVIEWER : Auto-correction '{tool_name}' → '{corrected}'")
            # Modifier le tool_call in-place pour que le ToolNode reçoive le bon nom
            last_message.tool_calls[0]["name"] = corrected
            tool_name = corrected
        else:
            error_msg = (
                f"REJECTED: '{tool_name}' is not a valid tool. "
                f"Valid tools: {', '.join(sorted(VALID_TOOLS))}"
            )
            logger.error(f"❌ REVIEWER: {error_msg}")
            return {"review_feedback": error_msg, "code_quality_score": 0}

    # ═══ PASS-DROIT POUR LES OUTILS SAFE ═══
    if tool_name in SAFE_TOOLS_NO_REVIEW:
        logger.info(f"✅ REVIEWER : Outil '{tool_name}' autorisé sans review.")
        return {"code_quality_score": 10, "review_feedback": None}

    # ═══ GUARDRAILS HARDCODED pour write_file ═══
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

    # ═══ APPROUVÉ ═══
    logger.info(f"✅ Code Validé ('{tool_name}' - no LLM review needed).")
    return {"review_feedback": None, "code_quality_score": 10}