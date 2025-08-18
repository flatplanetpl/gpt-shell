#!/usr/bin/env python3
"""
Demo Context Memory System

This script demonstrates the advanced context memory capabilities
of GPT Shell, showing how conversations are persisted and recalled.
"""

import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from context_memory import ContextMemoryManager, ConversationTurn
from datetime import datetime

def demo_context_memory():
    """Demonstrate context memory features"""
    
    print("🧠 GPT Shell Context Memory System Demo")
    print("=" * 50)
    
    # Initialize context memory
    workdir = Path.cwd()
    memory = ContextMemoryManager(workdir)
    
    print(f"📁 Working directory: {workdir}")
    print(f"💾 Memory database: {memory.db_path}")
    
    # Start a demo session
    session_id = memory.start_session(str(workdir))
    print(f"🚀 Started session: {session_id}")
    
    # Simulate some conversations
    demo_conversations = [
        {
            "user": "List all Python files in the project",
            "assistant": "I found 3 Python files: cli_assistant_fs.py, context_memory.py, and demo_context_memory.py",
            "tool_calls": [{"function": {"name": "list_dir", "arguments": '{"path": "."}'}}]
        },
        {
            "user": "Create a simple test file",
            "assistant": "I've created test_demo.py with a simple function",
            "tool_calls": [{"function": {"name": "write_file", "arguments": '{"path": "test_demo.py", "content": "def hello():\\n    return \\"Hello World\\""}'}}]
        },
        {
            "user": "What files did we create in this session?",
            "assistant": "In this session, we created test_demo.py with a simple hello function",
            "tool_calls": []
        }
    ]
    
    print("\n💬 Simulating conversations...")
    for i, conv in enumerate(demo_conversations, 1):
        turn = ConversationTurn(
            timestamp=datetime.now().isoformat(),
            user_message=conv["user"],
            assistant_message=conv["assistant"],
            tool_calls=conv["tool_calls"],
            tokens_used=50 + i * 10,  # Simulated token usage
            cost=0.001 * i,  # Simulated cost
            project_path=str(workdir),
            session_id=session_id
        )
        
        memory.save_conversation_turn(turn)
        print(f"  {i}. User: {conv['user'][:50]}...")
        print(f"     Assistant: {conv['assistant'][:50]}...")
    
    # End session
    memory.end_session(session_id)
    print(f"🏁 Ended session: {session_id}")
    
    # Show statistics
    print("\n📊 Project Statistics:")
    stats = memory.get_project_stats(str(workdir))
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Get recent context
    print("\n🔄 Recent Context (for next session):")
    recent = memory.get_recent_context(str(workdir), max_tokens=1000)
    print(f"  Found {len(recent)} recent messages")
    for msg in recent[:2]:  # Show first 2
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')[:60]
        print(f"  {role}: {content}...")
    
    # Create summary
    print("\n📝 Creating Summary...")
    summary = memory.create_summary(str(workdir), "last_day")
    print(f"  Period: {summary.period}")
    print(f"  Summary: {summary.summary[:100]}...")
    print(f"  Key topics: {summary.key_topics}")
    print(f"  Files created: {summary.created_files}")
    print(f"  Tokens saved: {summary.tokens_saved}")
    
    print("\n✅ Demo completed!")
    print("\nTo see this in action:")
    print("1. Run: gpt-shell")
    print("2. Have some conversations")
    print("3. Use commands: /stats, /summary, /cleanup")
    print("4. Exit and restart - your context will be remembered!")

if __name__ == "__main__":
    demo_context_memory()
