# app/tools/registry.py

VALID_TOOLS = {
    "web_search", "fetch_web_page", "smart_web_fetch",
    "write_file", "read_file_content", "replace_lines",
    "list_project_structure", "run_terminal"
}

SAFE_TOOLS_NO_REVIEW = {
    "web_search", "fetch_web_page", "read_file_content",
    "list_project_structure", "replace_lines",
    "smart_web_fetch", "run_terminal"
}

TOOL_ALIASES = {
    "read_file": "read_file_content",
    "read": "read_file_content",
    "readfile": "read_file_content",
    "read_content": "read_file_content",
    "file_read": "read_file_content",
    "get_file": "read_file_content",
    "get_file_content": "read_file_content",
    "open_file": "read_file_content",
    "cat": "read_file_content",
    "run_command": "run_terminal",
    "execute": "run_terminal",
    "exec": "run_terminal",
    "shell": "run_terminal",
    "terminal": "run_terminal",
    "command": "run_terminal",
    "bash": "run_terminal",
    "search": "web_search",
    "google": "web_search",
    "search_web": "web_search",
    "fetch": "fetch_web_page",
    "fetch_page": "fetch_web_page",
    "scrape": "fetch_web_page",
    "list_files": "list_project_structure",
    "ls": "list_project_structure",
    "list_dir": "list_project_structure",
    "tree": "list_project_structure",
    "create_file": "write_file",
    "save_file": "write_file",
    "edit_file": "replace_lines",
}

VALID_TOOLS_LIST_STR = ", ".join(sorted(VALID_TOOLS))

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