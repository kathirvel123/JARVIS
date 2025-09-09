import os
import subprocess
import json
import threading
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Union

from langchain_core.tools import tool

REMINDERS_FILE = "reminders.json"
reminder_scheduler_running = False

@tool
def create_folder(path: str) -> str:
    """Create a folder at the given path."""
    os.makedirs(path, exist_ok=True)
    return f"✅ Folder '{path}' created."

@tool
def create_file(path: str) -> str:
    """Create an empty file at the given path."""
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    with open(path, "w") as f:
        pass
    return f"✅ File '{path}' created."

@tool
def write_file(input_data: dict) -> str:
    """Write content to a file. Input should be a dict with keys: 'path', 'content'."""
    path = input_data["path"]
    content = input_data["content"]
    with open(path, "w") as f:
        f.write(content)
    return f"✅ Wrote to '{path}'."

@tool
def read_file(path: str) -> str:
    """Read content from a file."""
    try:
        with open(path, "r") as f:
            content = f.read()
        return f"✅ Content of '{path}':\n{content}"
    except FileNotFoundError:
        return f"❌ File '{path}' not found."
    except Exception as e:
        return f"❌ Error reading '{path}': {str(e)}"

@tool
def execute_command(command: str) -> dict:
    """
    Executes a shell command and returns stdout, stderr, and exit code.
    
    Args:
        command (str): The shell command to execute.
        
    Returns:
        dict: {"stdout": str, "stderr": str, "return_code": int}
    """
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        return {
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "return_code": process.returncode
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "return_code": 1
        }

@tool
def terminal(command: str) -> str:
    """
    Terminal tool for LangGraph to execute shell commands with safety checks.
    
    Args:
        command (str): The command to run.
    
    Returns:
        str: Output or error message.
    """
    # Dangerous commands to block
    dangerous_patterns = [
        "rm -rf /", "rm -rf *", "mkfs", "dd", "shutdown", "reboot", "halt", "poweroff",
        "kill -9 1", "chmod 777 -R /", "chown -R", ":(){ :|:& };:", "pacman -R", "pacman -Syu"
    ]
    
    for pattern in dangerous_patterns:
        if pattern in command:
            return f"Error: Command '{command}' is blocked for safety."

    result = execute_command(command)
    
    if result["return_code"] == 0:
        return result["stdout"] or "Command executed successfully."
    else:
        return f"Error executing command:\n{result['stderr']}"


@tool
def list_directory(path: str = ".") -> str:
    """List contents of a directory."""
    try:
        items = os.listdir(path)
        if not items:
            return f"📁 Directory '{path}' is empty."
        
        result = f"📁 Contents of '{path}':\n"
        for item in sorted(items):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                result += f"  📁 {item}/\n"
            else:
                result += f"  📄 {item}\n"
        return result
    except Exception as e:
        return f"❌ Error listing directory: {str(e)}"

def load_reminders() -> List[Dict]:
    """Load reminders from file."""
    try:
        if os.path.exists(REMINDERS_FILE):
            with open(REMINDERS_FILE, "r") as f:
                return json.load(f)
        return []
    except Exception:
        return []

def save_reminders(reminders: List[Dict]) -> None:
    """Save reminders to file."""
    try:
        with open(REMINDERS_FILE, "w") as f:
            json.dump(reminders, f, indent=2)
    except Exception:
        pass

def show_reminder_notification(reminder: Dict):
    """Show and speak reminder notification"""
    message = f"Reminder alert! {reminder['task']}"
    # In a modular approach, the main loop would handle calling the speak function.
    print("\n" + "="*60)
    print("🔔🔔🔔 REMINDER ALERT! 🔔🔔🔔")
    print("="*60)
    print(f"⏰ TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📝 TASK: {reminder['task']}")
    if reminder['description']:
        print(f"📄 DESCRIPTION: {reminder['description']}")
    print("="*60 + "\n")

def reminder_scheduler():
    """Background scheduler for reminders"""
    global reminder_scheduler_running
    
    while reminder_scheduler_running:
        try:
            reminders = load_reminders()
            now = datetime.now()
            
            for reminder in reminders:
                if not reminder["completed"] and not reminder.get("notified", False):
                    remind_time = datetime.strptime(reminder["datetime"], "%Y-%m-%d %H:%M")
                    
                    if 0 <= (now - remind_time).total_seconds() <= 60:
                        show_reminder_notification(reminder)
                        reminder["notified"] = True
                        save_reminders(reminders)
            
            time.sleep(30)
            
        except Exception as e:
            print(f"❌ Reminder scheduler error: {e}")
            time.sleep(60)

@tool
def create_reminder(input_data: dict) -> str:
    """Create a reminder with voice feedback."""
    try:
        task = input_data["task"]
        datetime_str = input_data["datetime"]
        description = input_data.get("description", "")
        
        now = datetime.now()
        remind_time = None

        # Regex for "in X seconds/minutes/hours"
        match = re.match(r"in (\d+) (seconds|minutes|hours)", datetime_str, re.IGNORECASE)

        if match:
            value = int(match.group(1))
            unit = match.group(2).lower()

            if unit == "seconds":
                remind_time = now + timedelta(seconds=value)
            elif unit == "minutes":
                remind_time = now + timedelta(minutes=value)
            elif unit == "hours":
                remind_time = now + timedelta(hours=value)

        elif datetime_str.lower().startswith("today"):
            time_part = datetime_str.split(" ", 1)[1]
            hour, minute = map(int, time_part.split(":"))
            remind_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if remind_time <= now:
                remind_time += timedelta(days=1)
        elif datetime_str.lower().startswith("tomorrow"):
            time_part = datetime_str.split(" ", 1)[1]
            hour, minute = map(int, time_part.split(":"))
            remind_time = (now + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        else:
            remind_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        
        if remind_time:
            reminders = load_reminders()
            new_reminder = {
                "id": len(reminders) + 1,
                "task": task,
                "description": description,
                "datetime": remind_time.strftime("%Y-%m-%d %H:%M"),
                "created_at": now.strftime("%Y-%m-%d %H:%M"),
                "completed": False,
                "notified": False
            }
            
            reminders.append(new_reminder)
            save_reminders(reminders)
            
            return f"✅ Reminder created: '{task}' on {remind_time.strftime('%Y-%m-%d at %H:%M')}"
        else:
            return "❌ Could not parse the time for the reminder."
        
    except Exception as e:
        return f"❌ Error creating reminder: {str(e)}"

@tool
def list_reminders() -> str:
    """List all active reminders."""
    try:
        reminders = load_reminders()
        active_reminders = [r for r in reminders if not r["completed"]]
        
        if not active_reminders:
            return "📅 No active reminders found."
        
        result = "📅 Active Reminders:\n"
        for reminder in active_reminders:
            result += f"  {reminder['id']}. {reminder['task']} - {reminder['datetime']}\n"
        
        return result
    except Exception as e:
        return f"❌ Error listing reminders: {str(e)}"

@tool
def get_current_time() -> str:
    """Get current date and time."""
    now = datetime.now()
    return f"🕐 Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}"

def start_reminder_scheduler():
    """Start reminder scheduler"""
    global reminder_scheduler_running
    if not reminder_scheduler_running:
        reminder_scheduler_running = True
        scheduler_thread = threading.Thread(target=reminder_scheduler, daemon=True)
        scheduler_thread.start()