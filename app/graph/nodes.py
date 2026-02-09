# app/graph/nodes.py
import os
import re
import time
import json
from app.llm.llm_client import get_llm, get_llm_constrained
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage, HumanMessage
from app.state.dev_state import DevState
from app.llm.llm_client import get_llm, get_llm_constrained
from app.utils.tool_parser import parse_tool_response
from app.config import MAX_CONTEXT_MESSAGES
from app.tools.terminal import run_terminal
from app.tools.fs import list_project_structure, read_file_content, write_file, replace_lines
from app.logger import get_logger
logger = get_logger("nodes")


def call_assistant(state: DevState):
    logger.info("🤖 GENERATOR : Analyse du contexte...")
    
    current_dir = state.get("root_dir", ".")
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
        logger.warning("⚡ TRAP ACTIVÉ : Force fetch_web_page")
        
        # Récupérer le contenu de la recherche pour le contexte
        search_content = ""
        for m in reversed(messages):
            if isinstance(m, ToolMessage) and getattr(m, 'name', '') == "web_search":
                search_content = m.content
                break
        
        system_content = (
            "You are a URL fetcher. Read the search results and call fetch_web_page on the best URL.\n\n"
            "### SEARCH RESULTS ###\n"
            f"{search_content[:3000]}\n\n" # On limite un peu pour pas exploser le contexte
            "### INSTRUCTION ###\n"
            "Pick the best URL and respond with JSON: {\"tool\": \"fetch_web_page\", \"args\": {\"url\": \"...\"}}"
        )
        
        # Extraction d'URLs de secours
        urls = re.findall(r'https?://[^\s\n,)]+', search_content)
        llm = get_llm_constrained(tool_names=["fetch_web_page"])
        
    else:
        # === MODIFICATION 1 : AJOUT DE L'OPTION "ANSWER" DANS LE PROMPT ===
        feedback = f"\n### FEEDBACK ###\n{guidelines}\n" if guidelines else ""
        
        system_content = (
            f"You are a Senior Autonomous Developer working in: {current_dir}.\n"
            f"### PLAN ###\n{plan}\n"
            f"{feedback}\n"
            "### STRATEGY ###\n"
            "Analyze the conversation. You have two options:\n"
            "1. USE A TOOL to advance the task.\n"
            "2. ANSWER the user if the task is done or if you need to explain something.\n\n"
            
            "### EXAMPLES (JSON ONLY) ###\n"
            "1. Tool - Create file:\n"
            "{\"tool\": \"write_file\", \"args\": {\"file_path\": \"calc.py\", \"content\": \"...\"}}\n\n"
            
            "2. Tool - Search:\n"
            "{\"tool\": \"web_search\", \"args\": {\"query\": \"FastAPI tutorial\"}}\n\n"
            
            "3. Answer - Task Done (MANDATORY FORMAT FOR TEXT):\n"
            "{\"answer\": \"I have finished creating the files. Here is the summary...\"}\n\n"
            
            "Respond with ONLY a JSON object. No text before or after."
        )
        
        llm = get_llm_constrained()
        urls = []

    # --- SLIDING WINDOW ---
    # (Assurez-vous que smart_context_window est importée ou définie)
    filtered_messages = messages # ou smart_context_window(messages, MAX_CONTEXT_MESSAGES)
    
    msg_history = [SystemMessage(content=system_content)] + filtered_messages
    
    # --- APPEL LLM ---
    logger.debug(f"⏳ Envoi au LLM... (context: {len(msg_history)} messages)")
    start = time.time()
    try:
        response = llm.invoke(msg_history)
        elapsed = time.time() - start
        logger.debug(f"✅ LLM a répondu en {elapsed:.1f}s")
    except Exception as e:
        logger.error(f"❌ Erreur LLM : {e}")
        return {"messages": [AIMessage(content="Error calling LLM.")]}
    
    # === MODIFICATION 2 : PARSING ROBUSTE (TOOL vs ANSWER) ===
    try:
        # Nettoyage basique si le LLM met du markdown ```json ... ```
        content_str = response.content.strip()
        if content_str.startswith("```json"):
            content_str = content_str[7:]
        if content_str.endswith("```"):
            content_str = content_str[:-3]
            
        content_json = json.loads(content_str.strip())
        
        # CAS A : Le LLM veut répondre (ANSWER)
        if "answer" in content_json:
            answer_text = content_json["answer"]
            logger.info(f"💬 RESPONSE : {answer_text[:50]}...")
            return {"messages": [AIMessage(content=answer_text)]}
            
        # CAS B : Le LLM veut utiliser un outil (TOOL)
        elif "tool" in content_json:
            tool_name = content_json["tool"]
            tool_args = content_json.get("args", {})
            
            logger.info(f"🤖 ACTION : {tool_name}")
            
            # Création du message d'outil standard LangChain
            ai_msg = AIMessage(
                content="",
                tool_calls=[{
                    "name": tool_name,
                    "args": tool_args,
                    "id": f"call_{int(time.time())}" # ID unique
                }]
            )
            return {"messages": [ai_msg]}
            
        else:
            logger.warning("⚠️ JSON valide mais structure inconnue (pas de 'tool' ni 'answer')")
            # Fallback : on considère tout le JSON comme une réponse texte
            return {"messages": [AIMessage(content=str(content_json))]}

    except json.JSONDecodeError:
        logger.error(f"❌ Erreur JSON Decode : {response.content}")
        
        # --- FILET DE SÉCURITÉ (TRAP MODE) ---
        if activate_trap and urls:
            logger.warning(f"🔧 FORCE FETCH (Fallback JSON) sur : {urls[0]}")
            forced_msg = AIMessage(
                content="",
                tool_calls=[{
                    "id": f"forced_fetch_{state.get('retry_count', 0)}",
                    "name": "fetch_web_page",
                    "args": {"url": urls[0]}
                }]
            )
            return {"messages": [forced_msg]}
            
        return {"messages": [AIMessage(content=f"Error parsing JSON: {response.content}")]}

def search_agent(state: DevState):
    """Sous-agent spécialisé web : ne connaît que web_search + fetch_web_page."""
    logger.info("🔍 SEARCH AGENT activé")
   
    
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
    
    logger.debug(f"⏳ Envoi au LLM... (context: {len(msg_history)} messages)")
    start = time.time()
    response = llm.invoke(msg_history)
    elapsed = time.time() - start
    logger.debug(f"✅ LLM a répondu en {elapsed:.1f}s : {response.content[:100]}...")
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
    """Sous-agent spécialisé code : ne connaît que write_file, replace_lines, read_file_content, list_project_structure."""
    logger.info("💻 CODER AGENT activé")

    
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
        "- replace_lines(file_path, start_line, end_line, new_content): Edit existing file\n"
        "- read_file_content(file_path): Read a file\n"
        "- run_terminal(command): Run a shell command (ls, grep, cat, etc.)\n"
        "- list_project_structure(root_dir): List files\n\n"
        
        "### EXAMPLE: Create a file ###\n"
        "{\"tool\": \"write_file\", \"args\": {\"file_path\": \"app.py\", \"content\": \"from flask import Flask\\napp = Flask(__name__)\\n\"}}\n\n"
        
        "### EXAMPLE: Edit a file ###\n"
        "{\"tool\": \"replace_lines\", \"args\": {\"file_path\": \"app.py\", \"start_line\": 10, \"end_line\": 12, \"new_content\": \"return 42\"}}\n\n"
        "### EXAMPLE: List files ###\n"
        "{\"tool\": \"run_terminal\", \"args\": {\"command\": \"ls -la\"}}\n\n"
        
        "Respond with JSON only. ONE tool call."
    )
    
    tool_names = ["write_file", "replace_lines", "read_file_content", "list_project_structure", "run_terminal"]
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
    
    logger.debug(f"⏳ Envoi au LLM... (context: {len(msg_history)} messages)")
    start = time.time()
    response = llm.invoke(msg_history)
    elapsed = time.time() - start
    logger.debug(f"✅ LLM a répondu en {elapsed:.1f}s : {response.content[:100]}...")
    parsed = parse_tool_response(response.content)
    
    return {"messages": [parsed]}

def research_agent(state: DevState):
    """Agent spécialisé web : utilise smart_web_fetch."""
    logger.info("🔬 RESEARCH AGENT activé")
 
    
    messages = state["messages"]
    
    # Extraire la requête user
    user_request = ""
    for m in reversed(messages):
        if hasattr(m, 'content') and isinstance(m.content, str) and len(m.content) > 10:
            user_request = m.content
            break
    
    system_content = (
        "You are a research agent. Call smart_web_fetch with a good search query.\n\n"
        "### EXAMPLE ###\n"
        "{\"tool\": \"smart_web_fetch\", \"args\": {\"query\": \"python FastAPI websocket tutorial\"}}\n\n"
        f"### USER REQUEST ###\n{user_request[:500]}\n\n"
        "Respond with JSON only."
    )
    
    llm = get_llm_constrained(tool_names=["smart_web_fetch"])
    
    filtered = [m for m in messages if not isinstance(m, SystemMessage)][-10:]
    msg_history = [SystemMessage(content=system_content)] + filtered
    
    logger.debug(f"⏳ Envoi au LLM... (context: {len(msg_history)} messages)")
    start = time.time()
    response = llm.invoke(msg_history)
    elapsed = time.time() - start
    logger.debug(f"✅ LLM a répondu en {elapsed:.1f}s : {response.content[:100]}...")
    parsed = parse_tool_response(response.content)
    
    return {"messages": [parsed]}

def smart_context_window(messages: list, max_messages: int = 20) -> list:
    """Garde TOUJOURS le premier message user + les N derniers."""
    filtered = [m for m in messages if not isinstance(m, SystemMessage)]
    
    if len(filtered) <= max_messages:
        return filtered
    
    # Garder le premier message user
    first_user = next((m for m in filtered if hasattr(m, 'content')), None)
    
    # Garder les N-1 derniers
    recent = filtered[-(max_messages - 1):]
    
    return [first_user] + recent if first_user else recent

def synthesizer_node(state: DevState):
    """Résume les résultats de recherche pour l'user."""
    messages = state["messages"]
    
    # Trouver le dernier fetch
    fetch_content = ""
    for m in reversed(messages):
        if isinstance(m, ToolMessage) and getattr(m, 'name', '') == "fetch_web_page":
            fetch_content = m.content[:3000]
            break
    
    llm = get_llm()
    prompt = f"Summarize this for the user:\n\n{fetch_content}"
    response = llm.invoke([HumanMessage(content=prompt)])
    
    return {"messages": [AIMessage(content=response.content)]}