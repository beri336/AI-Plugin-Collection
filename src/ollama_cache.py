# src/ollama_cache.py

"""
Caching system for Ollama responses and metadata.
  This module provides persistent caching for model responses, model metadata, and frequently accessed data to improve performance.
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional, Dict

import sqlite3
import hashlib
import pickle
import json


@dataclass
class CacheEntry:
    """Represents a cached entry with metadata.
    
    Attributes:
        key: Unique cache key
        value: Cached value (pickled)
        created_at: Timestamp when entry was created
        expires_at: Timestamp when entry expires
        hit_count: Number of times this entry was accessed
        size_bytes: Size of cached value in bytes
    """
    
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    hit_count: int=0
    size_bytes: int=0


class OllamaCache:
    """Cache manager for Ollama responses and metadata.
    
    Features:
    - Persistent SQLite-based caching
    - TTL (Time To Live) support
    - LRU-like eviction based on hit count
    - Size-based cache limits
    - Separate caches for responses and metadata
    """
    
    def __init__(
        self,
        cache_dir: Path=Path('.cache/ollama'),
        max_size_mb: int=100,
        default_ttl_seconds=3600
    ) -> None:
        """Initialize the cache system.
        
        Args:
            cache_dir: Directory for cache storage
            max_size_mb: Maximum cache size in megabytes
            default_ttl_seconds: Default time-to-live in seconds
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = timedelta(seconds=default_ttl_seconds)
        
        self.db_path = cache_dir / 'cache.db'
        self._init_database()

    def _init_database(self) -> None:
        """ Initialize SQLite database for cache storage """
        con = sqlite3.connect(self.db_path)
        con.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                hit_count INTEGER DEFAULT 0,
                size_bytes INTEGER NOT NULL
            )
        """)
        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at 
            ON cache_entries(expires_at)
        """)
        con.commit()
        con.close()

    def _generate_key(
        self,
        model: str,
        prompt: str,
        **kwargs
    ) -> str:
        """Generate a unique cache key from parameters.
        
        Args:
            model: Model name
            prompt: Prompt text
            **kwargs: Additional parameters to include in key
            
        Returns:
            SHA256 hash as cache key
        """
        # create a deterministic string from all parameters
        params_str = f"{model}:{prompt}:"
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            params_str += ':'.join(f"{k}={v}" for k, v in sorted_kwargs)
        
        return hashlib.sha256(params_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        con = sqlite3.connect(self.db_path)
        cursor = con.cursor()
        
        cursor.execute("""
            SELECT value, expires_at, hit_count 
            FROM cache_entries 
            WHERE key = ?
        """, (key,))
        
        row = cursor.fetchone()
        
        if not row:
            con.close()
            return None
        
        value_blob, expires_at_str, hit_count = row
        expires_at = datetime.fromisoformat(expires_at_str)
        
        # check if expired
        if datetime.now() > expires_at:
            self.delete(key)
            con.close()
            return None
        
        # update hit count
        cursor.execute("""
            UPDATE cache_entries 
            SET hit_count = ? 
            WHERE key = ?
        """, (hit_count + 1, key))
        con.commit()
        con.close()
        
        # deserialize value
        try:
            return pickle.loads(value_blob)
        except Exception as e:
            self.delete(key)
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Store a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds (uses default if None)
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            # Serialize value
            value_blob = pickle.dumps(value)
            size_bytes = len(value_blob)
            
            # Check if we need to evict entries
            self._evict_if_needed(size_bytes)
            
            # Calculate expiration
            ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else self.default_ttl
            created_at = datetime.now()
            expires_at = created_at + ttl
            
            # Store in database
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO cache_entries 
                (key, value, created_at, expires_at, hit_count, size_bytes)
                VALUES (?, ?, ?, ?, 0, ?)
            """, (
                key,
                value_blob,
                created_at.isoformat(),
                expires_at.isoformat(),
                size_bytes
            ))
            conn.commit()
            conn.close()
            
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """Delete a cache entry.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def clear(self) -> int:
        """Clear all cache entries.
        
        Returns:
            Number of entries deleted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cache_entries")
        count = cursor.fetchone()[0]
        cursor.execute("DELETE FROM cache_entries")
        conn.commit()
        conn.close()
        return count

    def clear_expired(self) -> int:
        """Remove all expired entries.
        
        Returns:
            Number of entries deleted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute("""
            DELETE FROM cache_entries 
            WHERE expires_at < ?
        """, (now,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total entries
        cursor.execute("SELECT COUNT(*) FROM cache_entries")
        total_entries = cursor.fetchone()[0]
        
        # Total size
        cursor.execute("SELECT SUM(size_bytes) FROM cache_entries")
        total_size_bytes = cursor.fetchone()[0] or 0
        
        # Expired entries
        now = datetime.now().isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM cache_entries 
            WHERE expires_at < ?
        """, (now,))
        expired_entries = cursor.fetchone()[0]
        
        # Most accessed
        cursor.execute("""
            SELECT key, hit_count FROM cache_entries 
            ORDER BY hit_count DESC LIMIT 5
        """)
        top_entries = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_entries': total_entries,
            'total_size_mb': total_size_bytes / (1024 * 1024),
            'max_size_mb': self.max_size_bytes / (1024 * 1024),
            'usage_percent': (total_size_bytes / self.max_size_bytes * 100) if self.max_size_bytes > 0 else 0,
            'expired_entries': expired_entries,
            'top_entries': [{'key': k[:16] + '...', 'hits': h} for k, h in top_entries]
        }

    def _evict_if_needed(self, new_entry_size: int) -> None:
        """Evict least-used entries if cache is full.
        
        Args:
            new_entry_size: Size of entry to be added
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current cache size
        cursor.execute("SELECT SUM(size_bytes) FROM cache_entries")
        current_size = cursor.fetchone()[0] or 0
        
        # Check if we need to evict
        if current_size + new_entry_size > self.max_size_bytes:
            # Calculate how much space we need
            space_needed = (current_size + new_entry_size) - self.max_size_bytes
            
            # Get entries sorted by hit count (LRU-like)
            cursor.execute("""
                SELECT key, size_bytes FROM cache_entries 
                ORDER BY hit_count ASC, created_at ASC
            """)
            
            freed_space = 0
            for key, size in cursor.fetchall():
                self.delete(key)
                freed_space += size
                if freed_space >= space_needed:
                    break
        
        conn.close()

    def cache_response(
        self,
        model: str,
        prompt: str,
        response: str,
        ttl_seconds: Optional[int] = None,
        **kwargs
    ) -> str:
        """Cache a model response.
        
        Args:
            model: Model name
            prompt: Prompt text
            response: Model response
            ttl_seconds: Time to live in seconds
            **kwargs: Additional parameters for cache key
            
        Returns:
            Cache key
        """
        key = self._generate_key(model, prompt, **kwargs)
        self.set(key, response, ttl_seconds)
        return key

    def get_cached_response(
        self,
        model: str,
        prompt: str,
        **kwargs
    ) -> Optional[str]:
        """Retrieve a cached response.
        
        Args:
            model: Model name
            prompt: Prompt text
            **kwargs: Additional parameters for cache key
            
        Returns:
            Cached response or None
        """
        key = self._generate_key(model, prompt, **kwargs)
        return self.get(key)

    def export_to_json(self, output_file: Path) -> None:
        """Export cache contents to JSON file.
        
        Args:
            output_file: Path to output JSON file
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT key, created_at, expires_at, hit_count, size_bytes 
            FROM cache_entries
        """)
        
        entries = []
        for row in cursor.fetchall():
            entries.append({
                'key': row[0],
                'created_at': row[1],
                'expires_at': row[2],
                'hit_count': row[3],
                'size_bytes': row[4]
            })
        
        conn.close()
        
        with open(output_file, 'w') as f:
            json.dump({
                'stats': self.get_stats(),
                'entries': entries
            }, f, indent=2)
