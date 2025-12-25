# docs/examples/usage_settings.py

"""
Example usage of Config class.

Demonstrates:
- Accessing connection and timeout settings
- Constructing valid API endpoints
- Ensuring necessary directories exist
- Using getters and setters
"""

from config.settings import Config


def main():
    config = Config()

    print("=== Config Example ===\n")

    # 1️⃣ Accessing endpoints and URLs
    print(f"Valid endpoint URL     : {config.get_endpoint('version')}")
    # Uncomment the line below to see error handling
    # print(f"Invalid endpoint URL   : {config.get_endpoint('ups')}")

    # 2️⃣ Ensure log and cache directories exist
    config.ensure_directories()
    print("\nEnsured directories:")
    print(f"- Log directory   : {config.log_directory.resolve()}")
    print(f"- Cache directory : {config.cache_directory.resolve()}")

    # 3️⃣ Connection info
    print("\n---- Connection Info ----")
    print(f"Host       : {config.get_host()}")
    print(f"Port       : {config.get_port()}")
    print(f"Base URL   : {config.get_base_url}")

    # 4️⃣ Changing host and port
    config.set_host("127.0.0.1")
    config.set_port(8080)
    print("\nUpdated Configuration:")
    print(f"Host       : {config.get_host()}")
    print(f"Port       : {config.get_port()}")
    print(f"New Endpoint URL : {config.get_endpoint('version')}")

    print("\n✅ Example complete.")


if __name__ == "__main__":
    main()
