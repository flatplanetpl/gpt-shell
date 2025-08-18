#!/bin/bash
# GPT Shell - Installation Script

set -e

echo "🚀 Installing GPT Shell globally..."

# Sprawdź czy jesteśmy w właściwym katalogu
if [ ! -f "cli_assistant_fs.py" ]; then
    echo "❌ Error: cli_assistant_fs.py not found. Run this script from the gpt-shell directory."
    exit 1
fi

# Sprawdź czy Python 3 jest dostępny
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not installed."
    exit 1
fi

# Sprawdź czy virtual environment istnieje
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Aktywuj venv i zainstaluj dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Sprawdź czy .env istnieje
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file and add your OPENAI_API_KEY"
fi

# Utwórz wrapper script jeśli nie istnieje
if [ ! -f "gpt-shell" ]; then
    echo "📝 Creating wrapper script..."
    cat > gpt-shell << 'EOF'
#!/bin/bash
# GPT Shell - Global Command Wrapper

# Znajdź prawdziwy katalog instalacji (obsługa symlinków)
if [ -L "${BASH_SOURCE[0]}" ]; then
    # Jeśli to symlink, znajdź prawdziwy plik
    REAL_SCRIPT="$(readlink "${BASH_SOURCE[0]}")"
    SCRIPT_DIR="$(cd "$(dirname "$REAL_SCRIPT")" && pwd)"
else
    # Jeśli to prawdziwy plik
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

# Aktywuj virtual environment jeśli istnieje
if [ -d "$SCRIPT_DIR/venv" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Uruchom aplikację z właściwego katalogu
cd "$SCRIPT_DIR"
exec python3 "$SCRIPT_DIR/cli_assistant_fs.py" "$@"
EOF
    chmod +x gpt-shell
fi

# Utwórz globalny symlink
INSTALL_DIR="$(pwd)"
echo "🔗 Creating global symlink..."

# Sprawdź czy /usr/local/bin istnieje
if [ ! -d "/usr/local/bin" ]; then
    echo "📁 Creating /usr/local/bin directory..."
    sudo mkdir -p /usr/local/bin
fi

# Utwórz symlink
sudo ln -sf "$INSTALL_DIR/gpt-shell" /usr/local/bin/gpt-shell

# Sprawdź czy /usr/local/bin jest w PATH
if [[ ":$PATH:" != *":/usr/local/bin:"* ]]; then
    echo "⚠️  Warning: /usr/local/bin is not in your PATH"
    echo "   Add this line to your ~/.bashrc or ~/.zshrc:"
    echo "   export PATH=\"/usr/local/bin:\$PATH\""
fi

# Test instalacji
echo "🧪 Testing installation..."
if gpt-shell --version > /dev/null 2>&1; then
    echo "✅ Installation successful!"
    echo ""
    echo "🎉 GPT Shell is now available globally as 'gpt-shell'"
    echo ""
    echo "Usage:"
    echo "  gpt-shell              # Start interactive chat"
    echo "  gpt-shell --version    # Show version"
    echo "  gpt-shell --help       # Show help (coming soon)"
    echo ""
    echo "📝 Don't forget to configure your OPENAI_API_KEY in .env file!"
else
    echo "❌ Installation failed. Please check the error messages above."
    exit 1
fi
