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

### 🔍 Analiza i audyt kodu

#### Znajdowanie podatności bezpieczeństwa
```
Ty> Przeszukaj projekt pod kątem potencjalnych luk bezpieczeństwa typu SQL injection lub XSS

AI> Analizuję pliki pod kątem bezpieczeństwa...
Znalazłem 3 potencjalne problemy:
1. views.py:45 - Niezabezpieczone zapytanie SQL z user input
2. templates/form.html:12 - Brak escapowania danych użytkownika
3. api.py:89 - Brak walidacji typu Content-Type
[Szczegółowy raport z sugestiami naprawy]
```

#### Analiza złożoności kodu
```
Ty> Znajdź najbardziej skomplikowane funkcje w projekcie i zasugeruj refaktoryzację

AI> Analizuję złożoność cyklomatyczną...
Top 3 najbardziej złożone funkcje:
1. process_payment() - złożoność: 15 (utils/payment.py:234)
2. validate_order() - złożoność: 12 (models/order.py:567) 
3. calculate_discount() - złożoność: 11 (services/pricing.py:89)
[Propozycje refaktoryzacji dla każdej funkcji]
```

### 📝 Automatyczne generowanie kodu

#### Tworzenie testów jednostkowych
```
Ty> Napisz testy jednostkowe dla klasy UserService w services/user.py

AI> Analizuję klasę UserService...
Tworzę plik tests/test_user_service.py z 15 testami pokrywającymi:
- Tworzenie użytkownika
- Walidację email
- Hashowanie hasła
- Obsługę błędów
[Generuje kompletny plik z testami pytest]
```

#### Generowanie CRUD API
```
Ty> Stwórz REST API dla modelu Product z pełnym CRUD

AI> Tworzę endpoint API dla Product...
Generuję:
- routes/product.py - endpoints GET/POST/PUT/DELETE
- schemas/product.py - walidacja Pydantic
- tests/test_product_api.py - testy integracyjne
[Tworzy kompletną strukturę API]
```

### 🛠️ Refaktoryzacja i migracje

#### Migracja z JavaScript na TypeScript
```
Ty> Przekonwertuj wszystkie pliki .js w katalogu components/ na TypeScript

AI> Rozpoczynam migrację do TypeScript...
Znalazłem 12 plików JavaScript.
Konwertuję:
- Button.js → Button.tsx (dodaję typy dla props)
- Modal.js → Modal.tsx (definiuję interfejsy)
- Form.js → Form.tsx (typowanie event handlers)
[Automatyczna konwersja z zachowaniem logiki]
```

#### Modernizacja składni Python
```
Ty> Zaktualizuj kod Python 2 do Python 3 w całym projekcie

AI> Skanuje w poszukiwaniu składni Python 2...
Znalazłem przestarzałe elementy:
- 8x print statements → print()
- 3x .iteritems() → .items()
- 5x xrange → range
- 2x unicode() → str()
[Wykonuje migrację z backupami]
```

### 📊 Analiza projektu i raportowanie

#### Generowanie dokumentacji z kodu
```
Ty> Wygeneruj dokumentację Markdown dla wszystkich klas w module core/

AI> Analizuję moduł core/...
Znalazłem 8 klas, 42 metody publiczne.
Generuję docs/core-api.md:
# Core Module API
## Class: DatabaseConnection
### Methods:
- connect() - Establishes database connection
- execute(query, params) - Executes SQL query
[Pełna dokumentacja z przykładami użycia]
```

#### Analiza zależności
```
Ty> Sprawdź które pakiety w requirements.txt są nieużywane

AI> Analizuję importy w projekcie...
Nieużywane pakiety:
- pandas==1.3.0 (brak importów)
- requests-mock==1.9.3 (tylko w zakomentowanym kodzie)
- python-dotenv==0.19.0 (zastąpione przez os.environ)
Sugeruję usunięcie lub aktualizację requirements.txt
```

### 🐛 Debugging i diagnostyka

#### Analiza logów błędów
```
Ty> Przeanalizuj error.log i znajdź najczęstsze błędy

AI> Analizuję plik error.log (2.3MB, 15432 linii)...
Top 5 błędów:
1. ConnectionTimeout (1823 wystąpień) - głównie między 14:00-15:00
2. KeyError 'user_id' (456 wystąpień) - endpoint /api/profile
3. ValueError invalid literal (234 wystąpienia) - parsowanie daty
4. FileNotFoundError (123 wystąpienia) - brak config.json
5. MemoryError (45 wystąpień) - podczas przetwarzania dużych plików
[Sugestie rozwiązań dla każdego błędu]
```

#### Znajdowanie wycieków pamięci
```
Ty> Sprawdź czy są wycieki pamięci w plikach Python

AI> Skanuje kod pod kątem potencjalnych wycieków...
Znalazłem problematyczne wzorce:
1. data_processor.py:78 - Niezamknięty file handler
2. cache_manager.py:234 - Circular reference w cache
3. worker.py:156 - Global list rosnący bez limitu
[Kod naprawczy dla każdego przypadku]
```

### 🔄 Automatyzacja zadań

#### Bulk rename plików
```
Ty> Zmień nazwy wszystkich plików test_*.py na *_test.py w projekcie

AI> Wyszukuję pliki test_*.py...
Znalazłem 23 pliki do zmiany nazwy:
- test_auth.py → auth_test.py
- test_database.py → database_test.py
- test_api.py → api_test.py
[Wykonuje zmianę nazw z logowaniem]
```

#### Czyszczenie kodu
```
Ty> Usuń wszystkie zakomentowane fragmenty kodu i console.log z projektu

AI> Skanuje pliki w poszukiwaniu martwego kodu...
Znalazłem:
- 67 bloków zakomentowanego kodu
- 23 wywołania console.log
- 12 instrukcji debugger
Tworzę backup przed czyszczeniem...
[Usuwa z zachowaniem historii w .backup/]
```

### 📈 Optymalizacja wydajności

#### Znajdowanie N+1 queries
```
Ty> Sprawdź czy są problemy N+1 w modelach Django

AI> Analizuję modele i views...
Potencjalne problemy N+1:
1. views.py:89 - Post.objects.all() bez select_related('author')
2. serializers.py:45 - Iteracja po comments bez prefetch
3. admin.py:23 - Multiple queries w list_display
[Proponuje użycie select_related/prefetch_related]
```

#### Optymalizacja importów
```
Ty> Zoptymalizuj importy - usuń nieużywane i posortuj

AI> Analizuję importy w 45 plikach Python...
Usuwam 89 nieużywanych importów:
- 23x 'from typing import Optional' (nieużywane)
- 15x 'import json' (nieużywane)
- 8x 'from datetime import datetime' (duplikaty)
Sortuję według konwencji PEP8...
[Reorganizuje importy w całym projekcie]
```

### 🌐 Integracje i API

#### Generowanie klienta API z OpenAPI
```
Ty> Mam plik openapi.yaml - wygeneruj klienta Python

AI> Parsuje specyfikację OpenAPI...
Znalazłem 12 endpoints, generuję:
- client/api.py - klasa główna APIClient
- client/models.py - 8 modeli Pydantic
- client/exceptions.py - custom exceptions
- examples/usage.py - przykłady użycia
[Kompletny klient z type hints]
```

#### Tworzenie webhooków
```
Ty> Dodaj obsługę webhooków dla wydarzeń user.created i order.completed

AI> Tworzę system webhooków...
Generuję:
- webhooks/handlers.py - obsługa wydarzeń
- webhooks/models.py - model WebhookSubscription
- webhooks/sender.py - async wysyłanie z retry
- webhooks/verify.py - weryfikacja podpisów HMAC
[Pełna implementacja z kolejkowaniem]
```

## 💪 Przewaga nad GitHub Copilot/Codex

### 🗂️ Dostęp do lokalnych plików i danych

W przeciwieństwie do GitHub Copilot, który działa tylko w kontekście edytora, CLI FS Bridge ma pełny dostęp do systemu plików w sandboxie.

#### Analiza lokalnych logów produkcyjnych
```
Ty> Mam logi z produkcji w ~/logs/prod-2024-12-15.log (200MB) - znajdź wszystkie błędy 500 i zrób statystyki

AI> Czytam plik ~/logs/prod-2024-12-15.log...
Analizuję 1,245,332 linii logów...

Znalazłem 3,421 błędów HTTP 500:
- 67% - Database connection timeout (głównie 02:00-04:00)
- 23% - Redis cache miss podczas heavy load
- 8% - External API timeout (payment gateway)
- 2% - Out of memory w image processing

Generuję szczegółowy raport: error_analysis_2024-12-15.md
[Tworzy raport z wykresami czasowymi i rekomendacjami]
```

#### Praca z lokalnymi bazami danych
```
Ty> Połącz się z moją lokalną bazą SQLite w ~/data/customers.db i wygeneruj modele Pydantic

AI> Łączę się z ~/data/customers.db...
Znalazłem 8 tabel:
- customers (15 kolumn)
- orders (12 kolumn)
- products (8 kolumn)
...

Generuję models/database.py z modelami Pydantic:
[Tworzy kompletne modele na podstawie rzeczywistej struktury DB]
```

#### Analiza prywatnych konfiguracji
```
Ty> Sprawdź moje wszystkie pliki .env w ~/projects/ i znajdź duplikaty kluczy API

AI> Skanuje katalog ~/projects/ w poszukiwaniu plików .env...
Znalazłem 12 plików .env w różnych projektach.

Duplikaty kluczy API:
- STRIPE_KEY używany w 3 projektach (ten sam klucz!)
- SENDGRID_KEY w 2 projektach
- AWS_ACCESS_KEY w 5 projektach (3 różne klucze)

⚠️ ALERT: Używasz tego samego STRIPE_KEY w produkcji i developmencie!
[Generuje raport bezpieczeństwa z rekomendacjami]
```

### 🔧 Custom Tools - Rozszerzanie możliwości

#### Przykład: Dodanie narzędzia do wykonywania zapytań SQL
```python
# Dodajesz do cli_assistant_fs.py nowe narzędzie:

def execute_sql(query: str, database: str) -> dict:
    """Wykonuje zapytanie SQL na lokalnej bazie"""
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return {"results": results, "row_count": len(results)}

# Rejestrujesz w TOOLS_SPEC
```

Użycie:
```
Ty> Znajdź wszystkich klientów którzy nie złożyli zamówienia od 6 miesięcy

AI> Wykonuję zapytanie SQL na bazie customers.db...
SELECT c.* FROM customers c 
LEFT JOIN orders o ON c.id = o.customer_id 
WHERE o.created_at < date('now', '-6 months') 
OR o.id IS NULL

Znalazłem 342 nieaktywnych klientów.
Generuję:
- inactive_customers.csv - lista do kampanii email
- reactivation_campaign.py - skrypt do automatycznej kampanii
[Tworzy pliki na podstawie rzeczywistych danych z DB]
```

#### Przykład: Integracja z lokalnym Docker
```python
# Custom tool do zarządzania kontenerami:

def docker_control(action: str, container: str) -> dict:
    """Kontroluje lokalne kontenery Docker"""
    import subprocess
    cmd = f"docker {action} {container}"
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return {"output": result.stdout.decode(), "status": result.returncode}
```

Użycie:
```
Ty> Sprawdź logi kontenera z błędem i napraw konfigurację

AI> Sprawdzam status kontenerów Docker...
3 kontenery działają, 1 zatrzymany (api-gateway).

Czytam logi api-gateway:
Error: Cannot connect to Redis at localhost:6379

Analizuję docker-compose.yml...
Problem: kontener api-gateway nie ma linku do redis.

Naprawiam docker-compose.yml:
[Edytuje plik dodając depends_on i link do Redis]

Restartuję kontener...
✅ Kontener api-gateway działa poprawnie!
```

#### Przykład: Web scraping z lokalnym cache
```python
# Custom tool z cache dla web scraping:

def scrape_with_cache(url: str, selector: str) -> dict:
    """Scrapuje stronę z lokalnym cache"""
    cache_file = f"cache/{hashlib.md5(url.encode()).hexdigest()}.html"
    
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            html = f.read()
        print(f"Używam cache dla {url}")
    else:
        response = requests.get(url)
        html = response.text
        with open(cache_file, 'w') as f:
            f.write(html)
    
    soup = BeautifulSoup(html, 'html.parser')
    return {"data": [el.text for el in soup.select(selector)]}
```

Użycie:
```
Ty> Monitoruj ceny 10 produktów z różnych sklepów i powiadom o zmianach

AI> Scrapuję ceny produktów...
- allegro.pl/laptop-dell-xps - 4899 PLN (cache miss, pobieram)
- x-kom.pl/laptop-gaming - 6299 PLN (używam cache)
...

Porównuję z cenami z ostatniego sprawdzenia (prices_history.json):
📉 Spadek ceny: Dell XPS -200 PLN (-4%)
📈 Wzrost ceny: Gaming Laptop +100 PLN (+1.6%)

Aktualizuję prices_history.json
Generuję raport: price_changes_2024-01-15.md
[Tworzy szczegółowy raport ze zmianami i wykresami trendu]
```

### 🔄 Pełna kontrola nad workflow

#### Przykład: Kompleksowy deployment z testami
```
Ty> Przygotuj pełny deployment - testy, build, sprawdzenie secretów, docker, backup

AI> Rozpoczynam kompleksowy proces deployment...

1. Sprawdzam środowisko:
   - Python 3.11 ✅
   - Docker 24.0.7 ✅
   - PostgreSQL 15 ✅

2. Weryfikuję secrety w .env.production:
   - Wszystkie 23 zmienne ustawione ✅
   - Sprawdzam czy klucze są różne od .env.development ✅

3. Uruchamiam testy:
   - Unit tests: 156 passed ✅
   - Integration tests: 42 passed ✅
   - E2E tests: 18 passed ✅

4. Tworzę backup bazy:
   - Dump database: backup_2024_01_15_1430.sql (2.3GB) ✅

5. Buduję Docker image:
   - docker build -t myapp:v2.3.0 ✅
   - Rozmiar: 387MB (zoptymalizowany multi-stage)

6. Sprawdzam logi z ostatniego deployment:
   - Analizuję deployment_history.log
   - Ostatni problem: memory spike podczas migracji
   - Dodaję --max-memory flag do migracji

7. Generuję deployment checklist:
   [Tworzy deployment_checklist_v2.3.0.md z 35 punktami do sprawdzenia]

Wszystko gotowe do deployment! Uruchomić? (wymaga potwierdzenia)
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

Pytania i sugestie: damian@lobsterbrew.pl

---

**Uwaga**: To narzędzie jest w aktywnym rozwoju. Używaj z rozwagą w środowiskach produkcyjnych.
