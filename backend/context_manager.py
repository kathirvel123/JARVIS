import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from collections import deque

@dataclass
class ConversationTurn:
    """Represents a single conversation turn"""
    timestamp: str
    user_input: str
    assistant_response: str
    session_id: str
    context_type: str = "general"  # general, task, reminder, etc.

@dataclass
class UserProfile:
    """User profile and preferences"""
    name: str = "Sir"
    preferences: Dict[str, Any] = None
    frequently_used_commands: List[str] = None
    last_interaction: str = None
    
    def __post_init__(self):
        if self.preferences is None:
            self.preferences = {}
        if self.frequently_used_commands is None:
            self.frequently_used_commands = []

class ContextManager:
    """Manages conversation context and memory"""
    
    def __init__(self, context_file="context_memory.json", max_history=100):
        self.context_file = context_file
        self.max_history = max_history
        self.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # In-memory storage for current session
        self.current_session = deque(maxlen=5)  # Keep last 5 turns in memory
        self.history = []  # Store all conversations
        self.user_profile = UserProfile()
        
        # Load existing context
        self._load_context()
        
    def _load_context(self):
        """Load context from file"""
        try:
            if os.path.exists(self.context_file):
                with open(self.context_file, 'r') as f:
                    data = json.load(f)
                    
                # Load user profile
                if 'user_profile' in data:
                    profile_data = data['user_profile']
                    self.user_profile = UserProfile(**profile_data)
                
                # Load recent conversations (last 24 hours)
                recent_cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
                if 'conversations' in data:
                    self.history = [ConversationTurn(**turn) for turn in data['conversations']]
                    # Add recent conversations to current session context
                    self.current_session.extend(self.history[-5:])
                    
        except Exception as e:
            print(f"⚠️ Error loading context: {e}")
            
    def _save_context(self):
        """Save context to file"""
        try:
            # Load existing data
            existing_data = {}
            if os.path.exists(self.context_file):
                with open(self.context_file, 'r') as f:
                    existing_data = json.load(f)
            
            # Update with current data
            existing_data['user_profile'] = asdict(self.user_profile)
            
            # Merge conversations
            if 'conversations' not in existing_data:
                existing_data['conversations'] = []
            
            # Add current session turns
            existing_data['conversations'] = [asdict(turn) for turn in self.history]
            
            # Keep only recent conversations to manage file size
            existing_data['conversations'] = existing_data['conversations'][-self.max_history:]
            
            # Save to file
            with open(self.context_file, 'w') as f:
                json.dump(existing_data, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Error saving context: {e}")
    
    def add_conversation_turn(self, user_input: str, assistant_response: str, context_type: str = "general"):
        """Add a conversation turn to memory"""
        turn = ConversationTurn(
            timestamp=datetime.now().isoformat(),
            user_input=user_input,
            assistant_response=assistant_response,
            session_id=self.current_session_id,
            context_type=context_type
        )
        
        self.current_session.append(turn)
        self.history.append(turn)
        
        # Update user profile
        self.user_profile.last_interaction = turn.timestamp
        self._update_user_preferences(user_input)
        
        # Auto-save every few turns
        if len(self.current_session) % 5 == 0:
            self._save_context()
    
    def _update_user_preferences(self, user_input: str):
        """Update user preferences based on input"""
        # Track frequently used commands
        command_keywords = ['create', 'write', 'read', 'execute', 'remind', 'list']
        for keyword in command_keywords:
            if keyword in user_input.lower():
                if keyword not in self.user_profile.frequently_used_commands:
                    self.user_profile.frequently_used_commands.append(keyword)
                elif len(self.user_profile.frequently_used_commands) > 10:
                    # Keep only top 10 most recent
                    self.user_profile.frequently_used_commands = \
                        self.user_profile.frequently_used_commands[-10:]
    
    def get_context_summary(self) -> str:
        """Get a summary of recent context for the agent"""
        if not self.current_session:
            return "No previous conversation context available."
        
        # Get last few turns for context
        recent_turns = list(self.current_session)[-5:]  # Last 5 turns
        
        context_summary = "## Recent Conversation Context:\n"
        for turn in recent_turns:
            # Truncate long responses for context
            response_preview = turn.assistant_response[:100] + "..." if len(turn.assistant_response) > 100 else turn.assistant_response
            context_summary += f"User: {turn.user_input}\nAssistant: {response_preview}\n---\n"
        
        # Add user preferences
        if self.user_profile.frequently_used_commands:
            context_summary += f"\n## User frequently uses: {', '.join(self.user_profile.frequently_used_commands[-5:])}\n"
        
        return context_summary
    
    def get_relevant_context(self, current_input: str) -> str:
        """Get context relevant to the current input"""
        if not self.current_session:
            return ""
        
        relevant_turns = []
        current_lower = current_input.lower()
        
        # Look for related previous conversations
        for turn in reversed(self.history):
            if any(word in turn.user_input.lower() for word in current_lower.split()):
                relevant_turns.append(turn)
                if len(relevant_turns) >= 3:  # Limit to 3 most relevant
                    break
        
        if not relevant_turns:
            return ""
        
        context = "## Relevant Previous Context:\n"
        for turn in reversed(relevant_turns):  # Most recent first
            context += f"Previously - User: {turn.user_input}\nAssistant: {turn.assistant_response[:150]}...\n---\n"
        
        return context
    
    def save_session(self):
        """Manually save the current session"""
        self._save_context()
        print("✅ Context saved successfully")
    
    def clear_session(self):
        """Clear current session but keep user profile"""
        self.current_session.clear()
        self.history.clear()
        self.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        print("✅ Current session cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context statistics"""
        return {
            "current_session_turns": len(self.current_session),
            "session_id": self.current_session_id,
            "user_name": self.user_profile.name,
            "frequently_used_commands": self.user_profile.frequently_used_commands[-5:],
            "last_interaction": self.user_profile.last_interaction
        }
    
    def clean_context_file(self):
        """Cleans the context file by writing an empty JSON object."""
        try:
            with open(self.context_file, 'w') as f:
                json.dump({}, f)
            print("✅ Context memory file cleaned.")
            # Reset in-memory state
            self.current_session.clear()
            self.user_profile = UserProfile()
            self.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        except Exception as e:
            print(f"⚠️ Error cleaning context file: {e}")