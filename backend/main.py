import sys
sys.path.append('/home/kathir/Documents/ProjectEND/')
import threading
from PyQt5.QtWidgets import QApplication
from yi import SiriVoiceWidget

from model import (
    process_voice_command, classify_and_summarize_response, context_manager,
    get_tool_status, refresh_remote_tools
)
from voicetalk.speech_to_text import listen_for_wakeword, record_and_transcribe
from voicetalk.text_to_speech import speak
from tools.localtools import start_reminder_scheduler, reminder_scheduler_running

def display_startup_info():
    """Display enhanced startup information including remote tools status"""
    print("🚀 Starting JARVIS Voice Assistant with Enhanced Capabilities...")
    print("=" * 80)
    print("🎯 Core Features:")
    print("✓ Wake word detection ('Hey JARVIS', 'JARVIS', etc.)")
    print("✓ Voice commands with speech-to-text")
    print("✓ Text-to-speech responses")
    print("✓ 🧠 Persistent context memory and learning")
    print("✓ 🔄 Conversation continuity across sessions")
    print()
    
    print("🛠️ Local Tools:")
    print("✓ File management (create, read, write, list)")
    print("✓ Command execution and terminal access")
    print("✓ Smart reminders with notifications")
    print("✓ System information and utilities")
    print("✓ Context management (save, clear, stats)")
    print()
    
    # Get and display tool status
    tool_status = get_tool_status()
    print("🌐 Tool Status:")
    print(f"📍 Local tools: {tool_status['local_tools']} available")
    print(f"🌍 Remote tools: {tool_status['remote_tools']} available")
    print(f"🔗 Remote server: {tool_status['remote_server_status']}")
    print(f"📊 Total tools: {tool_status['total_tools']}")
    print()
    
    if tool_status['remote_server_status'] == 'connected':
        print("🎉 Full capability mode - All tools available!")
    else:
        print("⚠️  Limited mode - Remote tools unavailable (server not running)")
        print("   Local tools still fully functional")
    
    print("\nSay 'Hey JARVIS' to wake me up!")
    print("=" * 80)

def handle_system_commands(command: str) -> bool:
    """Handle special system commands that don't require agent processing"""
    command_lower = command.lower()
    
    # Tool status command
    if any(phrase in command_lower for phrase in ['tool status', 'check tools', 'list tools']):
        tool_status = get_tool_status()
        response = f"""🛠️ Tool Status Report:
        
📍 Local Tools: {tool_status['local_tools']} available
🌍 Remote Tools: {tool_status['remote_tools']} available  
🔗 Server Status: {tool_status['remote_server_status']}
📊 Total Tools: {tool_status['total_tools']}

Status: {'All systems operational' if tool_status['remote_server_status'] == 'connected' else 'Limited mode (remote server disconnected)'}"""
        
        print(f"🤖 JARVIS: {response}")
        speak("Tool status displayed. All local tools are operational." + 
              (" Remote tools are also connected." if tool_status['remote_server_status'] == 'connected' 
               else " Remote tools are currently unavailable."))
        return True
    
    # Refresh remote tools command
    elif any(phrase in command_lower for phrase in ['refresh tools', 'reconnect tools', 'retry remote']):
        print("🔄 Refreshing remote tools connection...")
        speak("Refreshing remote tools connection...")
        
        if refresh_remote_tools():
            speak("Remote tools refreshed successfully. All capabilities restored.")
        else:
            speak("Failed to refresh remote tools. Local tools remain available.")
        return True
    
    return False

def main_voice_loop():
    """Enhanced main voice assistant loop with remote tools support"""
    print("\n🤖 JARVIS Voice Assistant Ready!")
    print("🧠 Context memory enabled - I'll remember our conversations!")
    
    # Load any existing context
    stats = context_manager.get_stats()
    if stats['current_session_turns'] > 0:
        print(f"📚 Loaded {stats['current_session_turns']} previous conversation turns")
    
    # Check initial tool status
    tool_status = get_tool_status()
    if tool_status['remote_server_status'] == 'connected':
        print("🎉 All tools are ready - full capability mode!")
    else:
        print("⚠️  Remote tools unavailable - operating in local mode")
        print("   (You can say 'refresh tools' to retry remote connection)")
    
    while True:
        try:
            # Wait silently for wakeword
            print("👂 Listening for wake word...")
            if not listen_for_wakeword():
                break
            
            if ui_widget:
                ui_widget.show()
                ui_widget.state_changed.emit('listening')

            # Context-aware greeting
            if stats['last_interaction']:
                speak("Welcome back! How may I assist you today?")
            else:
                speak("Yes sir, how may I assist you today?")
            
            # Continue conversation until dismissed
            while True:
                # Listen for user input
                print("\n🎤 Listening for your request...")
                if ui_widget:
                    ui_widget.state_changed.emit('listening')
                command = record_and_transcribe(duration=8)
                # command = input("Enter command: ").strip()
                
                if not command:
                    speak("I didn't hear anything. Could you repeat that?")
                    continue
                
                print(f"💬 You said: {command}")
                
                # Check for dismiss/goodbye commands
                if any(word in command.lower() for word in ['that\'s all', 'thank you', 'thanks', 'goodbye', 'bye', 'dismiss', 'go to sleep', 'sleep mode']):
                    # Save context before dismissing
                    context_manager.save_session()
                    if ui_widget:
                        ui_widget.hide()
                    speak("You're welcome! I'll remember our conversation. Going back to standby mode.")
                    print("😴 Returning to standby...\n")
                    break
                
                # Check for complete exit
                if any(word in command.lower() for word in ['exit', 'quit', 'shutdown']):
                    context_manager.save_session()
                    if ui_widget:
                        ui_widget.close()
                    speak("Goodbye sir! I'll remember everything for next time. Have a wonderful day!")
                    return
                
                # Handle system commands
                if handle_system_commands(command):
                    continue
                
                # Process the command with context and tools
                print("⚙️ Processing your request...")
                if ui_widget:
                    ui_widget.state_changed.emit('processing')
                
                # Show which tools are being considered
                tool_status = get_tool_status()
                if tool_status['remote_server_status'] == 'connected':
                    print(f"🛠️ Using {tool_status['total_tools']} tools (local + remote)")
                else:
                    print(f"🛠️ Using {tool_status['local_tools']} local tools (remote unavailable)")
                
                response = process_voice_command(command)
                print(f"🤖 JARVIS: {response}")
                
                # Classify and speak the response
                if ui_widget:
                    ui_widget.state_changed.emit('speaking')
                spoken_response_data = classify_and_summarize_response(response)
                speak(spoken_response_data["spoken_response"])
                
                # Wait a moment before next input
                print("👂 Ready for your next request...")
                
        except KeyboardInterrupt:
            print("\n🔴 Voice assistant stopped by user.")
            context_manager.save_session()
            if ui_widget:
                ui_widget.close()
            speak("Goodbye sir! Context saved.")
            break
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            if ui_widget:
                ui_widget.close()
            speak("I apologize, I encountered an error. Please try again.")
            continue

def test_tools():
    """Test function to verify both local and remote tools"""
    print("\n🧪 Testing Tool Functionality")
    print("=" * 50)
    
    # Test local tools
    print("📍 Testing local tools...")
    try:
        from tools.localtools import get_current_time, list_directory
        print("✅ Local tools import successful")
        
        # Test a simple local tool
        time_result = get_current_time()
        print(f"✅ Time tool test: {time_result}")
    except Exception as e:
        print(f"❌ Local tools error: {e}")
    
    # Test remote tools
    print("\n🌍 Testing remote tools...")
    tool_status = get_tool_status()
    if tool_status['remote_server_status'] == 'connected':
        print(f"✅ Remote server connected - {tool_status['remote_tools']} tools available")
        
        # You can add specific remote tool tests here
        print("✅ Remote tools ready for use")
    else:
        print("❌ Remote server not connected")
        print("   Make sure your FastAPI server is running on http://localhost:8000")
        print("   You can still use all local tools")
    
    print("=" * 50)

ui_widget = None

def run_ui():
    """Initializes and runs the PyQt5 UI in a separate thread."""
    global ui_widget
    app = QApplication(sys.argv)
    ui_widget = SiriVoiceWidget()
    sys.exit(app.exec_())

if __name__ == "__main__":
    try:
        # Start the UI thread
        ui_thread = threading.Thread(target=run_ui, daemon=True)
        ui_thread.start()

        # Clean the context file at the start of the program
        context_manager.clean_context_file()
        
        # Start reminder scheduler
        start_reminder_scheduler()
        
        # Display startup information
        display_startup_info()
        
        # Optional: Run tool tests
        test_tools()
        
        print("\n" + "=" * 80)
        print("🎤 JARVIS is now listening...")
        print("Say 'Hey JARVIS' to wake me up, or just type your commands!")
        print("Special commands:")
        print("  • 'tool status' - Check tool availability")
        print("  • 'refresh tools' - Reconnect to remote tools")
        print("  • 'list tools' - Show all available tools")
        print("=" * 80)
        
        # Start main voice loop
        main_voice_loop()
        
    except KeyboardInterrupt:
        print("\n👋 JARVIS shutting down...")
        context_manager.save_session()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        context_manager.save_session()
    finally:
        if ui_widget:
            ui_widget.close()
        reminder_scheduler_running = False
        print("✅ JARVIS shutdown complete. Context saved.")
        print("Thank you for using JARVIS! 🤖")