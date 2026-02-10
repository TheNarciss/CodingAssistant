# app/tools/terminal.py
from langchain_core.tools import tool
from pathlib import Path
import subprocess
import shlex
import os
from app.config import SANDBOX_PATH

# --- ÉTAT GLOBAL (Mémoire du dossier courant) ---
# S'assurer que le dossier racine existe
SANDBOX_PATH.mkdir(parents=True, exist_ok=True)

# Au démarrage, on est dans le sandbox
CURRENT_WORKING_DIR = SANDBOX_PATH

# Liste élargie pour un Coding Assistant viable
ALLOWED_COMMANDS = {
    # --- Navigation & Fichiers de base ---
    "pwd", "ls", "cd", 
    "mkdir", "touch", "cp", "mv", "rm", "rmdir", 
    "ln", "readlink", # Liens symboliques
    "find", "locate", "whereis", "which",
    "chmod", "chown", "chgrp", "umask",
    
    # --- Lecture & Manipulation de texte (Indispensable) ---
    "cat", "more", "less", "head", "tail",
    "grep", "egrep", "fgrep",
    "sed", "awk", "cut", "tr", "sort", "uniq", "wc",
    "tee", "echo", "printf", "xargs",
    "diff", "patch", "cmp", # Pour appliquer des fixs
    "jq", "yq", # INDISPENSABLE pour manipuler JSON/YAML sans Python
    "column", "paste", "join", "split", "strings",
    
    # --- Archives & Compression ---
    "tar", "zip", "unzip", "gzip", "gunzip", "bzip2", "bunzip2",
    "xz", "unxz", "7z", "jar",
    
    # --- Développement Python (Complet) ---
    "python", "python3", "python3.10", "python3.11", # Versions spécifiques
    "pip", "pip3", "pipx",
    "venv", "virtualenv",
    "poetry", "pipenv", "conda", "mamba", # Gestionnaires modernes
    "pytest", "pylint", "black", "mypy", "isort", # Qualité de code
    "jupyter", "ipython",
    
    # --- Développement Node/JS ---
    "node", "nodejs",
    "npm", "npx", "yarn", "pnpm",
    "tsc", "eslint", "prettier", # TypeScript & Linting
    
    # --- Compilateurs & Build Tools ---
    "make", "cmake",
    "gcc", "g++", "clang", "clang++",
    "go", "cargo", "rustc", # Go & Rust
    "java", "javac", "mvn", "gradle", # Java
    
    # --- Système & Monitoring ---
    "ps", "pgrep", "pkill", "kill", "killall",
    "top", "htop", "btop", # (En mode batch -b)
    "df", "du", "free", "uptime",
    "lscpu", "lsblk", "lsusb", "lspci",
    "uname", "hostname", "whoami", "id", "groups",
    "date", "cal", "time", "watch",
    "env", "printenv", "export", "alias", # (Alias ne marchera que dans le shell courant)
    
    # --- Réseau & Internet ---
    "curl", "wget", "http", # (httpie)
    "ping", "traceroute", "tracepath",
    "ifconfig", "ip", "netstat", "ss", "nc", # (netcat - attention sécu)
    "dig", "nslookup", "host",
    "ssh-keygen", # Pour générer des clés (pas pour se connecter, ssh est risqué)
    
    # --- Bases de Données (Clients CLI) ---
    "sqlite3",
    "psql", "pg_dump", "pg_restore", # PostgreSQL
    "mysql", "mysqldump", # MySQL/MariaDB
    "mongo", "mongosh", # MongoDB
    "redis-cli", # Redis
    
    # --- DevOps & Git ---
    "git",
    "docker", "docker-compose", # Si le conteneur a accès au socket Docker
    "kubectl", "helm", # Kubernetes
    "terraform", "ansible",
    
    # --- Cryptographie & Hash ---
    "openssl", "base64",
    "md5sum", "sha1sum", "sha256sum", "sha512sum", "shasum",
    "gpg",
    
    # --- Divers ---
    "yes", "sleep", "clear", "history"
}

# On garde l'interdiction des opérateurs complexes pour éviter les injections trop sales
# Mais on peut être plus souple si besoin.
DISALLOWED_TOKENS = {">", "<", "|", ";", "&", "&&"} 

def _validate_command(command: str) -> list[str]:
    if not command or not command.strip():
        raise ValueError("Commande vide.")

    # NOTE : J'ai supprimé le bloc qui interdisait "cd" ici.

    try:
        parts = shlex.split(command)
    except ValueError:
        raise ValueError("Erreur de syntaxe shell.")

    if not parts:
        raise ValueError("Commande vide.")

    # 2. Vérification des tokens interdits
    if any(token in command for token in DISALLOWED_TOKENS):
         raise ValueError(f"Opérateurs shell interdits ({', '.join(DISALLOWED_TOKENS)}). Exécutez une seule commande à la fois.")

    cmd = parts[0]
    
    # 3. Vérification de la commande principale
    if cmd not in ALLOWED_COMMANDS:
        raise ValueError(f"Commande '{cmd}' non autorisée. Commandes dev dispos: python, pip, git, npm, ls, etc.")

    return parts


@tool
def run_terminal(command: str):
    """
    Exécute une commande terminal.
    Supporte 'cd' pour changer de dossier (l'état est conservé).
    Outils Dev autorisés : python, pip, git, npm, ls, cat, grep, etc.
    """
    global CURRENT_WORKING_DIR # On accède à la mémoire globale du dossier

    try:
        # Nettoyage préventif
        command = command.strip()
        parts = _validate_command(command)
        
        # --- GESTION SPÉCIALE DU 'CD' ---
        if parts[0] == "cd":
            if len(parts) < 2:
                # 'cd' tout seul = retour à la racine du sandbox
                target_dir = SANDBOX_PATH
            else:
                # 'cd chemin'
                path_arg = parts[1]
                # Résolution du chemin par rapport au dossier courant
                # .resolve() gère les '..' et les chemins relatifs
                target_dir = (CURRENT_WORKING_DIR / path_arg).resolve()

            # Vérifications de sécurité et d'existence
            if not target_dir.exists():
                return f"Erreur: Le dossier '{target_dir}' n'existe pas."
            if not target_dir.is_dir():
                return f"Erreur: '{target_dir}' n'est pas un dossier."
            
            # Mise à jour de la mémoire
            CURRENT_WORKING_DIR = target_dir
            return f"Dossier courant changé vers : {CURRENT_WORKING_DIR}"

        # --- EXÉCUTION DES AUTRES COMMANDES ---
        result = subprocess.run(
            parts,
            cwd=str(CURRENT_WORKING_DIR), # On utilise le dossier mémorisé !
            capture_output=True,
            text=True,
            check=False,
            timeout=120 # Timeout de sécurité (2min max)
        )
        
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        output = ""
        if stdout:
            output += f"{stdout}"
        if stderr:
            output += f"\n[STDERR]\n{stderr}"
            
        if result.returncode != 0:
            return f"Erreur (code {result.returncode}):\n{output}"
            
        return output or "(commande exécutée avec succès, pas de sortie)"

    except ValueError as ve:
        return f"Erreur de validation : {ve}"
    except subprocess.TimeoutExpired:
        return "Erreur : Timeout de la commande (trop long)."
    except Exception as e:
        return f"Erreur système : {e}"