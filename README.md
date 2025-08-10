# CLI FS Bridge (gpt-5)

Lokalny most między Twoim terminalem a modelem. Czyta i edytuje pliki w **WORKDIR**, z backupami i bez biegania po systemie.

## Szybki start
```bash
python3 -m venv venv
source venv/bin/activate
cp .env.example .env && $EDITOR .env
./setup.sh
./run.sh
```

## Użyteczne polecenia (w interfejsie "Ty>")
- `pokaż strukturę katalogów do głębokości 2` → `list_tree(root=".", max_depth=2)`
- `przeczytaj src/app.ts` → `read_file(path="src/app.ts")`
- `znajdź NEXTAUTH_URL w projekcie` → `search_text(pattern="NEXTAUTH_URL")`
- `dry-run: zamień w .env.local http://localhost:3000 na https://app.example.com` → `replace_text(..., dry_run=true)`
- `zapisz te pliki naraz` → `write_files_batch([...])`
- `wczytaj 60kB z README_BIG.md od offsetu 0` → `read_file_range(path, start=0, size=60000)`

## Ograniczanie limitów TPM/RPM
Domyślnie włączone:
- `MAX_BYTES_PER_READ` (domyślnie 60000) — maks. bajtów przy `read_file` i domyślny rozmiar kawałka dla `read_file_range`.
- `MAX_OUTPUT_TOKENS` (domyślnie 1024) — górna granica długości odpowiedzi.
- `MAX_HISTORY_MSGS` (domyślnie 24) — historia jest przycinana do ostatnich wpisów.
- Prosty backoff retry na 429/TPM.

Jeśli dostajesz 429 „TPM”, zaostrzaj limity:
```bash
export MAX_BYTES_PER_READ=40000
export MAX_OUTPUT_TOKENS=512
export MAX_HISTORY_MSGS=16
```

## Kontekst sesji (clifs.context.json)
- Plik JSON trzymany obok skryptu (domyślnie `./clifs.context.json`, można nadpisać `CLIFS_CONTEXT`).
- Zawiera `instructions`, `project`, `notes`, `ignore_globs`, `macros`.
- Skrypt wczytuje go przy starcie i dokleja do system promptu.
- Modyfikacja z wnętrza rozmowy przez narzędzia:
  - `read_context()` — odczyt
  - `update_context(delta={...})` — częściowa aktualizacja
  - `write_context(content={...})` — pełny zapis
  - `add_note(note="...")` — dopisz notatkę z timestampem

## Opcjonalnie: komendy powłoki (domyślnie wyłączone)
Włącz **na własne ryzyko**:
```bash
export ALLOW_SHELL=1
export CMD_TIMEOUT=60
```
Potem: `run_command(command="npm run build", confirm=true, timeout=120)`.
Hard-kill jest zablokowany filtrami.

## Zmienne środowiskowe
- `OPENAI_API_KEY` — wymagane
- `OPENAI_MODEL` — np. `gpt-5`
- `WORKDIR` — katalog roboczy (domyślnie bieżący)
- `STREAM_PARTIAL` — `1/0` strumieniowanie finalnej odpowiedzi
- `REVIEW_PASS` — `1/0` drugi przebieg z auto-recenzją i ewentualnym zapisem plików
- `MAX_BYTES_PER_READ` — domyślny limit bajtów przy odczycie
- `MAX_OUTPUT_TOKENS` — maks. długość odpowiedzi
- `MAX_HISTORY_MSGS` — ile wiadomości historii utrzymujemy
- `ALLOW_SHELL` — `1/0` zezwól na komendy powłoki (z filtrami)
- `CMD_TIMEOUT` — timeout dla komend
- `GIT_AUTOSNAPSHOT` — rezerwowe (tu: manualny snapshot przez `git_snapshot`)
- `IGNORE_GLOBS` — lista globów po przecinku, np. `.git,node_modules,dist`
- `CLIFS_CONTEXT` — ścieżka do pliku kontekstu

## Wymagania
- Python 3.10+
- macOS lub Linux
- Pakiety: `openai`, `rich`

## Znane niuanse
- Nie ustawiaj `temperature` dla niektórych modeli — potrafią krzyczeć.
- `apply_unified_diff` jest celowo ograniczone; generuj pełny plik przez `write_file`.
- `stream=True` używamy tylko do finalnej odpowiedzi (narzędzia wymagają kompletnego bloku).
