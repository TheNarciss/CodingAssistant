# app/tools/fs.py
from langchain_core.tools import tool
from pathlib import Path

# --- CONFIGURATION DU SANDBOX ---
# On définit le chemin relatif par rapport au dossier CodingAssistant
# Note: J'ai gardé ta typo "Playgroud" pour être sûr que ça matche ta demande ;)
BASE_DIR = Path(__file__).resolve().parents[2]
SANDBOX_PATH = BASE_DIR / "PlaygroudForCodingAssistant"

# On s'assure que le dossier existe, sinon on le crée
SANDBOX_PATH.mkdir(parents=True, exist_ok=True)

def _sanitize_relative_path(file_path: str) -> str:
    if not file_path:
        return file_path

    p = Path(file_path)

    if p.is_absolute():
        try:
            return p.resolve().relative_to(SANDBOX_PATH.resolve()).as_posix()
        except Exception:
            parts = p.parts
            if "PlaygroudForCodingAssistant" in parts:
                idx = len(parts) - 1 - list(reversed(parts)).index("PlaygroudForCodingAssistant")
                rel_parts = parts[idx + 1:]
                return Path(*rel_parts).as_posix()
            return p.name

    parts = p.parts
    if "PlaygroudForCodingAssistant" in parts:
        idx = len(parts) - 1 - list(reversed(parts)).index("PlaygroudForCodingAssistant")
        rel_parts = parts[idx + 1:]
        return Path(*rel_parts).as_posix()

    if parts and parts[0] in ("CodingAssistant", "codingassistant"):
        return Path(*parts[1:]).as_posix()

    return file_path

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
def list_project_structure(root_dir: str = "."):
    """
    Explore the sandbox directory and return the file tree structure.
    """
    try:
        # On ignore l'argument root_dir de l'agent et on force le SANDBOX
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
        if len(content) > 10000:
            return content[:10000] + "\n... [Contenu tronqué]"
            
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
def smart_replace(file_path: str, target_snippet: str, replacement_snippet: str):
    """
    Replace a text snippet in a file within the sandbox.
    """
    try:
        path = get_safe_path(file_path)
        if not path.exists():
            return f"Erreur : Fichier {file_path} introuvable."
            
        content = path.read_text(encoding="utf-8")
        
        if target_snippet not in content:
            return "Erreur : Snippet cible introuvable (vérifie l'indentation)."
            
        if content.count(target_snippet) > 1:
            return "Erreur : Snippet non unique."
            
        new_content = content.replace(target_snippet, replacement_snippet)
        path.write_text(new_content, encoding="utf-8")
        
        return "Succès : Modification appliquée."
    except ValueError as ve:
        return str(ve)
    except Exception as e:
        return f"Erreur smart_replace : {str(e)}"