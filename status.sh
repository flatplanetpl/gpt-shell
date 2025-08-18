#!/bin/bash
# GPT Shell - Installation Status Check

echo "🔍 GPT Shell Installation Status"
echo "================================="

# Sprawdź czy globalny symlink istnieje
if [ -L "/usr/local/bin/gpt-shell" ]; then
    echo "✅ Global command: INSTALLED"
    echo "   Location: /usr/local/bin/gpt-shell"
    echo "   Target: $(readlink /usr/local/bin/gpt-shell)"
else
    echo "❌ Global command: NOT INSTALLED"
fi

# Sprawdź czy wrapper script istnieje
if [ -f "gpt-shell" ]; then
    echo "✅ Wrapper script: EXISTS"
    if [ -x "gpt-shell" ]; then
        echo "   Permissions: EXECUTABLE"
    else
        echo "   Permissions: NOT EXECUTABLE"
    fi
else
    echo "❌ Wrapper script: MISSING"
fi

# Sprawdź virtual environment
if [ -d "venv" ]; then
    echo "✅ Virtual environment: EXISTS"
    if [ -f "venv/bin/activate" ]; then
        echo "   Status: READY"
    else
        echo "   Status: CORRUPTED"
    fi
else
    echo "❌ Virtual environment: MISSING"
fi

# Sprawdź .env file
if [ -f ".env" ]; then
    echo "✅ Configuration file: EXISTS"
    if grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then
        echo "   API Key: CONFIGURED"
    elif grep -q "OPENAI_API_KEY=" .env 2>/dev/null; then
        echo "   API Key: EMPTY (needs configuration)"
    else
        echo "   API Key: MISSING (needs configuration)"
    fi
else
    echo "❌ Configuration file: MISSING"
fi

# Sprawdź czy /usr/local/bin jest w PATH
if [[ ":$PATH:" == *":/usr/local/bin:"* ]]; then
    echo "✅ PATH: /usr/local/bin is in PATH"
else
    echo "⚠️  PATH: /usr/local/bin is NOT in PATH"
fi

# Test funkcjonalności
echo ""
echo "🧪 Functionality Test:"
if command -v gpt-shell &> /dev/null; then
    echo "✅ Command available: YES"
    if gpt-shell --version &> /dev/null; then
        echo "✅ Command working: YES"
        VERSION=$(gpt-shell --version | head -1)
        echo "   Version: $VERSION"
    else
        echo "❌ Command working: NO"
    fi
else
    echo "❌ Command available: NO"
fi

echo ""
echo "📊 Summary:"
if command -v gpt-shell &> /dev/null && gpt-shell --version &> /dev/null; then
    echo "🎉 GPT Shell is properly installed and working!"
    echo ""
    echo "Usage:"
    echo "  gpt-shell              # Start interactive chat"
    echo "  gpt-shell --version    # Show version"
    echo "  gpt-shell --help       # Show help"
else
    echo "❌ GPT Shell installation has issues. Run ./install.sh to fix."
fi
