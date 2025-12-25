# src/modules/conversation_manager.py

'''
Conversation manager for multi-turn dialogues with Ollama
  This module manages context-aware conversations with history management and persistence.

- Manages message history with configurable maximum
- Supports system, user, and assistant messages
- Automatically trims history while retaining system messages
- Saves and loads conversations as JSON
- Exports dialogs in Markdown and plain text formats
- Automatically generates conversation titles from the first message
- Estimates token count for context management
- Provides context string building for prompts with complete history
'''

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import json
import uuid


@dataclass
class Message:
    """Represents a single message in a conversation.
    
    Stores message content along with metadata like role, timestamp,
    and additional information (tokens, model info, etc.).
    
    Attributes:
        role: Message role ('user', 'assistant', or 'system')
        content: Message content text
        timestamp: When the message was created (auto-generated)
        metadata: Additional metadata dictionary (tokens, model info, etc.)
    """
    
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization.
        
        Returns:
            Dictionary with all message fields, timestamp as ISO string
        """
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary (deserialization).
        
        Args:
            data: Dictionary with message fields
            
        Returns:
            Message instance reconstructed from dictionary
        """
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {})
        )


@dataclass
class Conversation:
    """Represents a complete conversation with metadata.
    
    Contains all messages in a conversation along with identifying
    information, timestamps, and metadata.
    
    Attributes:
        id: Unique conversation identifier (auto-generated UUID)
        title: Conversation title (auto-generated from first message or custom)
        model: Model name used for this conversation
        messages: List of Message objects in chronological order
        created_at: When conversation was started (auto-generated)
        updated_at: Last update timestamp (auto-updated)
        metadata: Additional conversation-level metadata
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Conversation"
    model: str = ""
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary for serialization.
        
        Returns:
            Dictionary with all conversation fields and nested messages
        """
        return {
            'id': self.id,
            'title': self.title,
            'model': self.model,
            'messages': [msg.to_dict() for msg in self.messages],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """Create conversation from dictionary (deserialization).
        
        Args:
            data: Dictionary with conversation fields
            
        Returns:
            Conversation instance reconstructed from dictionary
        """
        return cls(
            id=data['id'],
            title=data['title'],
            model=data['model'],
            messages=[Message.from_dict(msg) for msg in data['messages']],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            metadata=data.get('metadata', {})
        )


class ConversationManager:
    """Manages multi-turn conversations with context and history.
    
    Provides high-level interface for managing conversational context,
    including message history, automatic trimming, persistence, and
    export functionality.
    
    Features:
        - Context-aware message history management
        - Automatic history trimming with system message preservation
        - Conversation persistence (JSON save/load)
        - System message support for model instructions
        - Token estimation for context management
        - Export to Markdown and plain text formats
        - Auto-generated conversation titles
        
    Attributes:
        conversation: Current Conversation instance
        max_history: Maximum number of messages to keep in context
        auto_title: Whether to auto-generate titles from first message
    """
    
    def __init__(
        self,
        model: str,
        max_history: int = 20,
        system_message: Optional[str] = None,
        auto_title: bool = True
    ) -> None:
        """Initialize conversation manager with configuration.
        
        Args:
            model: Model name to use for generation (e.g., 'llama3.2:3b')
            max_history: Maximum messages to keep (older ones trimmed automatically)
            system_message: Optional system message for context/instructions
            auto_title: Auto-generate conversation title from first user message
        """
        self.conversation = Conversation(model=model)
        self.max_history = max_history
        self.auto_title = auto_title
        
        # add system message if provided
        if system_message:
            self.add_system_message(system_message)
    
    def add_system_message(self, content: str) -> None:
        """Add or update system message at the beginning of conversation.
        
        System messages provide instructions/context to the model and are
        preserved during history trimming. Only one system message is kept
        (new one replaces old).
        
        Args:
            content: System message content (instructions for the model)
            
        Side Effects:
            - Removes any existing system messages
            - Adds new system message at position 0
            - Updates conversation timestamp
        """
        # remove existing system messages
        self.conversation.messages = [
            msg for msg in self.conversation.messages 
            if msg.role != 'system'
        ]
        
        # add new system message at the beginning
        system_msg = Message(role='system', content=content)
        self.conversation.messages.insert(0, system_msg)
        self._update_timestamp()
    
    def add_user_message(self, content: str, metadata: Optional[Dict] = None) -> Message:
        """Add user message to conversation.
        
        Appends user message and triggers auto-title generation if this
        is the first user message.
        
        Args:
            content: User message text
            metadata: Optional metadata (e.g., input_tokens)
            
        Returns:
            Created Message object
            
        Side Effects:
            - Generates conversation title from first user message (if auto_title=True)
            - Triggers history trimming if max_history exceeded
            - Updates conversation timestamp
        """
        message = Message(
            role='user',
            content=content,
            metadata=metadata or {}
        )
        self.conversation.messages.append(message)
        
        # auto-generate title from first user message
        if self.auto_title and self.conversation.title == "New Conversation":
            self.conversation.title = self._generate_title(content)
        
        self._trim_history()
        self._update_timestamp()
        return message
    
    def add_assistant_message(self, content: str, metadata: Optional[Dict] = None) -> Message:
        """Add assistant (model) message to conversation.
        
        Args:
            content: Assistant response text
            metadata: Optional metadata (e.g., generation_tokens, model_used)
            
        Returns:
            Created Message object
            
        Side Effects:
            - Triggers history trimming if max_history exceeded
            - Updates conversation timestamp
        """
        message = Message(
            role='assistant',
            content=content,
            metadata=metadata or {}
        )
        self.conversation.messages.append(message)
        self._trim_history()
        self._update_timestamp()
        return message
    
    def get_messages(
        self,
        include_system: bool = True,
        last_n: Optional[int] = None
    ) -> List[Message]:
        """Get conversation messages with optional filtering.
        
        Args:
            include_system: Include system message in results
            last_n: Return only last N messages (after filtering)
            
        Returns:
            List of Message objects matching criteria
        """
        messages = self.conversation.messages
        
        if not include_system:
            messages = [msg for msg in messages if msg.role != 'system']
        
        if last_n:
            messages = messages[-last_n:]
        
        return messages
    
    def build_context(self, include_system: bool = True) -> str:
        """Build formatted context string from message history.
        
        Creates human-readable representation of conversation with
        role labels.
        
        Args:
            include_system: Include system message in context
            
        Returns:
            Formatted context string with "Role: Content" format
        """
        messages = self.get_messages(include_system=include_system)
        
        context_parts = []
        for msg in messages:
            role = msg.role.capitalize()
            context_parts.append(f"{role}: {msg.content}")
        
        return "\n\n".join(context_parts)
    
    def build_prompt(
        self,
        new_message: str,
        include_system: bool = True
    ) -> str:
        """Build complete prompt with conversation context for generation.
        
        Combines conversation history with new user message to create
        complete prompt for model generation.
        
        Args:
            new_message: New user message to append
            include_system: Include system message in prompt
            
        Returns:
            Complete prompt string ready for generation
        """
        context = self.build_context(include_system=include_system)
        
        if context:
            return f"{context}\n\nUser: {new_message}\n\nAssistant:"
        else:
            return f"User: {new_message}\n\nAssistant:"
    
    def clear_history(self, keep_system: bool = True) -> None:
        """Clear conversation history.
        
        Removes all messages, optionally preserving system message.
        
        Args:
            keep_system: Keep system message if present
            
        Side Effects:
            - Clears message list
            - Updates conversation timestamp
        """
        if keep_system:
            system_messages = [
                msg for msg in self.conversation.messages 
                if msg.role == 'system'
            ]
            self.conversation.messages = system_messages
        else:
            self.conversation.messages = []
        
        self._update_timestamp()
    
    def get_message_count(self) -> Dict[str, int]:
        """Get message count by role.
        
        Returns:
            Dictionary with counts: {'user': X, 'assistant': Y, 'system': Z}
        """
        counts = {'user': 0, 'assistant': 0, 'system': 0}
        for msg in self.conversation.messages:
            if msg.role in counts:
                counts[msg.role] += 1
        return counts
    
    def estimate_tokens(self) -> int:
        """Estimate total tokens in conversation.
        
        Uses rough heuristic: ~1.3 tokens per word. For accurate counts,
        use proper tokenizer.
        
        Returns:
            Estimated token count for entire conversation
        
        Note:
            This is a rough approximation. For precise token counts,
            use the model's actual tokenizer.
        """
        # rough estimation: ~1.3 tokens per word
        words = sum(len(msg.content.split()) for msg in self.conversation.messages)
        return int(words * 1.3)
    
    def save_to_file(self, filepath: Path) -> None:
        """Save conversation to JSON file.
        
        Creates parent directories if they don't exist.
        
        Args:
            filepath: Path where to save conversation
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.conversation.to_dict(), f, indent=2, ensure_ascii=False)
    
    def load_from_file(self, filepath: Path) -> None:
        """Load conversation from JSON file.
        
        Replaces current conversation with loaded one.
        
        Args:
            filepath: Path to conversation file
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.conversation = Conversation.from_dict(data)
    
    def export_to_markdown(self, filepath: Path) -> None:
        """Export conversation to formatted Markdown file.
        
        Creates human-readable Markdown with headers, metadata, and
        emoji icons for different roles.
        
        Args:
            filepath: Path where to save Markdown file
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        lines = [
            f"# {self.conversation.title}",
            f"",
            f"**Model:** {self.conversation.model}",
            f"**Created:** {self.conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Messages:** {len(self.conversation.messages)}",
            f"",
            "---",
            ""
        ]
        
        for msg in self.conversation.messages:
            role_icon = {
                'user': '👤',
                'assistant': '🤖',
                'system': '⚙️'
            }.get(msg.role, '❓')
            
            lines.append(f"## {role_icon} {msg.role.capitalize()}")
            lines.append(f"")
            lines.append(msg.content)
            lines.append(f"")
            lines.append(f"*{msg.timestamp.strftime('%H:%M:%S')}*")
            lines.append(f"")
            lines.append("---")
            lines.append(f"")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def export_to_text(self, filepath: Path) -> None:
        """Export conversation to plain text file.
        
        Creates simple text file with conversation context.
        
        Args:
            filepath: Path where to save text file
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.build_context(include_system=True))
    
    def get_conversation_info(self) -> Dict[str, Any]:
        """Get conversation information summary.
        
        Returns:
            Dictionary with conversation statistics including:
                - id: Conversation UUID
                - title: Conversation title
                - model: Model name
                - message_count: Total messages
                - user_messages: User message count
                - assistant_messages: Assistant message count
                - system_messages: System message count
                - estimated_tokens: Estimated token count
                - created_at: Creation timestamp (ISO format)
                - updated_at: Last update timestamp (ISO format)
        """
        counts = self.get_message_count()
        
        return {
            'id': self.conversation.id,
            'title': self.conversation.title,
            'model': self.conversation.model,
            'message_count': len(self.conversation.messages),
            'user_messages': counts['user'],
            'assistant_messages': counts['assistant'],
            'system_messages': counts['system'],
            'estimated_tokens': self.estimate_tokens(),
            'created_at': self.conversation.created_at.isoformat(),
            'updated_at': self.conversation.updated_at.isoformat()
        }
    
    def _trim_history(self) -> None:
        """Trim history to max_history length while preserving system messages.
        
        Keeps system messages and the most recent non-system messages
        up to max_history total count.
        
        Note:
            This is called automatically after adding messages.
        """
        if len(self.conversation.messages) <= self.max_history:
            return
        
        # separate system messages from conversation
        system_messages = [
            msg for msg in self.conversation.messages 
            if msg.role == 'system'
        ]
        other_messages = [
            msg for msg in self.conversation.messages 
            if msg.role != 'system'
        ]
        
        # keep only last N non-system messages
        available_slots = self.max_history - len(system_messages)
        if available_slots > 0:
            other_messages = other_messages[-available_slots:]
        
        # reconstruct message list
        self.conversation.messages = system_messages + other_messages
    
    def _update_timestamp(self) -> None:
        """Update conversation's updated_at timestamp to current time.
        
        Note:
            Called automatically after modifying conversation.
        """
        self.conversation.updated_at = datetime.now()
    
    def _generate_title(self, first_message: str, max_length: int = 50) -> str:
        """Generate conversation title from first user message.
        
        Truncates long messages and capitalizes first letter.
        
        Args:
            first_message: First user message content
            max_length: Maximum title length (default: 50)
            
        Returns:
            Generated title string
        """
        # clean and truncate
        title = first_message.strip()
        if len(title) > max_length:
            title = title[:max_length - 3] + "..."
        
        # capitalize first letter
        if title:
            title = title[0].upper() + title[1:]
        
        return title or "New Conversation"
