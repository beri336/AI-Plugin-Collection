# docs/examples/usage_conversation_manager.py

"""
Example usage of ConversationManager.

Demonstrates:
- Creating a new conversation session
- Adding user, assistant, and system messages
- Building context and prompts
- Saving / loading / exporting conversations
- Displaying conversation statistics
"""

from modules.conversation_manager import ConversationManager

from pathlib import Path


def main():
    # Initialize ConversationManager
    manager = ConversationManager(
        model="llama3.2:3b",
        max_history=10,
        system_message="You are a helpful AI assistant."
    )

    print("=== Conversation Manager Example ===\n")

    # 1️⃣ Add sample conversation turns
    manager.add_user_message("Hey, can you explain what recursion is?")
    manager.add_assistant_message(
        "Sure! Recursion is when a function calls itself to break down a task into smaller subproblems."
    )
    manager.add_user_message("Give me a simple Python example.")
    manager.add_assistant_message(
        "Here's an example:\n\n``````"
    )

    # 2️⃣ Show built context and next prompt
    print("---- Conversation Context ----")
    print(manager.build_context(include_system=True))

    print("\n---- Next Prompt ----")
    next_prompt = manager.build_prompt("Can you also explain its time complexity?")
    print(next_prompt)

    # 3️⃣ Export and save conversation
    output_dir = Path("output/conversations")
    output_dir.mkdir(parents=True, exist_ok=True)

    manager.save_to_file(output_dir / "conversation.json")
    manager.export_to_markdown(output_dir / "conversation.md")
    manager.export_to_text(output_dir / "conversation.txt")

    print(f"\nConversation exported to '{output_dir.resolve()}'")

    # 4️⃣ Show conversation metadata summary
    print("\n---- Conversation Info ----")
    for key, value in manager.get_conversation_info().items():
        print(f"{key:<20}: {value}")

    print("\n✅ Example complete — conversation saved successfully!")


if __name__ == "__main__":
    main()
