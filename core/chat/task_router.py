# core/chat/task_router.py
"""
Task-based LLM routing.
Analyzes user prompts to classify task type and routes to optimal provider.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

TASK_PATTERNS = {
    'code': [
        r'\bdef\s+\w+\s*\(',
        r'\bfunction\s+\w+\s*\(',
        r'\bclass\s+\w+',
        r'\bimport\s+\w+',
        r'\bfrom\s+\w+\s+import',
        r'\bconsole\.log\b',
        r'\bprint\s*\(',
        r'\bprintf\b',
        r'\bwrite.*code\b',
        r'\bcode\b.*\bwrite\b',
        r'\bprogram\b',
        r'\bscript\b',
        r'\bapi\b',
        r'\bendpoint\b',
        r'\bfunction\b',
        r'\bmethod\b',
        r'\balgorithm\b',
        r'\bdebug\b',
        r'\bfix.*bug\b',
        r'\brefactor\b',
        r'\bsyntax\b',
        r'\bcompile\b',
        r'\bdeploy\b',
        r'\bgit\b',
        r'\bgithub\b',
    ],
    'reasoning': [
        r'\bsolve\b',
        r'\bcalculate\b',
        r'\bmath\b',
        r'\bequation\b',
        r'\bprove\b',
        r'\blogic\b',
        r'\breasoning\b',
        r'\bthink\b.*\bstep\b',
        r'\bexplain\b.*\bwhy\b',
        r'\banalyze\b',
        r'\bevaluate\b',
        r'\bcompare\b',
        r'\bcontrast\b',
        r'\bdifference\b',
        r'\badvantages?\b',
        r'\bdisadvantages?\b',
    ],
    'creative': [
        r'\bstory\b',
        r'\bwrite\b.*\bstory\b',
        r'\bpoem\b',
        r'\bcreative\b',
        r'\bimagine\b',
        r'\bfiction\b',
        r'\bnarrative\b',
        r'\bcharacter\b',
        r'\bplot\b',
        r'\bdialogue\b',
        r'\bessay\b',
        r'\barticle\b',
        r'\bblog\b',
        r'\bpost\b',
        r'\bsummarize\b',
    ],
    'simple': [
        r'\bhello\b',
        r'\bhi\b',
        r'\bhey\b',
        r'\bhow are you\b',
        r'\bwhat is the weather\b',
        r'\btime\b',
        r'\bdate\b',
        r'\bsimple\b',
        r'\bquick\b',
        r'\bwhat.*is\b.*\?$',
        r'\bwho.*is\b.*\?$',
        r'\bwhere.*is\b.*\?$',
        r'\bwhen.*did\b.*\?$',
    ],
    'tool_use': [
        r'\bset.*timer\b',
        r'\btimer\b',
        r'\bremind.*me\b',
        r'\bcreate.*file\b',
        r'\bread.*file\b',
        r'\bwrite.*file\b',
        r'\bdelete.*file\b',
        r'\blist.*directory\b',
        r'\bsend.*notification\b',
        r'\bsearch\b',
        r'\blookup\b',
        r'\bfind\b',
        r'\bplay.*music\b',
        r'\bturn.*on\b',
        r'\bturn.*off\b',
        r'\bset.*temperature\b',
        r'\bweather\b',
        r'\bcalendar\b',
    ],
    'complex': [
        r'\band\b.*\band\b',
        r'\bthen\b.*\bthen\b',
        r'\bfirst\b.*\bthen\b',
        r'\balso\b.*\btoo\b',
        r'\bmultiple\b',
        r'\bseveral\b',
        r'\bcombine\b',
        r'\bintegrat',
        r'\breview\b.*\bcode\b',
        r'\baudit\b',
        r'\bdesign\b',
        r'\barchitecture\b',
        r'\bimplement\b',
        r'\bbuild\b.*\bsystem\b',
    ],
}

TOOL_KEYWORDS = [
    'set_timer', 'cancel_timer', 'list_timers', 'dismiss_timer', 'send_notification',
    'read_file', 'write_file', 'delete_file', 'create_directory', 'delete_directory', 'list_directory',
    'run_command', 'calendar_today', 'calendar_range', 'calendar_add', 'calendar_delete',
    'web_search', 'web_fetch', 'memory_search', 'memory_read', 'memory_write',
    'store_browse', 'store_install', 'homeassistant', 'telegram_send',
]


def classify_task(prompt: str, has_tools: bool = False) -> Tuple[str, str, List[str]]:
    """
    Classify task type from user prompt.
    
    Returns: (task_type, confidence, matched_patterns)
    """
    prompt_lower = prompt.lower()
    matched_patterns = []
    
    scores = {}
    for task_type, patterns in TASK_PATTERNS.items():
        scores[task_type] = 0
        for pattern in patterns:
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                scores[task_type] += 1
                matched_patterns.append(f"{task_type}:{pattern}")
    
    if has_tools:
        for tool in TOOL_KEYWORDS:
            if tool.lower() in prompt_lower:
                scores['tool_use'] += 2
                matched_patterns.append(f"tool:{tool}")
    
    if not scores or sum(scores.values()) == 0:
        return 'general', 'low', []
    
    max_score = max(scores.values())
    if max_score == 0:
        return 'general', 'low', []
    
    top_tasks = [t for t, s in scores.items() if s == max_score]
    
    if 'simple' in top_tasks and len(top_tasks) > 1:
        top_tasks.remove('simple')
    
    if 'complex' in top_tasks:
        return 'complex', 'high', matched_patterns
    
    if 'tool_use' in top_tasks:
        return 'tool_use', 'high', matched_patterns
    
    if 'code' in top_tasks:
        return 'code', 'high', matched_patterns
    
    if 'reasoning' in top_tasks:
        return 'reasoning', 'high', matched_patterns
    
    if 'creative' in top_tasks:
        return 'creative', 'medium', matched_patterns
    
    return top_tasks[0] if top_tasks else 'general', 'medium', matched_patterns


def get_task_routing_config() -> Dict:
    """
    Get task routing configuration.
    Can be overridden in user settings.
    """
    return {
        'enabled': True,
        'routing_rules': {
            'code': {
                'preferred_providers': ['ollama-coder', 'openrouter-sonnet', 'claude'],
                'fallback_providers': ['ollama-general', 'gemini', 'openrouter-free'],
            },
            'reasoning': {
                'preferred_providers': ['ollama-reasoning', 'openrouter-sonnet', 'claude'],
                'fallback_providers': ['ollama-general', 'gemini', 'openrouter-free'],
            },
            'tool_use': {
                'preferred_providers': ['ollama-general', 'ollama-coder', 'openrouter-free'],
                'fallback_providers': ['gemini', 'opencode-minimax'],
            },
            'complex': {
                'preferred_providers': ['openrouter-sonnet', 'claude', 'ollama-coder'],
                'fallback_providers': ['ollama-general', 'gemini', 'openrouter-free'],
            },
            'creative': {
                'preferred_providers': ['ollama-general', 'openrouter-free', 'gemini'],
                'fallback_providers': ['opencode-minimax'],
            },
            'simple': {
                'preferred_providers': ['ollama-fast', 'openrouter-free', 'opencode-minimax'],
                'fallback_providers': ['ollama-general', 'gemini'],
            },
            'general': {
                'preferred_providers': ['ollama-general', 'openrouter-free', 'gemini'],
                'fallback_providers': ['ollama-coder', 'opencode-minimax'],
            },
        },
        'force_tool_use_model': True,
    }
