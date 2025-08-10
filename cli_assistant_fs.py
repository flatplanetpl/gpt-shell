#!/usr/bin/env python3
"""
cli_assistant_fs.py — lokalny most: ja ↔ Twój filesystem (macOS/Linux)

Minimalny klient CLI, który pozwala modelowi (np. gpt-5) czytać i edytować pliki
u Ciebie lokalnie przez function calling. Działa w pętli: wpisujesz polecenie,
model odpowiada i w razie potrzeby wywołuje narzędzia (list_dir, read_file, write_file).

Bezpieczeństwo:
- Operujemy domyślnie w katalogu roboczym (WORKDIR). Nie wyjdziemy poza ten katalog.
- Każdy zapis robi kopię *.bak z timestampem.
- Brak wykonywania komend systemowych (domyślnie).

Szybki start (w katalogu projektu):
    python3 -m venv venv
    source venv/bin/activate
    export OPENAI_API_KEY="twoj_klucz_api_openai"
    export WORKDIR="$PWD"
    export OPENAI_MODEL="gpt-5"
    pip install --upgrade pip
    pip install openai rich
    python3 cli_assistant_fs.py
"""

import os
import sys
import json
import shutil
import pathlib
import re
import fnmatch
import subprocess
from datetime import datetime
from typing import List, Dict, Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

try:
    from openai import OpenAI
except Exception:
    print("[ERROR] Pakiet 'openai' nie jest zainstalowany. Zrób: pip install openai rich", file=sys.stderr)
    sys.exit(1)

console = Console()

# Konfiguracja
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5")
WORKDIR = pathlib.Path(os.environ.get("WORKDIR", os.getcwd())).resolve()

# Ścieżka do kontekstu (JSON) — utrzymuje notatki i wytyczne dla sesji CLI
CONTEXT_PATH = os.environ.get("CLIFS_CONTEXT")
if not CONTEXT_PATH:
    CONTEXT_PATH = str(WORKDIR / "clifs.context.json")
CONTEXT_PATH = str(pathlib.Path(CONTEXT_PATH).resolve())

# Stream on/off (domyślnie włączone; wyłącz: export STREAM_PARTIAL=0)
USE_STREAM = os.environ.get("STREAM_PARTIAL", "1") == "1"
# Drugi przebieg: auto-korekta/recenzja i ewentualne zapisy plików (bez gadania)
REVIEW_PASS = os.environ.get("REVIEW_PASS", "1") == "1"

# Limity i budżety (zmniejsz szum)
DEFAULT_MAX_BYTES = int(os.environ.get("MAX_BYTES_PER_READ", "60000"))  # ~60 kB
MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS", "1024"))
MAX_HISTORY_MSGS = int(os.environ.get("MAX_HISTORY_MSGS", "24"))  # system + ostatnie ~24 wpisy

# Twarde bezpieczniki dla komend (wyłączone domyślnie)
ALLOW_SHELL = os.environ.get("ALLOW_SHELL", "0") == "1"  # włącz uruchamianie komend
DEFAULT_CMD_TIMEOUT = int(os.environ.get("CMD_TIMEOUT", "30"))
GIT_AUTOSNAPSHOT = os.environ.get("GIT_AUTOSNAPSHOT", "0") == "1"
# Wzorce ignorowane przy chodzeniu po drzewie (po przecinku)
IGNORE_GLOBS = [s.strip() for s in os.environ.get("IGNORE_GLOBS", ".git,node_modules,dist,build,__pycache__,.venv,venv").split(",") if s.strip()]

client = OpenAI()

# ───────────────────────── Narzędzia FS ─────────────────────────

def within_workdir(p: pathlib.Path) -> pathlib.Path:
    p = (WORKDIR / p).resolve() if not p.is_absolute() else p.resolve()
    if not str(p).startswith(str(WORKDIR)):
        raise PermissionError(f"Ścieżka poza WORKDIR: {p}")
    return p

def list_dir(path: str = ".") -> Dict[str, Any]:
    base = within_workdir(pathlib.Path(path))
    items = []
    for entry in sorted(base.iterdir()):
        try:
            size = entry.stat().st_size
            mtime = int(entry.stat().st_mtime)
        except Exception:
            size = 0
            mtime = 0
        items.append({
            "name": entry.name,
            "is_dir": entry.is_dir(),
            "size": size,
            "mtime": mtime,
        })
    return {"cwd": str(base), "items": items}

def read_file(path: str, max_bytes: int = None) -> Dict[str, Any]:
    p = within_workdir(pathlib.Path(path))
    if not p.exists():
        return {"error": f"Brak pliku: {p}"}
    data = p.read_bytes()
    clipped = False
    max_bytes = max_bytes or DEFAULT_MAX_BYTES
    if len(data) > max_bytes:
        data = data[:max_bytes]
        clipped = True
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
    return {"path": str(p), "content": text, "bytes": len(data), "clipped": clipped}

def write_file(path: str, content: str, create_dirs: bool = True) -> Dict[str, Any]:
    p = within_workdir(pathlib.Path(path))
    if create_dirs:
        p.parent.mkdir(parents=True, exist_ok=True)
    # backup
    if p.exists():
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = p.with_suffix(p.suffix + f".{ts}.bak")
        shutil.copy2(p, backup)
        backup_str = str(backup)
    else:
        backup_str = ""
    p.write_text(content, encoding="utf-8")
    return {"path": str(p), "backup": backup_str, "written": len(content)}

def apply_unified_diff(path: str, unified_diff: str) -> Dict[str, Any]:
    # Świadomie ograniczone: zachęcam do pełnego zapisu pliku write_file.
    if not ("\n--- " in unified_diff and "\n+++ " in unified_diff):
        return {"error": "Nieprawidłowy/nieobsługiwany format unified diff."}
    return {"error": "apply_unified_diff jest ograniczone. Wyślij pełny docelowy plik przez write_file."}

# Czytaj plik w kawałkach, żeby nie wpaść w TPM
def read_file_range(path: str, start: int = 0, size: int = None) -> Dict[str, Any]:
    p = within_workdir(pathlib.Path(path))
    if not p.exists():
        return {"error": f"Brak pliku: {p}"}
    size = size or DEFAULT_MAX_BYTES
    try:
        with open(p, "rb") as f:
            f.seek(max(0, start))
            chunk = f.read(max(0, size))
        try:
            text = chunk.decode("utf-8")
        except UnicodeDecodeError:
            text = chunk.decode("utf-8", errors="replace")
        file_size = p.stat().st_size
        next_start = min(file_size, start + len(chunk))
        return {
            "path": str(p), "start": start, "size": len(chunk),
            "next_start": next_start, "file_size": file_size, "content": text
        }
    except Exception as e:
        return {"error": str(e)}

# ───────────────────────── Dodatkowe narzędzia ─────────────────────────

def _should_ignore(path: pathlib.Path) -> bool:
    rel = str(path.relative_to(WORKDIR)) if str(path).startswith(str(WORKDIR)) else path.name
    for pattern in IGNORE_GLOBS:
        if fnmatch.fnmatch(rel, pattern) or any(part == pattern for part in rel.split("/")):
            return True
    return False

def list_tree(root: str = ".", max_depth: int = 3, include_files: bool = True) -> Dict[str, Any]:
    base = within_workdir(pathlib.Path(root))
    out = []
    start_depth = len(base.parts)
    for dirpath, dirnames, filenames in os.walk(base):
        p = pathlib.Path(dirpath)
        depth = len(p.parts) - start_depth
        if depth > max_depth:
            dirnames[:] = []
            continue
        if _should_ignore(p):
            dirnames[:] = []
            continue
        rel = str(p.relative_to(base)) if p != base else "."
        entry = {"path": rel, "dirs": [], "files": []}
        entry["dirs"] = [d for d in dirnames if not _should_ignore(p / d)]
        if include_files:
            entry["files"] = [f for f in filenames if not _should_ignore(p / f)]
        out.append(entry)
    return {"root": str(base), "max_depth": max_depth, "entries": out}

def search_text(pattern: str, path: str = ".", regex: bool = False, max_results: int = 200) -> Dict[str, Any]:
    base = within_workdir(pathlib.Path(path))
    results = []
    compiled = re.compile(pattern) if regex else None
    for dirpath, _, filenames in os.walk(base):
        p = pathlib.Path(dirpath)
        if _should_ignore(p):
            continue
        for name in filenames:
            fp = p / name
            if _should_ignore(fp):
                continue
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if (compiled.search(line) if regex else (pattern in line)):
                    results.append({"file": str(fp.relative_to(base)), "line": i, "text": line.strip()})
                    if len(results) >= max_results:
                        return {"root": str(base), "pattern": pattern, "regex": bool(regex), "results": results, "truncated": True}
    return {"root": str(base), "pattern": pattern, "regex": bool(regex), "results": results, "truncated": False}

def replace_text(path: str, find: str, replace: str, regex: bool = False, dry_run: bool = True) -> Dict[str, Any]:
    p = within_workdir(pathlib.Path(path))
    if not p.exists():
        return {"error": f"Brak pliku: {p}"}
    text = p.read_text(encoding="utf-8", errors="ignore")
    if regex:
        compiled = re.compile(find)
        new_text, count = compiled.subn(replace, text)
    else:
        count = text.count(find)
        new_text = text.replace(find, replace)
    if dry_run:
        return {"path": str(p), "would_change": count}
    if count > 0:
        # backup i zapis
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = p.with_suffix(p.suffix + f".{ts}.bak")
        shutil.copy2(p, backup)
        p.write_text(new_text, encoding="utf-8")
        return {"path": str(p), "replacements": count, "backup": str(backup)}
    return {"path": str(p), "replacements": 0}

def write_files_batch(files: List[Dict[str, str]], create_dirs: bool = True) -> Dict[str, Any]:
    written = []
    for f in files:
        res = write_file(f["path"], f["content"], create_dirs=create_dirs)
        written.append(res)
    return {"written": written}

UNSAFE_TOKENS = {
    "rm -rf", "mkfs", ":(){", "dd if=", ">/dev/sd", "kill -9", "shutdown", "reboot",
    "chmod -R 777", "chown -R /", "mount ", "umount ", "pwsh -c Remove-Item -Recurse -Force"
}

def _is_safe_command(cmd: str) -> bool:
    lower = cmd.strip().lower()
    return not any(tok in lower for tok in UNSAFE_TOKENS)

def run_command(command: str, confirm: bool = False, timeout: int = None, cwd: str = ".") -> Dict[str, Any]:
    if not ALLOW_SHELL:
        return {"error": "Uruchamianie komend wyłączone. Ustaw ALLOW_SHELL=1 jeśli rozumiesz ryzyko."}
    if not confirm:
        return {"error": "Potrzebne 'confirm=true' aby wykonać komendę."}
    if not _is_safe_command(command):
        return {"error": "Komenda została uznana za niebezpieczną i zablokowana."}
    t = timeout or DEFAULT_CMD_TIMEOUT
    base = within_workdir(pathlib.Path(cwd))
    try:
        import shlex
        proc = subprocess.run(
            shlex.split(command),
            cwd=str(base),
            capture_output=True,
            text=True,
            timeout=t,
        )
        return {
            "cwd": str(base),
            "command": command,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-100000:],  # przycinamy
            "stderr": proc.stderr[-100000:],
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Przekroczono timeout {t}s", "command": command}
    except FileNotFoundError:
        return {"error": "Polecenie nie znalezione (sprawdź PATH).", "command": command}
    except Exception as e:
        return {"error": str(e), "command": command}

def git_snapshot(message: str = "snapshot: auto commit") -> Dict[str, Any]:
    """Jeśli repo istnieje, dodaj wszystkie zmiany i zrób commit."""
    repo = WORKDIR / ".git"
    if not repo.exists():
        return {"error": "To nie jest repozytorium git."}
    if not ALLOW_SHELL:
        return {"error": "Wymaga ALLOW_SHELL=1 (używa git)."}
    try:
        # git add -A
        a = run_command("git add -A", confirm=True, cwd=str(WORKDIR))
        if a.get("error"):
            return a
        # commit
        c = run_command(f"git commit -m {json.dumps(message)}", confirm=True, cwd=str(WORKDIR))
        return {"add": a, "commit": c}
    except Exception as e:
        return {"error": str(e)}

# Spec narzędzi (function calling)
TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "Listuj pliki i foldery w katalogu roboczym lub podkatalogu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ścieżka, domyślnie '.'"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Czytaj plik tekstowy (UTF-8) i zwróć jego zawartość.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "max_bytes": {"type": "integer", "minimum": 1024}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file_range",
            "description": "Czytaj plik w kawałku: start + size (domyślnie ~60kB).",
            "parameters": {
                "type":"object",
                "properties": {
                    "path":{"type":"string"},
                    "start":{"type":"integer"},
                    "size":{"type":"integer"}
                },
                "required":["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Zapisz cały plik (UTF-8). Tworzy backup jeśli plik istniał.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "create_dirs": {"type": "boolean"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_tree",
            "description": "Zwróć strukturę katalogów (drzewo) z limitem głębokości i filtrami.",
            "parameters": {
                "type": "object",
                "properties": {
                    "root": {"type": "string", "description": "Punkt startowy, domyślnie '.'"},
                    "max_depth": {"type": "integer", "minimum": 0, "maximum": 20},
                    "include_files": {"type": "boolean"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_text",
            "description": "Szukaj wzorca w plikach (rekurencyjnie). Użyj regex=true dla regexów.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "regex": {"type": "boolean"},
                    "max_results": {"type": "integer", "minimum": 1}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "replace_text",
            "description": "Zamień tekst w jednym pliku. Najpierw dry_run=true aby zobaczyć ile zmian.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "find": {"type": "string"},
                    "replace": {"type": "string"},
                    "regex": {"type": "boolean"},
                    "dry_run": {"type": "boolean"}
                },
                "required": ["path", "find", "replace"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_files_batch",
            "description": "Zapisz wiele plików naraz (każdy tworzy backup jeśli istniał).",
            "parameters": {
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {"type": "object", "required": ["path", "content"], "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}
                    },
                    "create_dirs": {"type": "boolean"}
                },
                "required": ["files"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "apply_unified_diff",
            "description": "Spróbuj zastosować unified diff do wskazanego pliku (ograniczone).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "unified_diff": {"type": "string"}
                },
                "required": ["path", "unified_diff"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Uruchom bezpieczną komendę powłoki w WORKDIR (wymaga ALLOW_SHELL=1 i confirm=true).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "confirm": {"type": "boolean"},
                    "timeout": {"type": "integer", "minimum": 1},
                    "cwd": {"type": "string"}
                },
                "required": ["command", "confirm"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_snapshot",
            "description": "Wykonaj `git add -A` i `git commit -m <msg>` jeśli to repo git (wymaga ALLOW_SHELL=1).",
            "parameters": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_context",
            "description": "Odczytaj bieżący plik kontekstu i jego ścieżkę.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_context",
            "description": "Zapisz pełny plik kontekstu (obiekt JSON).",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "object"}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_context",
            "description": "Częściowa aktualizacja pliku kontekstu (płytkie łączenie).",
            "parameters": {
                "type": "object",
                "properties": {
                    "delta": {"type": "object"}
                },
                "required": ["delta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "Dopisz notatkę (z timestampem) do pliku kontekstu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "note": {"type": "string"}
                },
                "required": ["note"]
            }
        }
    }
]

def dispatch_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if name == "list_dir":
            return list_dir(**args)
        if name == "read_file":
            return read_file(**args)
        if name == "read_file_range":
            return read_file_range(**args)
        if name == "write_file":
            return write_file(**args)
        if name == "list_tree":
            return list_tree(**args)
        if name == "search_text":
            return search_text(**args)
        if name == "replace_text":
            return replace_text(**args)
        if name == "write_files_batch":
            return write_files_batch(**args)
        if name == "apply_unified_diff":
            return apply_unified_diff(**args)
        if name == "run_command":
            return run_command(**args)
        if name == "git_snapshot":
            return git_snapshot(**args)
        if name == "read_context":
            return read_context()
        if name == "write_context":
            return write_context(**args)
        if name == "update_context":
            return update_context(**args)
        if name == "add_note":
            return add_note(**args)
        return {"error": f"Nieznane narzędzie: {name}"}
    except Exception as e:
        return {"error": str(e)}

# ───────────────────────── Kontekst i prompt ─────────────────────────

def _default_context() -> dict:
    return {
        "project": {
            "name": "CLI FS Bridge",
            "goals": [
                "Pracować na plikach lokalnie w WORKDIR z backupami",
                "Utrzymać minimalne ryzyko: brak wykonywania komend domyślnie",
                "Krótko odpowiadać po polsku"
            ],
            "constraints": [
                "Nie używaj patchy; generuj pełne pliki do zapisu",
                "Szanuj IGNORE_GLOBS",
                "Pytaj o dodatkowe pliki tylko gdy konieczne"
            ]
        },
        "instructions": "Bądź zwięzły, techniczny i po polsku. Preferuj write_file nad diff. Zanim coś zmienisz, wczytaj plik read_file.",
        "notes": [
            "Środowisko: macOS, zsh, venv, STREAM_PARTIAL=1, REVIEW_PASS=1",
            "Domyślnie ALLOW_SHELL=0; komendy wyłączone"
        ],
        "ignore_globs": ".git,node_modules,dist,build,__pycache__,.venv,venv",
        "macros": [
            {"name": "audit_nextjs", "prompt": "Przejrzyj config Next.js i Dockerfile; zaproponuj usprawnienia i zapisz poprawki."}
        ]
    }

def ensure_context_file() -> dict:
    p = pathlib.Path(CONTEXT_PATH)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        ctx = _default_context()
        p.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
        return ctx
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        ctx = _default_context()
        p.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
        return ctx

def save_context(ctx: dict) -> None:
    p = pathlib.Path(CONTEXT_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")

def build_system_prompt(ctx: dict) -> str:
    lines = [
        "Jesteś asystentem CLI pracującym w katalogu roboczym użytkownika.",
        "Zanim poprosisz o edycję, wczytaj plik przez read_file.",
        "Przy większych zmianach generuj cały docelowy plik i zapisuj write_file, zamiast diffa.",
        "Dbaj o idempotencję i bezpieczeństwo. Odpowiadaj po polsku, zwięźle."
    ]
    instr = ctx.get("instructions") or ""
    if instr:
        lines.append(f"[Kontekst] {instr}")
    proj = ctx.get("project", {})
    if proj:
        name = proj.get("name") or "Projekt"
        goals = "; ".join(proj.get("goals", []))
        constraints = "; ".join(proj.get("constraints", []))
        if goals:
            lines.append(f"[Projekt: {name}] Cele: {goals}")
        if constraints:
            lines.append(f"[Ograniczenia] {constraints}")
    notes = ctx.get("notes", [])
    if notes:
        lines.append("[Notatki] " + " | ".join(notes[:6]))
    return " ".join([l for l in lines if l])

def read_context() -> dict:
    ctx = ensure_context_file()
    return {"path": CONTEXT_PATH, "context": ctx}

def write_context(content: dict) -> dict:
    if not isinstance(content, dict):
        return {"error": "content musi być obiektem JSON"}
    save_context(content)
    return {"path": CONTEXT_PATH, "status": "saved"}

def update_context(delta: dict) -> dict:
    if not isinstance(delta, dict):
        return {"error": "delta musi być obiektem JSON"}
    ctx = ensure_context_file()
    for k, v in delta.items():
        if isinstance(v, dict) and isinstance(ctx.get(k), dict):
            ctx[k].update(v)
        else:
            ctx[k] = v
    save_context(ctx)
    return {"path": CONTEXT_PATH, "status": "updated", "context": ctx}

def add_note(note: str) -> dict:
    ctx = ensure_context_file()
    notes = ctx.setdefault("notes", [])
    from datetime import datetime as _dt
    ts = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
    notes.append(f"[{ts}] {note}")
    save_context(ctx)
    return {"path": CONTEXT_PATH, "status": "noted", "count": len(notes)}

# ───────────────────────── Model helpers ─────────────────────────

def chat_once(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Jedno wywołanie modelu."""
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS_SPEC,
        tool_choice="auto",
        max_completion_tokens=MAX_OUTPUT_TOKENS,
    )

def _trim_history(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Zostaw system + ostatnie MAX_HISTORY_MSGS wpisów
    if len(messages) <= MAX_HISTORY_MSGS + 1:
        return messages
    head = [m for m in messages if m.get("role") == "system"][:1]
    tail = [m for m in messages if m.get("role") != "system"][-MAX_HISTORY_MSGS:]
    return head + tail

def _with_retry(call, *args, **kwargs):
    # prosty backoff na 429
    import time
    for i in range(5):
        try:
            return call(*args, **kwargs)
        except Exception as e:
            s = str(e)
            if "rate_limit_exceeded" in s or "TPM" in s or "429" in s:
                time.sleep(1.5 * (i + 1))
                continue
            raise
    return call(*args, **kwargs)

def to_assistant_message_with_tool_calls(msg) -> Dict[str, Any]:
    """Zamiana obiektu odpowiedzi SDK na dict assistant z tool_calls dla historii."""
    tool_calls = getattr(msg, "tool_calls", None)
    calls = []
    if tool_calls:
        for tc in tool_calls:
            calls.append({
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments or "{}",
                },
            })
    out = {"role": "assistant", "content": msg.content or ""}
    if calls:
        out["tool_calls"] = calls
    return out

def stream_final_response(messages):
    """
    Streamuj końcową odpowiedź assistant (bez tool_calls).
    Używamy oddzielnego żądania z `stream=True`, żeby drukować treść na żywo.
    """
    try:
        from sys import stdout
        with client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
        ) as stream:
            buf = []
            for event in stream:
                if hasattr(event, "choices") and event.choices:
                    delta = event.choices[0].delta or {}
                    chunk = delta.get("content") or ""
                    if chunk:
                        buf.append(chunk)
                        stdout.write(chunk); stdout.flush()
            print()  # nowa linia po streamie
            return "".join(buf)
    except Exception as e:
        return f"[stream error] {e}"

REVIEW_PROMPT = (
    "Zrób krótki przegląd poprzedniej odpowiedzi asystenta pod kątem jakości i kompletności. "
    "Jeśli potrzebne są zmiany w plikach w WORKDIR (np. poprawki, dopisanie README, refaktor), "
    "zastosuj je WYŁĄCZNIE przez narzędzia write_file lub write_files_batch. "
    "Nie produkuj długiej prozy. Jeżeli nie ma nic do zmiany, odpowiedz po prostu: OK."
)

def review_and_apply(messages: List[Dict[str, Any]]) -> str:
    """Drugi przebieg: poproś model o auto-recenzję i ewentualne zapisy plików.
    Nic nie wypisuje na konsolę, chyba że zwróci błędy narzędzi.
    Zwraca 'OK' albo krótki raport zmian.
    """
    _msgs = list(messages) + [{"role": "user", "content": REVIEW_PROMPT}]

    _msgs = _trim_history(_msgs)
    resp = _with_retry(client.chat.completions.create,
        model=MODEL,
        messages=_msgs,
        tools=TOOLS_SPEC,
        tool_choice="auto",
        max_completion_tokens=MAX_OUTPUT_TOKENS,
    )
    msg = resp.choices[0].message
    applied = []

    while True:
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            _msgs.append(to_assistant_message_with_tool_calls(msg))
            for tc in tool_calls:
                fn = tc.function.name
                args = json.loads(tc.function.arguments or "{}")
                result = dispatch_tool(fn, args)
                _msgs.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result)[:200000],
                })
                if fn in {"write_file", "write_files_batch"}:
                    applied.append({"tool": fn, "result": result})
            _msgs = _trim_history(_msgs)
            resp = _with_retry(client.chat.completions.create,
                model=MODEL,
                messages=_msgs,
                tools=TOOLS_SPEC,
                tool_choice="auto",
                max_completion_tokens=MAX_OUTPUT_TOKENS,
            )
            msg = resp.choices[0].message
            continue
        text = (msg.content or "").strip()
        if applied:
            return f"Zastosowano {len(applied)} zmian przez narzędzia."
        return text if text else "OK"

# ───────────────────────── Pętla czatu ─────────────────────────

def chat_loop() -> None:
    console.print(Panel.fit(f"WORKDIR: [bold]{WORKDIR}[/bold] | MODEL: [bold]{MODEL}[/bold]", title="CLI FS Bridge"))
    ctx = ensure_context_file()
    sys_prompt = build_system_prompt(ctx)
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": sys_prompt},
    ]

    while True:
        try:
            user_in = console.input("[bold green]Ty> [/bold green]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Koniec.[/dim]")
            break
        if not user_in.strip():
            continue
        if user_in.strip() in {":q", ":quit", ":exit"}:
            break

        messages.append({"role": "user", "content": user_in})

        # Pierwsza odpowiedź
        messages = _trim_history(messages)
        resp = _with_retry(chat_once, messages)
        msg = resp.choices[0].message

        while True:
            tool_calls = getattr(msg, "tool_calls", None)

            if tool_calls:
                # 1) Najpierw zapisz assistant z tool_calls do historii (wymóg API)
                messages.append(to_assistant_message_with_tool_calls(msg))

                # 2) Teraz wywołaj narzędzia i dołóż role: tool
                for tc in tool_calls:
                    fn = tc.function.name
                    args = json.loads(tc.function.arguments or "{}")
                    result = dispatch_tool(fn, args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result)[:200000],
                    })

                # 3) Kolejna runda po narzędziach
                messages = _trim_history(messages)
                resp = _with_retry(chat_once, messages)
                msg = resp.choices[0].message
                continue

            # Brak tool_calls: mamy finalną odpowiedź
            if USE_STREAM:
                final_text = stream_final_response(messages)
                messages.append({"role": "assistant", "content": final_text})
            else:
                final_text = msg.content or ""
                messages.append({"role": "assistant", "content": final_text})
                console.print(Markdown(final_text))
            break

        # Opcjonalny drugi przebieg (auto-recenzja i ewentualne zapisy), cicho.
        if REVIEW_PASS:
            try:
                review_report = review_and_apply(messages)
                if review_report and review_report != "OK":
                    console.print(f"[dim]{review_report}[/dim]")
            except Exception as e:
                console.print(f"[dim]Review-pass pominięty: {e}[/dim]")

if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        console.print("[red]Brak zmiennej środowiskowej OPENAI_API_KEY.[/red] Ustaw ją i uruchom ponownie.")
        sys.exit(2)
    try:
        chat_loop()
    except Exception as e:
        console.print(f"[red]Błąd krytyczny:[/red] {e}")
        sys.exit(2)
