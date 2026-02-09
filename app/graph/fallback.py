# app/graph/fallback.py
from typing import Dict, Any
from langchain_core.messages import ToolMessage
from app.state.dev_state import DevState
from app.config import MAX_RETRIES
from app.logger import get_logger

logger = get_logger("fallback")

# Valid tools list (kept in sync with reviewer.py)
VALID_TOOLS_LIST = (
    "read_file_content, write_file, replace_lines, "
    "list_project_structure, run_terminal, "
    "web_search, fetch_web_page, smart_web_fetch"
)

def fallback_node(state: DevState) -> Dict[str, Any]:
    """
    Nœud de réparation. Activé quand le ToolNode plante ou que le LLM fait du JSON invalide.
    Injecte l'erreur RÉELLE + la liste des outils valides pour guider le retry.
    """
    logger.warning("\n🚑 FALLBACK ACTIVÉ : Tentative de réparation...")
    
    messages = state["messages"]
    last_message = messages[-1]
    current_retries = state.get("retry_count", 0)

    # ═══ Extraire l'erreur RÉELLE depuis les messages récents ═══
    actual_error = "Unknown error"
    for m in reversed(messages[-5:]):
        if isinstance(m, ToolMessage):
            content = m.content.lower()
            if any(kw in content for kw in ["error", "erreur", "failed", "invalid", "not found"]):
                actual_error = m.content[:500]
                break

    # ═══ Sécurité anti-boucle infinie ═══
    if current_retries >= MAX_RETRIES:
        logger.error(f"🛑 MAX RETRIES ({MAX_RETRIES}) atteint. Skip de l'étape.")
        tool_call_id = "error_id"
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_call_id = last_message.tool_calls[0]["id"]
        fallback_msg = ToolMessage(
            tool_call_id=tool_call_id,
            content=f"CRITICAL ERROR: Step skipped after {MAX_RETRIES} failures. Last error: {actual_error[:200]}"
        )
        return {
            "messages": [fallback_msg],
            "retry_count": 0,
            "last_error": f"Max retries reached: {actual_error[:200]}",
            "current_step": state.get("current_step", 0) + 1 
        }

    # ═══ Message d'erreur DÉTAILLÉ pour le LLM ═══
    error_feedback = (
        f"⚠️ YOUR LAST TOOL CALL FAILED.\n\n"
        f"ACTUAL ERROR:\n{actual_error}\n\n"
        f"VALID TOOLS (use EXACT names):\n{VALID_TOOLS_LIST}\n\n"
        f"COMMON FIXES:\n"
        f"- 'read_file' does NOT exist → use 'read_file_content'\n"
        f"- 'run_command' does NOT exist → use 'run_terminal'\n"
        f"- File paths should be relative (e.g., 'snake_game.py', not absolute paths)\n\n"
        f"Retry attempt {current_retries + 1}/{MAX_RETRIES}. Use the CORRECT tool name."
    )
    
    tool_call_id = "error_id"
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_call_id = last_message.tool_calls[0]["id"]
    retry_msg = ToolMessage(
        tool_call_id=tool_call_id,
        content=error_feedback
    )
    
    return {
        "messages": [retry_msg],
        "retry_count": current_retries + 1
    }