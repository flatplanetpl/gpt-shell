# 🚀 CLI Assistant FS - Plan Rozwoju

## Faza 1: Krytyczne funkcjonalności (Tydzień 1)

### 1. Wykonywanie poleceń shell (`run_command`)
**Priorytet:** KRYTYCZNY  
**Czas implementacji:** 2-3h  
**Opis:** Uruchamianie poleceń systemowych z timeout i strumieniowaniem
```python
def run_command(cmd: str, timeout: int = 30, stream: bool = True) -> Dict[str, Any]:
    # Wykorzystać istniejące ALLOW_SHELL i DEFAULT_CMD_TIMEOUT
    # Zwraca: stdout, stderr, exit_code, timed_out
```
**Korzyści:**
- Automatyzacja budowania (npm, pip, make)
- Uruchamianie testów
- Instalacja zależności

### 2. Integracja z Git
**Priorytet:** KRYTYCZNY  
**Czas implementacji:** 3-4h  
**Funkcje:**
- `git_status()` - sprawdzanie stanu repozytorium
- `git_diff(staged: bool = False)` - pokazywanie zmian
- `git_commit(message: str, files: List[str])` - tworzenie commitów
- `git_log(limit: int = 10)` - historia zmian

**Korzyści:**
- Model może commitować wprowadzone zmiany
- Śledzenie historii modyfikacji
- Integracja z workflow developera

### 3. Porównywanie plików (`file_diff`)
**Priorytet:** WYSOKI  
**Czas implementacji:** 2h  
**Opis:** Wizualizacja różnic między plikami lub wersjami
```python
def file_diff(file1: str, file2: str = None, unified: int = 3) -> Dict[str, Any]:
    # file2 = None oznacza porównanie z ostatnim backupem
    # Zwraca: diff w formacie unified, stats zmian
```
**Korzyści:**
- Dokładny podgląd zmian przed zapisem
- Łatwiejszy review modyfikacji
- Możliwość cofania zmian

## Faza 2: Produktywność (Tydzień 2)

### 4. Zarządzanie sesją
**Priorytet:** WYSOKI  
**Czas implementacji:** 3h  
**Funkcje:**
- `save_session(name: str = None)` - zapis historii konwersacji
- `load_session(name: str)` - wznowienie pracy
- `list_sessions()` - lista zapisanych sesji
- `export_history(format: str = "markdown")` - eksport do MD/JSON

**Korzyści:**
- Kontynuacja pracy po przerwie
- Dokumentacja wykonanych zadań
- Współdzielenie kontekstu

### 5. Monitorowanie zmian (`watch_changes`)
**Priorytet:** ŚREDNI  
**Czas implementacji:** 3h  
**Opis:** Śledzenie modyfikacji plików w czasie rzeczywistym
```python
def watch_changes(paths: List[str], callback: str = None) -> Dict[str, Any]:
    # Używa watchdog lub polling
    # Callback = nazwa makra do wykonania przy zmianie
```
**Korzyści:**
- Auto-reload przy zewnętrznych zmianach
- Synchronizacja z IDE
- Triggery dla automatyzacji

## Faza 3: Zaawansowane funkcje (Tydzień 3-4)

### 6. Analiza kodu
**Funkcje:**
- `analyze_dependencies()` - skanowanie package.json, requirements.txt
- `find_todos()` - wyszukiwanie TODO/FIXME
- `count_lines()` - statystyki kodu (LOC, języki)
- `find_duplicates()` - wykrywanie powtórzeń

### 7. Operacje na archiwach
**Funkcje:**
- `zip_create(files: List[str], output: str)`
- `zip_extract(archive: str, destination: str)`
- `tar_operations(action: str, archive: str, files: List[str])`

### 8. Integracja z API
**Funkcje:**
- `web_fetch(url: str, method: str = "GET")`
- `api_request(endpoint: str, data: dict = None)`
- `webhook_notify(url: str, message: str)`

### 9. System makr
**Funkcje:**
- `define_macro(name: str, commands: List[str])`
- `run_macro(name: str, args: dict = None)`
- `chain_commands(commands: List[str])`

### 10. Bezpieczeństwo
**Funkcje:**
- `encrypt_file(path: str, password: str)`
- `decrypt_file(path: str, password: str)`
- `hash_file(path: str, algorithm: str = "sha256")`

## Faza 4: Rozszerzenia (Długoterminowe)

### 11. Bazy danych
- Integracja z SQLite
- Operacje na CSV
- JQ-like queries na JSON

### 12. Monitoring systemu
- Użycie dysku i pamięci
- Informacje o procesach
- Testy sieci

### 13. Współpraca zespołowa
- Udostępnianie snippetów
- Synchronizacja kontekstu
- Wspólne notatki projektu

## Harmonogram implementacji

| Tydzień | Funkcjonalności | Priorytet |
|---------|----------------|-----------|
| 1 | run_command, git operations, file_diff | KRYTYCZNY |
| 2 | session management, watch_changes | WYSOKI |
| 3 | code analysis, archives | ŚREDNI |
| 4 | API integration, macros | ŚREDNI |
| 5+ | security, databases, monitoring | NISKI |

## Metryki sukcesu

- **Redukcja czasu zadań o 50%** dzięki automatyzacji
- **Zero ręcznych operacji git** - wszystko przez CLI
- **100% odtwarzalność sesji** - pełna historia pracy
- **<5s response time** dla wszystkich operacji

## Notatki techniczne

1. **Bezpieczeństwo**: Wszystkie nowe funkcje muszą respektować `within_workdir()`
2. **Kompatybilność**: Zachować wsparcie dla macOS/Linux
3. **Język**: Interfejs i komunikaty po polsku
4. **Limity**: Respektować MAX_BYTES_PER_READ i timeouty
5. **Retry**: Implementować retry logic dla operacji sieciowych

## Pierwsze kroki

```bash
# 1. Utworzyć branch dla nowych funkcji
git checkout -b feature/shell-commands

# 2. Implementować run_command
# 3. Dodać testy jednostkowe
# 4. Dokumentacja w README.md
# 5. PR z opisem zmian
```

---
*Ostatnia aktualizacja: 2025-08-10*