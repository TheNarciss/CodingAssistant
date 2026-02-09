# app/graph/graph.py
from langgraph.graph import StateGraph, END,START
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage

# Imports des briques
from app.state.dev_state import DevState
from app.graph.nodes import call_assistant, coder_agent , research_agent
from app.graph.planner import planner_node, should_plan
from app.graph.reviewer import reviewer_node
from app.graph.fallback import fallback_node
from app.graph.optimizer import prompt_optimizer_node

# Imports des outils
from app.tools.fs import list_project_structure, read_file_content, write_file, replace_lines
from app.tools.web import web_search, fetch_web_page , smart_web_fetch
from app.tools.terminal import run_terminal
from app.logger import get_logger

logger = get_logger("graph")


# ============================================================
# 1. OUTILS
# ============================================================
tools_list = [list_project_structure, read_file_content, write_file, replace_lines, web_search, fetch_web_page, smart_web_fetch,run_terminal]
tool_node = ToolNode(tools_list)


# ============================================================
# 2. FONCTIONS DE NŒUDS (définies AVANT le graphe)
# ============================================================

def dispatcher_node(state: DevState):
    """Nœud Python pur (pas de LLM). Lit l'étape courante et prépare le routing."""
    steps = state.get("plan_steps", [])
    current = state.get("current_step", 0)
    
    if current >= len(steps):
        logger.info("✅ DISPATCHER : Toutes les étapes terminées.")
        return {"step_type": "done"}
    
    step = steps[current]
    step_type = step.split(":")[0].lower()
    
    logger.info(f"📍 DISPATCHER : Étape {current + 1}/{len(steps)} → [{step_type.upper()}] {step}")
    
    return {"step_type": step_type, "current_step": current}


def advance_step_node(state: DevState):
    """Avance au step suivant après exécution réussie d'un outil."""
    current = state.get("current_step", 0)
    return {"current_step": current + 1}


# ============================================================
# 3. FONCTIONS DE ROUTAGE (définies AVANT le graphe)
# ============================================================

def route_from_dispatcher(state: DevState) -> str:
    """Dispatcher → quel agent appeler selon le tag du step."""
    step_type = state.get("step_type", "code")
    
    if step_type == "done":
        # AVANT : return END  <-- C'est ça qui coupait la parole au LLM
        # APRÈS :
        return "generator"  # <-- On renvoie au LLM pour qu'il synthétise la réponse finale
        
    elif step_type in ["search", "fetch"]:
        return "search_agent"
    elif step_type in ["code", "read"]:
        return "coder_agent"
    else:
        return "generator"


def route_after_agent(state: DevState) -> str:
    """Après un agent : si tool_call → reviewer. Sinon → optimizer ou fin."""
    last_msg = state["messages"][-1]
    retry_count = state.get("retry_count", 0)
    
    if retry_count >= 3:
        logger.warning(f"\n🛑 ROUTER : Trop d'échecs ({retry_count}). Arrêt d'urgence.")
        return END
    
    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
        return "reviewer"
    
    score = state.get("code_quality_score")
    if score is not None and score == 0:
        # Score à 0 = le reviewer a rejeté le code, on optimise
        return "optimizer"
    
    return END


def route_after_review(state: DevState) -> str:
    """Reviewer → tools si validé, optimizer si rejeté."""
    if state.get("code_quality_score") == 0:
        return "optimizer"
    return "tools"


def route_after_tools(state: DevState) -> str:
    """
    Décide de la suite après l'exécution d'un outil.
    - Si erreur : fallback.
    - Si mode Plan : on avance à l'étape suivante.
    - Si mode Conversation (pas de plan) : on retourne au Generator pour qu'il commente le résultat.
    """
    last_msg = state["messages"][-1]
    steps = state.get("plan_steps", [])
    
    # 1. Gestion des erreurs d'outils
    if isinstance(last_msg, ToolMessage) and "error" in last_msg.content.lower():
        return "fallback"
    
    # 2. Si on est dans un PLAN (steps n'est pas vide)
    if steps:
        current = state.get("current_step", 0)
        # Si c'était la dernière étape, on finit
        if current >= len(steps) - 1:
            return END
        # Sinon on avance
        return "advance_step"

    # 3. Si PAS DE PLAN (Generator a appelé l'outil directement)
    # C'est ici le changement CRITIQUE : on retourne au generator pour qu'il lise la réponse
    return "generator"

def entry_router(state: DevState) -> str:
    return "generator" if not should_plan(state) else "planner"


# ============================================================
# 4. CONSTRUCTION DU GRAPHE
# ============================================================
workflow = StateGraph(DevState)

# --- Ajout des nœuds ---
workflow.add_node("planner", planner_node)
workflow.add_node("dispatcher", dispatcher_node)
workflow.add_node("research_agent", research_agent)

workflow.add_node("coder_agent", coder_agent)
workflow.add_node("generator", call_assistant)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("tools", tool_node)
workflow.add_node("fallback", fallback_node)
workflow.add_node("optimizer", prompt_optimizer_node)

workflow.add_node("advance_step", advance_step_node)

# --- Entry point ---

workflow.add_conditional_edges(START, entry_router)
# --- Edges ---

# Planner → Dispatcher
workflow.add_edge("planner", "dispatcher")

# Dispatcher → agent selon le step type
workflow.add_conditional_edges("dispatcher", route_from_dispatcher)

# Agents → Reviewer (ou optimizer/fin)

workflow.add_conditional_edges("research_agent", route_after_agent)
workflow.add_conditional_edges("coder_agent", route_after_agent)
workflow.add_conditional_edges("generator", route_after_agent)

# Reviewer → Tools ou Optimizer
workflow.add_conditional_edges("reviewer", route_after_review)

# Tools → advance_step ou fallback
workflow.add_conditional_edges("tools", route_after_tools)

# Advance step → retour au dispatcher (boucle)
workflow.add_edge("advance_step", "dispatcher")

# Fallback → retour au dispatcher
workflow.add_edge("fallback", "dispatcher")

# Optimizer → retour au dispatcher
workflow.add_edge("optimizer", "dispatcher")



# ============================================================
# 5. COMPILATION
# ============================================================
app = workflow.compile()