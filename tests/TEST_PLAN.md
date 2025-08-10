# Plan rozszerzonych testów (do implementacji)

Poniżej lista dodatkowych przypadków do pokrycia w kolejnych iteracjach.

## FS i ignorowanie
- _should_ignore: sprawdzenie wszystkich domyślnych IGNORE_GLOBS i ścieżek zagnieżdżonych.
- list_tree: weryfikacja include_files=False, kontrola max_depth na głębokim drzewie, pomijanie ignorowanych folderów.
- list_dir: poprawne sortowanie, obsługa błędów stat() (np. brak uprawnień – do zasymulowania monkeypatchem).

## Odczyt/zapis
- read_file: clipping przy max_bytes (parametr i DEFAULT_MAX_BYTES), poprawne ustawienie "clipped"; dekodowanie błędnych bajtów z errors="replace".
- read_file_range: zakres wykraczający poza koniec pliku; start > file_size; size None (użycie domyślnego limitu).
- write_file: create_dirs=False gdy katalog nie istnieje (powinien rzucić błąd); wielokrotne backupy i format nazwy *.bak z timestampem.

## Wyszukiwanie
- search_text: regex=True z grupami; wieloliniowe pliki; pomijanie binariów; root=podkatalog relatywny.

## Narzędzia i dyspozytor
- dispatch_tool: nieznane narzędzie -> {"error": ...}; poprawna serializacja wyników; TOOLS_SPEC zgodne z dostępnymi funkcjami (nazwy i parametry).

## Retry/backoff
- _is_retriable_error: różne komunikaty (" 503 ", "timeout", "temporarily unavailable"); brak hintu.
- _sleep_backoff: jitter w granicach; clamp do [0.5, 10.0] przy dużych próbach; honorowanie parametru hint.
- with_retry: błąd niere-triable kończy natychmiast; osiągnięty max_attempts podnosi wyjątek; licznik prób i wywołań.

## Kontekst i historia
- ensure_context_file: istniejący plik – brak nadpisania; uszkodzony JSON – fallback; brak katalogu nadrzędnego – automatyczne utworzenie.
- build_system_prompt: zawiera wszystkie bazowe zasady (idempotencja, bezpieczeństwo, język PL).
- _trim_history: dla różnych długości; zachowanie 1 systemowego i N ostatnich; brak systemowego w wejściu – brak błędu.
- to_assistant_message_with_tool_calls: poprawne mapowanie wielu tool_calls; brak tool_calls – brak pola w wyniku.

## Chat/stream (opcjonalnie – z mockami)
- to_assistant_message_with_tool_calls integracja z obiektami podobnymi do OpenAI SDK (tc.id, tc.function.name/arguments).
- stream_final_response: ścieżki błędów i fallback do non-stream (wymaga rozbudowanego mocka – niski priorytet).

## Metryki i koszty (opcjonalnie)
- _update_usage + _print_turn_summary: z mockiem console; akumulacja SESSION_ACC; brak cennika.

## Narzędzia pracy
- pytest, pytest-cov; monkeypatch dla time.sleep i random.uniform; tmp_path jako WORKDIR; izolacja od systemu.
