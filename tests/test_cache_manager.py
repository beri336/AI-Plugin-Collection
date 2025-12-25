# tests/test_cache_manager.py

'''
Unit tests for the cache manager
  This test suite validates the caching system with SQLite backend.

- Tests database initialization and schema creation
- Validates cache key generation with deterministic hashes
- Checks set/get operations and hit count tracking
- Tests TTL expiration and automatic cleanup
- Validates eviction strategy when memory limits are reached
- Checks response caching for model outputs
- Tests cache statistics and export functions
- Uses pytest fixtures for isolated test environments
'''

from core.cache_manager import Cache
import sqlite3
import pytest
import json
import time


@pytest.fixture
def tmp_cache(tmp_path):
    cache_dir = tmp_path / "cache"
    c = Cache(cache_dir=cache_dir, max_size_mb=1, default_ttl_seconds=2)
    return c

def test_init_creates_db(tmp_cache):
    dbfile = tmp_cache.db_path
    assert dbfile.exists()
    con = sqlite3.connect(dbfile)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]
    assert "cache_entries" in tables
    con.close()

def test_generate_key_stable(tmp_cache):
    key1 = tmp_cache._generate_key("llama", "Hello", temperature=0.7)
    key2 = tmp_cache._generate_key("llama", "Hello", temperature=0.7)
    assert key1 == key2
    assert len(key1) == 64

def test_set_and_get_value(tmp_cache):
    key = "abcd1234"
    assert tmp_cache.set(key, {"answer": 42})
    result = tmp_cache.get(key)
    assert result == {"answer": 42}

    # verify hit_count updated
    con = sqlite3.connect(tmp_cache.db_path)
    cur = con.cursor()
    cur.execute("SELECT hit_count FROM cache_entries WHERE key=?", (key,))
    hits = cur.fetchone()[0]
    con.close()
    assert hits > 0

def test_expired_entry_returns_none(tmp_cache):
    key = "expireme"
    tmp_cache.set(key, "temp", ttl_seconds=1)
    time.sleep(1.1)
    val = tmp_cache.get(key)
    assert val is None

def test_delete_and_clear(tmp_cache):
    k1, k2 = "k1", "k2"
    tmp_cache.set(k1, "v1")
    tmp_cache.set(k2, "v2")

    assert tmp_cache.delete(k1) is True
    assert tmp_cache.get(k1) is None

    total = tmp_cache.clear()
    assert total >= 1
    stats = tmp_cache.get_stats()
    assert stats["total_entries"] == 0

def test_clear_expired(tmp_cache):
    k1, k2 = "a", "b"
    tmp_cache.set(k1, "1", ttl_seconds=1)
    tmp_cache.set(k2, "2", ttl_seconds=10)
    time.sleep(1.2)
    deleted = tmp_cache.clear_expired()
    assert deleted >= 1

def test_cache_response_and_get_cached(tmp_cache):
    key = tmp_cache.cache_response("llama", "say hi", "hello world", temperature=0.1)
    cached = tmp_cache.get_cached_response("llama", "say hi", temperature=0.1)
    assert cached == "hello world"
    assert isinstance(key, str)
    assert len(key) == 64

def test_get_stats_returns_expected_fields(tmp_cache):
    tmp_cache.set("k", "v")
    stats = tmp_cache.get_stats()
    assert "total_entries" in stats
    assert "usage_percent" in stats
    assert "expired_entries" in stats
    assert "top_entries" in stats

def test_evict_if_needed(tmp_cache):
    # artificially fill db to trigger eviction
    big_value = "x" * (1024 * 200)  # 200 KB * 6 ≈ 1.2 MB
    for i in range(6):
        tmp_cache.set(f"k{i}", big_value)

    stats = tmp_cache.get_stats()
    assert stats["total_entries"] > 0
    # usage must stay within max limit (1 MB ± margin)
    assert stats["total_size_mb"] <= 1.1

def test_export_to_json_creates_file(tmp_cache, tmp_path):
    tmp_cache.set("alpha", {"test": True})
    output_file = tmp_path / "out.json"
    tmp_cache.export_to_json(output_file)
    assert output_file.exists()

    content = json.loads(output_file.read_text())
    assert "stats" in content and "entries" in content
