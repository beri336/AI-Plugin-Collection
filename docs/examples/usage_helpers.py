# docs/examples/usage_helpers.py

"""
Example usage of the Helper class.

Demonstrates:
- Detecting package managers (Homebrew, Winget, Chocolatey)
- Attempting automated installations (commented for safety)
- Displaying manual installation instructions
- Validating model names and estimating token counts
- Searching for installed models via APIManager
"""

from modules.api_manager import APIManager
from core.helpers import Helper


def main():
    helper = Helper()

    print("=== Ollama Helper Utilities Example ===\n")

    # 1️⃣ Check for package managers
    print("[Package Manager Detection]")
    print("- Homebrew:", "✅ Installed" if helper._is_homebrew_installed() else "❌ Not found")
    print("- Winget   :", "✅ Installed" if helper._is_winget_installed() else "❌ Not found")
    print("- Chocolatey:", "✅ Installed" if helper._is_chocolatey_installed() else "❌ Not found")

    print("\n[Manual Installation Instructions Example]")
    helper._show_manual_install_instructions()

    # 2️⃣ Validate a model name
    model = "llama3.2:3b"
    print(f"\n[Model Validation]\nModel '{model}' valid?: {helper.validate_model_name(model)}")

    # 3️⃣ Estimate tokens for a sample text
    text = "This is a simple test sentence for token estimation."
    est = helper.estimate_tokens(text)
    print(f"\n[Token Estimation]\nEstimated tokens ({len(text)} chars) → {est}\n")

    # 4️⃣ Search installed models (requires Ollama API running)
    print("[Model Search via APIManager]")
    manager = APIManager()

    print("Checking Ollama connection ...")
    if not manager.check_connection():
        print("⚠️  Ollama service not reachable. Start it with: `ollama serve`")
        return

    manager.refresh_list_of_model_names()
    models = manager.get_list_model_names()

    print(f"Installed models ({len(models)}): {models}")
    matches = helper.search_models(model, models)
    if matches:
        print(f"✅ Model '{model}' found in installed models.")
    else:
        print(f"❌ Model '{model}' not found.")

    # 5️⃣ (Optional) Try automated installation (commented for safety)
    # print("\nAttempting installation on macOS ...")
    # success = helper._install_macos()
    # print("Result:", "✅ Success" if success else "❌ Failed")

    print("\n✅ Example complete — helper demonstration finished!")


if __name__ == "__main__":
    main()
