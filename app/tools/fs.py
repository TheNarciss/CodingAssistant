# app/tools/fs.py
from langchain_core.tools import tool
from pathlib import Path
from app.config import SANDBOX_PATH, FILE_CONTENT_MAX_CHARS

# --- CONFIGURATION DU SANDBOX ---


# On s'assure que le dossier existe, sinon on le crée
SANDBOX_PATH.mkdir(parents=True, exist_ok=True)

def _sanitize_relative_path(file_path: str) -> str:
    """Nettoie le chemin en supprimant les préfixes inutiles."""
    if not file_path:
        return file_path

    path = Path(file_path)
    
    # Supprimer les préfixes connus
    parts_to_remove = {"PlaygroundForCodingAssistant", "CodingAssistant", "codingassistant"}
    clean_parts = [p for p in path.parts if p not in parts_to_remove]
    
    # Si chemin absolu, garder juste le nom si tout est supprimé
    if not clean_parts:
        return path.name
    
    return Path(*clean_parts).as_posix()

def get_safe_path(file_path: str) -> Path:
    """
    Transforme un chemin relatif (ex: 'main.py') en chemin absolu dans le sandbox.
    Empêche de remonter dans les dossiers parents (sécurité).
    """
    # On enlève les éventuels "/" au début pour éviter de remonter à la racine système
    file_path = _sanitize_relative_path(file_path)
    clean_path = file_path.lstrip("/\\")
    full_path = (SANDBOX_PATH / clean_path).resolve()
    
    # Sécurité : On vérifie que le fichier final est bien DANS le sandbox
    if not str(full_path).startswith(str(SANDBOX_PATH.resolve())):
        raise ValueError(f"ACCÈS REFUSÉ : Tentative de sortir du sandbox ({file_path})")
    
    return full_path

@tool
def list_project_structure():
    """
    Explore the sandbox directory and return the file tree structure.
    """
    try:
        
        base_path = SANDBOX_PATH
        
        excluded = {".git", ".venv", "__pycache__", ".DS_Store", "node_modules"}
        files_list = []
        
        if not base_path.exists():
            return "Le répertoire de travail est vide (nouveau projet)."

        for path in base_path.rglob("*"):
            if not any(part in excluded for part in path.parts):
                if path.is_file():
                    # On affiche le chemin relatif par rapport au sandbox
                    files_list.append(str(path.relative_to(base_path)))
        
        if not files_list:
            return "Le répertoire est vide."
            
        return "\n".join(files_list[:100])
    except Exception as e:
        return f"Erreur lors du listage : {str(e)}"

@tool
def read_file_content(file_path: str):
    """
    Read the content of a file within the sandbox.
    """
    try:
        path = get_safe_path(file_path)
        
        if not path.exists():
            return f"Erreur : Le fichier {file_path} n'existe pas."
        
        if path.is_dir():
            return f"Erreur : {file_path} est un répertoire."

        content = path.read_text(encoding="utf-8")
        if len(content) > FILE_CONTENT_MAX_CHARS:
            return content[:FILE_CONTENT_MAX_CHARS] + "\n... [Contenu tronqué]"
            
        return content
    except ValueError as ve:
        return str(ve)
    except Exception as e:
        return f"Erreur lecture : {str(e)}"

@tool
def write_file(file_path: str, content: str):
    """
    Create or overwrite a file in the sandbox.
    """
    try:
        path = get_safe_path(file_path)
        
        # Création des dossiers parents si nécessaire
        path.parent.mkdir(parents=True, exist_ok=True)
        
        path.write_text(content, encoding="utf-8")
        return f"Succès : Fichier {file_path} sauvegardé."
    except ValueError as ve:
        return str(ve)
    except Exception as e:
        return f"Erreur écriture : {str(e)}"


@tool
def replace_lines(file_path: str, start_line: int, end_line: int, new_content: str):
    """Replace lines [start_line, end_line] with new_content. Lines are 1-indexed."""
    try:
        path = get_safe_path(file_path)
        
        if not path.exists():
            return f"Error: file {file_path} not found"
        
        lines = path.read_text().splitlines()

        # Validation
        if not (1 <= start_line <= len(lines)):
            return f"Error: line {start_line} out of range"
        if not (1 <= end_line <= len(lines)):
            return f"Error: line {end_line} out of range"
        if start_line > end_line:
            return "Error: start_line must be <= end_line"

        # Remplacement
        new_lines = lines[:start_line - 1] + [new_content] + lines[end_line:]
        path.write_text('\n'.join(new_lines), encoding="utf-8")
        return f"Success: lines {start_line}-{end_line} replaced in {file_path}"
    except ValueError as ve:
        return str(ve)
    except Exception as e:
        return f"Error replacing lines: {e}"