# NEOS Memory System - Implementation Log

## Date: 2026-03-22
## Status: Phase 2 Implementation Complete (Testing Pending)

---

## Overview

Implemented modular memory management plugins for NEOS as part of **Phase 2: Memory Architecture**.

### Plugins Created

#### 1. **neos_sleep** - Memory Consolidation
- **Purpose**: Automated memory consolidation at 5:00 AM daily
- **Location**: `plugins/neos_sleep/`
- **Schedule**: `0 5 * * *` (5:00 AM every day)
- **Features**:
  - 3 consolidation modes: light, medium, deep
  - Removes exact duplicates (light)
  - Semantic deduplication (medium/deep)
  - Extracts key learnings (medium/deep)
  - Creates daily summaries
  - Backs up before consolidation
  - Configurable per scope

**Files**:
- `plugins/neos_sleep/__init__.py` - Main plugin code
- `plugins/neos_sleep/plugin.json` - Plugin metadata
- `plugins/neos_sleep/config.json` - Default configuration

**Configuration** (user-editable in `~/.config/sapphire/plugins/neos_sleep/config.json`):
```json
{
  "enabled": true,
  "sleep_time": "0 5 * * *",
  "consolidation_mode": "medium",
  "backup_before_consolidation": true
}
```

**Disable**: 
- Method 1: Web UI → Settings → Plugins → Toggle "NEOS Sleep" OFF
- Method 2: Delete/Rename `plugins/neos_sleep/` folder
- Method 3: Set `"enabled": false` in config.json

---

#### 2. **neos_storage** - Storage Monitoring
- **Purpose**: Monitor storage usage and warn at 80% capacity
- **Location**: `plugins/neos_storage/`
- **Schedule**: `0 */6 * * *` (every 6 hours)
- **Features**:
  - Tracks 5 storage types: memories, knowledge, people, goals, chats
  - Warns at 80%, critical at 95%
  - Per-scope reporting
  - Event bus notifications
  - Cleanup suggestions

**Files**:
- `plugins/neos_storage/__init__.py` - Main plugin code
- `plugins/neos_storage/plugin.json` - Plugin metadata
- `plugins/neos_storage/config.json` - Default configuration

**Configuration**:
```json
{
  "enabled": true,
  "check_interval": "0 */6 * * *",
  "warning_threshold": 80,
  "critical_threshold": 95,
  "track_scopes": true,
  "send_notifications": true
}
```

**Storage Limits** (hardcoded defaults):
- Memories: 10,000 items
- Knowledge entries: 5,000 items  
- People: 1,000 items
- Goals: 500 items
- Chats: 100 sessions

**Disable**: Same methods as neos_sleep

---

## Architecture

### Modular Design
- Each plugin is self-contained in its own directory
- Plugins register via Sapphire's plugin loader
- One-click enable/disable in web UI
- Configuration stored in user directory (survives updates)

### Integration Points
- **Scheduler**: Uses Continuity scheduler for cron-based execution
- **Memory System**: Interfaces with functions/memory.py
- **Knowledge System**: Interfaces with functions/knowledge.py
- **Event Bus**: Publishes warnings/notifications
- **Scope System**: Respects scope isolation

### Safety Features
- Graceful degradation (plugins fail independently)
- Rollback: Disable plugin to restore original behavior
- Logging: All actions logged to standard Sapphire logs
- No auto-delete: Storage plugin only warns, doesn't delete

---

## ⚠️ Security Note: Plugin Signing Required

**Current Status**: Plugins are running with `ALLOW_UNSIGNED_PLUGINS: true`

**Security Issue**: The NEOS plugins (`neos_sleep` and `neos_storage`) are currently **unsigned**, which requires disabling Sapphire's security checks. This is a **temporary workaround** for development/testing only.

### Production Deployment Requires:
1. **Sign the plugins** using Sapphire's plugin signing tools
2. **Remove** `ALLOW_UNSIGNED_PLUGINS: true` from `user/settings.json`
3. **Verify** plugins load with signature verification

### To Sign Plugins (TODO):
```bash
# Use Sapphire's signing tool (when available)
# Typically requires:
# - Private key for signing
# - plugin.sig file in each plugin directory
# - Verification via plugin_verify.py
```

### Current Workaround (Development Only):
- Set `ALLOW_UNSIGNED_PLUGINS: true` in `user/settings.json`
- This allows sideloading of unsigned plugins
- **WARNING**: Only use this for development, never in production

**Action Required**: Before production deployment, properly sign both plugins to maintain security integrity.

---

## Implementation Details

### Sleep Cycle Process
1. **Trigger**: Scheduler runs at 5:00 AM
2. **Backup**: Optionally backup memories before changes
3. **Review**: Load memories older than 24 hours
4. **Deduplicate**: Remove exact/semantic duplicates based on mode
5. **Extract**: Identify key learnings (medium/deep modes)
6. **Merge**: Combine related memories (deep mode only)
7. **Summarize**: Create daily summary in knowledge base
8. **Log**: Record actions taken

### Storage Check Process
1. **Trigger**: Scheduler runs every 6 hours
2. **Count**: Query memory, knowledge, people, goals tables
3. **Calculate**: Percentage of each limit
4. **Check Thresholds**: Compare to 80% warning / 95% critical
5. **Warn**: Log warnings and send event bus notification
6. **Suggest**: Provide cleanup recommendations

---

## Testing Checklist

### Pre-Testing Setup
- [ ] Restart NEOS to load plugins
- [ ] Verify plugins appear in web UI → Settings → Plugins
- [ ] Check scheduler registered tasks in logs

### Sleep Plugin Testing
- [ ] Manual trigger: Call `neos_sleep.on_sleep_triggered()`
- [ ] Check logs for consolidation activity
- [ ] Verify backups created (if enabled)
- [ ] Review daily summary in knowledge base
- [ ] Test disable/enable toggle

### Storage Plugin Testing
- [ ] Manual trigger: Call `neos_storage.on_check_triggered()`
- [ ] Check logs for storage stats
- [ ] Fill memories to 80% and verify warning
- [ ] Test notification appears in UI
- [ ] Test disable/enable toggle

### Organic Memory Testing
- [ ] Start conversation with AI
- [ ] Mention facts AI should remember
- [ ] Ask "What do you know about X?"
- [ ] Verify AI saved memory using `save_memory`
- [ ] Check memories table for new entries

### Scope Testing
- [ ] Create new scope via API
- [ ] Save memory in specific scope
- [ ] Verify isolation from other scopes
- [ ] Test scope switching
- [ ] Verify global scope fallback

---

## Configuration Files

### Plugin Defaults
- `plugins/neos_sleep/config.json` - Default settings
- `plugins/neos_storage/config.json` - Default settings

### User Overrides (persistent)
- `~/.config/sapphire/plugins/neos_sleep/config.json`
- `~/.config/sapphire/plugins/neos_storage/config.json`

### Main Settings
- `user/settings.json` under `neos_plugins` section

---

## Troubleshooting

### Plugins Not Loading
1. Check logs for plugin loader errors
2. Verify `plugin.json` syntax is valid
3. Ensure `__init__.py` has `init_plugin()` function
4. Restart NEOS

### Scheduler Not Running
1. Check Continuity scheduler is running
2. Verify cron expression syntax
3. Check logs for "Registered task" messages
4. Manually trigger: `curl -X POST /api/continuity/trigger`

### No Storage Warnings
1. Check plugin is enabled in config
2. Verify threshold settings
3. Manually run check to test
4. Check event bus subscription

---

## Future Enhancements

### Sleep Plugin
- [ ] Web UI for manual trigger
- [ ] Visual sleep status indicator
- [ ] Sleep history/stats dashboard
- [ ] Custom consolidation rules
- [ ] Integration with external backup systems

### Storage Plugin
- [ ] Web UI showing storage charts
- [ ] One-click cleanup suggestions
- [ ] Auto-archive old memories (optional)
- [ ] Storage optimization recommendations
- [ ] Cross-scope usage analytics

### Organic Learning
- [ ] AI confidence scoring for memories
- [ ] User confirmation before saving (optional)
- [ ] Memory importance ranking
- [ ] Automatic categorization
- [ ] Memory decay (forgetting old info)

---

## Documentation

- **Main**: `plugins/README.md` - Plugin architecture overview
- **Sleep**: `plugins/neos_sleep/README.md` (create if needed)
- **Storage**: `plugins/neos_storage/README.md` (create if needed)
- **Plan**: `PLAN.md` - Phase 2 progress tracking
- **This File**: `docs/NEOS_MEMORY_CHANGES.md` - Implementation log

---

## Rollback Plan

If plugins cause issues:

1. **Quick Disable**:
   ```bash
   # Edit user config
   echo '{"enabled": false}' > ~/.config/sapphire/plugins/neos_sleep/config.json
   echo '{"enabled": false}' > ~/.config/sapphire/plugins/neos_storage/config.json
   ```

2. **Remove Plugins**:
   ```bash
   mv plugins/neos_sleep plugins/neos_sleep.disabled
   mv plugins/neos_storage plugins/neos_storage.disabled
   ```

3. **Restart NEOS**:
   ```bash
   pkill -f sapphire.py
   python main.py
   ```

---

## Verification

**Last Updated**: 2026-03-22
**Phase**: 2 (Memory Architecture)
**Status**: Implementation Complete, Testing Pending
**Next Milestone**: Phase 3 (Performance Tuning)

---

**Author**: Neo (assisted by NEOS AI)
**License**: AGPL-3.0 (following Sapphire framework)
