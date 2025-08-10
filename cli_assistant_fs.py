#!/usr/bin/env python3
"""
cli_assistant_fs.py — lokalny most: model ↔ filesystem (macOS/Linux)

Co potrafi:
- Czyta/edytuje pliki przez function calling (list_dir, read_file, read_file_range, write_file, list_tree, search_text).
- Retry z backoffem (429/5xx).
- Fallback limitów: max_completion_tokens → max_tokens.
- Licznik tokenów i kosztów po KAŻDEJ turze (cennik z .env).
- DEBUG logi + redakcja (DEBUG_REDACT=1).
- Stream fallback: jeśli org niezweryfikowana do streamingu, przełącza na non‑stream.

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
import re
from datetime import datetime
from typing import List, Dict, Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

try:
    from openai import OpenAI
except Exception:
    print("[ERROR] Zainstaluj: pip install openai rich", file=sys.stderr)
    sys.exit(1)

console = Console()

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

# Cennik: USD per 1M tokens
def _read_price(name: str):
    v = os.environ.get(name)
    try:
        return float(v) if v else None
    except Exception:
        return None

PRICE_IN  = _read_price("OPENAI_INPUT_PRICE_PER_M")   # np. 5.0
PRICE_OUT = _read_price("OPENAI_OUTPUT_PRICE_PER_M")  # np. 15.0
SESSION_ACC = {"p": 0, "c": 0, "cost": 0.0}

CONTEXT_PATH = os.environ.get("CLIFS_CONTEXT") or str(WORKDIR / "clifs.context.json")

# Shell (off domyślnie)
ALLOW_SHELL = os.environ.get("ALLOW_SHELL", "0") == "1"
DEFAULT_CMD_TIMEOUT = int(os.environ.get("CMD_TIMEOUT", "30"))
IGNORE_GLOBS = [s.strip() for s in os.environ.get("IGNORE_GLOBS", ".git,node_modules,dist,build,__pycache__,.venv,venv").split(",") if s.strip()]

client = OpenAI()

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
        log_line = " ".join([f"[{event}]"] + [f"{k}={_pv(v)}" for k, v in fields.items()])
    
    print(log_line)
    
    if DEBUG_FILE:
        try:
            with open(DEBUG_FILE, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception as e:
            print(f"[DEBUG_FILE_ERROR] Nie można zapisać do {DEBUG_FILE}: {e}")

# ── Koszty i usage ─────────────────────────────────────────────────────────────

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
    _dbg("list_tree", root=str(base), entries=len(out))
    return {"root": str(base), "max_depth": max_depth, "entries": out}

def read_file(path: str, max_bytes: int = None) -> Dict[str, Any]:
    p = within_workdir(pathlib.Path(path))
    if not p.exists():
        return {"error": f"Brak pliku: {p}"}
    data = p.read_bytes()
    clipped = False
    max_bytes = min(max_bytes or DEFAULT_MAX_BYTES, DEFAULT_MAX_BYTES)  # hard cap
    if len(data) > max_bytes:
        data = data[:max_bytes]
        clipped = True
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
    _dbg("read_file", path=str(p), bytes=len(text), clipped=clipped)
    return {"path": str(p), "content": text, "bytes": len(data), "clipped": clipped}

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
    if create_dirs:
        p.parent.mkdir(parents=True, exist_ok=True)
    backup_str = ""
    if p.exists():
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = p.with_suffix(p.suffix + f".{ts}.bak")
        shutil.copy2(p, backup)
        backup_str = str(backup)
    p.write_text(content, encoding="utf-8")
    _dbg("write_file", path=str(p), backup=bool(backup_str), bytes=len(content))
    return {"path": str(p), "backup": backup_str, "written": len(content)}

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
                        _dbg("search_text", pattern=pattern, truncated=True, count=len(results))
                        return {"root": str(base), "pattern": pattern, "regex": bool(regex), "results": results, "truncated": True}
    _dbg("search_text", pattern=pattern, truncated=False, count=len(results))
    return {"root": str(base), "pattern": pattern, "regex": bool(regex), "results": results, "truncated": False}

# ── Tools spec ─────────────────────────────────────────────────────────────────

TOOLS_SPEC = [
    {"type":"function","function":{"name":"list_dir","description":"Listuj pliki i foldery.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":[]}}},
    {"type":"function","function":{"name":"read_file","description":"Czytaj plik (UTF-8) z limitem bajtów.","parameters":{"type":"object","properties":{"path":{"type":"string"},"max_bytes":{"type":"integer","minimum":1024}},"required":["path"]}}},
    {"type":"function","function":{"name":"read_file_range","description":"Czytaj fragment pliku: start+size.","parameters":{"type":"object","properties":{"path":{"type":"string"},"start":{"type":"integer"},"size":{"type":"integer"}},"required":["path"]}}},
    {"type":"function","function":{"name":"write_file","description":"Zapisz cały plik (UTF-8).","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"},"create_dirs":{"type":"boolean"}},"required":["path","content"]}}},
    {"type":"function","function":{"name":"list_tree","description":"Zwróć drzewo katalogów.","parameters":{"type":"object","properties":{"root":{"type":"string"},"max_depth":{"type":"integer","minimum":0,"maximum":20},"include_files":{"type":"boolean"}},"required":[]}}},
    {"type":"function","function":{"name":"search_text","description":"Szukaj wzorca w plikach.","parameters":{"type":"object","properties":{"pattern":{"type":"string"},"path":{"type":"string"},"regex":{"type":"boolean"},"max_results":{"type":"integer","minimum":1}},"required":["pattern"]}}},
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
        "Dbaj o idempotencję i bezpieczeństwo. Odpowiadaj po polsku, zwięźle."
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
            with client.chat.completions.create(model=MODEL, messages=messages, stream=True) as stream:
                buf = []
                chunk_count = 0
                for event in stream:
                    chunk_count += 1
                    _dbg("stream_chunk", chunk_num=chunk_count, event=event.model_dump() if hasattr(event, 'model_dump') else str(event))
                    if hasattr(event, "choices") and event.choices:
                        delta = event.choices[0].delta or {}
                        chunk = delta.get("content") or ""
                        if chunk:
                            buf.append(chunk)
                            print(chunk, end="", flush=True)
                print()
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

# ── Pętla czatu ────────────────────────────────────────────────────────────────

def chat_loop() -> None:
    _dbg("app_start", workdir=str(WORKDIR), model=MODEL, debug=DEBUG)
    console.print(Panel.fit(f"WORKDIR: [bold]{WORKDIR}[/bold] | MODEL: [bold]{MODEL}[/bold] | DEBUG: [bold]{int(DEBUG)}[/bold]", title="CLI FS Bridge"))
    ctx = ensure_context_file()
    _dbg("context_loaded", context=ctx)
    sys_prompt = build_system_prompt(ctx)
    messages: List[Dict[str, Any]] = [{"role": "system", "content": sys_prompt}]
    _dbg("initial_messages", messages=messages)

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

        messages.append({"role": "user", "content": user_in})
        _dbg("messages_after_user", count=len(messages))

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
                    _dbg("tool_call_result", function=fn, result=result)
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

if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        console.print("[red]Brak zmiennej środowiskowej OPENAI_API_KEY.[/red] Ustaw ją i uruchom ponownie.")
        sys.exit(2)
    try:
        chat_loop()
    except Exception as e:
        console.print(f"[red]Błąd krytyczny:[/red] {e}")
        sys.exit(2)
