# 🧠 Context Memory System

**Advanced persistent conversation memory for GPT Shell**

## 🎯 Overview

The Context Memory System provides intelligent, persistent conversation history that survives between sessions. Unlike basic chat history that gets lost when you close the application, Context Memory:

- **Persists conversations** across sessions
- **Intelligently summarizes** old conversations to save tokens
- **Provides relevant context** from previous sessions
- **Tracks project statistics** and costs
- **Manages memory efficiently** with automatic cleanup

## ✨ Key Features

### 🔄 **Persistent Sessions**
- Each conversation session is tracked with unique ID
- Sessions are automatically started/ended
- Statistics tracked per session (tokens, cost, duration)

### 🧠 **Intelligent Context Retrieval**
- Recent conversations automatically loaded on startup
- Context filtered by token limits (default: 2000 tokens)
- Most relevant conversations prioritized

### 📊 **Smart Summarization**
- Old conversations compressed into summaries
- Key topics and decisions extracted
- File operations tracked (created/modified files)
- Significant token savings (typically 60-80% reduction)

### 📈 **Analytics & Statistics**
- Total conversations, tokens, and costs tracked
- Per-project statistics
- Session history and trends
- Performance metrics

## 🚀 Usage

### **Automatic Operation**
Context Memory works automatically - no setup required:

```bash
gpt-shell  # Context automatically loaded from previous sessions
```

### **Manual Commands**

#### View Statistics
```bash
/stats
```
Shows:
- Total conversations in this project
- Total tokens used and estimated costs
- Number of sessions
- First and last conversation dates

#### Create Summary
```bash
/summary                # Last day summary
/summary last_hour      # Last hour summary  
/summary last_week      # Last week summary
```

#### Cleanup Old Data
```bash
/cleanup
```
Removes conversations older than 30 days (after creating summaries)

## 🏗️ Architecture

### **Database Schema**
```sql
-- Conversations table
conversations (
    id, session_id, timestamp, project_path,
    user_message, assistant_message, tool_calls,
    tokens_used, cost
)

-- Sessions table  
sessions (
    session_id, project_path, started_at, ended_at,
    total_turns, total_tokens, total_cost
)

-- Context summaries table
context_summaries (
    id, project_path, period, summary,
    key_topics, important_decisions, 
    created_files, modified_files, tokens_saved
)
```

### **File Structure**
```
.gpt-shell/
├── memory/
│   ├── conversations.db    # SQLite database
│   └── summaries/         # Archived summaries
└── embeddings.db         # RAG embeddings (separate)
```

## 🔧 Configuration

### **Environment Variables**
```bash
# Context memory settings (optional)
CONTEXT_MEMORY_MAX_TOKENS=2000    # Max tokens for context loading
CONTEXT_MEMORY_CLEANUP_DAYS=30    # Days to keep detailed conversations
CONTEXT_MEMORY_SUMMARY_TOKENS=500 # Max tokens per summary
```

### **Per-Project Settings**
Context Memory is automatically scoped to the current working directory (WORKDIR). Each project maintains separate conversation history.

## 💡 Smart Features

### **Context Enhancement**
When you start a new session, Context Memory:

1. **Loads recent context** from previous sessions
2. **Adds context separator** to distinguish old vs new
3. **Respects token limits** to avoid exceeding model limits
4. **Prioritizes relevance** - recent and important conversations first

### **Automatic Summarization**
Old conversations are automatically summarized to save tokens:

```
Original: 1,500 tokens of detailed conversation
Summary: 300 tokens with key points extracted
Savings: 80% token reduction
```

### **Project Awareness**
- Each project directory has separate memory
- Context doesn't leak between different projects
- Statistics and summaries are project-specific

## 📊 Example Usage

### **Starting Fresh**
```bash
cd /my-project
gpt-shell
# No previous context - starts clean
```

### **Returning to Project**
```bash
cd /my-project  
gpt-shell
# Automatically loads: "Here's what we discussed recently..."
```

### **Checking Progress**
```bash
Ty> /stats
📊 Context Memory Stats
Total conversations: 45
Total tokens used: 12,450
Total cost: $0.1245
Sessions: 8
First conversation: 2024-01-15T10:30:00
Last conversation: 2024-01-20T16:45:00
```

### **Getting Summary**
```bash
Ty> /summary last_day
📝 Context Summary (last_day)

Recent activity summary:
- Created authentication system with JWT tokens
- Fixed database connection issues in user.py
- Added comprehensive tests for API endpoints
- Deployed to staging environment successfully

Key topics: python, api, database, authentication, testing
Files created: 8
Tokens saved: 2,340
```

## 🔒 Privacy & Security

### **Local Storage**
- All conversations stored locally in SQLite
- No data sent to external services
- Full control over your conversation history

### **Data Retention**
- Automatic cleanup after configurable period
- Summaries preserved for long-term context
- Manual cleanup available anytime

### **Project Isolation**
- Each project has separate memory space
- No cross-contamination between projects
- Context scoped to working directory

## 🚀 Advanced Use Cases

### **Long-term Projects**
Perfect for projects spanning weeks/months:
- Maintains context across many sessions
- Remembers decisions and rationale
- Tracks evolution of codebase

### **Team Collaboration**
When multiple team members use GPT Shell:
- Shared project context (if sharing .gpt-shell directory)
- Consistent understanding across team members
- Historical decision tracking

### **Learning & Documentation**
Automatically creates project documentation:
- Key decisions and their reasoning
- Evolution of architecture
- Important code changes and why they were made

## 🛠️ Troubleshooting

### **Memory Not Working**
```bash
# Check if tiktoken is installed
pip install tiktoken

# Verify context memory is enabled
gpt-shell  # Should show "MEMORY: ON" in header
```

### **Database Issues**
```bash
# Reset memory database
rm -rf .gpt-shell/memory/
gpt-shell  # Will recreate database
```

### **Performance Issues**
```bash
# Cleanup old conversations
/cleanup

# Or manually limit context
export CONTEXT_MEMORY_MAX_TOKENS=1000
```

## 🔮 Future Enhancements

- **Semantic search** in conversation history
- **Cross-project context** sharing
- **Export/import** conversation history
- **Advanced summarization** with AI models
- **Context visualization** and analytics
- **Integration with git history** for code context

---

**Context Memory makes GPT Shell truly intelligent by remembering your project's history and providing relevant context when you need it most.** 🧠✨
