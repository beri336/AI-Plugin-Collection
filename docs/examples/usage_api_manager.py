# docs/examples/usage_api_manager.py

"""
Example usage of APIManager:
- Connects to the local Ollama API
- Fetches model lists and metadata
- Demonstrates model management methods (pull, delete, run, stop)
"""

from modules.api_manager import APIManager


def main():
    manager = APIManager()

    print("=== Ollama API Manager Example ===\n")

    # 1️⃣ Connection check
    is_connected = manager.check_connection()
    print(f"Connection Check: {is_connected}")
    if not is_connected:
        print("⚠️  API is not reachable. Make sure Ollama is running (ollama serve).")
        return

    # 2️⃣ Fetch & display model lists
    print("\nFetching all model names...")
    manager.refresh_list_of_model_names()

    print("\n🧠 Detailed Model List:")
    for model in manager.get_detailed_list_models():
        print(f" - {model['name']:<25} {model['size']:>6} | {model['modified']:<15} | ID: {model['id']}")

    print("\nList only Model names:")
    print(manager.get_list_model_names())

    # Optional: Inspect a single model (uncomment if available)
    # model_name = "llama3.2:3b"
    # print(f"\nInformation to model '{model_name}':")
    # info = manager.get_model_info(model_name)
    # print(info)

    # 3️⃣ Model existence check
    model_name = "llama3.2:3b"
    print(f"\nModel exists: {manager.model_exists(model_name)}")

    # 4️⃣ (Optional) Model download or pull
    # print(f"\nPulling model '{model_name}' ...")
    # manager.pull_model(model_name)  # synchronous
    #
    # print("\nPulling model with progress:")
    # for progress in manager.pull_model_with_progress(model_name):
    #     print(progress)

    # 5️⃣ Managing running models
    # print("\nAll running models:")
    # manager.refresh_list_of_running_models()
    # print(manager.get_list_running_models())

    # 6️⃣ Start / stop models
    # print(f"\nStarting model '{model_name}' ...")
    # print("Started:", manager.start_running_model(model_name))
    #
    # print(f"Stopping model '{model_name}' ...")
    # print("Stopped:", manager.stop_running_model(model_name))
    #
    # print("\nStopping all running models ...")
    # print(manager.stop_all_running_models())

    # 7️⃣ Generate text (non-streaming)
    # prompt = "Explain Python decorators in simple terms."
    # print(f"\nPrompt: {prompt}")
    # output = manager.generate(model_name, prompt)
    # print("\nAssistant Response:\n", output)
    
    # 8️⃣ Generate text stream
    # print("\nStreaming response:")
    # for chunk in manager.generate_stream(model_name, "What is recursion?"):
    #     print(chunk)


if __name__ == "__main__":
    main()
