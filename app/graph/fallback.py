# app/graph/fallback.py
from typing import Dict, Any
from langchain_core.messages import ToolMessage
from app.state.dev_state import DevState

def fallback_node(state: DevState) -> Dict[str, Any]:
    """
    Nœud de réparation. Activé quand le ToolNode plante ou que le LLM fait du JSON invalide.
    """
    print("\n🚑 FALLBACK ACTIVÉ : Tentative de réparation...")
    
    messages = state["messages"]
    last_message = messages[-1]
    current_retries = state.get("retry_count", 0)

    # Sécurité anti-boucle infinie
    if current_retries >= 3:
        # On injecte un faux résultat d'outil pour dire "STOP"
        tool_call_id = "error_id"
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_call_id = last_message.tool_calls[0]["id"]
        fallback_msg = ToolMessage(
            tool_call_id=tool_call_id,
            content="ERREUR CRITIQUE : Trop d'échecs consécutifs. J'arrête d'essayer d'utiliser cet outil."
        )
        return {
            "messages": [fallback_msg],
            "retry_count": 0,
            "last_error": "Max retries reached"
        }

    # On prépare le message qui gronde gentiment le LLM
    error_feedback = (
        "WARNING: Your last tool call failed (invalid JSON or arguments). "
        "Please re-read the tool definition and correct your arguments. "
        "Do not halluniate arguments. Adhere strictly to the schema."
    )
    
    # On renvoie ce message "fake tool output" pour qu'il réessaie
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