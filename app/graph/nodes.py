# app/graph/nodes.py
import os
import re
import time
import json
from app.llm.llm_client import get_llm, get_llm_constrained
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage, HumanMessage
from app.state.dev_state import DevState
from app.config import MAX_CONTEXT_MESSAGES
from app.tools.terminal import run_terminal
from app.tools.fs import list_project_structure, read_file_content, write_file, replace_lines
from app.logger import get_logger
from app.llm.robust_parser import parser

logger = get_logger("nodes")

# ═══════════════════════════════════════════════════════════
# TOOLS MANIFEST — Injected into EVERY agent prompt
# This is the single source of truth for tool names.
# ═══════════════════════════════════════════════════════════
TOOLS_MANIFEST = """### AVAILABLE TOOLS (use EXACT names — any other name will fail) ###
- read_file_content(file_path): Read a file's content. File path is RELATIVE (e.g., "snake_game.py").
- write_file(file_path, content): Create or overwrite a file.
- replace_lines(file_path, start_line, end_line, new_content): Edit specific lines in a file.
- list_project_structure(): List all files in the project.
- run_terminal(command): Execute a shell command (ls, cat, grep, head, etc.).
- web_search(query): Search the internet via DuckDuckGo.
- fetch_web_page(url): Fetch a webpage's text content.
- smart_web_fetch(query): Search + fetch best result in one shot.

⚠️ CRITICAL RULES:
- "read_file" does NOT exist. Use "read_file_content" instead.
- "run_command" does NOT exist. Use "run_terminal" instead.
- File paths must be RELATIVE (e.g., "main.py", NOT "/Users/.../main.py").
- Respond with ONLY a JSON object, nothing else.
"""


def _build_tool_call_msg(parsed_result: dict) -> AIMessage:
    """Helper to build an AIMessage with tool_calls from a parsed result."""
    tool_name = parsed_result["tool"]
    tool_args = parsed_result.get("args", {})
    
    # Common hallucination fixes
    QUICK_FIXES = {
        "run_command": "run_terminal",
        "read_file": "read_file_content",
    }
    tool_name = QUICK_FIXES.get(tool_name, tool_name)
    
    return AIMessage(
        content="",
        tool_calls=[{
            "name": tool_name,
            "args": tool_args,
            "id": f"call_{int(time.time())}_{id(tool_args) % 10000}"
        }]
    )


def _parse_llm_response(response_content: str, context_label: str = "AGENT") -> dict:
    """
    Unified parsing for all agents. Returns parsed result dict.
    Uses RobustParser (handles {"tool":...}, {"name":...}, {"function":...}, etc.)
    """
    parsed = parser.parse(response_content)
    
    if "error" in parsed:
        logger.warning(f"⚠️ {context_label} parse error: {parsed['error']}")
    
    return parsed


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
    
    urls = []
    
    # --- CONSTRUCTION DU PROMPT ---
    if activate_trap:
        logger.warning("⚡ TRAP ACTIVÉ : Force fetch_web_page")
        
        search_content = ""
        for m in reversed(messages):
            if isinstance(m, ToolMessage) and getattr(m, 'name', '') == "web_search":
                search_content = m.content
                break
        
        urls = re.findall(r'https?://[^\s\n,)]+', search_content)
        
        system_content = (
            "You are a URL fetcher. Read the search results and call fetch_web_page on the best URL.\n\n"
            "### SEARCH RESULTS ###\n"
            f"{search_content[:3000]}\n\n"
            "### INSTRUCTION ###\n"
            "Pick the best URL and respond with JSON: {\"tool\": \"fetch_web_page\", \"args\": {\"url\": \"...\"}}"
        )
        
        llm = get_llm_constrained(tool_names=["fetch_web_page"])
        
    else:
        # MODE NORMAL
        feedback = f"\n### FEEDBACK ###\n{guidelines}\n" if guidelines else ""
        
        system_content = (
            f"You are a Senior Autonomous Developer working in: {current_dir}.\n"
            f"### PLAN ###\n{plan}\n"
            f"{feedback}\n"
            f"{TOOLS_MANIFEST}\n"
            "### STRATEGY ###\n"
            "Analyze the conversation. You have two options:\n"
            "1. USE A TOOL to advance the task.\n"
            "2. ANSWER the user if the task is done or if you need to explain something.\n\n"
            
            "### RESPONSE FORMAT (JSON ONLY) ###\n"
            "Tool call:  {\"tool\": \"write_file\", \"args\": {\"file_path\": \"calc.py\", \"content\": \"...\"}}\n"
            "Answer:     {\"answer\": \"I have finished creating the files. Here is the summary...\"}\n\n"
            
            "Respond with ONLY a JSON object."
        )
        
        llm = get_llm_constrained()

    # --- SLIDING WINDOW ---
    filtered_messages = messages 
    
    msg_history = [SystemMessage(content=system_content)] + filtered_messages
    
    # --- APPEL LLM ---
    logger.debug(f"⏳ Envoi au LLM... (context: {len(msg_history)} messages)")
    start = time.time()
    try:
        response = llm.invoke(msg_history)
        elapsed = time.time() - start
        logger.debug(f"✅ LLM a répondu en {elapsed:.1f}s")
    except Exception as e:
        logger.error(f"❌ Erreur Invocation LLM : {e}")
        return {"messages": [AIMessage(content="Error calling LLM.")]}
    
    # --- PARSING ROBUSTE ---
    parsed_result = _parse_llm_response(response.content, "GENERATOR")
    
    if "error" in parsed_result:
        # FILET DE SÉCURITÉ (TRAP MODE)
        if activate_trap and urls:
            logger.warning(f"🔧 FORCE FETCH (Fallback sur erreur) sur : {urls[0]}")
            forced_msg = AIMessage(
                content="",
                tool_calls=[{
                    "id": f"forced_fetch_{int(time.time())}",
                    "name": "fetch_web_page",
                    "args": {"url": urls[0]}
                }]
            )
            return {"messages": [forced_msg]}
        
        return {"messages": [AIMessage(content=f"System Error: Invalid output format. {parsed_result['error']}")]}

    if "answer" in parsed_result:
        answer_text = str(parsed_result["answer"])
        logger.info(f"💬 RESPONSE : {answer_text[:80]}...")
        return {"messages": [AIMessage(content=answer_text)]}
        
    if "tool" in parsed_result:
        ai_msg = _build_tool_call_msg(parsed_result)
        logger.info(f"🤖 ACTION : {ai_msg.tool_calls[0]['name']}")
        return {"messages": [ai_msg]}

    return {"messages": [AIMessage(content=response.content)]}


def search_agent(state: DevState):
    """Sous-agent spécialisé web : web_search + fetch_web_page."""
    logger.info("🔍 SEARCH AGENT activé")
    
    messages = state["messages"]
    
    recent = messages[-5:]
    has_search = any(isinstance(m, ToolMessage) and getattr(m, 'name', '') == "web_search" for m in recent)
    has_fetch = any(isinstance(m, ToolMessage) and getattr(m, 'name', '') == "fetch_web_page" for m in recent)
    has_search_results = has_search and not has_fetch
    
    if has_search_results:
        tool_names = ["fetch_web_page"]
        search_content = ""
        for m in reversed(messages):
            if isinstance(m, ToolMessage) and getattr(m, 'name', '') == "web_search":
                search_content = m.content[:2000]
                break
        system_content = (
            "You received search results. Call fetch_web_page on the best URL.\n\n"
            f"{TOOLS_MANIFEST}\n"
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
            f"{TOOLS_MANIFEST}\n"
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
    
    # ═══ FIX: Use RobustParser instead of tool_parser ═══
    parsed_result = _parse_llm_response(response.content, "SEARCH_AGENT")
    
    if "tool" in parsed_result:
        return {"messages": [_build_tool_call_msg(parsed_result)]}
    
    # Filet de sécurité pour fetch
    if has_search_results:
        search_text = ""
        for m in reversed(messages):
            if isinstance(m, ToolMessage) and getattr(m, 'name', '') == "web_search":
                search_text = m.content
                break
        urls = re.findall(r'https?://[^\s\n,)]+', search_text)
        if urls:
            return {"messages": [AIMessage(content="", tool_calls=[{
                "id": f"forced_{state.get('retry_count', 0)}",
                "name": "fetch_web_page",
                "args": {"url": urls[0]}
            }])]}
    
    # Fallback: return as text
    content = parsed_result.get("answer", response.content)
    return {"messages": [AIMessage(content=str(content))]}


def coder_agent(state: DevState):
    """Sous-agent spécialisé code : write_file, replace_lines, read_file_content, list_project_structure, run_terminal."""
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
        f"{TOOLS_MANIFEST}\n"
        "### RESPONSE FORMAT ###\n"
        "Respond with a JSON object containing \"tool\" and \"args\".\n\n"
        
        "### EXAMPLES ###\n"
        "Read a file:  {\"tool\": \"read_file_content\", \"args\": {\"file_path\": \"main.py\"}}\n"
        "Create file:  {\"tool\": \"write_file\", \"args\": {\"file_path\": \"app.py\", \"content\": \"from flask import Flask\\n\"}}\n"
        "Edit file:    {\"tool\": \"replace_lines\", \"args\": {\"file_path\": \"app.py\", \"start_line\": 10, \"end_line\": 12, \"new_content\": \"return 42\"}}\n"
        "Run command:  {\"tool\": \"run_terminal\", \"args\": {\"command\": \"cat main.py\"}}\n"
        "List files:   {\"tool\": \"list_project_structure\", \"args\": {}}\n\n"
        
        "Respond with JSON only. ONE tool call."
    )
    
    tool_names = ["write_file", "replace_lines", "read_file_content", "list_project_structure", "run_terminal"]
    llm = get_llm_constrained(tool_names=tool_names)
    
    filtered = [m for m in messages if not isinstance(m, SystemMessage)][-15:]
    # Tronquer les messages trop longs
    truncated = []
    for m in filtered:
        if isinstance(m, ToolMessage) and len(m.content) > 1500:
            truncated.append(ToolMessage(
                content=m.content[:1500] + "\n...[tronqué]",
                tool_call_id=m.tool_call_id,
                name=getattr(m, 'name', '')
            ))
        else:
            truncated.append(m)
    filtered = truncated
    msg_history = [SystemMessage(content=system_content)] + filtered
    
    logger.debug(f"⏳ Envoi au LLM... (context: {len(msg_history)} messages)")
    start = time.time()
    response = llm.invoke(msg_history)
    elapsed = time.time() - start
    logger.debug(f"✅ LLM a répondu en {elapsed:.1f}s : {response.content[:100]}...")
    
    # ═══ FIX: Use RobustParser instead of tool_parser ═══
    parsed_result = _parse_llm_response(response.content, "CODER")
    
    if "tool" in parsed_result:
        return {"messages": [_build_tool_call_msg(parsed_result)]}
    
    if "answer" in parsed_result:
        return {"messages": [AIMessage(content=str(parsed_result["answer"]))]}
    
    # Error or unparseable → return as text (will trigger fallback via route_after_agent)
    error_msg = parsed_result.get("error", f"Unexpected response: {response.content[:200]}")
    return {"messages": [AIMessage(content=f"Parse error: {error_msg}")]}


def research_agent(state: DevState):
    """Agent spécialisé web : utilise smart_web_fetch."""
    logger.info("🔬 RESEARCH AGENT activé")
    
    messages = state["messages"]
    
    user_request = ""
    for m in reversed(messages):
        if hasattr(m, 'content') and isinstance(m.content, str) and len(m.content) > 10:
            user_request = m.content
            break
    
    system_content = (
        "You are a research agent. Call smart_web_fetch with a good search query.\n\n"
        f"{TOOLS_MANIFEST}\n"
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
    
    # ═══ FIX: Use RobustParser instead of tool_parser ═══
    parsed_result = _parse_llm_response(response.content, "RESEARCH")
    
    if "tool" in parsed_result:
        return {"messages": [_build_tool_call_msg(parsed_result)]}
    
    content = parsed_result.get("answer", response.content)
    return {"messages": [AIMessage(content=str(content))]}


def smart_context_window(messages: list, max_messages: int = 20) -> list:
    """Garde TOUJOURS le premier message user + les N derniers."""
    filtered = [m for m in messages if not isinstance(m, SystemMessage)]
    
    if len(filtered) <= max_messages:
        return filtered
    
    first_user = next((m for m in filtered if hasattr(m, 'content')), None)
    recent = filtered[-(max_messages - 1):]
    
    return [first_user] + recent if first_user else recent


def synthesizer_node(state: DevState):
    """Résume les résultats de recherche pour l'user."""
    messages = state["messages"]
    
    fetch_content = ""
    for m in reversed(messages):
        if isinstance(m, ToolMessage) and getattr(m, 'name', '') == "fetch_web_page":
            fetch_content = m.content[:3000]
            break
    
    llm = get_llm()
    prompt = f"Summarize this for the user:\n\n{fetch_content}"
    response = llm.invoke([HumanMessage(content=prompt)])
    
    return {"messages": [AIMessage(content=response.content)]}