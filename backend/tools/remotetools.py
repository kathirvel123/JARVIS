import requests
import json
from typing import Dict, Any, List, Callable
from langchain_core.tools import tool
from functools import wraps


class RemoteToolsManager:
    """
    Manager for dynamically discovering and registering remote tools as LangChain tools
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.tools = []
        self.tool_configs = {}
        
    def discover_tools(self) -> bool:
        """
        Discover available tools from the FastAPI server and register them as LangChain tools
        """
        try:
            print(f"🔍 Discovering tools from {self.base_url}...")
            response = requests.get(f"{self.base_url}/gmail/tools/list", timeout=10)
            
            if response.status_code == 200:
                tools_data = response.json()
                self._register_tools(tools_data.get('tools', []))
                print(f"✅ Successfully registered {len(self.tools)} remote tools")
                return True
            else:
                print(f"❌ Failed to discover tools: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("❌ Could not connect to remote tools server. Is it running?")
            return False
        except requests.exceptions.Timeout:
            print("❌ Timeout while discovering remote tools")
            return False
        except Exception as e:
            print(f"❌ Error discovering tools: {e}")
            return False
    
    def _register_tools(self, tools_list: List[Dict]):
        """
        Register tools and convert them to LangChain tools
        """
        for tool_config in tools_list:
            try:
                # Store tool configuration
                self.tool_configs[tool_config['name']] = tool_config
                
                # Create and register LangChain tool
                langchain_tool = self._create_langchain_tool(tool_config)
                self.tools.append(langchain_tool)
                
                print(f"  ✓ Registered: {tool_config['name']} - {tool_config['description']}")
                
            except Exception as e:
                print(f"  ❌ Failed to register {tool_config.get('name', 'unknown')}: {e}")
    
    def _create_langchain_tool(self, tool_config: Dict):
        """
        Create a LangChain tool from tool configuration
        """
        tool_name = tool_config['name']
        tool_description = tool_config['description']
        
        # Create the actual function that will be called
        def remote_tool_function(**kwargs):
            return self._execute_remote_tool(tool_name, **kwargs)
        
        # Set function name and docstring
        remote_tool_function.__name__ = tool_name
        remote_tool_function.__doc__ = tool_description
        
        # Convert to LangChain tool
        langchain_tool = tool(remote_tool_function)
        langchain_tool.name = tool_name
        langchain_tool.description = tool_description
        
        return langchain_tool
    
    def _execute_remote_tool(self, tool_name: str, **kwargs) -> str:
        """
        Execute a remote tool and return formatted response
        """
        try:
            tool_config = self.tool_configs[tool_name]
            endpoint = tool_config['endpoint']
            method = tool_config['method']
            
            payload = kwargs
            
            print(f"🔧 Executing remote tool: {tool_name}")
            print(f"📤 Payload: {payload}")
            
            # Make the request
            if method.upper() == 'POST':
                response = requests.post(
                    f"{self.base_url}{endpoint}",
                    json=payload,
                    timeout=30,
                    headers={'Content-Type': 'application/json'}
                )
            elif method.upper() == 'GET':
                response = requests.get(
                    f"{self.base_url}{endpoint}",
                    params=payload,
                    timeout=30
                )
            else:
                return f"❌ Unsupported HTTP method: {method}"
            
            # Handle response
            if response.status_code == 200:
                try:
                    result = response.json()
                    return self._format_tool_response(tool_name, result)
                except json.JSONDecodeError:
                    return f"✅ {tool_name} completed successfully:\n{response.text}"
            else:
                return f"❌ {tool_name} failed with HTTP {response.status_code}: {response.text}"
                
        except requests.exceptions.Timeout:
            return f"❌ {tool_name} timed out after 30 seconds"
        except requests.exceptions.ConnectionError:
            return f"❌ Could not connect to remote service for {tool_name}"
        except Exception as e:
            return f"❌ Error executing {tool_name}: {str(e)}"
    
    def _format_tool_response(self, tool_name: str, result: Dict[str, Any]) -> str:
        """
        Format the tool response for better readability
        """
        if isinstance(result, dict):
            if "success" in result:
                if result["success"]:
                    message = result.get("message", "")
                    data = result.get("data", "")
                    
                    response = f"✅ {tool_name} completed successfully"
                    if message:
                        response += f"\n💬 {message}"
                    if data:
                        if isinstance(data, (list, dict)):
                            response += f"\n📊 Data: {json.dumps(data, indent=2)}"
                        else:
                            response += f"\n📊 Data: {data}"
                    return response
                else:
                    error = result.get("error", "Unknown error")
                    return f"❌ {tool_name} failed: {error}"
            
            # If no success field, format as general response
            elif "error" in result:
                return f"❌ {tool_name} error: {result['error']}"
            else:
                # Format general response
                response = f"✅ {tool_name} response:\n"
                for key, value in result.items():
                    if isinstance(value, (list, dict)):
                        response += f"📋 {key}: {json.dumps(value, indent=2)}\n"
                    else:
                        response += f"📋 {key}: {value}\n"
                return response.strip()
        else:
            return f"✅ {tool_name} result: {result}"
    
    def get_tools(self) -> List:
        """
        Get all registered LangChain tools
        """
        return self.tools
    
    def list_available_tools(self) -> Dict[str, str]:
        """
        Get a dictionary of tool names and descriptions
        """
        return {
            config['name']: config['description'] 
            for config in self.tool_configs.values()
        }
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific tool
        """
        return self.tool_configs.get(tool_name, {})
    
    def health_check(self) -> bool:
        """
        Check if the remote tools server is accessible
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False


# Example usage and testing
def test_remote_tools():
    """
    Test function to verify remote tools functionality
    """
    print("🧪 Testing Remote Tools Manager")
    print("=" * 50)
    
    # Initialize manager
    manager = RemoteToolsManager()
    
    # Test health check
    print("🏥 Health check:", "✅ OK" if manager.health_check() else "❌ Failed")
    
    # Discover tools
    if manager.discover_tools():
        # List available tools
        tools = manager.list_available_tools()
        print(f"\n📋 Available tools ({len(tools)}):")
        for name, description in tools.items():
            print(f"  • {name}: {description}")
        
        # Get LangChain tools
        langchain_tools = manager.get_tools()
        print(f"\n🔗 LangChain tools created: {len(langchain_tools)}")
        
        return manager
    else:
        print("❌ Failed to discover tools")
        return None


if __name__ == "__main__":
    # Run test
    manager = test_remote_tools()
    
    if manager:
        print("\n" + "=" * 50)
        print("✅ Remote Tools Manager is ready!")
        print("You can now import and use this in your main application.")
    else:
        print("\n" + "=" * 50)
        print("❌ Remote Tools Manager setup failed!")
        print("Make sure your FastAPI server is running on http://localhost:8000")