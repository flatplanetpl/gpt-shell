#!/bin/bash
# GPT Shell - Uninstall Script

set -e

echo "🗑️  Uninstalling GPT Shell..."

# Usuń globalny symlink
if [ -L "/usr/local/bin/gpt-shell" ]; then
    echo "🔗 Removing global symlink..."
    sudo rm /usr/local/bin/gpt-shell
    echo "✅ Global command removed"
else
    echo "ℹ️  Global symlink not found (already removed?)"
fi

# Opcjonalnie usuń virtual environment
read -p "🤔 Do you want to remove the virtual environment? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "venv" ]; then
        echo "📦 Removing virtual environment..."
        rm -rf venv
        echo "✅ Virtual environment removed"
    else
        echo "ℹ️  Virtual environment not found"
    fi
fi

# Opcjonalnie usuń pliki konfiguracyjne
read -p "🤔 Do you want to remove configuration files (.env, .gpt-shell/)? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f ".env" ]; then
        echo "⚙️  Removing .env file..."
        rm .env
    fi
    if [ -d ".gpt-shell" ]; then
        echo "🗄️  Removing .gpt-shell directory..."
        rm -rf .gpt-shell
    fi
    echo "✅ Configuration files removed"
fi

echo ""
echo "✅ GPT Shell uninstalled successfully!"
echo "📁 Project files remain in: $(pwd)"
echo "   You can safely delete this directory if you don't need it anymore."
