"""Smart routing module for MCP Vault server.

Contains the run_tool function with intelligent tool routing,
error correction, and server connection logic.
"""

from typing import Any, Dict

from .registry import ToolRegistry
from .vault import manager


async def run_tool(
    registry: ToolRegistry,
    tool_name: str,
    args: dict | None = None
) -> str:
    """
    Executes ANY tool from the available list.
    Smart Router: Automatically finds the correct server for the tool.
    
    Args:
        registry: The ToolRegistry instance containing tool mappings
        tool_name: Name of the tool to execute
        args: Arguments to pass to the tool (optional)
    
    Returns:
        Tool execution result or error message
    """
    if args is None:
        args = {}
    
    # 1. Load registry (build if missing)
    await registry.initialize()
    tool_registry = registry.get_registry()
    
    # 2. Normalization & Prefix Removal
    # Handle 'vault:' prefix or 'mcp_' prefix hallucinations
    target_name = tool_name
    if target_name.startswith("vault:"):
        target_name = target_name[6:]
    elif target_name.startswith("mcp_"):
        # Attempt to find the tool name even if the model tries to call it like a direct tool
        for reg_name in tool_registry.keys():
            if target_name.endswith(reg_name):
                target_name = reg_name
                break
    
    # 3. Exact match (Happy Path)
    info: Dict[str, Any] = tool_registry.get(target_name)
    
    # 4. On match failure: Agent error correction logic
    if not info:
        # A. Did user confuse server name for tool name? (e.g., context-7 -> context7)
        # Extract server list from tool registry
        known_servers = set(t['server'] for t in tool_registry.values())
        
        # Normalize input and server name (remove special chars, lowercase) for comparison
        normalized_input = tool_name.replace("-", "").replace("_", "").lower()
        
        target_server = None
        for sv in known_servers:
            if normalized_input == sv.replace("-", "").replace("_", "").lower():
                target_server = sv
                break
        
        if target_server:
            # Find actual tools belonging to this server and suggest them
            server_tools = [
                f"'{name}' (Args: {i['args']})" 
                for name, i in tool_registry.items() 
                if i['server'] == target_server
            ]
            return (
                f"🛑 Error: '{tool_name}' appears to be a SERVER name (or typo), not a TOOL name.\n"
                f"The server '{target_server}' has the following tools:\n"
                f"{chr(10).join(['- ' + t for t in server_tools])}\n\n"
                f"👉 Please retry 'run_tool' with one of the tool names above."
            )
        
        # B. Simple tool name typo? (similarity search)
        candidates = [k for k in tool_registry.keys() if tool_name in k or k in tool_name]
        if candidates:
            return f"❌ Tool '{tool_name}' not found. Did you mean one of these?\n- " + "\n- ".join(candidates)
            
        return f"❌ Tool '{tool_name}' not found in Registry. Please call 'get_initial_context' to see the full menu."
    
    # 5. Execution logic
    server_name = info['server']
    real_tool_name = info['real_name']
    
    try:
        session = await manager.get_session(server_name)
        # Session connection failure - retry logic or error messages handled by manager or here
        if not session:
            return f"❌ Failed to connect to server '{server_name}'."
        
        result = await session.call_tool(real_tool_name, args)
        
        output = []
        if hasattr(result, 'content'):
            for c in result.content:
                if c.type == "text":
                    output.append(c.text)
                else:
                    output.append(f"[{c.type} content]")
        
        final_res = "\n".join(output) if output else "✅ Executed (No output)"
        return final_res
        
    except Exception as e:
        return f"❌ Execution Error ({server_name} -> {tool_name}): {e}"
