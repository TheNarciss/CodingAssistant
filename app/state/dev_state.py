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