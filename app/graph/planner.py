# app/graph/planner.py
from langchain_core.messages import SystemMessage, HumanMessage
from app.state.dev_state import DevState
from app.llm.llm_client import get_llm
from app.config import MAX_PLAN_STEPS, plan_cache
from app.logger import get_logger

logger = get_logger("planner")

def planner_node(state: DevState):
    user_request = state["messages"][-1].content
    
    # 1. CHECK CACHE
    cached = plan_cache.get(user_request)
    user_request = state["messages"][-1].content.strip().lower()
    if cached:
        logger.info("♻️ CACHE HIT: Using cached plan")
        return cached

    # 2. IF NO CACHE, EXECUTE LOGIC
    logger.info("🗺️ PLANNER : Élaboration du plan technique...")
    
    llm = get_llm()
    
    system_msg = SystemMessage(content=(
        "You are a Technical Lead. Create a step-by-step plan.\n"
        "Each step MUST start with a tag: [RESEARCH], [CODE], or [READ].\n\n"
        
        "### EXAMPLE 1: Web task ###\n"
        "Request: 'Find how to use React hooks'\n"
        "Plan:\n"
        "[RESEARCH] React hooks tutorial\n"  # <- Plus besoin de SEARCH + FETCH
        "[CODE] write summary to hooks.md\n\n"
        
        "### EXAMPLE 2: Code task ###\n"
        "Request: 'Create a calculator class'\n"
        "Plan:\n"
        "[CODE] create calculator.py with Calculator class\n\n"
        
        "### EXAMPLE 3: Read + edit task ###\n"
        "Request: 'Fix the bug in main.py'\n"
        "Plan:\n"
        "[READ] read main.py\n"
        "[CODE] fix the bug replace_lines\n\n"
        
        "### RULES ###\n"
        f"- Max {MAX_PLAN_STEPS} steps\n"
        "- One tag per line\n"
    ))
    
    messages = [
        system_msg,
        HumanMessage(content=f"Create a plan for: {user_request}")
    ]
    
    response = llm.invoke(messages)
    plan_text = response.content
    
    # --- PARSING DU PLAN EN STEPS ---
    import re
    steps = []
    for line in plan_text.split("\n"):
        line = line.strip()
        match = re.match(r'\[?(RESEARCH|CODE|READ)\]?\s*(.*)', line, re.IGNORECASE)
        if match:
            tag = match.group(1).upper()
            detail = match.group(2).strip()
            steps.append(f"{tag}:{detail}")

            
    
  
    
    # Fallback : si le LLM n'a pas suivi le format
    if not steps:
        lower_req = user_request.lower()
        if any(w in lower_req for w in ["search", "find", "how to", "what is", "documentation"]):
            steps = [f"RESEARCH:{user_request}"]  # <- Plus simple
        else:
            steps = [f"CODE:{user_request}"]
        
    logger.debug(f"📋 Steps parsées : {steps}")
    
    # 3. BUILD RESULT
    result = {
        "plan": plan_text,
        "plan_steps": steps,
        "current_step": 0,
        "step_type": steps[0].split(":")[0].lower() if steps else "code"
    }

    # 4. SAVE TO CACHE & RETURN
    plan_cache.set(user_request, result)
    return result

def should_plan(state: DevState) -> bool:
    """Skip planner si requête simple."""
    request = state["messages"][-1].content.lower()
    
    # Patterns simples = pas besoin de plan
    simple_patterns = [
        "create", "write", "make a file",
        "add a function", "fix typo"
    ]
    
    if any(p in request for p in simple_patterns) and len(request.split()) < 15:
        return False
    
    # Patterns complexes = besoin de plan
    complex_patterns = ["search", "find", "research", "compare", "analyze"]
    return any(p in request for p in complex_patterns)