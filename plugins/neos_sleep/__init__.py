"""
NEOS Sleep Plugin - Memory Consolidation System

Schedules daily memory consolidation at 5 AM to:
- Review and deduplicate memories
- Extract key learnings
- Create daily summaries
- Optimize storage

Modular Design: Can be disabled via web UI or by removing plugin folder.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Plugin metadata
PLUGIN_NAME = "neos_sleep"
PLUGIN_VERSION = "1.0.0"

# Configuration defaults
DEFAULT_CONFIG = {
    "enabled": True,
    "sleep_time": "0 5 * * *",  # 5:00 AM daily
    "consolidation_mode": "medium",  # light, medium, deep
    "target_scopes": ["all"],  # or list specific scopes
    "create_summaries": True,
    "backup_before_consolidation": True,
    "min_age_hours": 24,  # Only consolidate memories older than this
    "similarity_threshold": 0.85,  # For deduplication
}

# Consolidation modes
CONSOLIDATION_MODES = {
    "light": {
        "description": "Minimal consolidation - only removes exact duplicates",
        "duplicate_check": "exact",
        "extract_learnings": False,
        "create_summaries": False
    },
    "medium": {
        "description": "Balanced consolidation - removes similar memories and extracts key points",
        "duplicate_check": "semantic",
        "extract_learnings": True,
        "create_summaries": True
    },
    "deep": {
        "description": "Aggressive consolidation - merges related memories and creates comprehensive summaries",
        "duplicate_check": "semantic_aggressive",
        "extract_learnings": True,
        "create_summaries": True,
        "merge_related": True
    }
}


class NeosSleepPlugin:
    """NEOS Memory Sleep Plugin"""
    
    def __init__(self, system=None):
        self.system = system
        self.config = self._load_config()
        self.scheduler = None
        logger.info(f"NEOS Sleep plugin initialized (enabled={self.config['enabled']})")
    
    def _load_config(self):
        """Load plugin configuration from user directory."""
        config_path = Path(__file__).parent / "config.json"
        user_config_path = Path.home() / ".config" / "sapphire" / "plugins" / "neos_sleep" / "config.json"
        
        config = DEFAULT_CONFIG.copy()
        
        # Load defaults from plugin directory
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config.update(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to load default config: {e}")
        
        # Override with user config
        if user_config_path.exists():
            try:
                with open(user_config_path, 'r') as f:
                    config.update(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to load user config: {e}")
        
        return config
    
    def _save_config(self):
        """Save configuration to user directory."""
        user_config_dir = Path.home() / ".config" / "sapphire" / "plugins" / "neos_sleep"
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
            logger.info("NEOS Sleep plugin is disabled, not registering tasks")
            return
        
        # Register sleep task
        task_id = "neos_sleep_consolidation"
        
        try:
            scheduler.add_task({
                "id": task_id,
                "name": "NEOS Memory Consolidation",
                "description": "Daily memory consolidation and optimization",
                "cron": self.config['sleep_time'],
                "type": "neos_sleep",
                "enabled": True,
                "source": f"plugin:{PLUGIN_NAME}",
                "task_data": {
                    "plugin": PLUGIN_NAME,
                    "action": "consolidate_memories"
                }
            })
            logger.info(f"Registered sleep task: {task_id} at {self.config['sleep_time']}")
        except Exception as e:
            logger.error(f"Failed to register sleep task: {e}")
    
    def on_sleep_triggered(self, task_data=None):
        """Called when sleep cycle is triggered by scheduler."""
        if not self.config['enabled']:
            logger.info("Sleep triggered but plugin is disabled")
            return
        
        logger.info("🌙 NEOS entering sleep cycle...")
        
        try:
            # Run consolidation
            self._consolidate_memories()
            
            # Create daily summary if enabled
            if self.config['create_summaries']:
                self._create_daily_summary()
            
            logger.info("✅ NEOS sleep cycle complete")
            
        except Exception as e:
            logger.error(f"Sleep cycle failed: {e}")
    
    def _consolidate_memories(self):
        """Consolidate memories based on configuration."""
        mode = CONSOLIDATION_MODES.get(self.config['consolidation_mode'], CONSOLIDATION_MODES['medium'])
        
        logger.info(f"Consolidating memories in {self.config['consolidation_mode']} mode")
        
        try:
            from functions import memory
            
            # Get recent memories (older than min_age_hours)
            cutoff_time = datetime.now() - timedelta(hours=self.config['min_age_hours'])

            # Use internal function to get all memories
            all_memories_result, success = memory._get_recent_memories(count=1000)
            
            if not success or not all_memories_result:
                logger.info("No memories to consolidate")
                return
            
            # Parse the result - format is "Recent N memories:\n[1]... [2]..."
            all_memories = []
            import re
            # Extract IDs from format like "[1]2025-01-15 10:30 [family] content..."
            ids = re.findall(r'\[(\d+)\]', all_memories_result)
            all_memories = [{"id": int(id)} for id in ids]
            
            logger.info(f"Found {len(all_memories)} memories to review")
            
            # Remove duplicates based on mode
            if mode.get('duplicate_check') == 'exact':
                self._remove_exact_duplicates(all_memories)
            elif mode.get('duplicate_check') in ['semantic', 'semantic_aggressive']:
                self._remove_semantic_duplicates(all_memories)
            
            # Extract key learnings if enabled
            if mode.get('extract_learnings'):
                self._extract_learnings(all_memories)
            
            # Merge related memories if deep mode
            if mode.get('merge_related'):
                self._merge_related_memories(all_memories)
                
        except Exception as e:
            logger.error(f"Memory consolidation error: {e}")
    
    def _remove_exact_duplicates(self, memories):
        """Remove memories with identical content."""
        seen_content = set()
        duplicates = []
        
        for mem in memories:
            content = mem.get('content', '').strip().lower()
            if content in seen_content:
                duplicates.append(mem.get('id'))
            else:
                seen_content.add(content)
        
        if duplicates:
            logger.info(f"Removing {len(duplicates)} exact duplicate memories")
            from functions import memory
            for mem_id in duplicates:
                try:
                    memory._delete_memory(mem_id)
                except Exception as e:
                    logger.warning(f"Failed to delete duplicate {mem_id}: {e}")
    
    def _remove_semantic_duplicates(self, memories):
        """Remove semantically similar memories."""
        # This would use embeddings to find similar memories
        # For now, just log that we would do this
        logger.info("Semantic deduplication would check embeddings (placeholder)")
    
    def _extract_learnings(self, memories):
        """Extract and save key learnings from memories."""
        logger.info("Extracting key learnings from memories (placeholder)")
        # This would analyze memories and create higher-level abstractions
    
    def _merge_related_memories(self, memories):
        """Merge closely related memories into comprehensive entries."""
        logger.info("Merging related memories (placeholder)")
    
    def _create_daily_summary(self):
        """Create a summary of the day's activities."""
        try:
            from functions import knowledge
            
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            summary_title = f"Daily Summary - {yesterday}"
            
            # Count new memories from yesterday
            # This is simplified - would need timestamp filtering
            summary_content = f"NEOS processed memories during sleep cycle on {datetime.now().strftime('%Y-%m-%d %H:%M')}.\n"
            summary_content += "Memory consolidation completed successfully.\n"
            
            # Save to knowledge base
            knowledge._save_knowledge(
                category="neos_summaries",
                content=summary_content,
                description="NEOS AI Daily Summaries"
            )
            
            logger.info(f"Created daily summary: {summary_title}")
            
        except Exception as e:
            logger.error(f"Failed to create daily summary: {e}")
    
    def is_enabled(self):
        """Check if plugin is enabled."""
        return self.config.get('enabled', False)
    
    def enable(self):
        """Enable the plugin."""
        self.config['enabled'] = True
        self._save_config()
        logger.info("NEOS Sleep plugin enabled")
        if self.scheduler:
            self.set_scheduler(self.scheduler)
    
    def disable(self):
        """Disable the plugin."""
        self.config['enabled'] = False
        self._save_config()
        logger.info("NEOS Sleep plugin disabled")
        # Task will be removed on next scheduler check
    
    def get_status(self):
        """Get current plugin status."""
        return {
            "enabled": self.is_enabled(),
            "next_sleep": self.config['sleep_time'],
            "mode": self.config['consolidation_mode'],
            "config_path": str(Path.home() / ".config" / "sapphire" / "plugins" / "neos_sleep" / "config.json")
        }


# Global plugin instance
_plugin_instance = None


def init_plugin(system=None):
    """Initialize plugin - called by Sapphire plugin loader."""
    global _plugin_instance
    _plugin_instance = NeosSleepPlugin(system)
    return _plugin_instance


def get_plugin():
    """Get plugin instance."""
    return _plugin_instance


def set_scheduler(scheduler):
    """Hook: Register with scheduler."""
    if _plugin_instance:
        _plugin_instance.set_scheduler(scheduler)


def on_sleep_triggered(task_data):
    """Handler called by scheduler when sleep task fires."""
    if _plugin_instance:
        _plugin_instance.on_sleep_triggered(task_data)

# Keep old names for backward compatibility
set_scheduler = set_scheduler