# docs/examples/usage_cache_manager.py

"""
Example usage of Cache Manager.

Demonstrates:
- Creating and configuring cache
- Storing and retrieving cached responses
- Viewing cache statistics
- Clearing and exporting cache data
"""

from core.cache_manager import Cache

from pathlib import Path


def main():
    cache = Cache(
        cache_dir=Path(".cache/ollama"),
        max_size_mb=50,
        default_ttl_seconds=600  # 10 minutes
    )

    print("=== Ollama Cache Manager Example ===\n")

    # 1️⃣ Add and retrieve a response from cache
    model = "llama3.2:3b"
    prompt = "Explain what recursion is in one sentence."
    response = "Recursion is when a function calls itself to solve smaller instances of a problem."

    print("→ Caching example response...")
    key = cache.cache_response(model, prompt, response)
    print(f"Cached under key: {key[:12]}...\n")

    cached_value = cache.get_cached_response(model, prompt)
    if cached_value:
        print("✅ Found cached response:")
        print("   ", cached_value)
    else:
        print("❌ Cache miss (not found or expired)")

    # 2️⃣ Display cache statistics
    stats = cache.get_stats()
    print("\n=== Cache Statistics ===")
    print(f"Total entries      : {stats['total_entries']}")
    print(f"Total size         : {stats['total_size_mb']:.2f} MB / {stats['max_size_mb']} MB")
    print(f"Usage              : {stats['usage_percent']:.1f}%")
    print(f"Expired entries    : {stats['expired_entries']}")

    if stats['top_entries']:
        print("\nMost accessed entries:")
        for entry in stats['top_entries']:
            print(f"  - {entry['key']}: {entry['hits']} hits")
    print()

    # 3️⃣ Clear expired cache entries
    expired_count = cache.clear_expired()
    print(f"🧹 Cleared {expired_count} expired cache entries.\n")

    # 4️⃣ Export cache metadata for inspection
    export_path = Path("cache_info.json")
    cache.export_to_json(export_path)
    print(f"📦 Cache metadata exported to: {export_path.resolve()}\n")
    
    # 5️⃣ (Optional) Clear the entire cache
    # Uncomment for a full wipe
    # total_deleted = cache.clear()
    # print(f"🚮 Cleared all {total_deleted} cache entries.")


if __name__ == "__main__":
    main()
