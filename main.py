import sys
import os
from langchain_core.messages import HumanMessage
from app.graph.graph import app 

# Configuration du path
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

def run_agent():
    print("🚀 Démarrage de l'Agent 'The Magnificent 8' (Llama 3.2 3B)...")
    root_path = os.path.join(base_dir, "PlaygroudForCodingAssistant")
    os.makedirs(root_path, exist_ok=True)
    print(f"📂 Dossier surveillé : {root_path}")
    
    # La requête de test
    user_question = "Create a new file 'calculator.py' containing a Calculator class with add, sub, mul, and div methods. Add a main block to test the class."
    
    # État initial
    initial_state = {
        "messages": [HumanMessage(content=user_question)],
        "root_dir": root_path,
        "active_file": None,
        "error_history": [],
        "plan": None,
        "review_feedback": None,
        "retry_count": 0,
        # Nouveaux champs state machine
        "plan_steps": [],
        "current_step": 0,
        "step_type": None,
    }
    
    print(f"\n💬 USER: {user_question}")
    print("-" * 60)

    try:
        # On écoute tout ce qui se passe dans le graphe
        for event in app.stream(initial_state):
            for node_name, node_content in event.items():
                
                # --- 1. LE PLANNER ---
                if node_name == "planner":
                    print(f"\n🗺️  PLANNER (Stratégie) :")
                    print(f"{node_content['plan']}")
                    print("-" * 30)

                # --- 2. LE GENERATOR (L'Agent) ---
                elif node_name == "generator":
                    message = node_content["messages"][-1]
                    
                    # Cas A : Il veut utiliser un outil
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        for tool_call in message.tool_calls:
                            print(f"\n🤖 GENERATOR : Je veux utiliser '{tool_call['name']}'")
                            print(f"   ARGS : {tool_call['args']}")
                    # Cas B : Il parle à l'utilisateur
                    else:
                        print(f"\n💡 RÉPONSE FINALE :\n{message.content}")

                # --- 3. LE REVIEWER (Le Juge) ---
                elif node_name == "reviewer":
                    score = node_content.get("code_quality_score")
                    feedback = node_content.get("review_feedback")
                    if score == 10:
                        print(f"\n✅ REVIEWER : Validation (Score 10/10). Exécution autorisée.")
                    else:
                        print(f"\n❌ REVIEWER : Rejet ! Feedback : {feedback}")

                # --- 4. LES TOOLS (L'Exécution) ---
                elif node_name == "tools":
                    # On affiche le dernier message (qui est le retour de l'outil)
                    tool_message = node_content["messages"][-1]
                    content_preview = tool_message.content[:200] + "..." if len(tool_message.content) > 200 else tool_message.content
                    print(f"\n🛠️  OUTIL TERMINÉ : {content_preview}") 

                # --- 5. LE FALLBACK (La Réparation) ---
                elif node_name == "fallback":
                    print(f"\n🚑 FALLBACK : Erreur détectée, tentative de correction...")

    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE DANS MAIN : {e}")

if __name__ == "__main__":
    run_agent()