# app/tools/terminal.py
from langchain_core.tools import tool
from pathlib import Path
import subprocess
import shlex
import os
from app.config import SANDBOX_PATH

# S'assurer que le dossier existe
SANDBOX_PATH.mkdir(parents=True, exist_ok=True)

# Liste élargie pour un Coding Assistant viable
ALLOWED_COMMANDS = {
    # --- Navigation & Fichiers de base ---
    "pwd", "ls", "cd", # (cd est géré virtuellement, mais on l'autorise dans la liste pour ne pas bloquer le parser)
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

    # 1. Gestion spécifique pour 'cd' qui ne marche pas avec subprocess
    if command.strip().startswith("cd "):
        raise ValueError("Erreur: La commande 'cd' n'est pas supportée (le terminal est stateless). Utilisez des chemins absolus ou relatifs dans vos autres commandes.")

    try:
        parts = shlex.split(command)
    except ValueError:
        raise ValueError("Erreur de syntaxe shell.")

    if not parts:
        raise ValueError("Commande vide.")

    # 2. Vérification des tokens interdits
    # Note: shlex.split gère mal les pipes s'ils ne sont pas quotés, 
    # donc on check aussi la string brute pour la sécurité
    if any(token in command for token in DISALLOWED_TOKENS):
         raise ValueError(f"Opérateurs shell interdits ({', '.join(DISALLOWED_TOKENS)}). Exécutez une seule commande à la fois.")

    cmd = parts[0]
    
    # 3. Vérification de la commande principale
    if cmd not in ALLOWED_COMMANDS:
        # On peut être plus explicite sur l'erreur
        raise ValueError(f"Commande '{cmd}' non autorisée. Commandes dev dispos: python, pip, git, npm, ls, etc.")

    return parts


@tool
def run_terminal(command: str):
    """
    Exécute une commande terminal.
    Outils Dev autorisés : python, pip, git, npm, ls, cat, grep, etc.
    Limitation : 'cd' ne fonctionne pas (stateless). Utilisez des chemins relatifs depuis la racine.
    """
    try:
        # Nettoyage préventif
        command = command.strip()
        
        parts = _validate_command(command)
        
        # Exécution
        result = subprocess.run(
            parts,
            cwd=str(SANDBOX_PATH), # Tout s'exécute dans le dossier du projet
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