# app/tools/terminal.py
from langchain_core.tools import tool
from pathlib import Path
import subprocess
import shlex

# Sandbox racine (même logique que fs.py)
BASE_DIR = Path(__file__).resolve().parents[2]
SANDBOX_PATH = BASE_DIR / "PlaygroudForCodingAssistant"
SANDBOX_PATH.mkdir(parents=True, exist_ok=True)

ALLOWED_COMMANDS = {
    "pwd",
    "ls",
    "mkdir",
    "cat",
    "grep",
    "head",
    "tail",
    "touch",
    "echo",
    "cp",
    "mv",
    "rm",
    "rmdir",
    "find",
    "wc",
    "sed",
    "awk",
    "cut",
    "sort",
    "uniq",
    "xargs",
    "printf",
    "basename",
    "dirname",
    "file",
    "stat",
    "date",
    "whoami",
    "uname",
    "curl",
    "wget",
    "tar",
    "zip",
    "unzip",
    "gzip",
    "gunzip",
    "sha256sum",
    "shasum",
    "md5",
    "diff",
    "patch",
    "env",
    "printenv",
    "which",
    "tee",
    "tr",
    "paste",
    "column",
    "yes",
    "sleep",
    "chmod",
    "chown",
    "id",
    "groups",
    "ps",
    "kill",
    "killall",
}

DISALLOWED_TOKENS = {"|", ">", ">>", "<", ";", "&&", "&"}


def _validate_command(command: str) -> list[str]:
    if not command or not command.strip():
        raise ValueError("Commande vide.")

    parts = shlex.split(command)
    if not parts:
        raise ValueError("Commande vide.")

    if any(tok in DISALLOWED_TOKENS for tok in parts):
        raise ValueError("Opérateurs shell interdits (|, >, <, ;, &&, &).")

    cmd = parts[0]
    if cmd not in ALLOWED_COMMANDS:
        raise ValueError(f"Commande non autorisée : {cmd}")

    return parts


@tool
def run_terminal(command: str):
    """
    Exécute une commande terminal simple dans le sandbox.
    Commandes autorisées : pwd, ls, mkdir, cat, grep, head, tail, touch, echo,
    cp, mv, rm, rmdir, find, wc, sed, awk, cut, sort, uniq, xargs, printf,
    basename, dirname, file, stat, date, whoami, uname, curl, wget, tar, zip,
    unzip, gzip, gunzip, sha256sum, shasum, md5, diff, patch, env, printenv,
    which, tee, tr, paste, column, yes, sleep, chmod, chown, id, groups,
    ps, kill, killall.
    Les opérateurs shell sont interdits.
    """
    try:
        parts = _validate_command(command)
        result = subprocess.run(
            parts,
            cwd=str(SANDBOX_PATH),
            capture_output=True,
            text=True,
            check=False,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if result.returncode != 0:
            return f"Erreur (code {result.returncode}): {stderr or stdout}"
        return stdout or "(ok)"
    except Exception as e:
        return f"Erreur exécution : {e}"
