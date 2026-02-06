# app/graph/nodes.py
import os
import re
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage
from app.state.dev_state import DevState
from app.llm.ollama_client import get_llm, get_llm_constrained
from app.utils.tool_parser import parse_tool_response

# Import des outils (gardé pour le mode normal qui pourrait en avoir besoin)
from app.tools.fs import list_project_structure, read_file_content, write_file, smart_replace
from app.tools.web import web_search, fetch_web_page

def call_assistant(state: DevState):
    print("🤖 GENERATOR : Analyse du contexte...")
    import time
    
    current_dir = state.get("root_dir", os.getcwd())
    plan = state.get("plan", "No plan provided.")
    messages = state["messages"]
    last_message = messages[-1]
    guidelines = state.get("dynamic_guidelines", "")
    
    # --- DÉTECTION DU MODE ---
    just_searched = isinstance(last_message, ToolMessage) and getattr(last_message, 'name', '') == "web_search"
    optimizer_forces_click = "fetch_web_page" in guidelines and "URGENT FIX" in guidelines
    activate_trap = just_searched or optimizer_forces_click
    
    # --- CONSTRUCTION DU PROMPT ---
    if activate_trap:
        print("⚡ TRAP ACTIVÉ : Force fetch_web_page")
        
        # Récupérer les résultats de recherche
        search_content = ""
        for m in reversed(messages):
            if isinstance(m, ToolMessage) and getattr(m, 'name', '') == "web_search":
                search_content = m.content
                break
        
        system_content = (
            "You are a URL fetcher. Read the search results and call fetch_web_page on the best URL.\n\n"
            "### EXAMPLE ###\n"
            "Search results: 'Title: Python Tutorial\\nURL: https://docs.python.org/3/tutorial'\n"
            "Your response: {\"tool\": \"fetch_web_page\", \"args\": {\"url\": \"https://docs.python.org/3/tutorial\"}}\n\n"
            f"### SEARCH RESULTS ###\n{search_content[:2000]}\n\n"
            "Pick the best URL and respond with JSON."
        )
        
        # Extraire les URLs en backup
        urls = re.findall(r'https?://[^\s\n,)]+', search_content)
        
        # LLM contraint : ne peut générer QUE fetch_web_page
        llm = get_llm_constrained(tool_names=["fetch_web_page"])
        
    else:
        # MODE NORMAL
        feedback = f"\n### FEEDBACK ###\n{guidelines}\n" if guidelines else ""
        
        system_content = (
            f"You are a Senior Autonomous Developer working in: {current_dir}.\n"
            f"### PLAN ###\n{plan}\n"
            f"{feedback}\n"
            "### STRATEGY ###\n"
            "Analyze the conversation, then call ONE tool.\n\n"
            
            "### EXAMPLE 1: Create a file ###\n"
            "Response: {\"tool\": \"write_file\", \"args\": {\"file_path\": \"calc.py\", \"content\": \"class Calc:\\n    pass\"}}\n\n"
            
            "### EXAMPLE 2: Search the web ###\n"
            "Response: {\"tool\": \"web_search\", \"args\": {\"query\": \"FastAPI tutorial\"}}\n\n"
            
            "### EXAMPLE 3: Read a file ###\n"
            "Response: {\"tool\": \"read_file_content\", \"args\": {\"file_path\": \"main.py\"}}\n\n"
            
            "Respond with ONLY a JSON object. No text before or after."
        )
        
        llm = get_llm_constrained()
        urls = []  # Pas de backup nécessaire
    
    # --- SLIDING WINDOW : limiter le contexte ---
    filtered_messages = [m for m in messages if not isinstance(m, SystemMessage)]
    if len(filtered_messages) > 15:
        filtered_messages = filtered_messages[-15:]
    
    msg_history = [SystemMessage(content=system_content)] + filtered_messages
    
    # --- APPEL LLM ---
    print(f"⏳ Envoi au LLM... (context: {len(msg_history)} messages)")
    start = time.time()
    response = llm.invoke(msg_history)
    elapsed = time.time() - start
    print(f"✅ LLM a répondu en {elapsed:.1f}s : {response.content[:100]}...")
    
    # --- PARSING DE LA RÉPONSE ---
    parsed = parse_tool_response(response.content)
    
    # --- FILET DE SÉCURITÉ (si parsing échoue ET trap actif) ---
    if activate_trap and (not hasattr(parsed, 'tool_calls') or not parsed.tool_calls):
        if urls:
            print(f"🔧 FORCE FETCH sur : {urls[0]}")
            parsed = AIMessage(
                content="",
                tool_calls=[{
                    "id": f"forced_fetch_{state.get('retry_count', 0)}",
                    "name": "fetch_web_page",
                    "args": {"url": urls[0]}
                }]
            )
    
    return {"messages": [parsed]}


def search_agent(state: DevState):
    """Sous-agent spécialisé web : ne connaît que web_search + fetch_web_page."""
    print("🔍 SEARCH AGENT activé")
    import time
    
    messages = state["messages"]
    last_message = messages[-1]
    
    # Si on a déjà des résultats de recherche, forcer fetch
    # Chercher dans les 5 derniers messages si on a un résultat web_search NON suivi d'un fetch
    recent = messages[-5:]
    has_search = any(isinstance(m, ToolMessage) and getattr(m, 'name', '') == "web_search" for m in recent)
    has_fetch = any(isinstance(m, ToolMessage) and getattr(m, 'name', '') == "fetch_web_page" for m in recent)
    has_search_results = has_search and not has_fetch
    
    if has_search_results:
        tool_names = ["fetch_web_page"]
        # Trouver le dernier résultat de web_search
        search_content = ""
        for m in reversed(messages):
            if isinstance(m, ToolMessage) and getattr(m, 'name', '') == "web_search":
                search_content = m.content[:2000]
                break
        system_content = (
            "You received search results. Call fetch_web_page on the best URL.\n\n"
            "### EXAMPLE ###\n"
            "{\"tool\": \"fetch_web_page\", \"args\": {\"url\": \"https://example.com/page\"}}\n\n"
            f"### SEARCH RESULTS ###\n{search_content}\n\n"
            "Respond with JSON only."
        )
    else:
        tool_names = ["web_search"]
        user_request = ""
        for m in reversed(messages):
            if hasattr(m, 'content') and isinstance(m.content, str) and len(m.content) > 10:
                user_request = m.content
                break
        system_content = (
            "You are a web search agent. Call web_search with a good query.\n\n"
            "### EXAMPLE ###\n"
            "{\"tool\": \"web_search\", \"args\": {\"query\": \"python FastAPI websocket example\"}}\n\n"
            f"### USER REQUEST ###\n{user_request[:500]}\n\n"
            "Respond with JSON only."
        )
    
    llm = get_llm_constrained(tool_names=tool_names)
    
    filtered = [m for m in messages if not isinstance(m, SystemMessage)][-10:]
    msg_history = [SystemMessage(content=system_content)] + filtered
    
    print(f"⏳ Envoi au LLM... (context: {len(msg_history)} messages)")
    start = time.time()
    response = llm.invoke(msg_history)
    elapsed = time.time() - start
    print(f"✅ LLM a répondu en {elapsed:.1f}s : {response.content[:100]}...")
    parsed = parse_tool_response(response.content)
    
    # Filet de sécurité pour fetch
    if has_search_results and (not parsed.tool_calls):
        search_text = ""
        for m in reversed(messages):
            if isinstance(m, ToolMessage) and getattr(m, 'name', '') == "web_search":
                search_text = m.content
                break
        urls = re.findall(r'https?://[^\s\n,)]+', search_text)
        if urls:
            parsed = AIMessage(content="", tool_calls=[{
                "id": f"forced_{state.get('retry_count', 0)}",
                "name": "fetch_web_page",
                "args": {"url": urls[0]}
            }])
    
    return {"messages": [parsed]}


def coder_agent(state: DevState):
    """Sous-agent spécialisé code : ne connaît que write_file, smart_replace, read_file_content, list_project_structure."""
    print("💻 CODER AGENT activé")
    import time
    
    messages = state["messages"]
    current_dir = state.get("root_dir", os.getcwd())
    plan = state.get("plan", "")
    guidelines = state.get("dynamic_guidelines", "")
    feedback = f"\n### FEEDBACK ###\n{guidelines}\n" if guidelines else ""
    
    system_content = (
        f"You are a code agent working in: {current_dir}.\n"
        f"### PLAN ###\n{plan}\n"
        f"{feedback}\n"
        "### TOOLS ###\n"
        "- write_file(file_path, content): Create/overwrite a file\n"
        "- smart_replace(file_path, target_snippet, replacement_snippet): Edit existing file\n"
        "- read_file_content(file_path): Read a file\n"
        "- list_project_structure(root_dir): List files\n\n"
        
        "### EXAMPLE: Create a file ###\n"
        "{\"tool\": \"write_file\", \"args\": {\"file_path\": \"app.py\", \"content\": \"from flask import Flask\\napp = Flask(__name__)\\n\"}}\n\n"
        
        "### EXAMPLE: Edit a file ###\n"
        "{\"tool\": \"smart_replace\", \"args\": {\"file_path\": \"app.py\", \"target_snippet\": \"pass\", \"replacement_snippet\": \"return 42\"}}\n\n"
        
        "Respond with JSON only. ONE tool call."
    )
    
    tool_names = ["write_file", "smart_replace", "read_file_content", "list_project_structure"]
    llm = get_llm_constrained(tool_names=tool_names)
    
    filtered = [m for m in messages if not isinstance(m, SystemMessage)][-15:]
    # Tronquer les messages trop longs (résultats de fetch)
    truncated = []
    for m in filtered:
        if isinstance(m, ToolMessage) and len(m.content) > 1500:
            from langchain_core.messages import ToolMessage as TM
            truncated.append(TM(content=m.content[:1500] + "\n...[tronqué]", tool_call_id=m.tool_call_id, name=getattr(m, 'name', '')))
        else:
            truncated.append(m)
    filtered = truncated
    msg_history = [SystemMessage(content=system_content)] + filtered
    
    print(f"⏳ Envoi au LLM... (context: {len(msg_history)} messages)")
    start = time.time()
    response = llm.invoke(msg_history)
    elapsed = time.time() - start
    print(f"✅ LLM a répondu en {elapsed:.1f}s : {response.content[:100]}...")
    parsed = parse_tool_response(response.content)
    
    return {"messages": [parsed]}