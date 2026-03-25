"""Bug tracking functions for NEOS."""

import sqlite3
import logging
import threading
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

from core.db_config import get_db_path

_db_path = None
_db_initialized = False
_db_lock = threading.Lock()


def _get_db_path():
    global _db_path
    if _db_path is None:
        _db_path = get_db_path()
    return _db_path


@contextmanager
def _get_connection():
    _ensure_db()
    conn = sqlite3.connect(str(_get_db_path()), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def _ensure_db():
    global _db_initialized
    if _db_initialized:
        return
    with _db_lock:
        if _db_initialized:
            return

        db_path = _get_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bugs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bug TEXT NOT NULL,
                description TEXT,
                date_found DATETIME DEFAULT CURRENT_TIMESTAMP,
                date_closed DATETIME,
                status TEXT NOT NULL DEFAULT 'open',
                resolution TEXT,
                scope TEXT NOT NULL DEFAULT 'default',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

        _db_initialized = True
        logger.info("Bugs database ready at %s", _get_db_path())


def get_bugs(status=None, scope="default"):
    """Get all bugs, optionally filtered by status and scope."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute(
                "SELECT id, bug, description, date_found, date_closed, status, resolution, scope, created_at, updated_at FROM bugs WHERE status = ? AND scope = ? ORDER BY date_found DESC",
                (status, scope),
            )
        else:
            cursor.execute(
                "SELECT id, bug, description, date_found, date_closed, status, resolution, scope, created_at, updated_at FROM bugs WHERE scope = ? ORDER BY date_found DESC",
                (scope,),
            )
        rows = cursor.fetchall()

    bugs = []
    for row in rows:
        bugs.append(
            {
                "id": row[0],
                "bug": row[1],
                "description": row[2],
                "date_found": row[3],
                "date_closed": row[4],
                "status": row[5],
                "resolution": row[6],
                "scope": row[7],
                "created_at": row[8],
                "updated_at": row[9],
            }
        )
    return bugs


def get_bug(bug_id):
    """Get a single bug by ID."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, bug, description, date_found, date_closed, status, resolution, scope, created_at, updated_at FROM bugs WHERE id = ?",
            (bug_id,),
        )
        row = cursor.fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "bug": row[1],
        "description": row[2],
        "date_found": row[3],
        "date_closed": row[4],
        "status": row[5],
        "resolution": row[6],
        "scope": row[7],
        "created_at": row[8],
        "updated_at": row[9],
    }


def create_bug(bug, description=None, date_found=None, scope="default"):
    """Create a new bug report."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO bugs (bug, description, date_found, status, scope) VALUES (?, ?, ?, ?, ?)",
            (
                bug,
                description,
                date_found or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "open",
                scope,
            ),
        )
        conn.commit()
        bug_id = cursor.lastrowid
        logger.info("Created bug: %s (ID: %d)", bug, bug_id)
        return {"id": bug_id, "bug": bug, "status": "open"}, True


def update_bug(
    bug_id, bug=None, description=None, status=None, resolution=None, scope=None
):
    """Update an existing bug."""
    updates = []
    params = []

    if bug is not None:
        updates.append("bug = ?")
        params.append(bug)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if status is not None:
        updates.append("status = ?")
        params.append(status)
        # Auto-set date_closed when status changes to closed/resolved
        if status in ("closed", "resolved"):
            updates.append("date_closed = CURRENT_TIMESTAMP")
    if resolution is not None:
        updates.append("resolution = ?")
        params.append(resolution)
    if scope is not None:
        updates.append("scope = ?")
        params.append(scope)

    if not updates:
        return "No changes to apply", False

    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(bug_id)

    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE bugs SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

        if cursor.rowcount == 0:
            return f"Bug {bug_id} not found", False

        logger.info("Updated bug: %d", bug_id)
        return get_bug(bug_id), True


def close_bug(bug_id, resolution):
    """Mark a bug as closed with resolution notes."""
    return update_bug(bug_id, status="closed", resolution=resolution)


def delete_bug(bug_id):
    """Delete a bug."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bugs WHERE id = ?", (bug_id,))
        conn.commit()

        if cursor.rowcount == 0:
            return f"Bug {bug_id} not found", False

        logger.info("Deleted bug: %d", bug_id)
        return f"Bug {bug_id} deleted", True


AVAILABLE_FUNCTIONS = [
    "get_bugs",
    "get_bug",
    "create_bug",
    "update_bug",
    "close_bug",
    "delete_bug",
]

TOOLS = [
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "get_bugs",
            "description": "Get all bugs, optionally filtered by status. Use this to see all known bugs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status: open, closed, resolved",
                    },
                    "scope": {
                        "type": "string",
                        "description": "Scope (default: default)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "get_bug",
            "description": "Get detailed information about a specific bug by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bug_id": {"type": "integer", "description": "Bug ID number"}
                },
                "required": ["bug_id"],
            },
        },
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "report_bug",
            "description": "Report a new bug in the system.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bug": {"type": "string", "description": "Brief bug title"},
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the bug",
                    },
                },
                "required": ["bug"],
            },
        },
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "resolve_bug",
            "description": "Mark a bug as resolved/closed with resolution notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bug_id": {"type": "integer", "description": "Bug ID to resolve"},
                    "resolution": {
                        "type": "string",
                        "description": "How the bug was resolved",
                    },
                },
                "required": ["bug_id", "resolution"],
            },
        },
    },
]


def execute(function_name, args):
    """Execute a function by name with given arguments."""
    func_map = {
        "get_bugs": lambda: get_bugs(args.get("status"), args.get("scope", "default")),
        "get_bug": lambda: get_bug(args.get("bug_id")),
        "create_bug": lambda: create_bug(
            args["bug"],
            args.get("description"),
            args.get("date_found"),
            args.get("scope", "default"),
        ),
        "update_bug": lambda: update_bug(
            args["bug_id"],
            args.get("bug"),
            args.get("description"),
            args.get("status"),
            args.get("resolution"),
            args.get("scope"),
        ),
        "close_bug": lambda: close_bug(args["bug_id"], args["resolution"]),
        "delete_bug": lambda: delete_bug(args["bug_id"]),
        "report_bug": lambda: create_bug(args["bug"], args.get("description")),
        "resolve_bug": lambda: close_bug(args["bug_id"], args["resolution"]),
    }

    if function_name not in func_map:
        return f"Unknown bug function: {function_name}", False

    try:
        return func_map[function_name]()
    except Exception as e:
        logger.error(f"Error executing {function_name}: {e}")
        return str(e), False


ENABLED = True
