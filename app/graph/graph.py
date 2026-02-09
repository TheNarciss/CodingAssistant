# app/graph/graph.py
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage

from app.state.dev_state import DevState
from app.graph.nodes import call_assistant, coder_agent, research_agent
from app.graph.planner import planner_node, should_plan
from app.graph.reviewer import reviewer_node
from app.graph.fallback import fallback_node
from app.graph.optimizer import prompt_optimizer_node

from app.tools.fs import list_project_structure, read_file_content, write_file, replace_lines
from app.tools.web import web_search, fetch_web_page, smart_web_fetch
from app.tools.terminal import run_terminal
from app.logger import get_logger

logger = get_logger("graph")


# ============================================================
# 1. OUTILS
# ============================================================
tools_list = [
    list_project_structure, read_file_content, write_file, replace_lines,
    web_search, fetch_web_page, smart_web_fetch, run_terminal
]
tool_node = ToolNode(tools_list)


# ============================================================
# 2. FONCTIONS DE NŒUDS
# ============================================================

def dispatcher_node(state: DevState):
    """Nœud Python pur. Lit l'étape courante et prépare le routing."""
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
    logger.info(f"⏩ Étape {current + 1} terminée → passage à la suivante")
    return {"current_step": current + 1}


# ============================================================
# 3. FONCTIONS DE ROUTAGE
# ============================================================

def route_from_dispatcher(state: DevState) -> str:
    """Dispatcher → quel agent appeler selon le tag du step."""
    step_type = state.get("step_type", "code")
    
    if step_type == "done":
        return "generator"
    elif step_type == "research":
        return "research_agent"
    elif step_type in ["code", "read"]:
        return "coder_agent"
    else:
        logger.warning(f"⚠️ Unknown step type '{step_type}', defaulting to coder_agent")
        return "coder_agent"


def route_after_agent(state: DevState) -> str:
    """Après un agent : si tool_call → reviewer. Sinon → vérifier le contexte."""
    last_msg = state["messages"][-1]
    retry_count = state.get("retry_count", 0)
    
    if retry_count >= 3:
        logger.warning(f"\n🛑 ROUTER : Trop d'échecs ({retry_count}). Arrêt d'urgence.")
        return END
    
    # ═══ L'agent a produit un tool call → reviewer ═══
    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
        return "reviewer"
    
    # ═══ L'agent n'a PAS produit de tool call ═══
    
    # Si le reviewer avait rejeté → optimizer
    score = state.get("code_quality_score")
    if score is not None and score == 0:
        return "optimizer"
    
    # ═══ FIX #6: Si on est en plein plan et l'agent n'a pas fait de tool call,
    # c'est un échec de parsing → fallback ═══
    steps = state.get("plan_steps", [])
    current = state.get("current_step", 0)
    if steps and current < len(steps):
        # On est dans un plan, il reste des étapes, mais l'agent a répondu en texte
        # C'est probablement un parse error → fallback pour retry
        logger.warning(f"⚠️ Agent a répondu en texte en plein plan (step {current+1}/{len(steps)}) → fallback")
        return "fallback"
    
    # Plan terminé ou mode direct : le generator a répondu → END
    return END


def route_after_review(state: DevState) -> str:
    """Reviewer → tools si validé, optimizer si rejeté."""
    if state.get("code_quality_score") == 0:
        return "optimizer"
    return "tools"


def route_after_tools(state: DevState) -> str:
    """
    Routeur post-exécution d'outil.
    1. Si erreur → Fallback
    2. Si plan en cours avec étapes restantes → Advance Step
    3. Si plan fini ou pas de plan → Generator (synthèse)
    """
    last_msg = state["messages"][-1]
    steps = state.get("plan_steps", [])
    
    # --- 1. DÉTECTION D'ERREUR ---
    if isinstance(last_msg, ToolMessage):
        content = last_msg.content.lower()
        if any(keyword in content for keyword in ["error", "erreur", "interdits", "failed", "not found", "not a valid"]):
            logger.warning("⚠️ Erreur outil détectée → Direction Fallback")
            return "fallback"
    
    # --- 2. GESTION DU PLAN ---
    if steps:
        current = state.get("current_step", 0)
        
        if current < len(steps) - 1:
            logger.info(f"⏩ Étape {current+1}/{len(steps)} terminée → Suivante")
            return "advance_step"
            
        logger.info("✅ Dernière étape du plan terminée → Retour au Generator pour bilan")
        return "generator"

    # --- 3. MODE CONVERSATION ---
    logger.info("✅ Action unique terminée → Retour au Generator")
    return "generator"


def entry_router(state: DevState) -> str:
    return "generator" if not should_plan(state) else "planner"


def route_after_fallback(state: DevState) -> str:
    """
    Après fallback :
    1. Si plan existant → retour au Dispatcher pour réessayer
    2. Si pas de plan → escalade vers le Planner
    """
    steps = state.get("plan_steps", [])
    
    if steps and len(steps) > 0:
        logger.info("↩️ FALLBACK : Retour au Dispatcher (Plan existant)")
        return "dispatcher"
    
    logger.info("🚨 FALLBACK : Mode Direct échoué → Activation du Planner")
    return "planner"


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
workflow.add_edge("planner", "dispatcher")
workflow.add_conditional_edges("dispatcher", route_from_dispatcher)

workflow.add_conditional_edges("research_agent", route_after_agent)
workflow.add_conditional_edges("coder_agent", route_after_agent)
workflow.add_conditional_edges("generator", route_after_agent)

workflow.add_conditional_edges("reviewer", route_after_review)
workflow.add_conditional_edges("tools", route_after_tools)

workflow.add_edge("advance_step", "dispatcher")
workflow.add_conditional_edges("fallback", route_after_fallback)
workflow.add_edge("optimizer", "dispatcher")

# ============================================================
# 5. COMPILATION
# ============================================================
app = workflow.compile()