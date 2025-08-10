# CLI FS Bridge (gpt-5) — z trybem DEBUG

## Start
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
cp .env.example .env && $EDITOR .env
./run.sh
```

## Tryb DEBUG
Włącz: `DEBUG=1`. Format logów: `DEBUG_FORMAT=text|json`. Redakcja treści: `DEBUG_REDACT=1`.
Przykład:
```bash
DEBUG=1 DEBUG_FORMAT=text ./run.sh
# albo
DEBUG=1 DEBUG_FORMAT=json DEBUG_REDACT=1 ./run.sh
```
Co loguje:
- wejście/wyjście do modelu (rozmiary, role, użyty limit `max_completion_tokens` vs `max_tokens`),
- wywołania narzędzi i rozmiary rezultatów,
- przycinanie historii,
- backoff/retry na 429,
- streaming start/koniec.

## TPM/RPM i duże pliki
- `MAX_BYTES_PER_READ` (domyślnie 60000)
- `MAX_OUTPUT_TOKENS` (domyślnie 1024)
- `MAX_HISTORY_MSGS` (domyślnie 24)
Używaj `read_file_range` do dużych plików.

## .env autoload
`run.sh` ładuje `.env` automatycznie. Skopiuj `cp .env.example .env` i uzupełnij.

## Kontekst
`clifs.context.json` jest wczytywany przy starcie. Możesz edytować z sesji narzędziami `read/update/write_context`, `add_note`.
