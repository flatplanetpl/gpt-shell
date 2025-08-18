#!/bin/bash
# Test script to verify working directory behavior

set -e

echo "🧪 Testing GPT Shell working directory behavior..."

# Create test directory
TEST_DIR="/tmp/gpt-shell-workdir-test"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"

echo "📁 Created test directory: $TEST_DIR"

# Go to test directory
cd "$TEST_DIR"
echo "📍 Current directory: $(pwd)"

# Create a test file
echo "test content" > original.txt
echo "✅ Created original.txt"

# Test that gpt-shell uses current directory as WORKDIR
echo "🔍 Testing WORKDIR detection..."
WORKDIR_OUTPUT=$(timeout 2 gpt-shell 2>&1 | grep "WORKDIR:" || echo "timeout")

if [[ "$WORKDIR_OUTPUT" == *"$TEST_DIR"* ]]; then
    echo "✅ WORKDIR correctly set to: $TEST_DIR"
else
    echo "❌ WORKDIR not set correctly. Output: $WORKDIR_OUTPUT"
    exit 1
fi

# Test file operations (if API key is available)
if [ -n "$OPENAI_API_KEY" ]; then
    echo "🔧 Testing file operations..."
    
    # Test creating a file
    python3 -c "
import sys
sys.path.insert(0, '/Users/djarosch/Downloads/temp/gpt/gpt-shell')
from cli_assistant_fs import write_file, list_dir
result = write_file('test_created.txt', 'Created by test')
print('File created at:', result['path'])
files = list_dir('.')
print('Files found:', [f['name'] for f in files['items'] if not f['name'].startswith('.')])
" 2>/dev/null || echo "⚠️  File operations test skipped (no valid API key)"
    
    if [ -f "test_created.txt" ]; then
        echo "✅ File created in correct directory"
        echo "   Content: $(cat test_created.txt)"
    else
        echo "❌ File not created in current directory"
        exit 1
    fi
else
    echo "⚠️  Skipping file operations test (no OPENAI_API_KEY)"
fi

# Cleanup
cd /
rm -rf "$TEST_DIR"
echo "🧹 Cleaned up test directory"

echo "🎉 All tests passed! GPT Shell correctly uses current working directory."
