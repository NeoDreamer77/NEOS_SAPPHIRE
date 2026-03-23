# plugins/neos_timer/tools.py
"""
Timer tools for NEOS AI.
Provides set_timer, cancel_timer, list_timers, and dismiss_timer tools.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

ENABLED = True
EMOJI = '⏱️'

AVAILABLE_FUNCTIONS = [
    'set_timer',
    'cancel_timer',
    'list_timers',
    'dismiss_timer',
    'send_notification',
]

TOOLS = [
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "set_timer",
            "description": "Set a countdown timer with optional alerts (sound, desktop notification, phone). Use this for 'in X minutes' reminders. The timer will alert when done.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Unique name for this timer (e.g., 'bread', 'pizza'). If a timer with this name exists, it will be updated."
                    },
                    "minutes": {
                        "type": "number",
                        "description": "Duration in minutes"
                    },
                    "message": {
                        "type": "string",
                        "description": "Custom message to display when timer fires (default: '{name} timer complete')"
                    },
                    "sound": {
                        "type": "boolean",
                        "description": "Play sound alert on PC (default: true)"
                    },
                    "sound_type": {
                        "type": "string",
                        "enum": ["beep", "bell", "alarm"],
                        "description": "Type of sound to play (default: beep)"
                    },
                    "repeat": {
                        "type": "integer",
                        "description": "Number of times to repeat the sound (default: 3)"
                    },
                    "repeat_interval": {
                        "type": "number",
                        "description": "Seconds between sound repeats (default: 3)"
                    },
                    "desktop": {
                        "type": "boolean",
                        "description": "Show desktop notification (default: true)"
                    },
                    "phone": {
                        "type": "boolean",
                        "description": "Send notification to phone via ntfy (default: false)"
                    }
                },
                "required": ["name", "minutes"]
            }
        }
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "cancel_timer",
            "description": "Cancel a running timer by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the timer to cancel"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "list_timers",
            "description": "List all active timers with their remaining time.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "dismiss_timer",
            "description": "Dismiss an active timer that is alerting (stop the sound/notifications).",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the timer to dismiss"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "send_notification",
            "description": "Send a notification to PC (desktop notification and/or sound) and optionally to phone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Notification title"
                    },
                    "message": {
                        "type": "string",
                        "description": "Notification message"
                    },
                    "sound": {
                        "type": "boolean",
                        "description": "Play sound on PC (default: true)"
                    },
                    "sound_type": {
                        "type": "string",
                        "enum": ["beep", "bell", "alarm"],
                        "description": "Type of sound (default: beep)"
                    },
                    "desktop": {
                        "type": "boolean",
                        "description": "Show desktop notification (default: true)"
                    },
                    "phone": {
                        "type": "boolean",
                        "description": "Send to phone (default: false)"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high"],
                        "description": "Phone notification priority (default: normal)"
                    }
                },
                "required": ["title", "message"]
            }
        }
    },
]


def execute(function_name: str, arguments: dict, config) -> tuple:
    """Execute timer tools."""
    try:
        from plugins.neos_timer import (
            set_timer, cancel_timer, list_timers, dismiss_timer, send_notification
        )
        
        if function_name == "set_timer":
            return set_timer(
                name=arguments.get("name", ""),
                minutes=arguments.get("minutes", 10),
                message=arguments.get("message"),
                sound=arguments.get("sound", True),
                sound_type=arguments.get("sound_type", "beep"),
                repeat=arguments.get("repeat", 3),
                repeat_interval=arguments.get("repeat_interval", 3),
                desktop=arguments.get("desktop", True),
                phone=arguments.get("phone", False)
            )
        
        elif function_name == "cancel_timer":
            return cancel_timer(arguments.get("name", ""))
        
        elif function_name == "list_timers":
            return list_timers()
        
        elif function_name == "dismiss_timer":
            return dismiss_timer(arguments.get("name", ""))
        
        elif function_name == "send_notification":
            return send_notification(
                title=arguments.get("title", "NEOS"),
                message=arguments.get("message", ""),
                sound=arguments.get("sound", True),
                sound_type=arguments.get("sound_type", "beep"),
                desktop=arguments.get("desktop", True),
                phone=arguments.get("phone", False),
                priority=arguments.get("priority", "normal")
            )
        
        else:
            return f"Unknown function: {function_name}", False
    
    except Exception as e:
        logger.error(f"Timer tool error in {function_name}: {e}", exc_info=True)
        return f"Error: {str(e)}", False
