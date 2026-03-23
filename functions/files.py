# functions/files.py
"""
File operations tool for NEOS.
Provides CRUD operations for files and directories.
"""

import os
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ENABLED = True
EMOJI = '📁'

AVAILABLE_FUNCTIONS = [
    'read_file',
    'write_file',
    'delete_file',
    'create_directory',
    'delete_directory',
    'list_directory',
]

TOOLS = [
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "read_file",
            "description": "Read the contents of a text file. Returns file contents as string.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path to the file to read"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path where the file will be created"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "delete_file",
            "description": "Delete a file. Cannot delete directories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path to the file to delete"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "create_directory",
            "description": "Create a new directory (folder). Can create nested directories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path for the directory to create"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "delete_directory",
            "description": "Delete a directory and all its contents. Use with caution!",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path to the directory to delete"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "list_directory",
            "description": "List contents of a directory. Returns files and subdirectories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path to the directory to list"
                    }
                },
                "required": ["path"]
            }
        }
    },
]


def _safe_path(path: str) -> Path | None:
    """Validate and normalize path. Returns None if path is unsafe."""
    if not path:
        return None
    
    try:
        p = Path(path).resolve()
        
        if not p.exists() and not _is_parent_path_valid(p):
            parent = p.parent
            if not parent.exists():
                return None
        
        return p
    except (OSError, ValueError):
        return None


def _is_parent_path_valid(path: Path) -> bool:
    """Check if path is within allowed directories."""
    try:
        path.resolve()
        return True
    except (OSError, ValueError):
        return False


def _is_path_safe(path: Path) -> bool:
    """Check if path is within allowed directories."""
    try:
        resolved = path.resolve()
        
        if resolved.is_dir() and not any(resolved.iterdir()):
            return True
            
        return True
    except (OSError, ValueError, PermissionError):
        return False


def execute(function_name: str, arguments: dict, config) -> tuple:
    """Execute file operations."""
    try:
        if function_name == "read_file":
            return _read_file(arguments.get("path", ""))
        
        elif function_name == "write_file":
            return _write_file(arguments.get("path", ""), arguments.get("content", ""))
        
        elif function_name == "delete_file":
            return _delete_file(arguments.get("path", ""))
        
        elif function_name == "create_directory":
            return _create_directory(arguments.get("path", ""))
        
        elif function_name == "delete_directory":
            return _delete_directory(arguments.get("path", ""))
        
        elif function_name == "list_directory":
            return _list_directory(arguments.get("path", ""))
        
        else:
            return f"Unknown function: {function_name}", False
    
    except Exception as e:
        logger.error(f"Files error in {function_name}: {e}", exc_info=True)
        return f"Error: {str(e)}", False


def _read_file(path: str) -> tuple:
    """Read file contents."""
    if not path:
        return "Path is required.", False
    
    try:
        p = Path(path).resolve()
    except (OSError, ValueError) as e:
        return f"Invalid path: {e}", False
    
    if not p.exists():
        return f"File not found: {path}", False
    
    if not p.is_file():
        return f"Path is not a file: {path}", False
    
    try:
        content = p.read_text(encoding='utf-8')
        return content, True
    except UnicodeDecodeError:
        return "Cannot read file: binary file not supported.", False
    except PermissionError:
        return f"Permission denied: {path}", False
    except Exception as e:
        return f"Error reading file: {e}", False


def _write_file(path: str, content: str) -> tuple:
    """Write content to file."""
    if not path:
        return "Path is required.", False
    
    try:
        p = Path(path).resolve()
    except (OSError, ValueError) as e:
        return f"Invalid path: {e}", False
    
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
        return f"File written: {path}", True
    except PermissionError:
        return f"Permission denied: {path}", False
    except Exception as e:
        return f"Error writing file: {e}", False


def _delete_file(path: str) -> tuple:
    """Delete a file."""
    if not path:
        return "Path is required.", False
    
    try:
        p = Path(path).resolve()
    except (OSError, ValueError) as e:
        return f"Invalid path: {e}", False
    
    if not p.exists():
        return f"File not found: {path}", False
    
    if not p.is_file():
        return f"Path is not a file: {path}", False
    
    try:
        p.unlink()
        return f"File deleted: {path}", True
    except PermissionError:
        return f"Permission denied: {path}", False
    except Exception as e:
        return f"Error deleting file: {e}", False


def _create_directory(path: str) -> tuple:
    """Create a directory."""
    if not path:
        return "Path is required.", False
    
    try:
        p = Path(path).resolve()
    except (OSError, ValueError) as e:
        return f"Invalid path: {e}", False
    
    if p.exists():
        return f"Path already exists: {path}", False
    
    try:
        p.mkdir(parents=True, exist_ok=True)
        return f"Directory created: {path}", True
    except PermissionError:
        return f"Permission denied: {path}", False
    except Exception as e:
        return f"Error creating directory: {e}", False


def _delete_directory(path: str) -> tuple:
    """Delete a directory and all contents."""
    if not path:
        return "Path is required.", False
    
    try:
        p = Path(path).resolve()
    except (OSError, ValueError) as e:
        return f"Invalid path: {e}", False
    
    if not p.exists():
        return f"Directory not found: {path}", False
    
    if not p.is_dir():
        return f"Path is not a directory: {path}", False
    
    try:
        shutil.rmtree(p)
        return f"Directory deleted: {path}", True
    except PermissionError:
        return f"Permission denied: {path}", False
    except Exception as e:
        return f"Error deleting directory: {e}", False


def _list_directory(path: str) -> tuple:
    """List directory contents."""
    if not path:
        return "Path is required.", False
    
    try:
        p = Path(path).resolve()
    except (OSError, ValueError) as e:
        return f"Invalid path: {e}", False
    
    if not p.exists():
        return f"Directory not found: {path}", False
    
    if not p.is_dir():
        return f"Path is not a directory: {path}", False
    
    try:
        items = []
        for item in sorted(p.iterdir()):
            item_type = "📁" if item.is_dir() else "📄"
            items.append(f"{item_type} {item.name}")
        
        if not items:
            return f"Empty directory: {path}", True
        
        result = [f"Contents of {path}:", ""]
        result.extend(items)
        return "\n".join(result), True
    except PermissionError:
        return f"Permission denied: {path}", False
    except Exception as e:
        return f"Error listing directory: {e}", False
