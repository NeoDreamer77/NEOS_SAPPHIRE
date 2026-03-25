"""Database configuration module for NEOS.

Centralized database path and connection configuration.
Can be configured for local or remote (future) database.
"""

import os
from pathlib import Path

# Default to local database
DEFAULT_DB_PATH = Path.home() / ".neos" / "core.db"

# Database configuration - can be overridden for remote setup
_db_config = {
    "type": "local",  # "local" or "remote"
    "path": str(DEFAULT_DB_PATH),
    "host": None,
    "port": None,
    "username": None,
    "password": None,
    "database": None,
}


def get_db_path():
    """Get the current database path."""
    if _db_config["type"] == "remote":
        # For remote, we'd return a connection string
        return None  # Remote needs special handling
    return Path(_db_config["path"])


def get_db_config():
    """Get the full database configuration."""
    return _db_config.copy()


def is_remote():
    """Check if database is configured as remote."""
    return _db_config["type"] == "remote"


def set_local(path=None):
    """Configure for local database."""
    global _db_config
    _db_config["type"] = "local"
    if path:
        _db_config["path"] = str(path)
    else:
        _db_config["path"] = str(DEFAULT_DB_PATH)
    # Clear remote settings
    _db_config["host"] = None
    _db_config["port"] = None
    _db_config["username"] = None
    _db_config["password"] = None
    _db_config["database"] = None


def set_remote(host, port, username, password, database):
    """Configure for remote database (PostgreSQL, MySQL, etc.)."""
    global _db_config
    _db_config["type"] = "remote"
    _db_config["host"] = host
    _db_config["port"] = port
    _db_config["username"] = username
    _db_config["password"] = password
    _db_config["database"] = database
    # Clear local path
    _db_config["path"] = None


def load_from_environment():
    """Load database configuration from environment variables.

    Environment variables:
    - NEOS_DB_TYPE: "local" or "remote"
    - NEOS_DB_PATH: path for local database
    - NEOS_DB_HOST: remote host
    - NEOS_DB_PORT: remote port
    - NEOS_DB_USER: remote username
    - NEOS_DB_PASS: remote password
    - NEOS_DB_NAME: remote database name
    """
    global _db_config

    db_type = os.environ.get("NEOS_DB_TYPE", "local")

    if db_type == "remote":
        set_remote(
            host=os.environ.get("NEOS_DB_HOST", "localhost"),
            port=int(os.environ.get("NEOS_DB_PORT", "5432")),
            username=os.environ.get("NEOS_DB_USER", ""),
            password=os.environ.get("NEOS_DB_PASS", ""),
            database=os.environ.get("NEOS_DB_NAME", "neos"),
        )
    else:
        set_local(os.environ.get("NEOS_DB_PATH"))


def get_connection_string():
    """Get a connection string for remote database."""
    if _db_config["type"] != "remote":
        return None

    # PostgreSQL format
    return f"postgresql://{_db_config['username']}:{_db_config['password']}@{_db_config['host']}:{_db_config['port']}/{_db_config['database']}"


# Load from environment on import
load_from_environment()
