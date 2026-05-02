"""Context building utilities for MCP server initialization and responses."""

from typing import Dict, Any, Optional

from . import constants
from .registry import ToolRegistry


def _build_compact_context(servers: Dict[str, list], registry: Dict[str, Any]) -> str:
    """Generate compact context summary to reduce token overhead (~60-80% reduction)."""
    manual = [
        "=== 🎮 MCPV SMART CONSOLE (Vault v0.4) ===",
        "Mode: Compact (use detailed=True for full tool listings)",
        f"Detected {len(servers)} active servers and {len(registry)} total tools.\n",
        "--- Available Servers ---"
    ]
    
    # Server names with tool counts only (no individual tool names)
    for srv, tools in servers.items():
        manual.append(f"📦 {srv}: {len(tools)} tools")
    
    manual.append("\n=== [🚀 CRITICAL: Access Modes] ===")
    manual.append("1. DIRECT TOOLS (e.g., mcp_exa_*): Call these directly as functions.")
    manual.append("2. VAULTED TOOLS: Use the 'run_tool' proxy with base tool name.")
    manual.append("   - Example: run_tool(tool_name='brave_web_search', args={...})")
    manual.append("\nTip: Use 'get_initial_context(detailed=True)' to see full tool listings and schema access info.")
    
    return "\n".join(manual)


def _build_detailed_context(servers: Dict[str, list], registry: Dict[str, Any]) -> str:
    """Generate detailed context with all tool names and complete instructions."""
    manual = [
        "=== 🎮 MCPV SMART CONSOLE (Vault v0.4) ===",
        "Mode: Detailed (full tool listings & instructions)",
        f"Detected {len(servers)} active servers and {len(registry)} total tools.\n",
        "--- Available Tools (Vaulted) ---"
    ]
    
    for srv, tools in servers.items():
        # Add 'vault:' prefix to indicate these are NOT direct functions
        prefixed_tools = [f"vault:{t}" for t in tools[:constants.MAX_TOOLS_DISPLAY]]
        tool_fmt = ", ".join(prefixed_tools)
        if len(tools) > constants.MAX_TOOLS_DISPLAY: tool_fmt += "..."
        manual.append(f"📦 {srv} ({len(tools)}): {tool_fmt}")
    
    manual.append("\n=== [🚀 CRITICAL: Access Modes] ===")
    manual.append("1. DIRECT TOOLS (e.g., mcp_exa_*): Call these directly as functions.")
    manual.append("2. VAULTED TOOLS (marked 'vault:...'): You MUST use the mcp_mcp-vault_run_tool proxy.")
    manual.append("   - Example: call run_tool(tool_name='brave_web_search', args={...})")
    manual.append("   - DO NOT call vaulted names directly.")
    manual.append("\n- VIEW FULL SCHEMA: call 'mcp_mcp-vault_mcpv_admin(action=\"list_tools\", params={\"server_name\": \"...\"})'")
    manual.append("- RUN A TOOL      : call 'run_tool(tool_name=\"...\", args={...})'")
    manual.append("\nTip: Just use the tool name in 'run_tool'. Arguments can be guessed or seen in full schema.")
    
    return "\n".join(manual)


async def get_initial_context(registry: ToolRegistry, force: bool = False, detailed: bool = False) -> str:
    """
    [System Start] Initializes the session.
    Returns a summary of available tools to save tokens and prevent truncation.
    
    Args:
        registry: The ToolRegistry instance
        force: Bypass valve cache if True
        detailed: If True, returns full tool listings and instructions.
                  If False (default), returns compact summary to reduce token overhead (~60-80% reduction).
    """
    from .valve import valve
    
    # 1. Valve check
    allowed, msg = valve.check(force)
    if not allowed: return msg
    
    # 2. Build registry (wake up servers)
    await registry.initialize()
    
    tool_registry = registry.get_registry()
    
    if not tool_registry:
        return "⚠️ No tools found in connected MCP servers."

    # 3. Server-by-server tool list summary (names only)
    servers = {}
    for t_name, info in tool_registry.items():
        srv = info.get('server')
        if not srv:
            continue
        if srv not in servers: servers[srv] = []
        servers[srv].append(t_name)
    
    if detailed:
        return _build_detailed_context(servers, tool_registry)
    else:
        return _build_compact_context(servers, tool_registry)
