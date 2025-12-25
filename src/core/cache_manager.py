# src/core/cache_manager.py

'''
Persistent caching system for Ollama API responses and metadata
  This module provides an SQLite-based caching system to optimize the performance of Ollama integration.

- Persistently stores model responses and metadata in SQLite
- Supports TTL (Time-to-Live) for automatic expiration of entries
- Implements LRU-like eviction strategy based on hit count
- Limits cache size with configurable maximum
- Provides statistics and export functions for cache analysis
- Generates deterministic cache keys using SHA256 hashing
'''

from datetime import datetime, timedelta
from typing import Any, Optional, Dict
from dataclasses import dataclass
from pathlib import Path

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


class Cache:
    """Cache manager for Ollama responses and metadata.
    
    Features:
    - Persistent SQLite-based caching
    - TTL (Time To Live) support with automatic expiration
    - LRU-like eviction based on hit count and creation time
    - Size-based cache limits with automatic eviction
    - Thread-safe database operations
    - Pickle serialization for arbitrary Python objects
    - Statistics and export functionality
    """
    
    def __init__(
        self,
        cache_dir: Path=Path('.cache/ollama'),
        max_size_mb: int=100,
        default_ttl_seconds: int=3600
    ) -> None:
        """Initialize the cache system.
        
        Creates cache directory and SQLite database if they don't exist.
        Sets up database schema with indices for efficient querying.
        
        Args:
            cache_dir: Directory for cache storage (created if missing)
            max_size_mb: Maximum cache size in megabytes
            default_ttl_seconds: Default time-to-live in seconds (default: 1 hour)
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = timedelta(seconds=default_ttl_seconds)
        
        self.db_path = cache_dir / 'cache.db'
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database schema for cache storage.
        
        Creates the cache_entries table and indices if they don't exist.
        Table stores pickled values as BLOBs along with metadata.
        
        Note:
            This method is idempotent and safe to call multiple times.
        """
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
        """Generate a unique deterministic cache key from parameters.
        
        Creates a SHA256 hash from model name, prompt, and any additional
        parameters. Kwargs are sorted to ensure deterministic key generation
        regardless of parameter order.
        
        Args:
            model: Model name (e.g., 'llama3.2:3b')
            prompt: Prompt text
            **kwargs: Additional parameters to include in key (e.g., temperature=0.7)
        
        Returns:
            64-character SHA256 hash as hexadecimal string
        """
        params_str = f"{model}:{prompt}:"
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            params_str += ':'.join(f"{k}={v}" for k, v in sorted_kwargs)
        
        return hashlib.sha256(params_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from cache.
        
        Fetches cached value by key, checking expiration and updating hit count.
        Failed deserialization also results in entry deletion.
        
        Args:
            key: Cache key (typically SHA256 hash)
            
        Returns:
            Cached value if found and not expired, None otherwise
            
        Side Effects:
            - Increments hit_count for accessed entries
            - Deletes expired or corrupted entries and returns None
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
        """Store a value in cache with optional TTL.
        
        Serializes value using pickle and stores in SQLite. Automatically
        evicts old entries if cache size limit would be exceeded. Replaces
        existing entries with same key.
        
        Args:
            key: Cache key (any string, typically from _generate_key())
            value: Value to cache (must be pickleable)
            ttl_seconds: Time to live in seconds (uses default if None)
            
        Returns:
            True if stored successfully, False on any error
        """
        try:
            # serialize value
            value_blob = pickle.dumps(value)
            size_bytes = len(value_blob)
            
            # check if we need to evict entries
            self._evict_if_needed(size_bytes)
            
            # calculate expiration
            ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else self.default_ttl
            created_at = datetime.now()
            expires_at = created_at + ttl
            
            # store in database
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
        """Delete a cache entry by key.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if entry was deleted, False if key not found
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
        
        Removes all entries from the cache database.
        
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
        """Remove all expired entries from cache.
        
        Deletes entries where expires_at is before current time.
        Useful for maintenance and freeing up space.
        
        Returns:
            Number of expired entries deleted
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
        """Get comprehensive cache statistics.
        
        Collects information about cache usage, size, and most accessed entries.
        
        Returns:
            Dictionary containing:
                - total_entries: Total number of cached entries
                - total_size_mb: Current cache size in megabytes
                - max_size_mb: Maximum configured cache size
                - usage_percent: Cache usage as percentage of max
                - expired_entries: Number of expired but not yet cleared entries
                - top_entries: List of 5 most accessed entries with hit counts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # total entries
        cursor.execute("SELECT COUNT(*) FROM cache_entries")
        total_entries = cursor.fetchone()[0]
        
        # total size
        cursor.execute("SELECT SUM(size_bytes) FROM cache_entries")
        total_size_bytes = cursor.fetchone()[0] or 0
        
        # expired entries
        now = datetime.now().isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM cache_entries 
            WHERE expires_at < ?
        """, (now,))
        expired_entries = cursor.fetchone()[0]
        
        # most accessed
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
        """Evict least-used entries if cache size limit would be exceeded.
        
        Calculates space needed and removes entries in order of least hits
        and oldest creation time until enough space is freed.
        
        Args:
            new_entry_size: Size in bytes of entry to be added
            
        Note:
            This is called automatically by set() before inserting new entries.
            Eviction strategy: lowest hit_count first, then oldest created_at.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # get current cache size
        cursor.execute("SELECT SUM(size_bytes) FROM cache_entries")
        current_size = cursor.fetchone()[0] or 0
        
        # check if we need to evict
        if current_size + new_entry_size > self.max_size_bytes:
            # calculate how much space we need
            space_needed = (current_size + new_entry_size) - self.max_size_bytes
            
            # get entries sorted by hit count
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
        """Cache a model response with automatic key generation.
        
        Convenience method that generates cache key from model/ prompt/ params
        and stores the response.
        
        Args:
            model: Model name used for generation
            prompt: Prompt text that generated the response
            response: Model's response text to cache
            ttl_seconds: Time to live in seconds (uses default if None)
            **kwargs: Additional parameters used in generation (e.g., temperature)
            
        Returns:
            Generated cache key (SHA256 hash)
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
        """Retrieve a cached model response.
        
        Generates cache key from parameters and retrieves cached response.
        Returns None if not found or expired.
        
        Args:
            model: Model name
            prompt: Prompt text
            **kwargs: Additional parameters (must match those used in cache_response)
            
        Returns:
            Cached response string or None if not found/ expired
        """
        key = self._generate_key(model, prompt, **kwargs)
        return self.get(key)
    
    def export_to_json(self, output_file: Path) -> None:
        """Export cache metadata to JSON file.
        
        Exports cache statistics and entry metadata (not actual values)
        for analysis and debugging. Values are not included to keep
        file size manageable.
        
        Args:
            output_file: Path where JSON file should be written
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
