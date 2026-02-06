# app/graph/graph.py
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage

# Imports des briques
from app.state.dev_state import DevState
from app.graph.nodes import call_assistant, search_agent, coder_agent
from app.graph.planner import planner_node
from app.graph.reviewer import reviewer_node
from app.graph.fallback import fallback_node
from app.graph.optimizer import prompt_optimizer_node

# Imports des outils
from app.tools.fs import list_project_structure, read_file_content, write_file, smart_replace
from app.tools.web import web_search, fetch_web_page


# ============================================================
# 1. OUTILS
# ============================================================
tools_list = [list_project_structure, read_file_content, write_file, smart_replace, web_search, fetch_web_page]
tool_node = ToolNode(tools_list)


# ============================================================
# 2. FONCTIONS DE NŒUDS (définies AVANT le graphe)
# ============================================================

def dispatcher_node(state: DevState):
    """Nœud Python pur (pas de LLM). Lit l'étape courante et prépare le routing."""
    steps = state.get("plan_steps", [])
    current = state.get("current_step", 0)
    
    if current >= len(steps):
        print("✅ DISPATCHER : Toutes les étapes terminées.")
        return {"step_type": "done"}
    
    step = steps[current]
    step_type = step.split(":")[0].lower()
    
    print(f"📍 DISPATCHER : Étape {current + 1}/{len(steps)} → [{step_type.upper()}] {step}")
    
    return {"step_type": step_type, "current_step": current}


def advance_step_node(state: DevState):
    """Avance au step suivant après exécution réussie d'un outil."""
    current = state.get("current_step", 0)
    return {"current_step": current + 1}


# ============================================================
# 3. FONCTIONS DE ROUTAGE (définies AVANT le graphe)
# ============================================================

def route_from_dispatcher(state: DevState):
    """Dispatcher → quel agent appeler selon le tag du step."""
    step_type = state.get("step_type", "code")
    
    if step_type == "done":
        return END
    elif step_type in ["search", "fetch"]:
        return "search_agent"
    elif step_type in ["code", "read"]:
        return "coder_agent"
    else:
        return "generator"


def route_after_agent(state: DevState):
    """Après un agent : si tool_call → reviewer. Sinon → optimizer ou fin."""
    last_msg = state["messages"][-1]
    retry_count = state.get("retry_count", 0)
    
    if retry_count >= 3:
        print(f"\n🛑 ROUTER : Trop d'échecs ({retry_count}). Arrêt d'urgence.")
        return END
    
    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
        return "reviewer"
    
    # Pas de tool call = le LLM a bavardé → optimizer
    if state.get("code_quality_score") == 0:
        return "optimizer"
    
    return END


def route_after_review(state: DevState):
    """Reviewer → tools si validé, optimizer si rejeté."""
    if state.get("code_quality_score") == 0:
        return "optimizer"
    return "tools"


def route_after_tools(state: DevState):
    """Tools → fallback si erreur, advance_step sinon."""
    last_msg = state["messages"][-1]
    if isinstance(last_msg, ToolMessage) and "error" in last_msg.content.lower():
        return "fallback"
    return "advance_step"


# ============================================================
# 4. CONSTRUCTION DU GRAPHE
# ============================================================
workflow = StateGraph(DevState)

# --- Ajout des nœuds ---
workflow.add_node("planner", planner_node)
workflow.add_node("dispatcher", dispatcher_node)
workflow.add_node("search_agent", search_agent)
workflow.add_node("coder_agent", coder_agent)
workflow.add_node("generator", call_assistant)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("tools", tool_node)
workflow.add_node("fallback", fallback_node)
workflow.add_node("optimizer", prompt_optimizer_node)
workflow.add_node("advance_step", advance_step_node)

# --- Entry point ---
workflow.set_entry_point("planner")

# --- Edges ---

# Planner → Dispatcher
workflow.add_edge("planner", "dispatcher")

# Dispatcher → agent selon le step type
workflow.add_conditional_edges("dispatcher", route_from_dispatcher)

# Agents → Reviewer (ou optimizer/fin)
workflow.add_conditional_edges("search_agent", route_after_agent)
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