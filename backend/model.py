# model.py (updated section with proper RemoteTools integration)
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
import google.generativeai as genai
import os
from tools.localtools import (
    create_folder, create_file, write_file, read_file, execute_command, list_directory,
    create_reminder, list_reminders,
    get_current_time
)
from tools.remotetools import RemoteToolsManager  # Import our new RemoteToolsManager
from context_manager import ContextManager

# Load environment variables
load_dotenv()

# Initialize Context Manager
context_manager = ContextManager()

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)

# Add context-aware tools
@tool
def save_context() -> str:
    """Save the current conversation context to memory."""
    context_manager.save_session()
    return "✅ Context saved successfully."

@tool
def clear_context() -> str:
    """Clear the current conversation context."""
    context_manager.clear_session()
    return "✅ Context cleared successfully."

@tool
def get_context_stats() -> str:
    """Get statistics about the current context and memory."""
    stats = context_manager.get_stats()
    return f"""📊 Context Statistics:
- Session turns: {stats['current_session_turns']}
- Session ID: {stats['session_id']}
- User: {stats['user_name']}
- Frequent commands: {', '.join(stats['frequently_used_commands'])}
- Last interaction: {stats['last_interaction']}"""

# Local tools
local_tools = [
    create_folder, create_file, write_file, read_file,
    execute_command, list_directory,
    create_reminder, list_reminders,
    get_current_time, save_context, clear_context, get_context_stats
]

# Initialize and load remote tools
remote_tools_manager = None
remote_tools = []

def initialize_remote_tools(base_url: str = "http://localhost:8000"):
    """Initialize remote tools manager and discover tools"""
    global remote_tools_manager, remote_tools
    
    try:
        print("🔄 Initializing remote tools...")
        remote_tools_manager = RemoteToolsManager(base_url)
        
        # Check if server is accessible
        if remote_tools_manager.health_check():
            print("✅ Remote tools server is accessible")
            
            # Discover and register tools
            if remote_tools_manager.discover_tools():
                remote_tools = remote_tools_manager.get_tools()
                print(f"✅ Loaded {len(remote_tools)} remote tools")
                
                # List available remote tools
                available_tools = remote_tools_manager.list_available_tools()
                if available_tools:
                    print("📋 Available remote tools:")
                    for name, desc in available_tools.items():
                        print(f"  • {name}: {desc}")
                
                return True
            else:
                print("❌ Failed to discover remote tools")
                return False
        else:
            print("❌ Remote tools server is not accessible")
            return False
            
    except Exception as e:
        print(f"❌ Error initializing remote tools: {e}")
        return False

# Initialize remote tools at startup
initialize_remote_tools()

# Combine all tools
all_tools = local_tools + remote_tools

# Add tool to list available tools
@tool
def list_available_tools() -> str:
    """List all available local and remote tools with their descriptions."""
    result = "🛠️ Available Tools:\n\n"
    
    # Local tools
    result += "📍 LOCAL TOOLS:\n"
    for tool_obj in local_tools:
        result += f"  • {tool_obj.name}: {tool_obj.description}\n"
    
    # Remote tools
    if remote_tools_manager and remote_tools:
        result += "\n🌐 REMOTE TOOLS:\n"
        available_remote = remote_tools_manager.list_available_tools()
        for name, desc in available_remote.items():
            result += f"  • {name}: {desc}\n"
    else:
        result += "\n🌐 REMOTE TOOLS: None available (server not accessible)\n"
    
    result += f"\n📊 Total tools: {len(all_tools)}"
    return result

# Add the tool listing to available tools
all_tools.append(list_available_tools)

def create_context_aware_agent():
    """Create an agent with context awareness and both local and remote tools"""
    
    # Build comprehensive tool descriptions
    tool_descriptions = []
    
    # Add local tools
    for tool_obj in local_tools:
        tool_descriptions.append(f"- {tool_obj.name}: {tool_obj.description}")
    
    # Add remote tools
    if remote_tools_manager and remote_tools:
        available_remote = remote_tools_manager.list_available_tools()
        for name, desc in available_remote.items():
            tool_descriptions.append(f"- {name}: {desc}")
    
    tool_descriptions_text = "\n".join(tool_descriptions)
    
    system_message = f"""You are JARVIS, an intelligent AI assistant with persistent memory, context awareness, and access to both local and remote tools.

Key capabilities:
- Remember previous conversations and maintain context across sessions
- Learn user preferences and adapt responses accordingly
- Provide personalized assistance based on conversation history
- Execute various tasks using local system tools (file management, reminders, commands)
- Access remote services and APIs through dynamic remote tools
- Handle complex workflows that may require multiple tools

Available Tools ({len(all_tools)} total):
{tool_descriptions_text}

Context Guidelines:
- Always consider previous conversation context when responding
- Reference relevant past interactions when appropriate
- Adapt your communication style based on user preferences
- Maintain continuity in ongoing tasks or projects
- Be proactive in suggesting relevant actions based on history

Tool Usage Guidelines:
- Use the most appropriate tool(s) to fulfill user requests
- For remote tools, handle any connection issues gracefully
- Chain multiple tools together when necessary for complex tasks
- Always provide clear feedback about tool execution results
- If a remote tool fails, try alternative approaches or inform the user

Personality:
- Professional yet friendly, like a capable personal assistant
- Proactive and anticipatory of user needs
- Respectful and always address the user appropriately
- Efficient and focused on providing value
- Adaptable to both simple queries and complex multi-step tasks

Always provide helpful, accurate, and contextually relevant responses while efficiently using available tools to accomplish tasks."""
    
    return create_react_agent(llm, all_tools, prompt=system_message)

# Create the agent
agent = create_context_aware_agent()

def configure_genai():
    """Configures the Generative AI model with the API key."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)

def get_gemini_model(model_name="gemini-1.5-flash"):
    """Returns a Gemini generative model."""
    configure_genai()
    return genai.GenerativeModel(model_name)

def generate_text(prompt: str) -> str:
    """Generates text using the Gemini 1.5 Flash model."""
    model = get_gemini_model()
    print(prompt)
    response = model.generate_content(prompt)
    return response.text

def process_voice_command(command):
    """Process voice command through the agent with context awareness and tool access"""
    try:
        # Get relevant context for this command
        context_summary = context_manager.get_context_summary()
        relevant_context = context_manager.get_relevant_context(command)
        
        # Check remote tools connectivity before processing
        remote_status = "available" if (remote_tools_manager and remote_tools_manager.health_check()) else "unavailable"
        
        # Build comprehensive tool descriptions
        tool_descriptions = []
        
        # Add local tools
        for tool_obj in local_tools:
            tool_descriptions.append(f"- {tool_obj.name}: {tool_obj.description}")
        
        # Add remote tools if available
        if remote_tools_manager and remote_tools:
            available_remote = remote_tools_manager.list_available_tools()
            for name, desc in available_remote.items():
                tool_descriptions.append(f"- {name}: {desc}")
        
        tool_descriptions_text = "\n".join(tool_descriptions)
        
        # Create a comprehensive system prompt with context
        system_prompt = f"""You are JARVIS, an intelligent AI assistant with persistent memory, context awareness, and access to both local and remote tools.

Core Objective:
- Always attempt to perform any task the user requests by leveraging the available tools.
- Use both local system tools and remote API tools as appropriate for the task.
- If multiple tools are relevant, decide the best one(s) to use or chain them effectively.
- When no direct tool is available, provide the most useful guidance, steps, or alternatives.

Key Capabilities:
- Remember previous conversations and maintain context across sessions.
- Learn and adapt to user preferences over time.
- Provide personalized and contextually relevant assistance.
- Execute tasks through local tools (file system, commands, reminders, etc.).
- Access remote services and APIs for extended functionality.
- Handle tool failures gracefully and provide alternatives.

Tool Usage:
- Use tools proactively to complete the user's instructions.
- Local tools are always available for system operations.
- Remote tools are currently {remote_status} for API operations.
- If remote tools are unavailable, inform user and suggest alternatives.
- Chain multiple tools when needed for complex workflows.
- Always prefer action over explanation when possible.

Available Tools ({len(all_tools)} total):
{tool_descriptions_text}

Context Guidelines:
- Always consider previous conversation history when responding.
- Reference relevant past interactions naturally in your replies.
- Maintain continuity in ongoing tasks or projects.
- Be proactive in suggesting actions or follow-ups based on prior context.

Personality:
- Professional yet approachable, like a trusted personal assistant.
- Respectful and polite while remaining efficient and action-focused.
- Proactive, anticipating user needs and offering helpful suggestions.
- Communicate clearly, adapting tone and style to the user's preferences.

Golden Rule:
Always strive to *do* what the user asks by executing tasks with available tools, maintaining context, and providing accurate, helpful, and actionable responses.

Remote Tools Status: {remote_status.upper()}
"""
        
        result = agent.invoke({"messages": [("system", system_prompt), ("user", command)]})
        
        if result and result.get('messages') and len(result['messages']) > 0:
            response = result['messages'][-1].content
            
            # Add this conversation turn to memory
            context_manager.add_conversation_turn(command, response)
            
            return response
        else:
            return "Sorry, I couldn't process that. The agent returned an empty response."
            
    except Exception as e:
        error_response = f"Sorry, I encountered an error: {str(e)}"
        # Still save the interaction even if there was an error
        context_manager.add_conversation_turn(command, error_response)
        return error_response

def classify_and_summarize_response(response: str) -> dict:
    """Classifies the agent's response and decides whether to speak the full response or a summary."""
    # Enhanced logic considering context
    user_stats = context_manager.get_stats()
    
    # If user frequently uses brief commands, provide shorter responses
    if len(user_stats['frequently_used_commands']) > 3 and len(response) > 300:
        prompt = f"""The user frequently uses commands like: {', '.join(user_stats['frequently_used_commands'])}
        
        Summarize this response for voice output, keeping it concise and focused on the key information:
        
        "{response}"
        
        Voice Summary:"""
        
        summary = generate_text(prompt)
        return {"speak_full_response": False, "spoken_response": summary}
    elif len(response) > 200:
        # Standard summarization for long responses
        prompt = f"""Summarize the following text for a voice assistant to speak. The summary should be concise and natural.
        Text: "{response}"
        Summary:"""
        summary = generate_text(prompt)
        return {"speak_full_response": False, "spoken_response": summary}
    else:
        return {"speak_full_response": True, "spoken_response": response}

def get_tool_status():
    """Get status of all tools"""
    status = {
        "local_tools": len(local_tools),
        "remote_tools": len(remote_tools),
        "remote_server_status": "connected" if (remote_tools_manager and remote_tools_manager.health_check()) else "disconnected",
        "total_tools": len(all_tools)
    }
    return status

# Utility function to refresh remote tools
def refresh_remote_tools():
    """Refresh remote tools connection and discovery"""
    global remote_tools, all_tools
    
    print("🔄 Refreshing remote tools...")
    if initialize_remote_tools():
        # Update combined tools list
        all_tools = local_tools + remote_tools + [list_available_tools]
        
        # Recreate agent with updated tools
        global agent
        agent = create_context_aware_agent()
        
        print("✅ Remote tools refreshed successfully")
        return True
    else:
        print("❌ Failed to refresh remote tools")
        return False