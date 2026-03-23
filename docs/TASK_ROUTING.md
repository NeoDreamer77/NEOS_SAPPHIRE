# NEOS Task-Based LLM Routing

## Overview

Task-based routing analyzes your prompt to determine what type of task you're asking NEOS to perform, then selects the optimal LLM provider for that task type. This provides:

- Better responses for specific tasks (code, reasoning, creative)
- Faster responses for simple queries
- Cost optimization (uses free/cheap models for simple tasks)
- Tool-use optimization

## How It Works

1. **Task Classification** - When you send a message, NEOS analyzes it to classify the task type
2. **Provider Selection** - Based on the task type, NEOS selects from predefined provider lists
3. **Health Check** - Providers are checked in order until one is available
4. **Fallback** - If task routing fails, falls back to global LLM_FALLBACK_ORDER

## Task Types

| Task Type | Description | Preferred Providers |
|-----------|-------------|-------------------|
| `code` | Writing, debugging, or reviewing code | ollama-coder, openrouter-sonnet |
| `reasoning` | Math, logic, analysis | ollama-reasoning, openrouter-sonnet |
| `tool_use` | Using NEOS tools (timers, files, etc) | ollama-general, openrouter-free |
| `complex` | Multi-step, complex requests | openrouter-sonnet, ollama-coder |
| `simple` | Quick questions, greetings | openrouter-free, ollama-general |
| `general` | Anything else | openrouter-free, ollama-general |

## Configuration

Settings are in `user/settings.json` under `LLM_TASK_ROUTING`:

```json
{
  "LLM_TASK_ROUTING": {
    "enabled": true,
    "routing_rules": {
      "code": {
        "preferred_providers": ["ollama-coder", "openrouter-sonnet"],
        "fallback_providers": ["ollama-general", "gemini", "openrouter-free"]
      }
      // ... other task types
    }
  }
}
```

## Disabling Task Routing (REVERSIBLE)

### Method 1: Disable via Settings UI
- Go to Settings > LLM
- Find "Task Routing" toggle
- Set to OFF

### Method 2: Edit settings.json
Set `enabled` to `false`:

```json
"LLM_TASK_ROUTING": {
  "enabled": false
}
```

### Method 3: Use Specific Provider
In the chat settings, explicitly select a provider (not "auto"). This bypasses all routing and uses only that provider.

## Available Providers

Ensure your providers are configured and enabled in `LLM_PROVIDERS`. The routing system only uses providers with `use_as_fallback: true` (except when explicitly selected).

## Troubleshooting

### Wrong model selected
- Check the logs - NEOS logs "Task classification: {task_type}"
- Verify your provider is enabled in LLM_PROVIDERS
- Check that the provider has `use_as_fallback: true`

### Task always classified as "general"
- Add more keywords to TASK_PATTERNS in `core/chat/task_router.py`
- Or explicitly select a provider per-chat

### Want different routing?
- Edit `LLM_TASK_ROUTING.routing_rules` in settings.json
- Each task type has `preferred_providers` (tried first) and `fallback_providers` (if preferred fail)
