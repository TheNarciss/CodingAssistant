# app/graph/optimizer.py
from app.state.dev_state import DevState
from app.config import MAX_RETRIES
from app.logger import get_logger

logger = get_logger("optimizer")


def prompt_optimizer_node(state: DevState):
    """
    Analyse l'erreur et génère une instruction corrective.
    Gère le cas où le Routeur envoie l'agent ici sans feedback explicite.
    """
    # 1. Incrémentation du compteur
    current_count = state.get("retry_count", 0)
    new_count = current_count + 1
    
    logger.warning(f"\n💉 OPTIMIZER : Injection stratégie (Essai {new_count}/{MAX_RETRIES})...")
    
    # 2. Récupération sécurisée du feedback
    feedback = state.get("review_feedback")
    
    # --- FIX CRITIQUE : Si feedback est None, c'est que le Routeur a détecté du bavardage ---
    if feedback is None:
        feedback = "You searched but failed to call `fetch_web_page`. Stop chatting."

    current_guidelines = ""

    # Stratégie 1 : Le modèle fait du JSON
    if "JSON" in feedback or "starts with '{'" in feedback:
        current_guidelines = (
            "⚠️ URGENT FIX: You outputted JSON text.\n"
            "STRATEGY: Do NOT start with '{'. Write raw code."
        )

    # Stratégie 2 : Snippets ($1)
    elif "$1" in feedback or "snippet" in feedback:
        current_guidelines = (
            "⚠️ URGENT FIX: You used snippet placeholders ($1).\n"
            "STRATEGY: Write complete code only."
        )

    # Stratégie 3 : Bavardage après recherche (Le cas actuel)
    elif "Stop chatting" in feedback or "fetch_web_page" in feedback:
        current_guidelines = (
            "⚠️ CRITICAL ERROR: You performed a Search but replied with Text.\n"
            "STRATEGY: You are FORBIDDEN from summarizing URLs.\n"
            "ACTION: Call `fetch_web_page(url)` on the best result immediately."
        )

    # Stratégie par défaut
    else:
        current_guidelines = (
            f"⚠️ FIX: Your previous attempt failed: {feedback}\n"
            "STRATEGY: Analyze the error and correct the syntax."
        )

    final_guidelines = f"⚠️ URGENT FIX (Attempt {new_count}/{MAX_RETRIES}): {current_guidelines}"

    return {
        "dynamic_guidelines": final_guidelines,
        "retry_count": new_count,
        # On remet un feedback propre pour la suite
        "review_feedback": feedback 
    }