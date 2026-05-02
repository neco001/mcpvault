import pytest
import importlib
import inspect
import os
from pathlib import Path


def test_constants_module_exists():
    """Test that src/mcpv/constants.py module exists"""
    try:
        import src.mcpv.constants
    except ImportError:
        pytest.fail("src/mcpv/constants.py module does not exist")


def test_required_constants_exist():
    """Test that all required constants exist in constants module"""
    try:
        constants = importlib.import_module('src.mcpv.constants')
    except ImportError:
        pytest.fail("src/mcpv/constants.py module does not exist")
    
    # Check MCPV_INSTRUCTIONS exists and is string
    assert hasattr(constants, 'MCPV_INSTRUCTIONS'), "MCPV_INSTRUCTIONS constant missing"
    assert isinstance(constants.MCPV_INSTRUCTIONS, str), "MCPV_INSTRUCTIONS should be string"
    
    # Check UI_MESSAGES exists and has required keys
    assert hasattr(constants, 'UI_MESSAGES'), "UI_MESSAGES constant missing"
    ui_messages = constants.UI_MESSAGES
    assert isinstance(ui_messages, dict), "UI_MESSAGES should be dictionary"
    
    required_keys = ['status', 'no_tools', 'error', 'not_found', 'unknown_action', 'invalid_path', 'read_error', 'list_error']
    for key in required_keys:
        assert key in ui_messages, f"UI_MESSAGES missing required key: {key}"
    
    # Check timeout constants exist and are floats
    assert hasattr(constants, 'GATHER_TIMEOUT'), "GATHER_TIMEOUT constant missing"
    assert isinstance(constants.GATHER_TIMEOUT, (int, float)), "GATHER_TIMEOUT should be numeric"
    
    assert hasattr(constants, 'TOOL_LIST_TIMEOUT'), "TOOL_LIST_TIMEOUT constant missing"
    assert isinstance(constants.TOOL_LIST_TIMEOUT, (int, float)), "TOOL_LIST_TIMEOUT should be numeric"
    
    assert hasattr(constants, 'REGISTRY_INIT_TIMEOUT'), "REGISTRY_INIT_TIMEOUT constant missing"
    assert isinstance(constants.REGISTRY_INIT_TIMEOUT, (int, float)), "REGISTRY_INIT_TIMEOUT should be numeric"
    
    # Check MAX_TOOLS_DISPLAY exists and is int
    assert hasattr(constants, 'MAX_TOOLS_DISPLAY'), "MAX_TOOLS_DISPLAY constant missing"
    assert isinstance(constants.MAX_TOOLS_DISPLAY, int), "MAX_TOOLS_DISPLAY should be integer"


def test_server_functions_have_type_hints():
    """Test that server.py functions have proper type hints"""
    try:
        server = importlib.import_module('src.mcpv.server')
    except ImportError:
        pytest.fail("src/mcpv/server.py module does not exist")
    
    # Get the file to check which objects are defined in this module vs imported
    current_dir = Path(__file__).parent.parent  # Go up from tests/ to project root
    server_file = current_dir / 'src' / 'mcpv' / 'server.py'
    if not server_file.exists():
        server_file = Path('src/mcpv/server.py')
        if not server_file.exists():
            pytest.fail("src/mcpv/server.py file does not exist")
    
    content = server_file.read_text()
    
    # Find all function definitions (def or async def) in this file
    import re
    defined_functions = set(re.findall(r'(?:async\s+)?def\s+(\w+)\s*\(', content))
    
    # Find functions decorated with @asynccontextmanager - these don't need traditional type hints
    decorated_with_asynccontextmanager = set()
    for match in re.finditer(r'@asynccontextmanager\s+(?:async\s+)?def\s+(\w+)\s*\(', content):
        decorated_with_asynccontextmanager.add(match.group(1))
    
    # Get all callable functions from server module
    for name, obj in inspect.getmembers(server, inspect.isfunction):
        # Only check functions that are defined in this module, not imported
        if name not in defined_functions:
            continue
        
        # Skip functions decorated with @asynccontextmanager - decorator handles type info
        if name in decorated_with_asynccontextmanager:
            continue
            
        sig = inspect.signature(obj)
        
        # Check return annotation exists
        if sig.return_annotation == inspect.Parameter.empty:
            pytest.fail(f"Function {name} in server.py missing return type hint")
        
        # Check parameter annotations exist for parameters without defaults
        for param_name, param in sig.parameters.items():
            if param.annotation == inspect.Parameter.empty and param.default is inspect.Parameter.empty:
                pytest.fail(f"Function {name} parameter {param_name} missing type hint")


def test_server_imports_from_constants():
    """Test that server.py imports from constants module instead of using hardcoded strings"""
    try:
        server = importlib.import_module('src.mcpv.server')
    except ImportError:
        pytest.fail("src/mcpv/server.py module does not exist")
    
    # Read the source code to check for hardcoded strings
    import os
    # Get the correct path relative to the project root
    current_dir = Path(__file__).parent.parent  # Go up from tests/ to project root
    server_file = current_dir / 'src' / 'mcpv' / 'server.py'
    if not server_file.exists():
        # Try alternate path in case of different directory structure
        server_file = Path('src/mcpv/server.py')
        if not server_file.exists():
            pytest.fail("src/mcpv/server.py file does not exist")
    
    content = server_file.read_text()
    lines = content.split('\n')
    
    # Look for common hardcoded strings that should come from constants
    hardcoded_strings = [
        'status', 'no_tools', 'error', 'not_found', 'unknown_action',
        'invalid_path', 'read_error', 'list_error'
    ]
    
    for i, line in enumerate(lines, 1):
        # Skip lines that already use constants
        if 'UI_MESSAGES' in line or 'constants.' in line:
            continue
        
        # Skip lines that are method calls (contain . after identifiers)
        # e.g., logger.error() - "error" here is a method name, not a hardcoded string
        import re
        # Pattern: identifier.method() or identifier.property
        if re.search(r'\w+\.\w+\(', line):
            continue
        
        # Check for hardcoded UI message strings
        # Look for patterns like: return "...", msg = "...", "...",
        # But exclude method calls and variable assignments that are method calls
        for msg_key in hardcoded_strings:
            # Check if string literal appears as a standalone value
            single_quoted = f"'{msg_key}'"
            double_quoted = f'"{msg_key}"'
            
            if single_quoted in line or double_quoted in line:
                # Only flag if it's being used as a string literal value
                # Patterns to check: = "...", return "...", f"...{...}...", ["...", "..."]
                # But NOT: logger.error() or similar method calls
                if any(pattern in line for pattern in [' = ', '= ', 'return ', 'return[', '[', ', ']):
                    # Make sure it's not part of a method call pattern
                    if not any(pattern in line for pattern in ['.', '()']):
                        pytest.fail(f"Hardcoded string '{msg_key}' found in server.py at line {i}, should use constants")


def test_mutable_default_arguments_fixed():
    """Test that server.py functions don't use mutable default arguments"""
    try:
        server = importlib.import_module('src.mcpv.server')
    except ImportError:
        pytest.fail("src/mcpv/server.py module does not exist")
    
    for name, obj in inspect.getmembers(server, inspect.isfunction):
        sig = inspect.signature(obj)
        
        for param_name, param in sig.parameters.items():
            # Check for mutable defaults like {} or []
            if param.default is not None:
                if isinstance(param.default, (dict, list)) and param.default == {}:
                    pytest.fail(f"Function {name} uses mutable default argument {param_name}={param.default}")
                elif isinstance(param.default, (dict, list)):
                    pytest.fail(f"Function {name} uses mutable default argument {param_name}={param.default.default}")
            
            # Check specifically for params: dict = {} pattern
            if param_name == 'params' and param.default == {}:
                pytest.fail(f"Function {name} uses params={{}} as default, should be params=None")
