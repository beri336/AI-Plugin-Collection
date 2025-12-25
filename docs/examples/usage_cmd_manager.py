# docs/examples/usage_cmd_manager.py

"""
Example usage of CMDManager:
- Lists, inspects and manages Ollama models via CLI commands.
- Demonstrates local pull, delete, start/stop, and generation via subprocess interface.
"""

from modules.cmd_manager import CMDManager


def main():
    manager = CMDManager()
    model_name = "llama3.2:3b"

    print("=== Ollama CMD Manager Example ===\n")

    # 1️⃣ List cached model names (may be empty initially)
    print("Current model names in memory:")
    for item in manager.get_list_model_names():
        print(" -", item)

    # 2️⃣ Refresh model list from shell command
    print("\nFetching model list from Ollama (CLI)...")
    manager.refresh_list_of_model_names()

    print("\nAvailable models:")
    for item in manager.get_detailed_list_models():
        print(f" - {item['name']:<20} | {item['size']:<10} | Modified: {item['modified']}")

    # 3️⃣ Inspect model info
    print(f"\nInspecting model info for '{model_name}' ...")
    info = manager.get_model_info(model_name)
    if info:
        print("Model Info:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    else:
        print("⚠️ Model info unavailable or model not found.")

    # 4️⃣ Check existence of model
    print(f"\nModel '{model_name}' exists: {manager.model_exists(model_name)}")

    # 5️⃣ Pull model (uncomment to test)
    # print(f"\nPulling model '{model_name}' in foreground...")
    # manager.pull_model(model_name)

    # print("\nPulling with progress:")
    # for progress in manager.pull_model_with_progress(model_name):
    #     print(progress)
    
    # 6️⃣ Show running models
    print("\nRefreshing running models...")
    manager.refresh_list_of_running_models()

    running = manager.get_list_running_models()
    print(f"Running Models ({len(running)}):")
    for item in running:
        print(f" - {item}")

    print("\nRunning Model Names:")
    for name in manager.get_running_model_names():
        print(" -", name)

    # 7️⃣ Start/Stop models (uncomment if desired)
    # print(f"\nStarting model '{model_name}' ...")
    # print("Success:", manager.start_running_model(model_name))
    #
    # print(f"Stopping model '{model_name}' ...")
    # print("Success:", manager.stop_running_model(model_name))
    #
    # print("Stopping all running models...")
    # print(manager.stop_all_running_models())

    # 8️⃣ Generate responses (non-streaming / streaming)
    # prompt = "Explain recursion in one short sentence."
    # print(f"\nGenerating response for: '{prompt}'")
    # result = manager.generate(model_name, prompt)
    # print("Response:\n", result)
    #
    # print("\nStreaming response:")
    # for chunk in manager.generate_stream(model_name, "What are Python decorators?"):
    #     print(chunk)


if __name__ == "__main__":
    main()
