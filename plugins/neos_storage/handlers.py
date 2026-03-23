# handlers.py - Schedule task handler for neos_storage plugin

import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


def run(event):
    """
    Execute storage check.
    
    Args:
        event: Dict with 'system', 'config', 'task', 'plugin_state'
    
    Returns:
        Result string or dict
    """
    try:
        logger.info("🔍 NEOS Storage: Starting storage check")
        
        # Get plugin state from event (passed by executor)
        plugin_state = event.get('plugin_state', {})
        
        # Check if plugin is enabled via state
        enabled = True
        if hasattr(plugin_state, 'get'):
            enabled = plugin_state.get('enabled', True)
        elif isinstance(plugin_state, dict):
            enabled = plugin_state.get('enabled', True)
        
        if not enabled:
            logger.warning("⚠️  NEOS Storage: Plugin disabled in state")
            return "Plugin disabled in state"
        
        # Run storage check directly
        import re
        from datetime import datetime
        stats = {
            "timestamp": datetime.now().isoformat(),
            "memories": 0,
            "knowledge": 0,
            "people": 0,
            "goals": 0,
            "total_items": 0,
            "warnings": []
        }
        
        try:
            # Import functions directly
            import sys
            project_root = Path(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            from functions import memory, knowledge, goals
            
            # Count memories
            try:
                recent_memories_result, _ = memory._get_recent_memories(count=1000)
                if recent_memories_result:
                    stats["memories"] = len(re.findall(r'\[(\d+)\]', recent_memories_result))
                stats["total_items"] += stats["memories"]
            except Exception as e:
                logger.warning(f"Could not count memories: {e}")
            
            # Count knowledge tabs/entries
            current_scope = 'default'
            try:
                current_scope = memory._get_current_scope()
            except Exception:
                pass
            
            try:
                tabs = knowledge.get_tabs(scope=current_scope) or []
                knowledge_count = sum(len(knowledge.get_tab_entries(tab["id"], scope=current_scope) or []) for tab in tabs)
                stats["knowledge"] = knowledge_count
                stats["total_items"] += knowledge_count
            except Exception as e:
                logger.warning(f"Could not count knowledge: {e}")
            
            # Count people
            try:
                people = knowledge.get_people(scope=current_scope) or []
                stats["people"] = len(people)
                stats["total_items"] += len(people)
            except Exception as e:
                logger.warning(f"Could not count people: {e}")
            
            # Count goals
            try:
                all_goals_result, _ = goals._list_goals(status='all', scope=current_scope)
                if all_goals_result:
                    stats["goals"] = len(re.findall(r'\[G\d+\]', all_goals_result))
                stats["total_items"] += stats["goals"]
            except Exception as e:
                logger.warning(f"Could not count goals: {e}")
            
            # Check thresholds
            warning_threshold = 80
            if stats["memories"] > 8000:  # 80% of 10K limit
                stats["warnings"].append(f"Memories: {stats['memories']}/10000 ({stats['memories']/100:.0f}%)")
            if stats["knowledge"] > 4000:  # 80% of 5K limit
                stats["warnings"].append(f"Knowledge: {stats['knowledge']}/5000 ({stats['knowledge']/50:.0f}%)")
            
            if stats["warnings"]:
                logger.warning(f"⚠️  Storage warnings: {stats['warnings']}")
            else:
                logger.info("✅ All storage levels normal")
            
            logger.info(f"✅ Storage check complete. Total items: {stats['total_items']}")
            return f"Storage check complete. Memories: {stats['memories']}, Knowledge: {stats['knowledge']}, People: {stats['people']}, Goals: {stats['goals']}"
            
        except Exception as e:
            logger.error(f"❌ NEOS Storage: Error during check: {e}")
            return f"Error: {str(e)}"

    except Exception as e:
        logger.error(f"❌ NEOS Storage: Outer error: {e}")
        return f"Error: {str(e)}"