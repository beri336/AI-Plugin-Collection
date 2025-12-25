# tests/test_conversation_manager.py

'''
Unit tests for the ConversationManager
  This test suite validates the multi-turn conversation management system.

- Tests message and conversation serialization
- Validates message addition and retrieval
- Checks context and prompt building with history
- Tests persistence (saving/loading JSON)
- Validates export to text and Markdown formats
- Checks history trimming at max limit
- Tests title generation and truncation
- Validates token estimation and conversation info
'''

from modules.conversation_manager import ConversationManager, Message, Conversation
from pathlib import Path


# --------------------------------------------------------------------
# Test: Message serialization / deserialization
# --------------------------------------------------------------------
def test_message_to_and_from_dict():
    msg = Message(role="user", content="Hello")
    data = msg.to_dict()
    restored = Message.from_dict(data)

    assert restored.role == msg.role
    assert restored.content == msg.content
    assert isinstance(restored.timestamp, type(msg.timestamp))

# --------------------------------------------------------------------
# Test: Conversation to_dict / from_dict
# --------------------------------------------------------------------
def test_conversation_serialization():
    msg = Message(role="assistant", content="Hi user")
    conv = Conversation(model="test", messages=[msg])
    data = conv.to_dict()
    restored = Conversation.from_dict(data)

    assert restored.model == "test"
    assert restored.messages[0].content == "Hi user"
    assert isinstance(restored.created_at, type(conv.created_at))

# --------------------------------------------------------------------
# Test: ConversationManager basic message flow
# --------------------------------------------------------------------
def test_add_and_retrieve_messages():
    mgr = ConversationManager(model="llama3.2:3b")
    mgr.add_system_message("System ready!")
    mgr.add_user_message("Hello, what can you do?")
    mgr.add_assistant_message("I can explain things.")

    msgs = mgr.get_messages()
    assert len(msgs) == 3
    assert msgs[0].role == "system"
    assert msgs[1].role == "user"
    assert msgs[2].role == "assistant"

    # build context should contain all parts
    ctx = mgr.build_context()
    assert "System" in ctx and "User" in ctx and "Assistant" in ctx

# --------------------------------------------------------------------
# Test: build_prompt output correctness
# --------------------------------------------------------------------
def test_build_prompt_contains_roles():
    mgr = ConversationManager(model="llama3.2:3b")
    mgr.add_user_message("What is recursion?")
    prompt = mgr.build_prompt("Explain again.")
    assert prompt.startswith("User:")
    assert "Assistant:" in prompt

# --------------------------------------------------------------------
# Test: save_to_file and load_from_file using tmp_path
# --------------------------------------------------------------------
def test_save_and_load_conversation(tmp_path: Path):
    mgr = ConversationManager(model="llama3.2:3b")
    mgr.add_user_message("Hello AI")
    file_path = tmp_path / "conv.json"

    mgr.save_to_file(file_path)
    assert file_path.exists()

    # load into a new instance
    new_mgr = ConversationManager(model="none")
    new_mgr.load_from_file(file_path)

    assert new_mgr.conversation.model == "llama3.2:3b"
    assert new_mgr.conversation.messages[0].content == "Hello AI"

# --------------------------------------------------------------------
# Test: export_to_text and export_to_markdown
# --------------------------------------------------------------------
def test_export_text_and_markdown(tmp_path: Path):
    mgr = ConversationManager(model="gemma")
    mgr.add_user_message("Test export.")
    txt_path = tmp_path / "conv.txt"
    md_path = tmp_path / "conv.md"

    mgr.export_to_text(txt_path)
    mgr.export_to_markdown(md_path)

    txt_data = txt_path.read_text()
    md_data = md_path.read_text()
    assert "User:" in txt_data
    assert "##" in md_data  # markdown header present

# --------------------------------------------------------------------
# Test: message trimming (max_history)
# --------------------------------------------------------------------
def test_trim_history_respects_limit():
    mgr = ConversationManager(model="gemma", max_history=3)
    # Add more messages than allowed
    for i in range(6):
        mgr.add_user_message(f"Msg {i}")
        mgr.add_assistant_message(f"Reply {i}")

    all_msgs = mgr.get_messages()
    assert len(all_msgs) <= 3
    counts = mgr.get_message_count()
    assert counts["user"] >= 1
    assert counts["assistant"] >= 1

# --------------------------------------------------------------------
# Test: title generation truncation
# --------------------------------------------------------------------
def test_generate_title_truncates_long_text():
    mgr = ConversationManager(model="x")
    long_text = "a" * 100
    title = mgr._generate_title(long_text)
    assert len(title) <= 50
    assert title.endswith("...")

# --------------------------------------------------------------------
# Test: token estimation (roughly proportional to text length)
# --------------------------------------------------------------------
def test_token_estimation():
    mgr = ConversationManager(model="x")
    mgr.add_user_message("12345678")  # 8 chars ≈ 2 tokens
    assert mgr.estimate_tokens() >= 1

# --------------------------------------------------------------------
# Test: get_conversation_info fields completeness
# --------------------------------------------------------------------
def test_conversation_info_fields():
    mgr = ConversationManager(model="x")
    mgr.add_user_message("hi")
    info = mgr.get_conversation_info()

    expected_keys = {
        "id", "title", "model", "message_count",
        "user_messages", "assistant_messages", "created_at"
    }
    assert expected_keys.issubset(set(info.keys()))
    assert isinstance(info["message_count"], int)
