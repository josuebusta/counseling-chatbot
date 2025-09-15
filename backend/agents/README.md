# HIV PrEP Counseling System - Modular Architecture

This directory contains the refactored HIV PrEP counseling system, organized into distinct modules for better maintainability and separation of concerns.

## File Structure

### Core Components

- **`hiv_counselor.py`** - Main orchestrator class that coordinates all components
- **`config.py`** - Configuration management and shared utilities
- **`__init__.py`** - Package initialization and public API exports

### Specialized Modules

- **`rag_system.py`** - Retrieval-Augmented Generation for knowledge base queries
- **`teachability_manager.py`** - Conversation memory and learning capabilities
- **`agents.py`** - Agent factory for creating different types of AI agents
- **`function_registry.py`** - Function registration and tool management
- **`group_chat_manager.py`** - WebSocket communication and message handling

### Legacy Support

- **`CHIA_LangchainEmbeddings.py`** - Legacy file maintained for backward compatibility

## Key Benefits of Refactoring

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Maintainability**: Easier to locate and modify specific functionality
3. **Testability**: Individual components can be tested in isolation
4. **Reusability**: Components can be reused in different contexts
5. **Readability**: Smaller, focused files are easier to understand

## Usage

```python
from agents import HIVPrEPCounselor, TrackableGroupChatManager

# Create a new counselor instance
counselor = HIVPrEPCounselor(
    websocket=websocket,
    user_id="user123",
    chat_id="chat456",
    teachability_flag=True
)

# Initiate a chat session
await counselor.initiate_chat("Hello, I have questions about PrEP")
```

## Module Dependencies

```
hiv_counselor.py
├── config.py
├── rag_system.py
├── teachability_manager.py
├── agents.py
├── function_registry.py
└── group_chat_manager.py
```

## Migration Notes

The original monolithic `CHIA_LangchainEmbeddings.py` file has been refactored while maintaining backward compatibility. Existing code using the original file will continue to work, but new development should use the modular structure.
