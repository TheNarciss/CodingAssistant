# app/graph/planner.py
from langchain_core.messages import SystemMessage, HumanMessage
from app.state.dev_state import DevState
from app.llm.ollama_client import get_llm

def planner_node(state: DevState):
    """
    Génère un plan structuré avec des tags [SEARCH], [FETCH], [CODE], [READ].
    """
    print("🗺️ PLANNER : Élaboration du plan technique...")
    
    user_request = state["messages"][-1].content
    
    llm = get_llm(model_name="llama3.2:3b", temperature=0)
    
    system_msg = SystemMessage(content=(
        "You are a Technical Lead. Create a step-by-step plan.\n"
        "Each step MUST start with a tag: [SEARCH], [FETCH], [CODE], or [READ].\n\n"
        
        "### EXAMPLE 1: Web task ###\n"
        "Request: 'Find how to use React hooks'\n"
        "Plan:\n"
        "[SEARCH] React hooks tutorial\n"
        "[FETCH] best URL from search\n"
        "[CODE] write summary to hooks.md\n\n"
        
        "### EXAMPLE 2: Code task ###\n"
        "Request: 'Create a calculator class'\n"
        "Plan:\n"
        "[CODE] create calculator.py with Calculator class\n\n"
        
        "### EXAMPLE 3: Read + edit task ###\n"
        "Request: 'Fix the bug in main.py'\n"
        "Plan:\n"
        "[READ] read main.py\n"
        "[CODE] fix the bug using smart_replace\n\n"
        
        "### RULES ###\n"
        "- Web tasks ALWAYS need [SEARCH] then [FETCH] (both required)\n"
        "- Max 5 steps\n"
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
        match = re.match(r'\[?(SEARCH|FETCH|CODE|READ)\]?\s*(.*)', line, re.IGNORECASE)
        if match:
            tag = match.group(1).upper()
            detail = match.group(2).strip()
            steps.append(f"{tag}:{detail}")
    cleaned_steps = []
    for s in steps:
        tag = s.split(":")[0]
        # Skip les SEARCH en double
        if tag == "SEARCH" and cleaned_steps and cleaned_steps[-1].startswith("SEARCH"):
            continue
        cleaned_steps.append(s)

    # Garantir que chaque SEARCH est suivi d'un FETCH
    final_steps = []
    for i, s in enumerate(cleaned_steps):
        final_steps.append(s)
        tag = s.split(":")[0]
        if tag == "SEARCH":
            # Vérifier si le step suivant est déjà un FETCH
            next_tag = cleaned_steps[i + 1].split(":")[0] if i + 1 < len(cleaned_steps) else ""
            if next_tag != "FETCH":
                final_steps.append("FETCH:best result from search")
    
    steps = final_steps
    
    # Fallback : si le LLM n'a pas suivi le format
    if not steps:
        # Détection basique : si "search" ou "find" dans la requête → web task
        lower_req = user_request.lower()
        if any(w in lower_req for w in ["search", "find", "how to", "what is", "documentation"]):
            steps = [f"SEARCH:{user_request}", "FETCH:best result", "CODE:summarize"]
        else:
            steps = [f"CODE:{user_request}"]
    
    print(f"📋 Steps parsées : {steps}")
    
    return {
        "plan": plan_text,
        "plan_steps": steps,
        "current_step": 0,
        "step_type": steps[0].split(":")[0].lower() if steps else "code"
    }