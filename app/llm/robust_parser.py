import re
import json
from typing import Dict, Any, Union, Optional
from json_repair import repair_json
from pydantic import BaseModel, ValidationError

class ToolCall(BaseModel):
    """Schéma strict de sortie attendu par ton application."""
    tool: str
    args: Dict[str, Any]

class RobustParser:
    def __init__(self):
        # Regex pour repérer des blocs JSON ou XML potentiels
        self.json_pattern = re.compile(r"(\{.*?\})", re.DOTALL)
        self.xml_tool_pattern = re.compile(r"<tool_code>(.*?)</tool_code>", re.DOTALL) # Adaptable

    def parse(self, llm_output: str) -> Union[Dict[str, Any], str]:
        """
        Entrée : Le bazar généré par le LLM.
        Sortie : Un dictionnaire PROPRE {'tool': ..., 'args': ...} ou {'answer': ...}
        """
        text = llm_output.strip()

        # ÉTAPE 1 : Nettoyage Préalable (DeepSeek, Markdown)
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        text = text.replace("```json", "").replace("```", "").strip()

        # ÉTAPE 2 : Extraction et Réparation du JSON
        # On essaie de parser tout le texte avec json_repair (il est très fort pour trouver le JSON au milieu du bruit)
        decoded_obj = repair_json(text, return_objects=True)

        if not decoded_obj:
            # Si json_repair échoue, on tente l'extraction XML (Fallback Pony)
            xml_result = self._extract_xml_fallback(text)
            if xml_result:
                decoded_obj = xml_result
            else:
                # Si vraiment rien ne ressemble à de la data, c'est du texte conversationnel
                return {"answer": text}

        # ÉTAPE 3 : Normalisation (Le "Funnel")
        # On transforme n'importe quel dictionnaire en format standard
        try:
            normalized = self._normalize(decoded_obj)
        except ValueError:
            # Si c'est un JSON mais pas un tool call (ex: une liste simple), on le rend en texte
            return {"answer": str(decoded_obj)}
        
        if "answer" in normalized:
            return {"answer": normalized["answer"]}

        # ÉTAPE 4 : Validation Stricte (Pydantic)
        # C'est ici qu'on vérifie que les args sont cohérents
        try:
            valid_tool = ToolCall(**normalized)
            return valid_tool.model_dump()
        except ValidationError as e:
            # Si le LLM a oublié des arguments obligatoires, on renvoie une erreur expliquée
            # C'est utile pour le mécanisme de Retry
            return {"error": f"Validation Error: {e}", "raw": text}

    def _normalize(self, data: Any) -> Dict[str, Any]:
        """Transforme les dialectes (OpenAI, Trinity...) en standard interne."""
        if isinstance(data, list):
            # Parfois le LLM renvoie une liste de tools, on prend le premier
            if data: data = data[0]
            else: raise ValueError("Empty list")
            
        if not isinstance(data, dict):
            raise ValueError("Not a dictionary")

        normalized = {}

        # MAPPING DES CLÉS (Extensible)
        keys_map = {
            "tool": ["tool", "name", "function", "tool_name", "tool_call"],
            "args": ["args", "arguments", "parameters", "input", "kwargs"]
        }

        # Recherche du nom de l'outil
        found_tool = False
        for target, aliases in keys_map.items():
            for alias in aliases:
                if alias in data:
                    normalized[target] = data[alias]
                    if target == "tool": found_tool = True
                    break
        
        # Gestion spécifique des args (parfois stringifiés)
        if "args" in normalized and isinstance(normalized["args"], str):
            normalized["args"] = repair_json(normalized["args"], return_objects=True)

        if not found_tool:
            # Si on a un JSON valide mais pas de clé "tool", c'est peut-être une réponse "answer" JSON
            if "answer" in data:
                return {"answer": data["answer"]}
            raise ValueError("No tool name found")

        # Valeur par défaut pour args
        if "args" not in normalized:
            normalized["args"] = {}

        return normalized

    def _extract_xml_fallback(self, text: str) -> Optional[Dict[str, Any]]:
        """Logique spécifique pour Pony XML"""
        if "<tool_call>" in text:
            try:
                tool_match = re.search(r'<tool_call>\s*([a-zA-Z0-9_]+)', text)
                if tool_match:
                    tool_name = tool_match.group(1).strip()
                    args = {}
                    arg_matches = re.findall(r'<arg_key>(.*?)</arg_key>\s*<arg_value>(.*?)</arg_value>', text, re.DOTALL)
                    for key, value in arg_matches:
                        key = key.strip()
                        value = value.strip()
                        if value.lower() == "true": value = True
                        elif value.lower() == "false": value = False
                        elif value.isdigit(): value = int(value)
                        args[key] = value
                    return {"tool": tool_name, "args": args}
            except:
                pass
        return None

# Instance globale
parser = RobustParser()