# app/graph/planner.py
from langchain_core.messages import SystemMessage, HumanMessage
from app.state.dev_state import DevState
from app.llm.llm_client import get_llm
from app.config import MAX_PLAN_STEPS, plan_cache
from app.logger import get_logger
import re

logger = get_logger("planner")

PLAN_TEMPLATES = {
    "create_single": {
        "pattern": lambda r, w: len(w) <= 8 and any(k in r for k in ["create", "make", "write", "build"]) and "and" not in r,
        "plan": lambda r: f"[CODE] {r}",
    },
    "read_and_fix": {
        "pattern": lambda r, w: any(k in r for k in ["fix", "debug", "refactor"]),
        "plan": lambda r: "[READ] read the file to understand the issue\n[CODE] apply the fix",
    },
    "generate_from_file": {
        "pattern": lambda r, w: any(k in r for k in ["based on", "from", "generate"]) and any(k in r for k in ["read", "file", ".py", ".js", ".ts"]),
        "plan": lambda r: "[READ] read the source file\n[CODE] generate the output based on what was read",
    },
    "search_task": {
        "pattern": lambda r, w: any(k in r for k in ["search", "find", "how to", "what is", "research"]),
        "plan": lambda r: f"[RESEARCH] search for: {r}",
    },
}


def _match_template(user_request: str) -> dict | None:
    lower = user_request.lower().strip()
    words = lower.split()
    for _, tmpl in PLAN_TEMPLATES.items():
        if tmpl["pattern"](lower, words):
            plan_text = tmpl["plan"](user_request)
            steps = []
            for line in plan_text.split("\n"):
                match = re.match(r'\[?(RESEARCH|CODE|READ)\]?\s*(.*)', line, re.IGNORECASE)
                if match:
                    steps.append(f"{match.group(1).upper()}:{match.group(2).strip()}")
            if steps:
                return {
                    "plan": plan_text,
                    "plan_steps": steps,
                    "current_step": 0,
                    "step_type": steps[0].split(":")[0].lower(),
                }
    return None

def planner_node(state: DevState):
    messages = state["messages"]
    
    # --- 1. RÉCUPÉRATION DE LA DEMANDE UTILISATEUR ---
    user_request = ""
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            user_request = m.content
            break
            
    if not user_request:
        user_request = messages[-1].content

    # --- 2. CHECK CACHE ---
    cache_key = user_request.strip().lower()
    
    # ═══ FIX: Invalider le cache si on arrive ici après un fallback ═══
    # (Si on est au planner avec retry_count > 0, le cache a déjà échoué)
    retry_count = state.get("retry_count", 0)
    if retry_count > 0:
        logger.info("🗑️ Cache invalidé (arrivée post-fallback)")
        plan_cache.cache.pop(cache_key, None)
    else:
        cached = plan_cache.get(cache_key)
        if cached:
            logger.info("♻️ CACHE HIT: Using cached plan")
            return cached

    # --- 2b. CHECK TEMPLATES (skip LLM if match) ---
    template_result = _match_template(user_request)
    if template_result:
        logger.info("📋 TEMPLATE MATCH: Skipping LLM call")
        plan_cache.set(cache_key, template_result)
        return template_result

    # --- 3. GÉNÉRATION DU PLAN ---
    logger.info(f"🗺️ PLANNER : Élaboration du plan technique pour '{user_request[:50]}...'")
    
    llm = get_llm()
    
    system_msg = SystemMessage(content=(
        "You are a Technical Lead. Create a step-by-step plan.\n"
        "Each step MUST start with a tag: [RESEARCH], [CODE], or [READ].\n\n"
        
        "### AVAILABLE TOOLS ###\n"
        "- [READ] → uses read_file_content or run_terminal (cat)\n"
        "- [CODE] → uses write_file, replace_lines, or run_terminal\n"
        "- [RESEARCH] → uses smart_web_fetch or web_search\n\n"
        
        "### EXAMPLE 1: Web task ###\n"
        "Request: 'Find how to use React hooks'\n"
        "Plan:\n"
        "[RESEARCH] search for React hooks tutorial\n"
        "[CODE] write summary to hooks.md\n\n"
        
        "### EXAMPLE 2: Code task ###\n"
        "Request: 'Create a calculator class'\n"
        "Plan:\n"
        "[CODE] create calculator.py with Calculator class\n\n"
        
        "### EXAMPLE 3: Read + generate task ###\n"
        "Request: 'Generate requirements.txt for my app'\n"
        "Plan:\n"
        "[READ] read the source file to identify imports\n"
        "[CODE] write requirements.txt with the identified dependencies\n\n"
        
        "### EXAMPLE 4: Fix task ###\n"
        "Request: 'Fix the bug in main.py'\n"
        "Plan:\n"
        "[READ] read main.py to understand the code\n"
        "[CODE] fix the bug using replace_lines\n\n"
        
        "### RULES ###\n"
        f"- Max {MAX_PLAN_STEPS} steps\n"
        "- One tag per line\n"
        "- Be specific about WHAT each step does\n"
    ))
    
    msg_payload = [
        system_msg,
        HumanMessage(content=f"Create a plan for: {user_request}")
    ]
    
    response = llm.invoke(msg_payload)
    plan_text = response.content
    
    # --- 4. PARSING DU PLAN EN STEPS ---
    steps = []
    for line in plan_text.split("\n"):
        line = line.strip()
        match = re.match(r'\[?(RESEARCH|CODE|READ)\]?\s*(.*)', line, re.IGNORECASE)
        if match:
            tag = match.group(1).upper()
            detail = match.group(2).strip()
            if detail:  # Skip empty steps
                steps.append(f"{tag}:{detail}")

    # Fallback si le LLM n'a pas suivi le format
    if not steps:
        lower_req = user_request.lower()
        if any(w in lower_req for w in ["search", "find", "how to", "what is", "documentation", "research"]):
            steps = [f"RESEARCH:{user_request}"]
        elif any(w in lower_req for w in ["read", "generate", "based on", "from"]):
            steps = [f"READ:{user_request}", f"CODE:complete the task based on what was read"]
        else:
            steps = [f"CODE:{user_request}"]
        
    logger.debug(f"📋 Steps parsées : {steps}")
    
    # --- 5. CONSTRUCTION DU RÉSULTAT ---
    result = {
        "plan": plan_text,
        "plan_steps": steps,
        "current_step": 0,
        "step_type": steps[0].split(":")[0].lower() if steps else "code"
    }

    # --- 6. SAUVEGARDE ET RETOUR ---
    plan_cache.set(cache_key, result)
    return result


def should_plan(state: DevState) -> bool:
    msg = state["messages"][-1]
    if not hasattr(msg, 'content'):
        return False

    request = msg.content.lower().strip()
    words = request.split()

    # TRIVIAL: No plan needed
    if len(words) <= 3 and not any(w in request for w in ["fix", "debug", "refactor", "based"]):
        return False

    trivial_exact = {
        "hello", "hi", "hey", "bonjour", "salut",
        "help", "aide", "list files", "show files",
        "what can you do", "who are you",
    }
    if request in trivial_exact:
        return False

    # Questions → no plan, let generator answer directly
    if request.endswith("?") and len(words) <= 10 and not any(w in request for w in ["create", "build", "make", "write", "fix"]):
        return False

    # Simple single-file creation
    if len(words) <= 6 and any(w in request for w in ["create", "write", "make"]):
        if not any(w in request for w in ["based on", "from", "and", "then", "after", "for each"]):
            return False

    # COMPLEX: Needs a plan
    multi_step_signals = ["and then", "based on", "after that", "step by step", "for each", "first", "finally"]
    if any(phrase in request for phrase in multi_step_signals):
        return True

    if any(w in request for w in ["fix", "debug", "refactor", "analyze", "update", "modify", "generate"]):
        return True

    if len(words) > 12:
        return True

    # Default: no plan (was True before — caused over-planning for simple tasks)
    return False