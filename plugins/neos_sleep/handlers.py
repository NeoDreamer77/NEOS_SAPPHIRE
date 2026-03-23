# handlers.py - Schedule task handler for neos_sleep plugin

import logging

logger = logging.getLogger(__name__)


def run(event):
    """
    Execute sleep cycle for memory consolidation.
    
    Args:
        event: Dict with 'system', 'config', 'task', 'plugin_state'
    
    Returns:
        Result string or dict
    """
    try:
        logger.info("🌙 NEOS Sleep: Starting memory consolidation cycle")
        
        # Get plugin state from event (passed by executor)
        plugin_state = event.get('plugin_state', {})
        
        # Check if plugin is enabled via state
        enabled = True
        if hasattr(plugin_state, 'get'):
            enabled = plugin_state.get('enabled', True)
        elif isinstance(plugin_state, dict):
            enabled = plugin_state.get('enabled', True)
        
        if not enabled:
            logger.warning("⚠️  NEOS Sleep: Plugin disabled in state")
            return "Plugin disabled in state"
        
        # Import and run consolidation directly
        import sys
        from pathlib import Path
        
        # Add plugin dir to path
        plugin_dir = Path(__file__).parent
        if str(plugin_dir) not in sys.path:
            sys.path.insert(0, str(plugin_dir))
        
        # Import the main module and run consolidation
        try:
            from __init__ import NeosSleepPlugin
            
            # Create temporary plugin instance for this run
            system = event.get('system')
            plugin = NeosSleepPlugin(system)
            
            # Load state into plugin - use .all() to get dict from PluginState
            if plugin_state:
                if hasattr(plugin_state, 'all'):
                    plugin.config.update(plugin_state.all())
                elif isinstance(plugin_state, dict):
                    plugin.config.update(plugin_state)
            
            if plugin.is_enabled():
                task_data = event.get('task', {})
                plugin.on_sleep_triggered(task_data)
                logger.info("✅ NEOS Sleep: Memory consolidation completed")
                return "Memory consolidation completed successfully"
            else:
                logger.warning("⚠️  NEOS Sleep: Plugin not enabled")
                return "Plugin not enabled"
                
        except ImportError as e:
            logger.error(f"❌ NEOS Sleep: Import error: {e}")
            return f"Import error: {e}"
            
    except Exception as e:
        logger.error(f"❌ NEOS Sleep: Error during consolidation: {e}")
        return f"Error: {str(e)}"