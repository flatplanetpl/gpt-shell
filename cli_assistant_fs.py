#!/usr/bin/env python3
"""
cli_assistant_fs.py — lokalny most: model ↔ filesystem (macOS/Linux)

Co potrafi:
- Czyta/edytuje pliki przez function calling (list_dir, read_file, read_file_range, write_file, list_tree, search_text).
- Retry z backoffem (429/5xx).
- Fallback limitów: max_completion_tokens → max_tokens.
- Licznik tokenów i kosztów po KAŻDEJ turze (cennik z .env).
- DEBUG logi + redakcja (DEBUG_REDACT=1).
- Stream fallback: jeśli org niezweryfikowana do streamingu, przełącza na non-stream.
- [NOWE] RAG z embeddingami: /init indeksuje repo do SQLite w .gpt-shell, a przy każdym pytaniu do modelu
  dołączany jest lokalny kontekst z najbardziej podobnych fragmentów.

Szybki start:
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip && pip install -r requirements.txt
    cp .env.example .env && $EDITOR .env
    ./run.sh
"""

import os
import sys
import json
import time
import random
import shutil
import pathlib
import hashlib
import sqlite3
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Ładowanie zmiennych środowiskowych z .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv nie jest wymagane, ale przydatne
    pass

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

try:
    from openai import OpenAI
except Exception:
    print("[ERROR] Zainstaluj: pip install openai rich", file=sys.stderr)
    sys.exit(1)

console = Console()

# ── Progress Bar System ──────────────────────────────────────────────────────

def create_progress() -> Progress:
    """Tworzy skonfigurowany progress bar"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False  # Zostaw widoczny po zakończeniu
    )

def show_spinner_progress(description: str):
    """Context manager dla prostego spinnera bez określonej długości"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True  # Ukryj po zakończeniu
    )

# ── Lepsze obsługiwanie błędów ────────────────────────────────────────────────

class GPTShellError(Exception):
    """Bazowa klasa błędów aplikacji"""
    def __init__(self, message: str, suggestion: str = None, error_code: str = None):
        self.message = message
        self.suggestion = suggestion
        self.error_code = error_code
        super().__init__(message)

class ConfigurationError(GPTShellError):
    """Błędy konfiguracji"""
    pass

class FileOperationError(GPTShellError):
    """Błędy operacji na plikach"""
    pass

class APIError(GPTShellError):
    """Błędy API OpenAI"""
    pass

def handle_error(error: Exception, context: str = ""):
    """Obsługuje błędy z czytelnym komunikatem i sugestiami"""
    if isinstance(error, GPTShellError):
        console.print(f"[red]❌ {error.message}[/red]")
        if error.suggestion:
            console.print(f"[yellow]💡 Spróbuj: {error.suggestion}[/yellow]")
        if error.error_code:
            console.print(f"[dim]Kod błędu: {error.error_code}[/dim]")
    else:
        console.print(f"[red]❌ Nieoczekiwany błąd{' w ' + context if context else ''}: {str(error)}[/red]")
        console.print("[yellow]💡 Spróbuj: Sprawdź logi lub uruchom z DEBUG=1[/yellow]")

# ── Wersja aplikacji ──────────────────────────────────────────────────────────
__version__ = "1.0.0"

# Obsługa argumentu --version
if "--version" in sys.argv:
    console.print(f"[bold green]ChatGPT CLI FS Bridge[/bold green] v{__version__}")
    console.print("🚀 Secure CLI interface for ChatGPT integration with local filesystem")
    sys.exit(0)

# ── Konfiguracja ───────────────────────────────────────────────────────────────

MODEL = os.environ.get("OPENAI_MODEL", "gpt-5")
WORKDIR = pathlib.Path(os.environ.get("WORKDIR", os.getcwd())).resolve()

USE_STREAM = os.environ.get("STREAM_PARTIAL", "0") == "1"
REVIEW_PASS = os.environ.get("REVIEW_PASS", "1") == "1"

DEBUG = os.environ.get("DEBUG", "0") == "1"
DEBUG_FORMAT = os.environ.get("DEBUG_FORMAT", "text")  # text|json
DEBUG_REDACT = os.environ.get("DEBUG_REDACT", "0") == "1"
DEBUG_FILE = os.environ.get("DEBUG_FILE", None)  # ścieżka do pliku z logami

DEFAULT_MAX_BYTES = int(os.environ.get("MAX_BYTES_PER_READ", "40000"))
MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS", "1536"))
MAX_HISTORY_MSGS = int(os.environ.get("MAX_HISTORY_MSGS", "16"))

# Embeddingi / RAG
EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-small")
RAG_ENABLE = os.environ.get("RAG_ENABLE", "1") == "1"
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "8"))
RAG_MAX_CHUNK_CHARS = int(os.environ.get("RAG_MAX_CHUNK_CHARS", "900"))
CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", "1500"))
CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "200"))
EMBED_BATCH = int(os.environ.get("EMBED_BATCH", "96"))
EMBED_MAX_FILE_BYTES = int(os.environ.get("EMBED_MAX_FILE_BYTES", "2000000"))

DATA_DIR = (WORKDIR / ".gpt-shell").resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
EMBED_DB = DATA_DIR / "embeddings.db"

# Shell (off domyślnie)
ALLOW_SHELL = os.environ.get("ALLOW_SHELL", "0") == "1"
DEFAULT_CMD_TIMEOUT = int(os.environ.get("CMD_TIMEOUT", "30"))

IGNORE_GLOBS = [s.strip() for s in os.environ.get("IGNORE_GLOBS", ".git,node_modules,dist,build,__pycache__,.venv,venv,.gpt-shell").split(",") if s.strip()]

try:
    client = OpenAI()
except Exception as e:
    print(f"[ERROR] Nie można zainicjalizować klienta OpenAI: {e}", file=sys.stderr)
    sys.exit(1)

# ── Debug helper ───────────────────────────────────────────────────────────────

def _dbg(event: str, **fields):
    if not DEBUG:
        return
    def _pv(v):
        if DEBUG_REDACT:
            return f"<len={len(str(v))}>"
        if isinstance(v, str):
            t = v.replace("\n", "\\n")
            return t[:200] + ("…" if len(t) > 200 else "")
        try:
            s = json.dumps(v, ensure_ascii=False).replace("\n", "\\n")
            return s[:200] + ("…" if len(s) > 200 else "")
        except Exception:
            return str(v)[:200]

    if DEBUG_FORMAT == "json":
        out = {"ts": datetime.now().isoformat(timespec="seconds"), "event": event}
        out.update({k: _pv(v) for k, v in fields.items()})
        log_line = json.dumps(out, ensure_ascii=False)
    else:
        log_line = " ".join([f"[{event}]", *[f"{k}={_pv(v)}" for k, v in fields.items()]])
    print(log_line)
    if DEBUG_FILE:
        try:
            with open(DEBUG_FILE, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception as e:
            print(f"[DEBUG_FILE_ERROR] Nie można zapisać do {DEBUG_FILE}: {e}")

# ── Koszty i usage ─────────────────────────────────────────────────────────────

def _read_price(name: str):
    v = os.environ.get(name)
    try:
        return float(v) if v else None
    except Exception:
        return None

PRICE_IN  = _read_price("OPENAI_INPUT_PRICE_PER_M")   # np. 5.0
PRICE_OUT = _read_price("OPENAI_OUTPUT_PRICE_PER_M")  # np. 15.0
SESSION_ACC = {"p": 0, "c": 0, "cost": 0.0}

def _cost_for_call(p, c):
    if PRICE_IN is None or PRICE_OUT is None:
        return None
    return (p/1_000_000.0)*PRICE_IN + (c/1_000_000.0)*PRICE_OUT

def _update_usage(turn_acc: Dict[str, int], usage) -> None:
    if not usage:
        return
    try:
        p = int(getattr(usage, "prompt_tokens", 0) or 0)
        c = int(getattr(usage, "completion_tokens", 0) or 0)
    except Exception:
        p = int((usage or {}).get("prompt_tokens", 0) or 0)
        c = int((usage or {}).get("completion_tokens", 0) or 0)
    turn_acc["p"] = turn_acc.get("p", 0) + p
    turn_acc["c"] = turn_acc.get("c", 0) + c

def _print_turn_summary(turn_acc: Dict[str, int], note: str = ""):
    p, c = turn_acc.get("p", 0), turn_acc.get("c", 0)
    cost = _cost_for_call(p, c)
    SESSION_ACC["p"] += p
    SESSION_ACC["c"] += c
    if cost is not None:
        SESSION_ACC["cost"] += cost
    if note:
        console.print(f"[dim]{note}[/dim]")
    if cost is not None:
        console.print(f"[blue]Zużycie (ta tura)[/blue]: {p} in / {c} out tok → ~${cost:.4f} USD")
        console.print(f"[magenta]Suma sesji[/magenta]: {SESSION_ACC['p']} in / {SESSION_ACC['c']} out tok → ~${SESSION_ACC['cost']:.4f} USD")
    else:
        console.print(f"[blue]Zużycie (ta tura)[/blue]: {p} in / {c} out tokenów (brak cennika)")
        console.print(f"[magenta]Suma sesji[/magenta]: {SESSION_ACC['p']} in / {SESSION_ACC['c']} out tokenów")

# ── Retry ──────────────────────────────────────────────────────────────────────

def _is_retriable_error(e: Exception):
    msg = str(e).lower()
    retry_after = 0.0
    m = re.search(r"try again in ([0-9.]+)s", msg)
    if m:
        try:
            retry_after = float(m.group(1))
        except Exception:
            retry_after = 0.0
    retriable = any(s in msg for s in [
        "rate limit", "rate_limit_exceeded",
        "timeout", "temporarily unavailable",
        "service unavailable", "internal server error",
        " 429", " 500", " 502", " 503", " 504"
    ])
    return retriable, retry_after

def _sleep_backoff(attempt: int, base: float = 1.0, jitter: float = 0.25, hint: float = 0.0):
    if hint and hint > 0:
        delay = hint
    else:
        delay = base * (2 ** (attempt - 1))
    delay = delay * (1.0 + random.uniform(-jitter, jitter))
    delay = max(0.5, min(delay, 10.0))
    time.sleep(delay)

def with_retry(call, *args, **kwargs):
    max_attempts = kwargs.pop("max_attempts", 6)
    attempt = 0
    while True:
        attempt += 1
        try:
            return call(*args, **kwargs)
        except Exception as e:
            retriable, hint = _is_retriable_error(e)
            _dbg("retry", attempt=attempt, retriable=retriable, hint=hint, error=str(e)[:160])
            if not retriable or attempt >= max_attempts:
                raise
            _sleep_backoff(attempt, hint=hint)

# ── FS ─────────────────────────────────────────────────────────────────────────

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
        items.append({"name": entry.name, "is_dir": entry.is_dir(), "size": size, "mtime": mtime})
    return {"cwd": str(base), "items": items}

def _should_ignore(path: pathlib.Path) -> bool:
    rel = str(path.relative_to(WORKDIR)) if str(path).startswith(str(WORKDIR)) else path.name
    for pattern in IGNORE_GLOBS:
        if rel == pattern or pattern in rel or any(part == pattern for part in rel.split("/")):
            return True
    return False

def list_tree(root: str = ".", max_depth: int = 3, include_files: bool = True) -> Dict[str, Any]:
    base = within_workdir(pathlib.Path(root))
    out = []
    start_depth = len(base.parts)
    
    # Dla małych operacji nie pokazuj progress bara
    if max_depth <= 2:
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
    else:
        # Dla głębszych drzew pokaż progress
        with show_spinner_progress(f"🌳 Budowanie drzewa katalogów (głębokość: {max_depth})...") as progress:
            task = progress.add_task("Skanowanie...", total=None)
            
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
                
                # Aktualizuj opis co jakiś czas
                if len(out) % 50 == 0:
                    progress.update(task, description=f"Skanowanie... ({len(out)} katalogów)")
        
        console.print(f"[green]✅ Zbudowano drzewo: {len(out)} katalogów[/green]")
    
    _dbg("list_tree", root=str(base), entries=len(out))
    return {"root": str(base), "max_depth": max_depth, "entries": out}

# ── Sprawdzanie rozmiaru plików ───────────────────────────────────────────────

def check_file_size(filepath: pathlib.Path, max_size: int = 10*1024*1024) -> bool:
    """Sprawdza rozmiar pliku i ostrzega przed dużymi plikami"""
    if not filepath.exists():
        return True
        
    size = filepath.stat().st_size
    
    if size > max_size:
        size_mb = size / (1024 * 1024)
        max_mb = max_size / (1024 * 1024)
        
        console.print(f"[yellow]⚠️  Duży plik: {filepath.name} ({size_mb:.1f}MB > {max_mb:.1f}MB)[/yellow]")
        console.print(f"[dim]Pełna ścieżka: {filepath}[/dim]")
        
        # W trybie interaktywnym pytaj użytkownika
        if sys.stdin.isatty():
            response = input("Kontynuować odczyt? (y/N): ").lower().strip()
            return response in ['y', 'yes', 'tak', 't']
        else:
            # W trybie nieinteraktywnym ostrzeż ale kontynuuj
            console.print("[yellow]Tryb nieinteraktywny - kontynuuję odczyt[/yellow]")
            return True
    
    return True

def format_file_size(size_bytes: int) -> str:
    """Formatuje rozmiar pliku w czytelny sposób"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f}KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f}MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.1f}GB"

def read_file(path: str, max_bytes: int = None) -> Dict[str, Any]:
    p = within_workdir(pathlib.Path(path))
    if not p.exists():
        return {"error": f"Brak pliku: {p}"}
    
    # Sprawdź rozmiar pliku przed odczytem
    if not check_file_size(p):
        return {"error": f"Odczyt anulowany przez użytkownika: {p}"}
    
    data = p.read_bytes()
    original_size = len(data)
    clipped = False
    max_bytes = min(max_bytes or DEFAULT_MAX_BYTES, DEFAULT_MAX_BYTES)  # hard cap
    
    if len(data) > max_bytes:
        data = data[:max_bytes]
        clipped = True
        console.print(f"[yellow]⚠️  Plik obcięty z {format_file_size(original_size)} do {format_file_size(max_bytes)}[/yellow]")
    
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
        console.print("[yellow]⚠️  Plik zawiera znaki nie-UTF8, zastąpiono problematyczne znaki[/yellow]")
    
    _dbg("read_file", path=str(p), bytes=len(text), clipped=clipped, original_size=original_size)
    
    result = {
        "path": str(p), 
        "content": text, 
        "bytes": len(data), 
        "original_bytes": original_size,
        "clipped": clipped
    }
    
    if clipped:
        result["clipped_info"] = f"Pokazano {len(data)} z {original_size} bajtów"
    
    return result

def read_file_range(path: str, start: int = 0, size: int = None) -> Dict[str, Any]:
    p = within_workdir(pathlib.Path(path))
    if not p.exists():
        return {"error": f"Brak pliku: {p}"}
    size = min(size or DEFAULT_MAX_BYTES, DEFAULT_MAX_BYTES)  # hard cap
    with open(p, "rb") as f:
        f.seek(max(0, start))
        chunk = f.read(max(0, size))
    try:
        text = chunk.decode("utf-8")
    except UnicodeDecodeError:
        text = chunk.decode("utf-8", errors="replace")
    file_size = p.stat().st_size
    next_start = min(file_size, start + len(chunk))
    _dbg("read_file_range", path=str(p), start=start, size=len(chunk), next_start=next_start, file_size=file_size)
    return {"path": str(p), "start": start, "size": len(chunk), "next_start": next_start, "file_size": file_size, "content": text}

def write_file(path: str, content: str, create_dirs: bool = True) -> Dict[str, Any]:
    p = within_workdir(pathlib.Path(path))
    content_size = len(content.encode('utf-8'))
    
    # Progress bar dla dużych plików (>1MB)
    show_progress = content_size > 1024 * 1024
    
    if create_dirs:
        p.parent.mkdir(parents=True, exist_ok=True)
    
    backup_str = ""
    if p.exists():
        if show_progress:
            with show_spinner_progress("💾 Tworzenie kopii zapasowej...") as progress:
                progress.add_task("Backup...", total=None)
                ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup = p.with_suffix(p.suffix + f".{ts}.bak")
                shutil.copy2(p, backup)
                backup_str = str(backup)
        else:
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = p.with_suffix(p.suffix + f".{ts}.bak")
            shutil.copy2(p, backup)
            backup_str = str(backup)
    
    if show_progress:
        with show_spinner_progress(f"✍️  Zapisywanie pliku ({format_file_size(content_size)})...") as progress:
            progress.add_task("Zapis...", total=None)
            p.write_text(content, encoding="utf-8")
        console.print(f"[green]✅ Zapisano {format_file_size(content_size)} do {p.name}[/green]")
    else:
        p.write_text(content, encoding="utf-8")
    
    _dbg("write_file", path=str(p), backup=bool(backup_str), bytes=len(content))
    return {
        "path": str(p), 
        "backup": backup_str, 
        "written": len(content),
        "size_formatted": format_file_size(content_size)
    }

def search_text(pattern: str, path: str = ".", regex: bool = False, max_results: int = 200) -> Dict[str, Any]:
    base = within_workdir(pathlib.Path(path))
    results = []
    compiled = re.compile(pattern) if regex else None
    
    # Najpierw zlicz wszystkie pliki do przeszukania
    all_files = []
    for dirpath, _, filenames in os.walk(base):
        p = pathlib.Path(dirpath)
        if _should_ignore(p):
            continue
        for name in filenames:
            fp = p / name
            if not _should_ignore(fp):
                all_files.append(fp)
    
    if not all_files:
        return {"root": str(base), "pattern": pattern, "regex": bool(regex), "results": [], "truncated": False}
    
    # Progress bar dla przeszukiwania
    with create_progress() as progress:
        task = progress.add_task(
            f"🔍 Przeszukiwanie {len(all_files)} plików dla '{pattern}'...", 
            total=len(all_files)
        )
        
        for fp in all_files:
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(text.splitlines(), 1):
                    if (compiled.search(line) if regex else (pattern in line)):
                        results.append({
                            "file": str(fp.relative_to(base)), 
                            "line": i, 
                            "text": line.strip()
                        })
                        if len(results) >= max_results:
                            progress.update(task, completed=len(all_files))  # Zakończ progress
                            console.print(f"[yellow]⚠️  Znaleziono więcej niż {max_results} wyników, obcinanie...[/yellow]")
                            _dbg("search_text", pattern=pattern, truncated=True, count=len(results))
                            return {
                                "root": str(base), 
                                "pattern": pattern, 
                                "regex": bool(regex), 
                                "results": results, 
                                "truncated": True,
                                "files_searched": len(all_files)
                            }
            except Exception as e:
                _dbg("search_text_error", file=str(fp), error=str(e))
                continue
            finally:
                progress.advance(task)
    
    console.print(f"[green]✅ Przeszukano {len(all_files)} plików, znaleziono {len(results)} wyników[/green]")
    _dbg("search_text", pattern=pattern, truncated=False, count=len(results))
    return {
        "root": str(base), 
        "pattern": pattern, 
        "regex": bool(regex), 
        "results": results, 
        "truncated": False,
        "files_searched": len(all_files)
    }

# ── Tools spec ─────────────────────────────────────────────────────────────────

TOOLS_SPEC = [
    {"type":"function","function":{"name":"list_dir","description":"Listuj pliki i foldery.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":[]}}},
    {"type":"function","function":{"name":"read_file","description":"Czytaj plik (UTF-8) z limitem bajtów.","parameters":{"type":"object","properties":{"path":{"type":"string"},"max_bytes":{"type":"integer","minimum":1024}},"required":["path"]}}},
    {"type":"function","function":{"name":"read_file_range","description":"Czytaj fragment pliku: start+size.","parameters":{"type":"object","properties":{"path":{"type":"string"},"start":{"type":"integer"},"size":{"type":"integer"}},"required":["path"]}}},
    {"type":"function","function":{"name":"write_file","description":"Zapisz cały plik (UTF-8).","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"},"create_dirs":{"type":"boolean"}},"required":["path","content"]}}},
    {"type":"function","function":{"name":"list_tree","description":"Zwróć drzewo katalogów.","parameters":{"type":"object","properties":{"root":{"type":"string"},"max_depth":{"type":"integer","minimum":0,"maximum":20},"include_files":{"type":"boolean"}},"required":[]}}},
    {"type":"function","function":{"name":"search_text","description":"Szukaj wzorca w plikach.","parameters":{"type":"object","properties":{"pattern":{"type":"string"},"path":{"type":"string"},"regex":{"type":"boolean"},"max_results":{"type":"integer","minimum":1}},"required":["pattern"]}}}
]

def dispatch_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    _dbg("tool_call", name=name, args=args)
    try:
        if name == "list_dir": return list_dir(**args)
        if name == "read_file": return read_file(**args)
        if name == "read_file_range": return read_file_range(**args)
        if name == "write_file": return write_file(**args)
        if name == "list_tree": return list_tree(**args)
        if name == "search_text": return search_text(**args)
        return {"error": f"Nieznane narzędzie: {name}"}
    except Exception as e:
        return {"error": str(e)}

# ── System prompt ──────────────────────────────────────────────────────────────

CONTEXT_PATH = os.environ.get("CLIFS_CONTEXT") or str(WORKDIR / "clifs.context.json")

def ensure_context_file() -> dict:
    p = pathlib.Path(CONTEXT_PATH)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        ctx = {"instructions":"Bądź zwięzły, techniczny i po polsku. Preferuj write_file nad diff. Zanim coś zmienisz, wczytaj plik read_file."}
        p.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
        return ctx
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"instructions":"Bądź zwięzły, techniczny i po polsku."}

def build_system_prompt(ctx: dict) -> str:
    parts = [
        "Jesteś asystentem CLI pracującym w katalogu roboczym użytkownika.",
        "Zanim poprosisz o edycję, wczytaj plik przez read_file.",
        "Przy większych zmianach generuj cały docelowy plik i zapisuj write_file, zamiast diffów.",
        "Dbaj o idempotencję i bezpieczeństwo. Odpowiadaj po polsku, zwięźle.",
        "Jeśli dostarczono 'Kontekst lokalny', traktuj go jako priorytetowy materiał źródłowy w odpowiedzi."
    ]
    instr = ctx.get("instructions")
    if instr: parts.append(f"[Kontekst] {instr}")
    sp = " ".join(parts)
    _dbg("system_prompt", length=len(sp))
    return sp

# ── API helpers ────────────────────────────────────────────────────────────────

def _chat_create_with_limits(messages: List[Dict[str, Any]]):
    _dbg("chat_request", model=MODEL, messages_count=len(messages), max_tokens=MAX_OUTPUT_TOKENS)
    if DEBUG:
        _dbg("chat_request_messages", messages=messages)
    
    # Progress bar dla wywołań API
    with show_spinner_progress(f"🤖 Wysyłanie zapytania do {MODEL}...") as progress:
        task = progress.add_task("API call...", total=None)
        
        try:
            _dbg("chat_create_try", param="max_completion_tokens")
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS_SPEC,
                tool_choice="auto",
                max_completion_tokens=MAX_OUTPUT_TOKENS,
            )
            _dbg("chat_response_success", usage=getattr(response, "usage", None))
            if DEBUG:
                _dbg("chat_response_full", response=response.model_dump() if hasattr(response, 'model_dump') else str(response))
            return response
        except Exception as e1:
            s1 = str(e1)
            _dbg("chat_response_error", error=s1)
            if "max_completion_tokens" in s1 or "unsupported parameter" in s1.lower():
                _dbg("chat_create_fallback", to="max_tokens", error=s1[:160])
                progress.update(task, description="Ponowna próba z max_tokens...")
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=TOOLS_SPEC,
                    tool_choice="auto",
                    max_tokens=MAX_OUTPUT_TOKENS,
                )
            _dbg("chat_response_fallback_success", usage=getattr(response, "usage", None))
            if DEBUG:
                _dbg("chat_response_fallback_full", response=response.model_dump() if hasattr(response, 'model_dump') else str(response))
            return response
        raise

def chat_once(messages: List[Dict[str, Any]]):
    return with_retry(_chat_create_with_limits, messages)

def to_assistant_message_with_tool_calls(msg) -> Dict[str, Any]:
    tool_calls = getattr(msg, "tool_calls", None)
    calls = []
    if tool_calls:
        for tc in tool_calls:
            calls.append({"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"}})
    out = {"role": "assistant", "content": msg.content or ""}
    if calls:
        out["tool_calls"] = calls
        _dbg("tool_calls", count=len(calls))
    return out

def stream_final_response(messages: List[Dict[str, Any]]) -> str:
    _dbg("stream_request", model=MODEL, messages_count=len(messages))
    if DEBUG:
        _dbg("stream_request_messages", messages=messages)
    attempts = 0
    while True:
        attempts += 1
        try:
            _dbg("stream_start", attempt=attempts)
            
            # Pokaż spinner podczas nawiązywania połączenia
            console.print(f"[dim]🔄 Łączenie ze streamingiem {MODEL}...[/dim]")
            
            with client.chat.completions.create(model=MODEL, messages=messages, stream=True) as stream:
                buf = []
                chunk_count = 0
                
                # Pokaż że streaming się rozpoczął
                console.print(f"[dim]💬 Odpowiedź {MODEL}:[/dim]")
                
                for event in stream:
                    chunk_count += 1
                    _dbg("stream_chunk", chunk_num=chunk_count, event=event.model_dump() if hasattr(event, 'model_dump') else str(event))
                    if hasattr(event, "choices") and event.choices:
                        delta = event.choices[0].delta or {}
                        chunk = delta.get("content") or ""
                        if chunk:
                            buf.append(chunk)
                            print(chunk, end="", flush=True)
                            
                            # Co 50 chunków pokaż progress
                            if chunk_count % 50 == 0:
                                console.print(f"[dim] ({chunk_count} chunks)[/dim]", end="")
                
                print()  # Nowa linia na końcu
                final_content = "".join(buf)
                _dbg("stream_end", chunks_received=chunk_count, bytes=len(final_content), content=final_content)
                return final_content
        except Exception as e:
            msg = str(e).lower()
            retriable, hint = _is_retriable_error(e)
            _dbg("stream_error", retriable=retriable, error=str(e)[:160])
            if "must be verified to stream" in msg:
                globals()['USE_STREAM'] = False
                try:
                    resp = with_retry(_chat_create_with_limits, messages)
                    text = resp.choices[0].message.content or ""
                    if text: print(text, flush=True)
                    return text
                except Exception as ee:
                    return f"[stream disabled] {e}; [fallback error] {ee}"
            if retriable and attempts < 6:
                _sleep_backoff(attempts, hint=hint); continue
            try:
                resp = with_retry(_chat_create_with_limits, messages)
                text = resp.choices[0].message.content or ""
                if text: print(text, flush=True)
                return text
            except Exception as ee:
                return f"[stream error] {e}; [fallback error] {ee}"

def _trim_history(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if len(messages) <= MAX_HISTORY_MSGS + 1:
        return messages
    head = [m for m in messages if m.get("role") == "system"][:1]
    tail = [m for m in messages if m.get("role") != "system"][-MAX_HISTORY_MSGS:]
    trimmed = head + tail
    _dbg("trim_history", before=len(messages), after=len(trimmed))
    return trimmed

# ── Embeddingi / RAG ───────────────────────────────────────────────────────────

_TEXT_EXTS = {
    ".txt",".md",".mdx",".rst",".csv",".tsv",".json",".ndjson",".yaml",".yml",".toml",".ini",".cfg",
    ".py",".ipynb",".js",".jsx",".ts",".tsx",".mjs",".cjs",".java",".kt",".go",".rs",".c",".cpp",".h",".hpp",".cs",
    ".php",".rb",".pl",".sh",".bash",".zsh",".fish",".ps1",".sql",
    ".html",".htm",".xhtml",".xml",".svg",".css",".scss",".less"
}

def _is_probably_text(path: pathlib.Path) -> bool:
    if path.suffix.lower() in _TEXT_EXTS:
        return True
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
        head.decode("utf-8")
        return True
    except Exception:
        return False

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def _ensure_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(EMBED_DB))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY,
        path TEXT UNIQUE,
        mtime INTEGER,
        size INTEGER,
        sha256 TEXT
    );
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY,
        file_id INTEGER,
        ord INTEGER,
        start INTEGER,
        end INTEGER,
        text TEXT,
        embedding TEXT, -- JSON list[float], znormalizowana
        FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
    );
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_id);")
    return conn

def _chunk_text(s: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[Tuple[int,int,str]]:
    if size <= 0:
        return [(0, len(s), s)]
    chunks = []
    i = 0
    n = len(s)
    while i < n:
        j = min(n, i + size)
        chunk = s[i:j]
        chunks.append((i, j, chunk))
        if j == n:
            break
        i = max(i + size - overlap, i + 1)
    return chunks

def _l2_normalize(v: List[float]) -> List[float]:
    s = sum(x*x for x in v) ** 0.5
    if s == 0:
        return v
    return [x / s for x in v]

def _dot(a: List[float], b: List[float]) -> float:
    m = min(len(a), len(b))
    return sum(a[i]*b[i] for i in range(m))

def _embed_batch(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    def _call():
        resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
        return [d.embedding for d in resp.data]
    try:
        vectors = with_retry(_call)
        return [_l2_normalize(v) for v in vectors]
    except Exception as e:
        _dbg("embed_batch_error", error=str(e)[:200])
        return []

def _indexable_files() -> List[pathlib.Path]:
    out = []
    for dirpath, dirnames, filenames in os.walk(WORKDIR):
        p = pathlib.Path(dirpath)
        if _should_ignore(p):
            dirnames[:] = []
            continue
        for name in filenames:
            fp = p / name
            if _should_ignore(fp):
                continue
            try:
                if fp.stat().st_size > EMBED_MAX_FILE_BYTES:
                    continue
            except Exception:
                continue
            if _is_probably_text(fp):
                out.append(fp)
    return out

def _file_row(conn: sqlite3.Connection, path_abs: pathlib.Path):
    cur = conn.execute("SELECT id, mtime, size, sha256 FROM files WHERE path = ?", (str(path_abs),))
    return cur.fetchone()

def _upsert_file(conn: sqlite3.Connection, path_abs: pathlib.Path, mtime: int, size: int, sha: str) -> int:
    cur = conn.execute("INSERT INTO files(path, mtime, size, sha256) VALUES(?,?,?,?) ON CONFLICT(path) DO UPDATE SET mtime=excluded.mtime, size=excluded.size, sha256=excluded.sha256", (str(path_abs), mtime, size, sha))
    # fetch id
    cur = conn.execute("SELECT id FROM files WHERE path = ?", (str(path_abs),))
    return int(cur.fetchone()[0])

def _delete_chunks_for_file(conn: sqlite3.Connection, file_id: int):
    conn.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))

def _insert_chunks(conn: sqlite3.Connection, file_id: int, chs: List[Tuple[int,int,str]], embs: List[List[float]]):
    assert len(chs) == len(embs)
    rows = []
    for k, ((start, end, text), emb) in enumerate(zip(chs, embs), start=0):
        rows.append((file_id, k, start, end, text, json.dumps(emb)))
    conn.executemany("INSERT INTO chunks(file_id, ord, start, end, text, embedding) VALUES(?,?,?,?,?,?)", rows)

def run_init_index() -> Dict[str, Any]:
    conn = _ensure_db()
    files = _indexable_files()
    indexed_files = 0
    indexed_chunks = 0

    if not files:
        return {"files_indexed": 0, "chunks_indexed": 0, "db": RAG_DB}
    
    # Progress bar dla indeksowania
    with create_progress() as progress:
        task = progress.add_task(
            f"🔍 Indeksowanie {len(files)} plików...", 
            total=len(files)
        )
        
        for fp in files:
            try:
                b = fp.read_bytes()
            except Exception:
                progress.advance(task)
                continue
                
            sha = _sha256_bytes(b)
            st = fp.stat()
            row = _file_row(conn, fp)
            need = True
            if row:
                _, mtime_old, size_old, sha_old = row
                if int(st.st_mtime) == int(mtime_old) and st.st_size == size_old and sha_old == sha:
                    need = False
            if not need:
                progress.advance(task)
                continue

            try:
                text = b.decode("utf-8", errors="ignore")
            except Exception:
                progress.advance(task)
                continue

            chs = _chunk_text(text)
            if not chs:
                progress.advance(task)
                continue

            # Aktualizuj opis z nazwą pliku
            progress.update(task, description=f"📄 Przetwarzanie {fp.name} ({len(chs)} chunków)...")

            # embed in batches
            embeds: List[List[float]] = []
            batch: List[str] = []
            map_idx: List[int] = []
            for idx, (_, _, chunk) in enumerate(chs):
                batch.append(chunk)
                map_idx.append(idx)
                if len(batch) >= EMBED_BATCH:
                    embeds_batch = _embed_batch(batch)
                    if not embeds_batch:
                        _dbg("embed_batch_failed", file=str(fp))
                        progress.advance(task)
                        continue
                    for ii, v in zip(map_idx, embeds_batch):
                        embeds.append(v)
                    batch, map_idx = [], []
            if batch:
                embeds_batch = _embed_batch(batch)
                if embeds_batch:
                    for ii, v in zip(map_idx, embeds_batch):
                        embeds.append(v)
            
            if not embeds:
                _dbg("no_embeddings_generated", file=str(fp))
                progress.advance(task)
                continue

            conn.execute("BEGIN")
            try:
                file_id = _upsert_file(conn, fp, int(st.st_mtime), st.st_size, sha)
                _delete_chunks_for_file(conn, file_id)
                _insert_chunks(conn, file_id, chs, embeds)
                conn.commit()
                indexed_files += 1
                indexed_chunks += len(chs)
            except Exception as e:
                conn.rollback()
                _dbg("index_insert_error", file=str(fp), error=str(e)[:200])
            finally:
                progress.advance(task)

    # sprzątanie opcjonalne: brak
    conn.close()
    
    console.print(f"[green]✅ Indeksowanie zakończone: {indexed_files} plików, {indexed_chunks} chunków[/green]")
    return {"files_indexed": indexed_files, "chunks_indexed": indexed_chunks, "db": str(EMBED_DB)}

def _have_index() -> bool:
    return EMBED_DB.exists() and EMBED_DB.stat().st_size > 0

def _retrieve_context(query: str, top_k: int = RAG_TOP_K) -> List[Dict[str, Any]]:
    if not RAG_ENABLE or not _have_index():
        return []
    embeddings = _embed_batch([query])
    if not embeddings:
        return []
    vec = embeddings[0]
    conn = _ensure_db()
    cur = conn.execute("""
        SELECT files.path, chunks.text, chunks.embedding
        FROM chunks
        JOIN files ON files.id = chunks.file_id
    """)
    scored = []
    for path, text, emb_json in cur.fetchall():
        try:
            emb = json.loads(emb_json)
        except Exception:
            continue
        s = _dot(vec, emb)  # cosine, bo oba L2
        scored.append((s, path, text))
    conn.close()
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for s, path, text in scored[:max(1, top_k)]:
        snippet = text[:RAG_MAX_CHUNK_CHARS]
        out.append({"score": float(s), "path": path, "text": snippet})
    return out

def _format_context_snippets(snips: List[Dict[str, Any]]) -> str:
    # Format lekki i przewidywalny
    lines = ["[Kontekst lokalny] Najbardziej podobne fragmenty z repozytorium:"]
    for i, s in enumerate(snips, 1):
        lines.append(f"\n### {i}. {s['path']}  (score={s['score']:.3f})\n{s['text']}")
    return "\n".join(lines)

# ── Pętla czatu ────────────────────────────────────────────────────────────────

def chat_loop() -> None:
    _dbg("app_start", workdir=str(WORKDIR), model=MODEL, debug=DEBUG)
    console.print(Panel.fit(f"WORKDIR: [bold]{WORKDIR}[/bold] | MODEL: [bold]{MODEL}[/bold] | DEBUG: [bold]{int(DEBUG)}[/bold]\nRAG: [bold]{'ON' if RAG_ENABLE else 'OFF'}[/bold] | DB: [bold]{EMBED_DB}[/bold]", title="CLI FS Bridge + RAG"))

    ctx = ensure_context_file()
    _dbg("context_loaded", context=ctx)
    sys_prompt = build_system_prompt(ctx)
    messages: List[Dict[str, Any]] = [{"role": "system", "content": sys_prompt}]
    _dbg("initial_messages", messages=messages)

    console.print("[dim]Komendy specjalne: /init (zbuduj/odśwież indeks embeddingów w .gpt-shell)[/dim]")

    while True:
        try:
            _dbg("waiting_for_input")
            user_in = console.input("[bold green]Ty> [/bold green]")
            _dbg("user_input", input=user_in)
        except (EOFError, KeyboardInterrupt):
            _dbg("user_exit", reason="EOF_or_KeyboardInterrupt")
            console.print("\n[dim]Koniec.[/dim]"); break

        if not user_in.strip():
            _dbg("empty_input")
            continue
        if user_in.strip() in {":q", ":quit", ":exit"}:
            _dbg("user_exit", reason="quit_command")
            break

        # Komenda: /init
        if user_in.strip().startswith("/init"):
            console.print("[cyan]Buduję indeks embeddingów w .gpt-shell...[/cyan]")
            try:
                stats = run_init_index()
                console.print(f"[green]OK[/green]: plików: {stats['files_indexed']}, chunków: {stats['chunks_indexed']} → [dim]{stats['db']}[/dim]")
            except Exception as e:
                console.print(f"[red]Błąd indeksowania:[/red] {e}")
            continue

        # Normalny czat + ewentualny RAG
        messages.append({"role": "user", "content": user_in})
        _dbg("messages_after_user", count=len(messages))

        # Augmentacja kontekstem
        if RAG_ENABLE and _have_index():
            try:
                snips = _retrieve_context(user_in, top_k=RAG_TOP_K)
            except Exception as e:
                snips = []
                _dbg("rag_retrieve_error", error=str(e)[:200])
            if snips:
                rag_block = _format_context_snippets(snips)
                # Wstrzykujemy jako system, żeby model traktował to jak źródło, nie pytanie
                messages.append({"role": "system", "content": rag_block})
                _dbg("rag_context_added", snippets=len(snips))

        turn_acc = {"p": 0, "c": 0}

        messages = _trim_history(messages)
        _dbg("turn_start", messages_count=len(messages))
        resp = chat_once(messages)
        msg = resp.choices[0].message
        _dbg("first_response", message_content=msg.content, has_tool_calls=bool(getattr(msg, "tool_calls", None)))
        _update_usage(turn_acc, getattr(resp, "usage", None))

        while True:
            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                _dbg("processing_tool_calls", count=len(tool_calls))
                messages.append(to_assistant_message_with_tool_calls(msg))
                for tc in tool_calls:
                    fn = tc.function.name
                    args = json.loads(tc.function.arguments or "{}")
                    _dbg("tool_call_dispatch", function=fn, args=args)
                    result = dispatch_tool(fn, args)
                    _dbg("tool_call_result", function=fn, result=(str(result)[:300] + "…") if len(str(result))>300 else result)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)[:200000]})
                messages = _trim_history(messages)
                _dbg("tool_response_request", messages_count=len(messages))
                resp = chat_once(messages)
                msg = resp.choices[0].message
                _dbg("tool_response", message_content=msg.content, has_more_tool_calls=bool(getattr(msg, "tool_calls", None)))
                _update_usage(turn_acc, getattr(resp, "usage", None))
                continue

            _dbg("final_response_phase", use_stream=USE_STREAM)
            if USE_STREAM:
                final_text = stream_final_response(messages)
                messages.append({"role": "assistant", "content": final_text})
                _print_turn_summary(turn_acc, note="[i]Stream: usage końcówki bywa niedostępne.[/i]")
            else:
                final_text = msg.content or ""
                messages.append({"role": "assistant", "content": final_text})
                _dbg("final_response_non_stream", content=final_text)
                console.print(Markdown(final_text))
                _print_turn_summary(turn_acc)
            _dbg("turn_complete", final_messages_count=len(messages))
            break

# ── Walidacja konfiguracji ────────────────────────────────────────────────────

def validate_config():
    """Waliduje wszystkie wymagane zmienne środowiskowe i konfigurację"""
    errors = []
    warnings = []
    
    # Wymagane zmienne
    required_vars = {
        'OPENAI_API_KEY': 'Klucz API OpenAI (sk-...)'
    }
    
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if not value:
            errors.append(ConfigurationError(
                f"Brakuje {var} - {description}",
                f"Ustaw {var} w pliku .env lub zmiennych środowiskowych",
                "CONFIG_MISSING_VAR"
            ))
        elif var == 'OPENAI_API_KEY':
            if not value.startswith('sk-'):
                errors.append(ConfigurationError(
                    f"{var} powinien zaczynać się od 'sk-'",
                    "Sprawdź czy skopiowałeś pełny klucz z OpenAI Dashboard",
                    "CONFIG_INVALID_API_KEY"
                ))
            elif len(value) < 20:
                errors.append(ConfigurationError(
                    f"{var} wydaje się za krótki",
                    "Sprawdź czy skopiowałeś pełny klucz z OpenAI Dashboard",
                    "CONFIG_SHORT_API_KEY"
                ))
    
    # Opcjonalne zmienne z ostrzeżeniami
    optional_vars = {
        'OPENAI_MODEL': ('gpt-4', 'Model OpenAI'),
        'WORKDIR': (os.getcwd(), 'Katalog roboczy'),
        'MAX_BYTES_PER_READ': ('40000', 'Limit bajtów na odczyt pliku'),
        'MAX_OUTPUT_TOKENS': ('1536', 'Limit tokenów odpowiedzi'),
    }
    
    for var, (default, description) in optional_vars.items():
        value = os.environ.get(var)
        if not value:
            warnings.append(f"⚠️  {var} nie ustawione, używam domyślnej wartości: {default}")
    
    # Sprawdzenie katalogu roboczego
    workdir = os.environ.get('WORKDIR', os.getcwd())
    if not os.path.exists(workdir):
        errors.append(ConfigurationError(
            f"WORKDIR nie istnieje: {workdir}",
            f"Utwórz katalog: mkdir -p {workdir}",
            "CONFIG_WORKDIR_NOT_EXISTS"
        ))
    elif not os.access(workdir, os.R_OK | os.W_OK):
        errors.append(ConfigurationError(
            f"Brak uprawnień do WORKDIR: {workdir}",
            f"Zmień uprawnienia: chmod 755 {workdir}",
            "CONFIG_WORKDIR_NO_PERMISSIONS"
        ))
    
    # Wyświetlenie wyników
    if errors:
        console.print("[red]Błędy konfiguracji:[/red]")
        for error in errors:
            handle_error(error)
        console.print("\n[yellow]Popraw konfigurację w pliku .env i uruchom ponownie.[/yellow]")
        return False
    
    if warnings:
        console.print("[yellow]Ostrzeżenia konfiguracji:[/yellow]")
        for warning in warnings:
            console.print(f"  {warning}")
        console.print()
    
    console.print("✅ [green]Konfiguracja poprawna[/green]")
    return True

if __name__ == "__main__":
    try:
        # Walidacja konfiguracji
        if not validate_config():
            sys.exit(2)
            
        chat_loop()
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Do widzenia![/yellow]")
        sys.exit(0)
    except GPTShellError as e:
        handle_error(e, "główna pętla aplikacji")
        sys.exit(2)
    except Exception as e:
        handle_error(e, "główna pętla aplikacji")
        sys.exit(2)
