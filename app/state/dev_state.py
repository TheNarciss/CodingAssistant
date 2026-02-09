# app/state/dev_state.py
from typing import Annotated, TypedDict, List, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class DevState(TypedDict):
    # --- CHAMPS EXISTANTS (On les garde) ---
    messages: Annotated[List[BaseMessage], add_messages]
    root_dir: str
    active_file: Optional[str]
    error_history: List[str]
    current_task: str
    iteration_count: int

    # --- NOUVEAUX CHAMPS (Architecture 8 Nœuds) ---
    
    # 1. Pour le PLANNER
    plan: Optional[str]               # La liste des étapes (ex: "1. Lire main.py, 2. Modifier...")
    
    # 2. Pour le REVIEWER / CRITIC
    review_feedback: Optional[str]    # Le retour du critique ("Tu as oublié un import")
    code_quality_score: Optional[int] # Note sur 10 (pour décider si on valide)
    
    # 3. Pour le FALLBACK
    retry_count: int                  # Combien de fois on a essayé de corriger une erreur technique
    last_error: Optional[str]         # La dernière erreur brute pour l'analyse
    dynamic_guidelines: Optional[str]

    # 4. Pour la STATE MACHINE
    plan_steps: list                  # Liste des étapes parsées ["SEARCH:query", "FETCH", "CODE:description"]
    current_step: int                 # Index de l'étape en cours
    step_type: Optional[str]  

def make_initial_state(messages, root_dir: str = "", **overrides) -> dict:
    """Crée un état initial avec des valeurs par défaut saines."""
    defaults = {
        "messages": messages,
        "root_dir": root_dir,
        "active_file": None,
        "error_history": [],
        "current_task": "",
        "iteration_count": 0,
        "plan": None,
        "review_feedback": None,
        "code_quality_score": None,
        "retry_count": 0,
        "last_error": None,
        "dynamic_guidelines": None,
        "plan_steps": [],
        "current_step": 0,
        "step_type": None,
    }
    defaults.update(overrides)
    return defaults