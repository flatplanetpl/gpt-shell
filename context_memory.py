#!/usr/bin/env python3
"""
Advanced Context Memory System for GPT Shell

Features:
- Persistent conversation history
- Intelligent summarization
- Context compression
- Session management
- Long-term memory
- Project-specific contexts
"""

import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import tiktoken

@dataclass
class ConversationTurn:
    """Single conversation turn"""
    timestamp: str
    user_message: str
    assistant_message: str
    tool_calls: List[Dict] = None
    tokens_used: int = 0
    cost: float = 0.0
    project_path: str = ""
    session_id: str = ""

@dataclass
class ContextSummary:
    """Compressed context summary"""
    period: str  # "last_hour", "last_day", "last_week"
    summary: str
    key_topics: List[str]
    important_decisions: List[str]
    created_files: List[str]
    modified_files: List[str]
    tokens_saved: int

class ContextMemoryManager:
    """Advanced context memory management"""
    
    def __init__(self, workdir: Path):
        self.workdir = workdir
        self.memory_dir = workdir / ".gpt-shell" / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.memory_dir / "conversations.db"
        self.init_database()
        
        # Tokenizer for counting
        try:
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        except:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def init_database(self):
        """Initialize SQLite database for conversations"""
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                project_path TEXT NOT NULL,
                user_message TEXT NOT NULL,
                assistant_message TEXT NOT NULL,
                tool_calls TEXT,  -- JSON
                tokens_used INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS context_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_path TEXT NOT NULL,
                period TEXT NOT NULL,
                summary TEXT NOT NULL,
                key_topics TEXT,  -- JSON
                important_decisions TEXT,  -- JSON
                created_files TEXT,  -- JSON
                modified_files TEXT,  -- JSON
                tokens_saved INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                project_path TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                total_turns INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0.0
            );
            
            CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
            CREATE INDEX IF NOT EXISTS idx_conversations_project ON conversations(project_path);
            CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp);
        """)
        conn.close()
    
    def start_session(self, project_path: str) -> str:
        """Start new conversation session"""
        session_id = hashlib.md5(f"{project_path}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO sessions (session_id, project_path, started_at)
            VALUES (?, ?, ?)
        """, (session_id, project_path, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        return session_id
    
    def end_session(self, session_id: str):
        """End conversation session"""
        conn = sqlite3.connect(self.db_path)
        
        # Update session stats
        stats = conn.execute("""
            SELECT COUNT(*), SUM(tokens_used), SUM(cost)
            FROM conversations 
            WHERE session_id = ?
        """, (session_id,)).fetchone()
        
        conn.execute("""
            UPDATE sessions 
            SET ended_at = ?, total_turns = ?, total_tokens = ?, total_cost = ?
            WHERE session_id = ?
        """, (datetime.now().isoformat(), stats[0] or 0, stats[1] or 0, stats[2] or 0.0, session_id))
        
        conn.commit()
        conn.close()
    
    def save_conversation_turn(self, turn: ConversationTurn):
        """Save single conversation turn"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO conversations 
            (session_id, timestamp, project_path, user_message, assistant_message, 
             tool_calls, tokens_used, cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            turn.session_id,
            turn.timestamp,
            turn.project_path,
            turn.user_message,
            turn.assistant_message,
            json.dumps(turn.tool_calls) if turn.tool_calls else None,
            turn.tokens_used,
            turn.cost
        ))
        conn.commit()
        conn.close()
    
    def get_recent_context(self, project_path: str, max_tokens: int = 4000) -> List[Dict[str, Any]]:
        """Get recent conversation context within token limit"""
        conn = sqlite3.connect(self.db_path)
        
        # Get recent conversations
        conversations = conn.execute("""
            SELECT user_message, assistant_message, tool_calls, timestamp
            FROM conversations 
            WHERE project_path = ?
            ORDER BY timestamp DESC
            LIMIT 50
        """, (project_path,)).fetchall()
        
        conn.close()
        
        # Build context within token limit
        context = []
        total_tokens = 0
        
        for user_msg, assistant_msg, tool_calls_json, timestamp in conversations:
            # Estimate tokens
            turn_tokens = len(self.tokenizer.encode(user_msg + assistant_msg))
            
            if total_tokens + turn_tokens > max_tokens:
                break
            
            context.insert(0, {"role": "user", "content": user_msg})
            context.insert(1, {"role": "assistant", "content": assistant_msg})
            
            total_tokens += turn_tokens
        
        return context
    
    def create_summary(self, project_path: str, period: str = "last_day") -> ContextSummary:
        """Create intelligent summary of recent conversations"""
        conn = sqlite3.connect(self.db_path)
        
        # Define time range
        if period == "last_hour":
            since = datetime.now() - timedelta(hours=1)
        elif period == "last_day":
            since = datetime.now() - timedelta(days=1)
        elif period == "last_week":
            since = datetime.now() - timedelta(weeks=1)
        else:
            since = datetime.now() - timedelta(days=1)
        
        # Get conversations in period
        conversations = conn.execute("""
            SELECT user_message, assistant_message, tool_calls
            FROM conversations 
            WHERE project_path = ? AND timestamp > ?
            ORDER BY timestamp ASC
        """, (project_path, since.isoformat())).fetchall()
        
        conn.close()
        
        if not conversations:
            return ContextSummary(
                period=period,
                summary="No recent activity",
                key_topics=[],
                important_decisions=[],
                created_files=[],
                modified_files=[],
                tokens_saved=0
            )
        
        # Analyze conversations
        all_text = ""
        tool_calls = []
        created_files = []
        modified_files = []
        
        for user_msg, assistant_msg, tool_calls_json in conversations:
            all_text += f"User: {user_msg}\nAssistant: {assistant_msg}\n\n"
            
            if tool_calls_json:
                calls = json.loads(tool_calls_json)
                tool_calls.extend(calls)
                
                # Extract file operations
                for call in calls:
                    if call.get('function', {}).get('name') == 'write_file':
                        args = call.get('function', {}).get('arguments', {})
                        if isinstance(args, str):
                            args = json.loads(args)
                        created_files.append(args.get('path', ''))
        
        # Create summary (this would use AI in real implementation)
        summary = self._generate_summary(all_text)
        key_topics = self._extract_topics(all_text)
        
        tokens_saved = len(self.tokenizer.encode(all_text)) - len(self.tokenizer.encode(summary))
        
        return ContextSummary(
            period=period,
            summary=summary,
            key_topics=key_topics,
            important_decisions=[],  # Would extract from analysis
            created_files=list(set(created_files)),
            modified_files=list(set(modified_files)),
            tokens_saved=max(0, tokens_saved)
        )
    
    def _generate_summary(self, text: str) -> str:
        """Generate summary of conversation text"""
        # Simplified - in real implementation would use AI
        lines = text.split('\n')
        important_lines = [line for line in lines if any(keyword in line.lower() 
                          for keyword in ['created', 'modified', 'error', 'fixed', 'implemented'])]
        
        if len(important_lines) > 10:
            important_lines = important_lines[:10]
        
        return "Recent activity summary:\n" + "\n".join(important_lines[:5])
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract key topics from conversation"""
        # Simplified topic extraction
        words = text.lower().split()
        tech_words = [word for word in words if word in [
            'python', 'javascript', 'react', 'api', 'database', 'sql', 
            'docker', 'git', 'test', 'bug', 'feature', 'function'
        ]]
        
        # Count frequency and return top topics
        from collections import Counter
        return [word for word, count in Counter(tech_words).most_common(5)]
    
    def get_project_stats(self, project_path: str) -> Dict[str, Any]:
        """Get statistics for project conversations"""
        conn = sqlite3.connect(self.db_path)
        
        stats = conn.execute("""
            SELECT 
                COUNT(*) as total_turns,
                SUM(tokens_used) as total_tokens,
                SUM(cost) as total_cost,
                MIN(timestamp) as first_conversation,
                MAX(timestamp) as last_conversation,
                COUNT(DISTINCT session_id) as total_sessions
            FROM conversations 
            WHERE project_path = ?
        """, (project_path,)).fetchone()
        
        conn.close()
        
        return {
            "total_turns": stats[0] or 0,
            "total_tokens": stats[1] or 0,
            "total_cost": stats[2] or 0.0,
            "first_conversation": stats[3],
            "last_conversation": stats[4],
            "total_sessions": stats[5] or 0
        }
    
    def cleanup_old_conversations(self, days_to_keep: int = 30):
        """Clean up old conversations to save space"""
        cutoff = datetime.now() - timedelta(days=days_to_keep)
        
        conn = sqlite3.connect(self.db_path)
        
        # Create summaries for old conversations before deleting
        old_conversations = conn.execute("""
            SELECT DISTINCT project_path 
            FROM conversations 
            WHERE timestamp < ?
        """, (cutoff.isoformat(),)).fetchall()
        
        for (project_path,) in old_conversations:
            # Create summary if not exists
            existing = conn.execute("""
                SELECT COUNT(*) FROM context_summaries 
                WHERE project_path = ? AND period = 'archived'
            """, (project_path,)).fetchone()[0]
            
            if existing == 0:
                summary = self.create_summary(project_path, "archived")
                self.save_summary(summary, project_path)
        
        # Delete old conversations
        deleted = conn.execute("""
            DELETE FROM conversations 
            WHERE timestamp < ?
        """, (cutoff.isoformat(),)).rowcount
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def save_summary(self, summary: ContextSummary, project_path: str):
        """Save context summary to database"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO context_summaries 
            (project_path, period, summary, key_topics, important_decisions, 
             created_files, modified_files, tokens_saved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_path,
            summary.period,
            summary.summary,
            json.dumps(summary.key_topics),
            json.dumps(summary.important_decisions),
            json.dumps(summary.created_files),
            json.dumps(summary.modified_files),
            summary.tokens_saved
        ))
        conn.commit()
        conn.close()
