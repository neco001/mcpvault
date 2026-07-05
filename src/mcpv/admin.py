"""Admin dispatch module for handling mcpv_admin commands."""

import json
from typing import Any, Dict

from . import constants
from .registry import ToolRegistry


async def dispatch(registry: ToolRegistry, action: str, params: dict = None) -> str:
    """
    Unified administration console for MCP Vault.
    Actions:
    - list_servers: List all upstream servers and status.
    - list_tools: Show detailed tools for a server (params: {'server_name': '...'}).
    - search: Search tools by keyword (params: {'query': '...'}).
    - toggle_server: Enable/disable server (params: {'server_name': '...', 'enabled': bool}).
    - toggle_tool: Enable/disable tool (params: {'server_name': '...', 'tool_name': '...', 'enabled': bool}).
    """
    from .vault import BACKUP_FILE, manager
    
    if params is None:
        params = {}
    
    if action == "list_servers":
        if not BACKUP_FILE.exists(): return "❌ Vault backup not found."
        with open(BACKUP_FILE, "r", encoding="utf-8") as f: config = json.load(f)
        servers = config.get("mcpServers", {})
        output = ["=== 🛰️ UPSTREAM SERVERS ==="]
        for name, srv in servers.items():
            status = "🔴 DISABLED" if srv.get("disabled") else "🟢 ACTIVE"
            output.append(f"- {name:20} | {status}")
        return "\n".join(output)

    elif action == "list_tools":
        server_name = params.get("server_name")
        if not server_name: return "❌ Missing param 'server_name'."
        
        await registry.initialize()
        tool_registry = registry.get_registry()
        
        relevant = {k: v for k, v in tool_registry.items() if v['server'] == server_name}
        if not relevant: return f"⚠️ No active tools for '{server_name}'."
        output = [f"=== 🛠️ TOOLS for '{server_name}' ==="]
        for name, info in relevant.items():
            output.append(f"🔹 {name}\n   └─ Args: {info['args']}\n   └─ Desc: {info['desc']}\n")
        return "\n".join(output)

    elif action == "search":
        query = params.get("query", "").lower()
        if not query: return "❌ Missing param 'query'."
        
        await registry.initialize()
        tool_registry = registry.get_registry()
        
        matches = [f"🔍 {name} ({info['server']})\n   └─ Desc: {info['desc']}" 
                   for name, info in tool_registry.items() 
                   if query in name.lower() or query in info['desc'].lower()]
        return "=== 🔎 SEARCH RESULTS ===\n" + "\n\n".join(matches) if matches else "❌ No matches."

    elif action == "toggle_server":
        server_name, enabled = params.get("server_name"), params.get("enabled", True)
        if not server_name: return "❌ Missing param 'server_name'."
        success = manager.update_config(server_name, "disabled", not enabled)
        if success:
            import asyncio
            asyncio.create_task(registry.initialize(force=True))
        return f"✅ Server '{server_name}' is now {'ENABLED' if enabled else 'DISABLED'}." if success else "❌ Update failed."

    elif action == "toggle_tool":
        server_name, tool_name, enabled = params.get("server_name"), params.get("tool_name"), params.get("enabled", True)
        if not (server_name and tool_name): return "❌ Missing params."
        success = manager.update_disabled_tools(server_name, tool_name, not enabled)
        if success:
            import asyncio
            asyncio.create_task(registry.initialize(force=True))
        return f"✅ Tool '{tool_name}' on '{server_name}' is now {'ENABLED' if enabled else 'DISABLED'}." if success else "❌ Update failed."

    return constants.UI_MESSAGES["unknown_action"]
