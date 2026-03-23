# NEOS Memory System - Plugin Architecture

## Overview
Modular memory plugins for NEOS that can be individually enabled/disabled.

## Plugins

### 1. neos-sleep
**Purpose**: Scheduled memory consolidation at 5 AM
**Location**: `plugins/neos_sleep/`
**Status**: Enabled by default, can disable via web UI

**Features**:
- Runs daily at 5:00 AM via Continuity scheduler
- Reviews previous day's conversations
- Consolidates redundant memories
- Extracts key learnings
- Updates knowledge base with insights
- Creates daily summary

**Configuration**:
- Sleep time: 5:00 AM (configurable)
- Scope: Can target specific scopes or all
- Consolidation depth: Light/Medium/Deep

### 2. neos-storage
**Purpose**: Monitor storage usage and warn when approaching limits
**Location**: `plugins/neos_storage/`
**Status**: Enabled by default

**Features**:
- Check storage every 6 hours
- Warn at 80% capacity
- Per-scope usage reporting
- Suggests cleanup actions
- Tracks memory vs knowledge vs people storage

**Configuration**:
- Warning threshold: 80%
- Critical threshold: 95%
- Check interval: 6 hours

### 3. neos-scopes (Built-in)
**Purpose**: Enhanced scope management for better context isolation
**Location**: `core/chat/function_manager.py` extensions
**Status**: Always enabled

**Features**:
- Auto-create scopes for different contexts
- Scope suggestion based on conversation topic
- Easy scope switching
- Scope-specific memory search

## Modular Design

Each plugin has:
- `plugin.json` - Metadata and settings
- `__init__.py` - Main plugin code
- `hooks.py` - Event hooks (if needed)
- `config.json` - Default configuration

**Disable Plugin**:
1. Web UI: Settings → Plugins → Toggle OFF
2. Or: Delete/Rename plugin folder
3. Restart NEOS

## File Structure
```
plugins/
├── neos_sleep/
│   ├── __init__.py
│   ├── plugin.json
│   ├── config.json
│   └── README.md
├── neos_storage/
│   ├── __init__.py
│   ├── plugin.json
│   ├── config.json
│   └── README.md
└── README.md
```

## Integration Points

**neos-sleep**:
- Hooks: `scheduler` for 5 AM cron job
- Uses: `save_memory`, `search_memory`, `create_tab`
- Creates: Daily summaries in knowledge base

**neos-storage**:
- Hooks: `scheduler` for periodic checks
- Uses: SQLite queries to count records
- Reports: Storage metrics via event bus

## Safety Features

1. **Graceful Degradation**: If plugin fails, core system continues
2. **Disable Switch**: One-click disable in web UI
3. **Scope Isolation**: Plugins can't corrupt other scopes
4. **Logging**: All actions logged for debugging
5. **Backup**: Memories backed up before consolidation

## Documentation

- All changes logged to `docs/NEOS_MEMORY_CHANGES.md`
- Configuration in `user/settings.json` under `neos_plugins`
- Plan updates in `PLAN.md`
