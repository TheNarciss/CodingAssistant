from langchain_core.messages import SystemMessage, HumanMessage
from app.state.dev_state import DevState
from app.llm.ollama_client import get_llm

def reviewer_node(state: DevState):
    print("\n🧐 REVIEWER : Vérification du code...")
    
    messages = state["messages"]
    last_message = messages[-1]
    
    # Sécurité : Si pas d'appel d'outil, on valide par défaut (ou on rejette selon ta logique)
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        return {"review_feedback": None, "code_quality_score": 10}

    # Récupération propre
    tool_call = last_message.tool_calls[0]
    tool_name = tool_call["name"]
    args = tool_call["args"]

    # ✅ LE PASS-DROIT POUR LE WEB (Crucial pour ton problème)
    if tool_name in ["web_search", "fetch_web_page"]:
        print(f"✅ REVIEWER : Outil '{tool_name}' autorisé sans review de code.")
        return {"code_quality_score": 10, "review_feedback": None}

    # --- 🛡️ GUARDRAILS LOGIQUES (Sécurité Fichiers) ---
    
    if tool_name == "write_file":
        content = args.get("content", "")
        
        # 1. Check de taille
        if len(content) < 10: # J'ai réduit à 10 pour être moins strict
            error_msg = f"REJECTED: Content too short ({len(content)} chars)."
            print(f"❌ REVIEWER (Auto): {error_msg}")
            return {"review_feedback": error_msg, "code_quality_score": 0}

        # 2. Check de format (JSON dans string)
        if content.strip().startswith("{") and "class" in content:
            error_msg = (
                "REJECTED: You wrapped the Python code inside a JSON object (starts with '{'). "
                "Send ONLY the raw Python code string. Do not wrap it."
            )
            print(f"❌ REVIEWER (Auto): {error_msg}")
            return {"review_feedback": error_msg, "code_quality_score": 0}

        # 3. Check de snippet ($1)
        if "$1" in content or "${1" in content:
            error_msg = "REJECTED: You used snippet placeholders like '$1'. Use valid Python syntax."
            print(f"❌ REVIEWER (Auto): {error_msg}")
            return {"review_feedback": error_msg, "code_quality_score": 0}

    # 3. Validation par LLM pour le reste
    llm = get_llm(model_name="llama3.2:3b", temperature=0)
    
    prompt = (
        f"You are a Senior Code Reviewer. Analyze this action:\n"
        f"Tool: {tool_name}\n"
        f"Arguments: {args}\n\n"
        "Reply ONLY with 'APPROVE' if safe, or a short reason if rejected."
    )
    
    review = llm.invoke([HumanMessage(content=prompt)])
    decision = review.content.strip()
    
    if "APPROVE" in decision.upper():
        print("✅ Code Validé.")
        return {"review_feedback": None, "code_quality_score": 10}
    else:
        print(f"❌ Code Rejeté : {decision}")
        return {"review_feedback": decision, "code_quality_score": 0}