# src/conversation_manager.py

"""
Conversation management for multi-turn dialogues with Ollama.

This module provides context-aware conversation handling with features like
history management, conversation persistence, and context summarization.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from datetime import datetime
from pathlib import Path

import json
import uuid


@dataclass
class Message:
    """Represents a single message in a conversation.
    
    Attributes:
        role: Message role ('user', 'assistant', or 'system')
        content: Message content text
        timestamp: When the message was created
        metadata: Additional metadata (tokens, model info, etc.)
    """
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """ Convert message to dictionary """
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """ Create message from dictionary """
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {})
        )


@dataclass
class Conversation:
    """Represents a complete conversation with metadata.
    
    Attributes:
        id: Unique conversation identifier
        title: Conversation title (auto-generated from first message)
        model: Model used for this conversation
        messages: List of messages in chronological order
        created_at: When conversation started
        updated_at: Last update timestamp
        metadata: Additional conversation metadata
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Conversation"
    model: str = ""
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """ Convert conversation to dictionary """
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
        """ Create conversation from dictionary """
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
    """Manages multi-turn conversations with context.
    
    Features:
    - Context-aware message history
    - Automatic history trimming
    - Conversation persistence (save/load)
    - System message support
    - Token estimation
    - Export to multiple formats
    """
    
    def __init__(
        self,
        model: str,
        max_history: int = 20,
        system_message: Optional[str] = None,
        auto_title: bool = True
    ) -> None:
        """Initialize conversation manager.
        
        Args:
            model: Model to use for generation
            max_history: Maximum number of messages to keep in context
            system_message: Optional system message for context
            auto_title: Auto-generate conversation title from first message
        """
        self.conversation = Conversation(model=model)
        self.max_history = max_history
        self.auto_title = auto_title
        
        # add system message if provided
        if system_message:
            self.add_system_message(system_message)
    
    def add_system_message(self, content: str) -> None:
        """Add or update system message.
        
        Args:
            content: System message content
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
        
        Args:
            content: Message content
            metadata: Optional metadata
            
        Returns:
            Created message object
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
        """Add assistant message to conversation.
        
        Args:
            content: Message content
            metadata: Optional metadata (tokens, model info, etc.)
            
        Returns:
            Created message object
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
        """Get conversation messages.
        
        Args:
            include_system: Include system message
            last_n: Return only last N messages
            
        Returns:
            List of messages
        """
        messages = self.conversation.messages
        
        if not include_system:
            messages = [msg for msg in messages if msg.role != 'system']
        
        if last_n:
            messages = messages[-last_n:]
        
        return messages
    
    def build_context(self, include_system: bool = True) -> str:
        """Build context string from message history.
        
        Args:
            include_system: Include system message in context
            
        Returns:
            Formatted context string
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
        """Build complete prompt with context for generation.
        
        Args:
            new_message: New user message
            include_system: Include system message
            
        Returns:
            Complete prompt with context
        """
        context = self.build_context(include_system=include_system)
        
        if context:
            return f"{context}\n\nUser: {new_message}\n\nAssistant:"
        else:
            return f"User: {new_message}\n\nAssistant:"
    
    def clear_history(self, keep_system: bool = True) -> None:
        """Clear conversation history.
        
        Args:
            keep_system: Keep system message
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
            Dictionary with counts per role
        """
        counts = {'user': 0, 'assistant': 0, 'system': 0}
        for msg in self.conversation.messages:
            if msg.role in counts:
                counts[msg.role] += 1
        return counts
    
    def estimate_tokens(self) -> int:
        """Estimate total tokens in conversation.
        
        Returns:
            Estimated token count
        """
        total_chars = sum(len(msg.content) for msg in self.conversation.messages)
        # Rough estimation: 1 token ≈ 4 characters
        return total_chars // 4
    
    def save_to_file(self, filepath: Path) -> None:
        """Save conversation to JSON file.
        
        Args:
            filepath: Path to save file
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.conversation.to_dict(), f, indent=2, ensure_ascii=False)
    
    def load_from_file(self, filepath: Path) -> None:
        """Load conversation from JSON file.
        
        Args:
            filepath: Path to load file
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.conversation = Conversation.from_dict(data)
    
    def export_to_markdown(self, filepath: Path) -> None:
        """Export conversation to Markdown format.
        
        Args:
            filepath: Path to save file
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
        """Export conversation to plain text.
        
        Args:
            filepath: Path to save file
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.build_context(include_system=True))
    
    def get_conversation_info(self) -> Dict[str, Any]:
        """Get conversation information summary.
        
        Returns:
            Dictionary with conversation stats
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
        """ Trim history to max_history length, preserving system messages """
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
        """ Update conversation timestamp """
        self.conversation.updated_at = datetime.now()
    
    def _generate_title(self, first_message: str, max_length: int = 50) -> str:
        """Generate conversation title from first message.
        
        Args:
            first_message: First user message
            max_length: Maximum title length
            
        Returns:
            Generated title
        """
        # clean and truncate
        title = first_message.strip()
        if len(title) > max_length:
            title = title[:max_length - 3] + "..."
        
        # capitalize first letter
        if title:
            title = title[0].upper() + title[1:]
        
        return title or "New Conversation"
