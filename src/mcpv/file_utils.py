"""File utilities module for MCP Vault server.

Contains read_file and list_directory functions for safe file access
within the project root directory.
"""

import os

from . import constants


def read_file(path: str) -> str:
    """
    Reads a file from the project root.
    
    Args:
        path: Relative path to the file
    
    Returns:
        File contents or error message
    """
    try:
        p = (constants.ROOT_DIR / path).resolve()
        # Resolve symlinks and verify containment
        p = p.resolve(strict=True)
        try:
            # Use os.path.commonpath for robust containment check
            os.path.commonpath([constants.ROOT_DIR, p])
        except ValueError:
            return constants.UI_MESSAGES["invalid_path"]
        if not p.is_relative_to(constants.ROOT_DIR):
            return constants.UI_MESSAGES["invalid_path"]
        return p.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return constants.UI_MESSAGES["read_error"]
    except Exception as e:
        return f"{constants.UI_MESSAGES['error']} {e}"


def list_directory(path: str = ".") -> str:
    """
    Lists files in a directory.
    
    Args:
        path: Relative path to the directory (default: current directory)
    
    Returns:
        List of file names or error message
    """
    try:
        p = (constants.ROOT_DIR / path).resolve()
        # Resolve symlinks and verify containment
        p = p.resolve(strict=True)
        try:
            os.path.commonpath([constants.ROOT_DIR, p])
        except ValueError:
            return constants.UI_MESSAGES["invalid_path"]
        if not p.is_relative_to(constants.ROOT_DIR):
            return constants.UI_MESSAGES["invalid_path"]
        out = []
        with os.scandir(p) as it:
            for e in it:
                if not e.name.startswith("."):
                    out.append(e.name)
        return "\n".join(out)
    except FileNotFoundError:
        return constants.UI_MESSAGES["list_error"]
    except Exception as e:
        return f"{constants.UI_MESSAGES['error']} {e}"
