"""
NEOS Storage Monitor Plugin - Storage Usage Tracking

Monitors memory and storage usage across all scopes.
Warns when approaching limits (80% warning, 95% critical).
Provides storage statistics and cleanup suggestions.

Modular Design: Can be disabled via web UI or by removing plugin folder.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Plugin metadata
PLUGIN_NAME = "neos_storage"
PLUGIN_VERSION = "1.0.0"

# Configuration defaults
DEFAULT_CONFIG = {
    "enabled": True,
    "check_interval": "0 */6 * * *",  # Every 6 hours
    "warning_threshold": 80,  # Warn at 80%
    "critical_threshold": 95,  # Critical at 95%
    "track_scopes": True,
    "send_notifications": True,
    "max_memories": 10000,
    "max_knowledge_entries": 5000,
    "max_people": 1000,
}

# Storage limits by type (suggested maximums)
STORAGE_LIMITS = {
    "memories": {"max": 10000, "description": "Long-term memories"},
    "knowledge": {"max": 5000, "description": "Knowledge base entries"},
    "people": {"max": 1000, "description": "People/contacts"},
    "goals": {"max": 500, "description": "Active goals"},
    "chats": {"max": 100, "description": "Chat sessions"},
}


class NeosStoragePlugin:
    """NEOS Storage Monitor Plugin"""
    
    def __init__(self, system=None):
        self.system = system
        self.config = self._load_config()
        self.scheduler = None
        self.last_check = None
        self.storage_stats = {}
        logger.info(f"NEOS Storage plugin initialized (enabled={self.config['enabled']})")
    
    def _load_config(self):
        """Load plugin configuration."""
        config_path = Path(__file__).parent / "config.json"
        user_config_path = Path.home() / ".config" / "sapphire" / "plugins" / "neos_storage" / "config.json"
        
        config = DEFAULT_CONFIG.copy()
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config.update(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to load default config: {e}")
        
        if user_config_path.exists():
            try:
                with open(user_config_path, 'r') as f:
                    config.update(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to load user config: {e}")
        
        return config
    
    def _save_config(self):
        """Save configuration."""
        user_config_dir = Path.home() / ".config" / "sapphire" / "plugins" / "neos_storage"
        user_config_dir.mkdir(parents=True, exist_ok=True)
        user_config_path = user_config_dir / "config.json"
        
        try:
            with open(user_config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def set_scheduler(self, scheduler):
        """Register with Continuity scheduler."""
        self.scheduler = scheduler
        
        if not self.config['enabled']:
            logger.info("NEOS Storage plugin is disabled, not registering tasks")
            return
        
        task_id = "neos_storage_check"
        
        try:
            scheduler.add_task({
                "id": task_id,
                "name": "NEOS Storage Check",
                "description": "Monitor memory and storage usage",
                "cron": self.config['check_interval'],
                "type": "neos_storage",
                "enabled": True,
                "source": f"plugin:{PLUGIN_NAME}",
                "task_data": {
                    "plugin": PLUGIN_NAME,
                    "action": "check_storage"
                }
            })
            logger.info(f"Registered storage check task: {task_id}")
        except Exception as e:
            logger.error(f"Failed to register storage task: {e}")
    
    def on_check_triggered(self, task_data=None):
        """Called when storage check is triggered."""
        if not self.config['enabled']:
            return
        
        logger.info("🔍 NEOS checking storage usage...")
        
        try:
            stats = self._gather_storage_stats()
            self.storage_stats = stats
            self.last_check = datetime.now().isoformat()
            
            # Check thresholds
            self._check_thresholds(stats)
            
            logger.info(f"✅ Storage check complete. Total items: {stats.get('total_items', 0)}")
            
        except Exception as e:
            logger.error(f"Storage check failed: {e}")
    
    def _gather_storage_stats(self):
        """Gather storage statistics from all scopes."""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "scopes": {},
            "total_items": 0,
            "warnings": [],
            "suggestions": []
        }
        
        try:
            # Count memories
            from functions import memory
            recent_memories_result, _ = memory._get_recent_memories(count=1000)
            memory_count = 0
            if recent_memories_result:
                import re
                memory_count = len(re.findall(r'\[(\d+)\]', recent_memories_result))
            stats["memories"] = {
                "count": memory_count,
                "limit": STORAGE_LIMITS["memories"]["max"],
                "percentage": (memory_count / STORAGE_LIMITS["memories"]["max"]) * 100
            }
            stats["total_items"] += memory_count
            
            # Count knowledge entries
            from functions import knowledge
            current_scope = 'default'
            try:
                from functions.memory import _get_current_scope
                current_scope = _get_current_scope()
            except Exception:
                pass
            
            tabs = knowledge.get_tabs(scope=current_scope) or []
            knowledge_count = sum(len(knowledge.get_tab_entries(tab["id"], scope=current_scope) or []) for tab in tabs)
            stats["knowledge"] = {
                "count": knowledge_count,
                "limit": STORAGE_LIMITS["knowledge"]["max"],
                "percentage": (knowledge_count / STORAGE_LIMITS["knowledge"]["max"]) * 100,
                "tabs": len(tabs)
            }
            stats["total_items"] += knowledge_count
            
            # Count people
            people = knowledge.get_people(scope=current_scope) or []
            people_count = len(people)
            stats["people"] = {
                "count": people_count,
                "limit": STORAGE_LIMITS["people"]["max"],
                "percentage": (people_count / STORAGE_LIMITS["people"]["max"]) * 100
            }
            stats["total_items"] += people_count
            
            # Count goals
            from functions import goals
            try:
                all_goals_result, _ = goals._list_goals(status='all', scope=current_scope)
                all_goals = all_goals_result if all_goals_result else ""
            except Exception:
                all_goals = ""
            import re
            goals_count = len(re.findall(r'\[G\d+\]', all_goals)) if all_goals else 0
            stats["goals"] = {
                "count": goals_count,
                "limit": STORAGE_LIMITS["goals"]["max"],
                "percentage": (goals_count / STORAGE_LIMITS["goals"]["max"]) * 100
            }
            stats["total_items"] += goals_count
            
            # Count chats
            # This would need access to chat history
            stats["chats"] = {
                "count": 0,  # Placeholder
                "limit": STORAGE_LIMITS["chats"]["max"],
                "percentage": 0
            }
            
        except Exception as e:
            logger.error(f"Error gathering stats: {e}")
        
        return stats
    
    def _check_thresholds(self, stats):
        """Check if storage is approaching limits and generate warnings."""
        warnings = []
        suggestions = []
        
        warning_threshold = self.config['warning_threshold']
        critical_threshold = self.config['critical_threshold']
        
        for storage_type, data in stats.items():
            if not isinstance(data, dict) or 'percentage' not in data:
                continue
            
            percentage = data['percentage']
            count = data.get('count', 0)
            limit = data.get('limit', 1)
            
            if percentage >= critical_threshold:
                warning_level = "🔴 CRITICAL"
                warnings.append({
                    "type": storage_type,
                    "level": "critical",
                    "percentage": percentage,
                    "count": count,
                    "limit": limit,
                    "message": f"{storage_type}: {count}/{limit} ({percentage:.1f}%) - CRITICAL"
                })
                suggestions.append(f"Urgent: Clean up {storage_type} - consider removing old entries")
                
            elif percentage >= warning_threshold:
                warning_level = "🟡 WARNING"
                warnings.append({
                    "type": storage_type,
                    "level": "warning",
                    "percentage": percentage,
                    "count": count,
                    "limit": limit,
                    "message": f"{storage_type}: {count}/{limit} ({percentage:.1f}%) - WARNING"
                })
                suggestions.append(f"Consider reviewing {storage_type} for items to archive or delete")
        
        # Add general suggestions
        total_items = stats.get('total_items', 0)
        if total_items > 20000:
            suggestions.append("Overall storage is high. Consider running neos_sleep consolidation.")
        
        stats['warnings'] = warnings
        stats['suggestions'] = suggestions
        
        # Log warnings
        if warnings:
            for warning in warnings:
                if warning['level'] == 'critical':
                    logger.error(warning['message'])
                else:
                    logger.warning(warning['message'])
            
            # Send notification if enabled
            if self.config.get('send_notifications') and self.system:
                self._send_notification(warnings, suggestions)
    
    def _send_notification(self, warnings, suggestions):
        """Send notification about storage warnings."""
        try:
            from core.event_bus import publish
            
            notification = {
                "type": "storage_warning",
                "timestamp": datetime.now().isoformat(),
                "warnings": warnings,
                "suggestions": suggestions,
                "message": f"Storage warning: {len(warnings)} items approaching limits"
            }
            
            publish("neos_storage_warning", notification)
            logger.info("Storage warning notification sent")
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def get_status(self):
        """Get current storage status."""
        return {
            "enabled": self.config.get('enabled', False),
            "last_check": self.last_check,
            "stats": self.storage_stats,
            "thresholds": {
                "warning": self.config['warning_threshold'],
                "critical": self.config['critical_threshold']
            },
            "config_path": str(Path.home() / ".config" / "sapphire" / "plugins" / "neos_storage" / "config.json")
        }
    
    def is_enabled(self):
        """Check if plugin is enabled."""
        return self.config.get('enabled', False)
    
    def enable(self):
        """Enable the plugin."""
        self.config['enabled'] = True
        self._save_config()
        logger.info("NEOS Storage plugin enabled")
        if self.scheduler:
            self.set_scheduler(self.scheduler)
    
    def disable(self):
        """Disable the plugin."""
        self.config['enabled'] = False
        self._save_config()
        logger.info("NEOS Storage plugin disabled")


# Global plugin instance
_plugin_instance = None


def init_plugin(system=None):
    """Initialize plugin - called by Sapphire plugin loader."""
    global _plugin_instance
    _plugin_instance = NeosStoragePlugin(system)
    return _plugin_instance


def get_plugin():
    """Get plugin instance."""
    return _plugin_instance


def set_scheduler(scheduler):
    """Hook: Register with scheduler."""
    if _plugin_instance:
        _plugin_instance.set_scheduler(scheduler)


def on_check_triggered(task_data):
    """Handler called by scheduler when storage check task fires."""
    if _plugin_instance:
        _plugin_instance.on_check_triggered(task_data)

# Keep old names for backward compatibility
set_scheduler = set_scheduler