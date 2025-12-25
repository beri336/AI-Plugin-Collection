# docs/examples/usage_service_manager.py

"""
Example usage of the Service class.

Demonstrates:
- Checking installation and version
- Inspecting system and runtime status
- Performing a detailed health check
- (Optional) Starting or stopping the Ollama service
"""

from modules.service_manager import Service


def main():
    service = Service()

    print("=== Ollama Service Manager Example ===\n")

    # 1️⃣ General system & installation info
    print("---- System Information ----")
    print(f"Operating System     : {service.get_os_name()}")
    print(f"Ollama Installed     : {service.is_installed()}")
    print(f"Installation Path    : {service.get_installation_path()}")
    print(f"Version              : {service.get_version()}\n")

    # 2️⃣ Runtime and connectivity checks
    print("---- Runtime Status ----")
    print(f"Process Running      : {service.is_running()}")
    print(f"API Reachable        : {service.is_api_reachable()}")
    print(f"Fully Operational    : {service.is_operatable()}\n")

    # 3️⃣ Health overview (aggregated information)
    print("---- Health Summary ----")
    health_info = service.get_health_status()
    for key, value in health_info.items():
        print(f"- {key:<20}: {value}")
    print()

    # 4️⃣ (Optional) Start or stop the service
    # Uncomment to control the Ollama process directly.
    #
    # print("Starting Ollama service...")
    # if service.start(timeout=10):
    #     print("✅ Service started successfully.")
    # else:
    #     print("❌ Failed to start service.")
    #
    # print("Stopping Ollama service...")
    # if service.stop():
    #     print("✅ Service stopped successfully.")
    # else:
    #     print("⚠️ Could not stop service (may not be running).")

    print("✅ Example complete — Service checks finished.\n")


if __name__ == "__main__":
    main()
