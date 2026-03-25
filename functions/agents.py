"""Agent management functions for multi-agent system."""

import sqlite3
import logging
import threading
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_db_path = None
_db_initialized = False
_db_lock = threading.Lock()

from core.db_config import get_db_path


def _get_db_path():
    global _db_path
    if _db_path is None:
        # Use centralized db_config for configurable database path
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
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                purpose TEXT,
                instructions TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                scope TEXT NOT NULL DEFAULT 'default',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
                task TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                result TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            )
        """)

        conn.commit()
        conn.close()

        _db_initialized = True
        logger.info("Agents database ready at %s", _get_db_path())


def get_agents(status=None, scope="default"):
    """Get all agents, optionally filtered by status and scope."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute(
                "SELECT id, name, purpose, instructions, status, scope, created_at, updated_at FROM agents WHERE status = ? AND scope = ? ORDER BY name",
                (status, scope),
            )
        else:
            cursor.execute(
                "SELECT id, name, purpose, instructions, status, scope, created_at, updated_at FROM agents WHERE scope = ? ORDER BY name",
                (scope,),
            )
        rows = cursor.fetchall()

    agents = []
    for row in rows:
        agents.append(
            {
                "id": row[0],
                "name": row[1],
                "purpose": row[2],
                "instructions": row[3],
                "status": row[4],
                "scope": row[5],
                "created_at": row[6],
                "updated_at": row[7],
            }
        )
    return agents


def get_agent(name):
    """Get a single agent by name."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, purpose, instructions, status, scope, created_at, updated_at FROM agents WHERE name = ?",
            (name,),
        )
        row = cursor.fetchone()

    if not row:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "purpose": row[2],
        "instructions": row[3],
        "status": row[4],
        "scope": row[5],
        "created_at": row[6],
        "updated_at": row[7],
    }


def create_agent(
    name, purpose=None, instructions=None, status="active", scope="default"
):
    """Create a new agent."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO agents (name, purpose, instructions, status, scope) VALUES (?, ?, ?, ?, ?)",
                (name, purpose, instructions, status, scope),
            )
            conn.commit()
            agent_id = cursor.lastrowid
            logger.info("Created agent: %s", name)
            return {"id": agent_id, "name": name, "status": status}, True
        except sqlite3.IntegrityError:
            return f"Agent '{name}' already exists", False


def update_agent(name, purpose=None, instructions=None, status=None, scope=None):
    """Update an existing agent."""
    updates = []
    params = []

    if purpose is not None:
        updates.append("purpose = ?")
        params.append(purpose)
    if instructions is not None:
        updates.append("instructions = ?")
        params.append(instructions)
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if scope is not None:
        updates.append("scope = ?")
        params.append(scope)

    if not updates:
        return "No changes to apply", False

    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(name)

    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE agents SET {', '.join(updates)} WHERE name = ?", params)
        conn.commit()

        if cursor.rowcount == 0:
            return f"Agent '{name}' not found", False

        logger.info("Updated agent: %s", name)
        return get_agent(name), True


def delete_agent(name):
    """Delete an agent."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM agents WHERE name = ?", (name,))
        conn.commit()

        if cursor.rowcount == 0:
            return f"Agent '{name}' not found", False

        logger.info("Deleted agent: %s", name)
        return f"Agent '{name}' deleted", True


def create_task(agent_name, task):
    """Create a task for an agent."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM agents WHERE name = ?", (agent_name,))
        row = cursor.fetchone()

        if not row:
            return f"Agent '{agent_name}' not found", False

        agent_id = row[0]
        cursor.execute(
            "INSERT INTO agent_tasks (agent_id, task, status) VALUES (?, ?, ?)",
            (agent_id, task, "pending"),
        )
        conn.commit()
        task_id = cursor.lastrowid

        logger.info("Created task %d for agent %s", task_id, agent_name)
        return {
            "task_id": task_id,
            "agent": agent_name,
            "task": task,
            "status": "pending",
        }, True


def get_agent_tasks(agent_name, status=None):
    """Get tasks for an agent."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM agents WHERE name = ?", (agent_name,))
        row = cursor.fetchone()

        if not row:
            return [], False

        agent_id = row[0]

        if status:
            cursor.execute(
                "SELECT id, task, status, result, created_at, completed_at FROM agent_tasks WHERE agent_id = ? AND status = ? ORDER BY created_at DESC",
                (agent_id, status),
            )
        else:
            cursor.execute(
                "SELECT id, task, status, result, created_at, completed_at FROM agent_tasks WHERE agent_id = ? ORDER BY created_at DESC",
                (agent_id,),
            )

        rows = cursor.fetchall()

    tasks = []
    for row in rows:
        tasks.append(
            {
                "id": row[0],
                "task": row[1],
                "status": row[2],
                "result": row[3],
                "created_at": row[4],
                "completed_at": row[5],
            }
        )
    return tasks, True


def complete_task(task_id, result):
    """Mark a task as completed with result."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE agent_tasks SET status = ?, result = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            ("completed", result, task_id),
        )
        conn.commit()

        if cursor.rowcount == 0:
            return f"Task {task_id} not found", False

        logger.info("Completed task %d", task_id)
        return {"task_id": task_id, "status": "completed", "result": result}, True


def fail_task(task_id, error):
    """Mark a task as failed with error."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE agent_tasks SET status = ?, result = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            ("failed", error, task_id),
        )
        conn.commit()

        logger.info("Failed task %d: %s", task_id, error)
        return {"task_id": task_id, "status": "failed", "result": error}, True


AVAILABLE_FUNCTIONS = [
    "get_agents",
    "get_agent",
    "create_agent",
    "update_agent",
    "delete_agent",
    "create_task",
    "get_agent_tasks",
    "complete_task",
    "fail_task",
]

TOOLS = [
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "get_agents",
            "description": "Get all available agents. Use this to see what agents are available for delegation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status: active, paused, archived",
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
            "name": "get_agent",
            "description": "Get detailed information about a specific agent.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Agent name"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "create_agent",
            "description": "Create a new specialized agent for a specific task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Unique agent name"},
                    "purpose": {
                        "type": "string",
                        "description": "What this agent does",
                    },
                    "instructions": {
                        "type": "string",
                        "description": "Agent instructions/rules",
                    },
                    "status": {
                        "type": "string",
                        "description": "Status: active, paused, archived (default: active)",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "assign_task",
            "description": "Assign a task to an agent. The agent will work on it and report back.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the agent to assign task to",
                    },
                    "task": {"type": "string", "description": "Task description"},
                },
                "required": ["agent_name", "task"],
            },
        },
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "check_agent_tasks",
            "description": "Check the status of tasks assigned to an agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "description": "Agent name"},
                    "status": {
                        "type": "string",
                        "description": "Filter: pending, completed, failed",
                    },
                },
                "required": ["agent_name"],
            },
        },
    },
]


def execute(function_name, args):
    """Execute a function by name with given arguments."""
    func_map = {
        "get_agents": lambda: get_agents(
            args.get("status"), args.get("scope", "default")
        ),
        "get_agent": lambda: get_agent(args.get("name")),
        "create_agent": lambda: create_agent(
            args["name"],
            args.get("purpose"),
            args.get("instructions"),
            args.get("status", "active"),
            args.get("scope", "default"),
        ),
        "update_agent": lambda: update_agent(
            args["name"],
            args.get("purpose"),
            args.get("instructions"),
            args.get("status"),
            args.get("scope"),
        ),
        "delete_agent": lambda: delete_agent(args["name"]),
        "create_task": lambda: create_task(args["agent_name"], args["task"]),
        "get_agent_tasks": lambda: get_agent_tasks(
            args["agent_name"], args.get("status")
        ),
        "complete_task": lambda: complete_task(args["task_id"], args["result"]),
        "fail_task": lambda: fail_task(args["task_id"], args["error"]),
        "assign_task": lambda: create_task(args["agent_name"], args["task"]),
        "check_agent_tasks": lambda: get_agent_tasks(
            args["agent_name"], args.get("status")
        ),
    }

    if function_name not in func_map:
        return f"Unknown agent function: {function_name}", False

    try:
        return func_map[function_name]()
    except Exception as e:
        logger.error(f"Error executing {function_name}: {e}")
        return str(e), False


ENABLED = True
