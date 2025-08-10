# CLI FS Bridge

**Bezpieczny interfejs CLI do integracji modeli AI z lokalnym systemem plików**

CLI FS Bridge to narzędzie pozwalające modelom językowym (LLM) na bezpieczną interakcję z systemem plików poprzez kontrolowane API. Aplikacja tworzy sandboxowane środowisko, w którym AI może czytać, zapisywać i przeszukiwać pliki, zachowując pełną kontrolę bezpieczeństwa.

## 🎯 Główne zastosowania

- **Automatyzacja zadań programistycznych** - AI może analizować kod, generować pliki, refaktoryzować
- **Przetwarzanie dokumentów** - masowe operacje na plikach tekstowych z inteligentną analizą
- **Asystent deweloperski** - interaktywna pomoc przy debugowaniu i rozwoju projektów
- **Analiza kodu** - przeszukiwanie i analiza dużych baz kodu
- **Generowanie raportów** - automatyczne tworzenie dokumentacji na podstawie struktury projektu

## ✨ Kluczowe funkcje

- 🔒 **Sandbox bezpieczeństwa** - wszystkie operacje ograniczone do zdefiniowanego katalogu roboczego
- 🚀 **6 bezpiecznych narzędzi filesystem** - list_dir, read_file, write_file, search_text i więcej
- 🔄 **Inteligentna obsługa błędów** - automatyczne retry z exponential backoff dla rate limits
- 📊 **Śledzenie kosztów** - licznik tokenów i szacowanie kosztów w czasie rzeczywistym
- 🎨 **Bogaty interfejs CLI** - formatowanie Markdown, panele, kolorowanie składni
- 🔍 **Tryb debug** - szczegółowe logi z opcją redakcji wrażliwych danych
- 💾 **Automatyczne backupy** - każda modyfikacja pliku tworzy kopię zapasową

## 🚀 Szybki start

### Wymagania

- Python 3.8+
- Klucz API OpenAI
- macOS lub Linux (Windows z WSL)

### Instalacja

```bash
# Klonowanie repozytorium
git clone https://github.com/yourusername/gpt-shell.git
cd gpt-shell

# Automatyczna konfiguracja
./setup.sh

# Konfiguracja zmiennych środowiskowych
cp .env.example .env
nano .env  # Dodaj swój OPENAI_API_KEY

# Uruchomienie
./run.sh
```

### Konfiguracja ręczna

```bash
# Utworzenie środowiska wirtualnego
python3 -m venv venv
source venv/bin/activate

# Instalacja zależności
pip install --upgrade pip
pip install -r requirements.txt

# Uruchomienie
python cli_assistant_fs.py
```

## ⚙️ Konfiguracja

### Zmienne środowiskowe (.env)

```bash
# Wymagane
OPENAI_API_KEY=sk-...          # Twój klucz API

# Model AI
OPENAI_MODEL=gpt-4             # Domyślnie: gpt-5

# Bezpieczeństwo
WORKDIR=/path/to/safe/dir      # Katalog roboczy (domyślnie: bieżący)
ALLOW_SHELL=0                   # Wykonywanie poleceń shell (0=wyłączone)

# Limity
MAX_BYTES_PER_READ=40000       # Max bajtów na odczyt pliku
MAX_OUTPUT_TOKENS=1536         # Max tokenów odpowiedzi
MAX_HISTORY_MSGS=16            # Max wiadomości w historii

# Debug
DEBUG=0                        # Tryb debug (0/1)
DEBUG_FORMAT=text              # Format logów (text/json)
DEBUG_REDACT=0                 # Redakcja wrażliwych danych (0/1)

# Koszty (USD per 1M tokenów)
OPENAI_INPUT_PRICE_PER_M=5.0   # Cena tokenów wejściowych
OPENAI_OUTPUT_PRICE_PER_M=15.0 # Cena tokenów wyjściowych
```

### Kontekst projektu (clifs.context.json)

```json
{
  "instructions": "Dodatkowe instrukcje dla AI...",
  "project_goals": "Cele projektu...",
  "constraints": "Ograniczenia..."
}
```

## 📚 Dostępne narzędzia

| Narzędzie | Opis | Przykład użycia |
|-----------|------|-----------------|
| `list_dir` | Listuje pliki i katalogi | "Pokaż zawartość katalogu src/" |
| `read_file` | Czyta plik (z limitem bajtów) | "Przeczytaj plik config.py" |
| `read_file_range` | Czyta fragment dużego pliku | "Pokaż linie 100-200 z log.txt" |
| `write_file` | Zapisuje lub nadpisuje plik | "Utwórz plik test.py z kodem..." |
| `list_tree` | Pokazuje drzewo katalogów | "Pokaż strukturę projektu" |
| `search_text` | Szuka wzorca w plikach | "Znajdź wszystkie wystąpienia 'TODO'" |

## 🔒 Bezpieczeństwo

### Mechanizmy ochronne

- **Sandbox WORKDIR** - niemożność wyjścia poza zdefiniowany katalog
- **Path traversal protection** - blokada ataków typu `../../../etc/passwd`
- **Wyłączone polecenia shell** - domyślnie brak możliwości wykonania komend systemowych
- **Limity odczytu** - ochrona przed wyczerpaniem pamięci
- **Automatyczne backupy** - zabezpieczenie przed utratą danych
- **Ignorowanie wrażliwych katalogów** - `.git`, `node_modules`, klucze

### Audyt bezpieczeństwa

Pełny audyt dostępny w pliku [AUDIT_SECURITY_2025.txt](AUDIT_SECURITY_2025.txt)

## 🐛 Tryb Debug

```bash
# Debug w formacie tekstowym
DEBUG=1 DEBUG_FORMAT=text ./run.sh

# Debug w formacie JSON
DEBUG=1 DEBUG_FORMAT=json ./run.sh

# Debug z redakcją danych
DEBUG=1 DEBUG_REDACT=1 ./run.sh
```

## 📖 Przykłady użycia

### Analiza kodu
```
Ty> Przeanalizuj wszystkie pliki Python w projekcie i znajdź potencjalne problemy

AI> Przeszukuję pliki Python...
[Analiza i raport]
```

### Generowanie dokumentacji
```
Ty> Wygeneruj dokumentację API na podstawie plików w src/

AI> Analizuję strukturę API...
[Generuje documentation.md]
```

### Refaktoryzacja
```
Ty> Zamień wszystkie wystąpienia starej funkcji process_data() na nową process_data_v2()

AI> Szukam wystąpień process_data()...
[Wykonuje zamianę z backupami]
```

## 🤝 Wkład w projekt

1. Fork repozytorium
2. Stwórz branch (`git checkout -b feature/AmazingFeature`)
3. Commit zmian (`git commit -m 'Add AmazingFeature'`)
4. Push do branch (`git push origin feature/AmazingFeature`)
5. Otwórz Pull Request

### Zasady contribuowania

- Zachowaj istniejący styl kodu
- Dodaj testy dla nowych funkcji
- Aktualizuj dokumentację
- Przejdź audyt bezpieczeństwa dla zmian krytycznych

## 📝 Licencja

[DO OKREŚLENIA - Sugerowana: MIT lub Apache 2.0]

## ⚠️ Zastrzeżenia

- Narzędzie przeznaczone do użytku w kontrolowanym środowisku
- Nie używaj z niezaufanymi modelami AI
- Regularnie twórz backupy ważnych danych
- Monitoruj zużycie API i koszty

## 🙏 Podziękowania

- OpenAI za API i modele językowe
- Społeczność Rich za bibliotekę formatowania CLI
- Kontrybutorzy i testerzy

## 📧 Kontakt

Pytania i sugestie: [your-email@example.com]

---

**Uwaga**: To narzędzie jest w aktywnym rozwoju. Używaj z rozwagą w środowiskach produkcyjnych.