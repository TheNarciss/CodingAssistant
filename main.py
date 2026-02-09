import sys
import os
from langchain_core.messages import HumanMessage

from app.config import SANDBOX_PATH
from app.state.dev_state import make_initial_state
from app.graph.graph import app
from app.logger import get_logger


# Configuration du path
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)
logger = get_logger("main")

def run_agent():
    logger.info("🚀 Démarrage de l'Agent 'The Magnificent 8' (Llama 3.2 3B)...")
    root_path = str(SANDBOX_PATH)
    os.makedirs(root_path, exist_ok=True)
    logger.info(f"📂 Dossier surveillé : {root_path}")
    
    # La requête de test
    user_question = "say hello"
    
    # État initial
    initial_state = make_initial_state(
        
        messages=[HumanMessage(content=user_question)],
        root_dir=str(SANDBOX_PATH),
    )
    
    logger.info(f"\n💬 USER: {user_question}")
    logger.info("-" * 60)

    try:
        # On écoute tout ce qui se passe dans le graphe
        for event in app.stream(initial_state):
            for node_name, node_content in event.items():
                
                # --- 1. LE PLANNER ---
                if node_name == "planner":
                    logger.info("\n🗺️  PLANNER (Stratégie) :")
                    logger.info(f"{node_content['plan']}")
                    logger.info("-" * 30)

                # --- 2. LE GENERATOR (L'Agent) ---
                elif node_name == "generator":
                    message = node_content["messages"][-1]
                    
                    # Cas A : Il veut utiliser un outil
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        for tool_call in message.tool_calls:
                            logger.info(f"\n🤖 GENERATOR : Je veux utiliser '{tool_call['name']}'")
                            logger.debug(f"   ARGS : {tool_call['args']}")
                    # Cas B : Il parle à l'utilisateur
                    else:
                        logger.info(f"\n💡 RÉPONSE FINALE :\n{message.content}")

                # --- 3. LE REVIEWER (Le Juge) ---
                elif node_name == "reviewer":
                    score = node_content.get("code_quality_score")
                    feedback = node_content.get("review_feedback")
                    if score == 10:
                        logger.info("\n✅ REVIEWER : Validation (Score 10/10). Exécution autorisée.")
                    else:
                        logger.warning(f"\n❌ REVIEWER : Rejet ! Feedback : {feedback}")

                # --- 4. LES TOOLS (L'Exécution) ---
                elif node_name == "tools":
                    # On affiche le dernier message (qui est le retour de l'outil)
                    tool_message = node_content["messages"][-1]
                    content_preview = tool_message.content[:200] + "..." if len(tool_message.content) > 200 else tool_message.content
                    logger.info(f"\n🛠️  OUTIL TERMINÉ : {content_preview}") 

                # --- 5. LE FALLBACK (La Réparation) ---
                elif node_name == "fallback":
                    logger.warning("\n🚑 FALLBACK : Erreur détectée, tentative de correction...")

    except Exception as e:
        logger.error(f"\n❌ ERREUR CRITIQUE DANS MAIN : {e}")

if __name__ == "__main__":
    run_agent()