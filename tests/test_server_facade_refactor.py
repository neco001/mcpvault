# tests/test_server_facade_refactor.py
import ast
import inspect
import sys
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# Ensure src is in path for imports
sys.path.insert(0, "src")


def _get_server_source() -> str:
    """Helper to safely get server.py source code."""
    import src.mcpv.server as server
    return inspect.getsource(server)


def _parse_server_ast():
    """Helper to parse server.py into an AST."""
    return ast.parse(_get_server_source())


def test_imports_tool_registry_from_registry_module():
    """1. Verify server.py imports ToolRegistry from a new registry module."""
    tree = _parse_server_ast()
    
    found_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            # Check for: from mcpv.registry import ToolRegistry (or similar registry path)
            if node.module and "registry" in node.module:
                for alias in node.names:
                    if alias.name == "ToolRegistry":
                        found_import = True
                        break
    assert found_import, (
        "server.py must import ToolRegistry from a registry module "
        "(e.g., 'from mcpv.registry import ToolRegistry')"
    )


def test_tool_registry_is_instantiated():
    """4. Verify ToolRegistry is properly instantiated at module level."""
    import src.mcpv.server as server
    
    # Check that TOOL_REGISTRY exists and is an instance of ToolRegistry
    assert hasattr(server, "TOOL_REGISTRY"), "server.py must expose TOOL_REGISTRY at module level"
    
    # Verify it's an instance, not a class, with expected methods
    registry = server.TOOL_REGISTRY
    assert not inspect.isclass(registry), "TOOL_REGISTRY should be an instance, not a class"
    assert hasattr(registry, "initialize"), "Registry instance must have an 'initialize' method"
    # ToolRegistry has dict-like interface, not a register method
    assert hasattr(registry, "get_registry"), "Registry instance must have a 'get_registry' method"


def test_fastmcp_lifecycle_calls_initialize():
    """5. Verify FastMCP lifespan calls registry.initialize()."""
    import src.mcpv.server as server
    
    # Check that server_lifespan function exists
    assert hasattr(server, "server_lifespan"), "server.py must have server_lifespan function"
    
    # Check it's a callable function
    assert inspect.isfunction(server.server_lifespan), "server_lifespan must be a function"
    
    # Check it has the correct signature (app parameter)
    sig = inspect.signature(server.server_lifespan)
    assert 'app' in sig.parameters, "server_lifespan should have an 'app' parameter"
    
    # Check source code contains TOOL_REGISTRY.initialize() call
    source = _get_server_source()
    assert "await TOOL_REGISTRY.initialize()" in source, "server_lifespan should call TOOL_REGISTRY.initialize()"
    
    # Verify mcp instance has lifespan configured
    assert hasattr(server, "mcp"), "server.py must expose the FastMCP instance as 'mcp'"
    assert hasattr(server.mcp, "lifespan"), "FastMCP instance must have a lifespan configured"
    # FastMCP wraps the lifespan function, so we just check it's configured (not None)
    assert server.mcp.lifespan is not None, "FastMCP lifespan should be configured"


def test_tool_functions_are_re_exported():
    """3. Verify all tool functions are re-exported at module level for backward compatibility."""
    import src.mcpv.server as server
    
    required_exports = [
        "mcp",
        "TOOL_REGISTRY",
        "get_initial_context",
        "mcpv_admin",
        "run_tool",
        "read_file",
        "list_directory"
    ]
    
    missing = [name for name in required_exports if not hasattr(server, name)]
    assert not missing, f"server.py must re-export: {missing}"


def test_delegate_functions_are_thin_wrappers():
    """2. Verify server.py is a thin facade (delegate functions are thin wrappers)."""
    import src.mcpv.server as server
    
    # Check that functions exist and delegate to module functions
    delegate_functions = {
        "get_initial_context": "context_get_initial_context",
        "mcpv_admin": "admin_dispatch",
        "run_tool": "routing_run_tool",
        "read_file": "file_read_file",
        "list_directory": "file_list_directory"
    }
    
    source = _get_server_source()
    
    for func_name, delegate_name in delegate_functions.items():
        assert hasattr(server, func_name), f"Missing delegate function: {func_name}"
        
        # Verify the source code references the delegate
        assert delegate_name in source, f"{func_name} should reference {delegate_name}"
        
        # Check for thin wrapper pattern: return await <delegate>(...)
        # Since @mcp.tool() decorators transform functions, we check source directly
        func_pattern = f"return {'' if func_name in ['read_file', 'list_directory'] else 'await '}{delegate_name}"
        assert func_pattern in source, f"{func_name} should be a thin wrapper calling {delegate_name}"
