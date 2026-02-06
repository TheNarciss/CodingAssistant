# app/utils/tool_parser.py
import json
import uuid
from langchain_core.messages import AIMessage

def parse_tool_response(response_text: str) -> AIMessage:
    """
    Parse la sortie JSON contrainte du LLM et construit un AIMessage 
    avec tool_calls compatible LangGraph/ToolNode.
    """
    try:
        # Nettoyer si le LLM ajoute des backticks
        clean = response_text.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        
        data = json.loads(clean)
        
        tool_name = data.get("tool", "")
        tool_args = data.get("args", {})
        
        if not tool_name:
            return AIMessage(content="Error: no tool specified in JSON output.")
        
        # Construire le tool_call au format LangChain
        tool_call_id = f"call_{uuid.uuid4().hex[:12]}"
        
        return AIMessage(
            content="",
            tool_calls=[{
                "id": tool_call_id,
                "name": tool_name,
                "args": tool_args
            }]
        )
        
    except json.JSONDecodeError as e:
        return AIMessage(content=f"Error: Failed to parse JSON: {e}\nRaw: {response_text[:200]}")
    except Exception as e:
        return AIMessage(content=f"Error: {e}")