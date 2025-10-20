"""Database management for translation history and caching"""
import sqlite3
import threading
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional

log = logging.getLogger("Translator")

class DatabaseManager:
    """Manages SQLite database for translation history and caching"""
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._local = threading.local()
        self.init_tables()
    
    def _get_connection(self):
        """Get thread-local database connection"""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(str(self.db_path), check_same_thread=True)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def init_tables(self):
        """Initialize database tables"""
        conn = self._get_connection()
        conn.execute("""CREATE TABLE IF NOT EXISTS translations (
            id INTEGER PRIMARY KEY,
            source_text TEXT,
            translated_text TEXT,
            source_lang TEXT,
            target_lang TEXT,
            mode TEXT,
            engine TEXT,
            confidence REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            duration_ms INTEGER
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS cache (
            id INTEGER PRIMARY KEY,
            hash TEXT UNIQUE,
            source_text TEXT,
            translated_text TEXT,
            source_lang TEXT,
            target_lang TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 0,
            last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.commit()
    
    def add_translation(self, source, translated, src_lang, tgt_lang, mode, 
                       engine="google", confidence=1.0, duration_ms=0):
        """Add translation to history"""
        conn = self._get_connection()
        conn.execute(
            """INSERT INTO translations 
            (source_text, translated_text, source_lang, target_lang, mode, engine, confidence, duration_ms) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (source, translated, src_lang, tgt_lang, mode, engine, confidence, duration_ms)
        )
        conn.commit()
    
    def get_cached_translation(self, text: str, src: str, tgt: str) -> Optional[str]:
        """Get cached translation if it exists"""
        key = hashlib.md5(f"{text}:{src}:{tgt}".encode()).hexdigest()
        conn = self._get_connection()
        result = conn.execute(
            "SELECT translated_text FROM cache WHERE hash = ?",
            (key,)
        ).fetchone()
        return result[0] if result else None
    
    def cache_translation(self, text: str, translated: str, src: str, tgt: str):
        """Cache a translation"""
        key = hashlib.md5(f"{text}:{src}:{tgt}".encode()).hexdigest()
        conn = self._get_connection()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO cache 
                (hash, source_text, translated_text, source_lang, target_lang, last_accessed) 
                VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                (key, text, translated, src, tgt)
            )
            conn.commit()
        except Exception as e:
            log.warning(f"Cache insert failed: {e}")
    
    def get_history(self, limit=50, search="") -> List[Dict]:
        """Get translation history with optional search"""
        conn = self._get_connection()
        if search:
            results = conn.execute(
                """SELECT source_text, translated_text, source_lang, target_lang, mode, 
                engine, confidence, timestamp 
                FROM translations 
                WHERE source_text LIKE ? OR translated_text LIKE ? 
                ORDER BY id DESC LIMIT ?""",
                (f"%{search}%", f"%{search}%", limit)
            ).fetchall()
        else:
            results = conn.execute(
                """SELECT source_text, translated_text, source_lang, target_lang, mode, 
                engine, confidence, timestamp 
                FROM translations 
                ORDER BY id DESC LIMIT ?""",
                (limit,)
            ).fetchall()
        return [dict(row) for row in results]
    
    def export_history(self, filepath: str):
        """Export translation history to file"""
        conn = self._get_connection()
        results = conn.execute(
            "SELECT * FROM translations ORDER BY timestamp DESC"
        ).fetchall()
        with open(filepath, 'w', encoding='utf-8') as f:
            for row in results:
                r = dict(row)
                f.write(f"[{r['timestamp']}] {r['source_lang']}→{r['target_lang']} ({r['mode']}/{r['engine']})\n")
                f.write(f"Source: {r['source_text']}\nTranslation: {r['translated_text']}\n{'-'*80}\n\n")
    
    def clear_history(self):
        """Clear all translation history"""
        conn = self._get_connection()
        conn.execute("DELETE FROM translations")
        conn.commit()
