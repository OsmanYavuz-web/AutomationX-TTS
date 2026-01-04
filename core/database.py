"""
AutomationX TTS - SQLite Database Layer
"""

import sqlite3
import json
import os
import shutil
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

from .exceptions import DatabaseError, logger

# ===================================================================
# DATABASE CONFIGURATION
# ===================================================================

DB_NAME = "history.db"
JSON_BACKUP_SUFFIX = ".json.migrated"

SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    text TEXT NOT NULL,
    language TEXT NOT NULL,
    seed INTEGER NOT NULL,
    exaggeration REAL NOT NULL,
    cfg_weight REAL NOT NULL,
    filename TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_created_at ON history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_filename ON history(filename);
"""


# ===================================================================
# CONNECTION MANAGEMENT
# ===================================================================

@contextmanager
def get_connection(db_path: str):
    """Context manager for database connections"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise DatabaseError(f"Veritabanı hatası: {e}")
    finally:
        if conn:
            conn.close()


def init_database(outputs_dir: str) -> str:
    """
    Veritabanını başlat ve migration yap.
    Returns: Database path
    """
    os.makedirs(outputs_dir, exist_ok=True)
    db_path = os.path.join(outputs_dir, DB_NAME)
    json_path = os.path.join(outputs_dir, "history.json")
    
    # Schema oluştur
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
    
    # JSON'dan migration
    if os.path.exists(json_path):
        migrate_from_json(json_path, db_path)
    
    logger.info(f"Database initialized: {db_path}")
    return db_path


def migrate_from_json(json_path: str, db_path: str) -> int:
    """
    JSON history'den SQLite'a migration.
    Returns: Migrate edilen kayıt sayısı
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            history = json.load(f)
        
        if not history:
            return 0
        
        migrated = 0
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            for entry in history:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO history 
                        (timestamp, text, language, seed, exaggeration, cfg_weight, filename)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry.get("timestamp", ""),
                        entry.get("text", ""),
                        entry.get("language", "tr"),
                        entry.get("seed", -1),
                        entry.get("exaggeration", 0.5),
                        entry.get("cfg_weight", 0.5),
                        entry.get("filename", ""),
                    ))
                    if cursor.rowcount > 0:
                        migrated += 1
                except sqlite3.IntegrityError:
                    continue  # Duplicate filename, skip
            conn.commit()
        
        # JSON'ı yedekle
        backup_path = json_path + JSON_BACKUP_SUFFIX
        shutil.move(json_path, backup_path)
        logger.info(f"Migrated {migrated} entries from JSON. Backup: {backup_path}")
        
        return migrated
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 0


# ===================================================================
# CRUD OPERATIONS
# ===================================================================

def add_entry(db_path: str, entry: Dict[str, Any]) -> bool:
    """Yeni kayıt ekle"""
    try:
        with get_connection(db_path) as conn:
            conn.execute("""
                INSERT INTO history 
                (timestamp, text, language, seed, exaggeration, cfg_weight, filename)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                entry["timestamp"],
                entry["text"],
                entry["language"],
                entry["seed"],
                entry["exaggeration"],
                entry["cfg_weight"],
                entry["filename"],
            ))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to add entry: {e}")
        return False


def get_entries(db_path: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Son N kaydı getir"""
    try:
        with get_connection(db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, text, language, seed, exaggeration, cfg_weight, filename
                FROM history
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Failed to get entries: {e}")
        return []


def get_by_filename(db_path: str, filename: str) -> Optional[Dict[str, Any]]:
    """Filename ile kayıt bul"""
    try:
        with get_connection(db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, text, language, seed, exaggeration, cfg_weight, filename
                FROM history
                WHERE filename = ?
            """, (filename,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"Failed to get entry by filename: {e}")
        return None


def get_entry_count(db_path: str) -> int:
    """Toplam kayıt sayısı"""
    try:
        with get_connection(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM history")
            return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Failed to get count: {e}")
        return 0
