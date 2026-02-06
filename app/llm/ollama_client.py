# app/llm/ollama_client.py
from langchain_ollama import ChatOllama

def get_llm(model_name="llama3.2:3b", temperature=0.0):
    """LLM standard pour le texte libre (planner, reviewer)."""
    return ChatOllama(
        model=model_name,
        temperature=temperature,
        base_url="http://localhost:11434",
        keep_alive="5m"
    )

def get_llm_constrained(model_name="llama3.2:3b", temperature=0.0, tool_names=None):
    """
    LLM avec sortie JSON forcée par Ollama.
    Le modèle NE PEUT PAS générer autre chose que du JSON valide.
    """
    if tool_names is None:
        tool_names = ["web_search", "fetch_web_page", "write_file", 
                      "read_file_content", "smart_replace", "list_project_structure"]
    
    return ChatOllama(
        model=model_name,
        temperature=temperature,
        base_url="http://localhost:11434",
        keep_alive="5m",
        format={
            "type": "object",
            "properties": {
                "tool": {
                    "type": "string",
                    "enum": tool_names
                },
                "args": {
                    "type": "object"
                }
            },
            "required": ["tool", "args"]
        }
    )