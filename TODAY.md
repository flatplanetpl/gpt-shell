# Dzisiaj do zrobienia - Quick Wins

## ⚡ Zadania na dziś (30 min - 2h każde)

### 1. Walidacja konfiguracji (30 min)
```python
def validate_config():
    required = ['OPENAI_API_KEY']
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"❌ Brakuje: {', '.join(missing)}")
        sys.exit(1)
    print("✅ Konfiguracja OK")
```

### 2. Better error messages (30 min)
```python
class GPTShellError(Exception):
    def __init__(self, message, suggestion=None):
        self.message = message
        self.suggestion = suggestion
        
def handle_error(error):
    print(f"❌ {error.message}")
    if error.suggestion:
        print(f"💡 Spróbuj: {error.suggestion}")
```

### 3. Version command (15 min)
```python
__version__ = "1.0.0"

if "--version" in sys.argv:
    print(f"ChatGPT CLI FS Bridge v{__version__}")
    sys.exit(0)
```

### 4. File size warnings (45 min)
```python
def check_file_size(filepath, max_size=10*1024*1024):  # 10MB
    size = os.path.getsize(filepath)
    if size > max_size:
        print(f"⚠️  Duży plik: {filepath} ({size/1024/1024:.1f}MB)")
        return input("Kontynuować? (y/N): ").lower() == 'y'
    return True
```

### 5. Logging levels (1h)
```python
import logging

def setup_logging():
    level = os.getenv('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
```

### 6. Backup cleanup (1h)
```python
def cleanup_old_backups(days=30):
    backup_dir = ".backup"
    cutoff = time.time() - (days * 24 * 3600)
    
    for file in os.listdir(backup_dir):
        filepath = os.path.join(backup_dir, file)
        if os.path.getctime(filepath) < cutoff:
            os.remove(filepath)
            print(f"🗑️  Usunięto stary backup: {file}")
```

## 🎯 Cel na dziś
Zaimplementować **3-4 zadania** z powyższej listy.

**Sugerowana kolejność:**
1. Version command (najłatwiejsze)
2. Walidacja konfiguracji (krytyczne)  
3. Better error messages (user experience)
4. File size warnings (bezpieczeństwo)

## ✅ Checklist
- [x] Zadanie 1 zaimplementowane i przetestowane ✅ Version command
- [x] Zadanie 2 zaimplementowane i przetestowane ✅ Walidacja konfiguracji
- [x] Zadanie 3 zaimplementowane i przetestowane ✅ Better error messages
- [x] Zadanie 4 zaimplementowane i przetestowane ✅ File size warnings
- [x] Zadanie 5 zaimplementowane i przetestowane ✅ Progress bars
- [ ] Wszystko zacommitowane i wypchnięte
- [ ] TODO.md zaktualizowane (✅ przy zrobionych)

**Czas rzeczywisty:** ~2 godziny (zgodnie z szacunkami!)

## 🎉 Ukończone dzisiaj:
1. **Version command** - `python3 cli_assistant_fs.py --version`
2. **Walidacja konfiguracji** - sprawdzanie API key, WORKDIR, lepsze błędy
3. **Better error messages** - klasy GPTShellError z sugestiami i kodami błędów
4. **File size warnings** - ostrzeżenia przed dużymi plikami z interaktywnym potwierdzeniem
5. **Progress bars** - Rich progress bars dla wszystkich długich operacji:
   - 🔍 **search_text()** - progress bar z liczbą przeszukanych plików
   - 🌳 **list_tree()** - spinner dla głębokich drzew katalogów (>2 poziomy)
   - ✍️  **write_file()** - progress dla dużych plików (>1MB) z backupem
   - 🤖 **API calls** - spinner podczas wywołań OpenAI API
   - 💬 **Streaming** - wskaźniki postępu dla streaming responses
   - 📄 **RAG indexing** - progress bar dla /init z nazwami plików i chunkami

## 🚀 Nowe funkcje Progress Bar:
- **Inteligentne progi** - progress tylko dla operacji, które tego potrzebują
- **Informacyjne opisy** - pokazują co się dzieje i ile zostało
- **Czas wykonania** - TimeElapsedColumn pokazuje ile trwa operacja
- **Spinner vs Bar** - spinner dla nieznanych długości, bar dla znanych
- **Transient vs Persistent** - niektóre znikają, inne zostają jako podsumowanie
- **Kolorowe podsumowania** - ✅ sukces, ⚠️ ostrzeżenia, ❌ błędy
