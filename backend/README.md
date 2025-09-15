# CHIA - Chatbot for HIV Intervention & Action - Backend

This directory contains CHIA's backend implementation, organized into a modular architecture for better maintainability and separation of concerns.

## Directory Structure

```
backend/
├── agents/                    # AI Agent implementations
│   ├── __init__.py
│   ├── agents.py             # Agent factory for creating different types of AI agents
│   ├── base_agent.py         # Base agent class with common functionality
│   ├── counselor_agent.py    # Primary counselor agent implementation
│   ├── assistant_agent.py    # Counselor assistant agent implementation
│   └── rag_system.py         # RAG system implementation (duplicate in components/)
├── components/               # Core system components
│   ├── __init__.py
│   ├── rag_system.py         # Retrieval-Augmented Generation for knowledge base queries
│   ├── teachability_manager.py # Conversation memory and learning capabilities
│   └── group_chat_manager.py # WebSocket communication and message handling
├── config/                   # Configuration management
│   ├── __init__.py
│   ├── settings.py           # Project settings and environment variables
│   ├── model_config.py       # Model configuration management
│   └── model_config.yaml     # Model configuration file
├── data/                     # Data storage and vector databases
│   ├── README.md
│   └── vector_store/         # ChromaDB vector stores for embeddings
├── services/                 # Business logic services
│   ├── __init__.py
│   └── counselor_session.py  # Main orchestrator class that coordinates all components
├── tools/                    # Agent tools and utilities
│   ├── chat_management.py    # Chat management utilities
│   ├── hiv_assessment.py     # HIV assessment tools
│   ├── provider_search.py    # Healthcare provider search functionality
│   ├── support_system.py     # Support system tools
│   ├── tool_registry.py      # Function registration and tool management
│   └── utils.py              # Utility functions
├── tasks/                    # Background tasks and maintenance
│   └── maintenance.py        # System maintenance tasks
├── tests/                    # Test files
│   ├── accuracy_evaluation.py
│   ├── automate_transcripts.py
│   └── test.py
├── modified_packages/        # Custom modifications to third-party packages
│   └── autogen/              # Modified AutoGen package
├── main.py                   # FastAPI application entry point
├── startup.py                # Application startup configuration
└── Dockerfile.backend        # Docker configuration for backend
```

## Core Components

### 1. Agents (`agents/`)
- **AgentFactory**: Factory pattern for creating different types of agents
- **BaseAgent**: Abstract base class with common agent functionality
- **CounselorAgent**: Primary HIV PrEP counselor with specialized knowledge
- **AssistantAgent**: Supporting agent that assists the counselor

### 2. Services (`services/`)
- **HIVPrEPCounselor**: Main orchestrator class that coordinates all components and manages the counseling session

### 3. Components (`components/`)
- **RAGSystem**: Retrieval-Augmented Generation for knowledge base queries
- **TeachabilityManager**: Conversation memory and learning capabilities
- **TrackableGroupChatManager**: WebSocket communication and message handling

### 4. Tools (`tools/`)
- **FunctionRegistry**: Manages agent tools and capabilities
- **HIV Assessment**: Tools for HIV risk assessment and evaluation
- **Provider Search**: Healthcare provider search and location services
- **Support System**: User support and help functionality
- **Chat Management**: Chat session management utilities

### 5. Configuration (`config/`)
- **Settings**: Environment variables and project configuration
- **Model Config**: LLM model configuration and API settings

## Key Features

1. **AI Agent System**: Multiple specialized agents working together
2. **RAG Integration**: Retrieval-Augmented Generation for knowledge base queries
3. **Teachability**: Conversation memory and learning capabilities
4. **WebSocket Communication**: Real-time chat functionality
5. **Tool Integration**: Extensible tool system for agent capabilities
6. **Vector Database**: ChromaDB integration for document embeddings

## Usage

### Basic Setup

```python
from backend.services.counselor_session import HIVPrEPCounselor
from backend.components.group_chat_manager import TrackableGroupChatManager
from backend.agents import AgentFactory, BaseAgent, CounselorAgent, AssistantAgent

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

### Creating Specific Agents

```python
# Create specific agent types
counselor_agent = AgentFactory.create_counselor_agent(llm_config, teachability_flag=True)
assistant_agent = AgentFactory.create_counselor_assistant_agent(llm_config, teachability_flag=True)
```

### Using Tools

```python
from backend.tools.tool_registry import FunctionRegistry
from backend.tools.hiv_assessment import HIVAssessmentTool
from backend.tools.provider_search import ProviderSearchTool

# Register and use tools
registry = FunctionRegistry()
registry.register_tool(HIVAssessmentTool())
registry.register_tool(ProviderSearchTool())
```

## Module Dependencies

```
services/counselor_session.py
├── config/
│   ├── model_config.py
│   ├── settings.py
│   └── model_config.yaml
├── agents/
│   ├── agents.py (AgentFactory)
│   ├── base_agent.py
│   ├── counselor_agent.py
│   ├── assistant_agent.py
│   └── rag_system.py
├── tools/
│   ├── tool_registry.py
│   ├── chat_management.py
│   ├── hiv_assessment.py
│   ├── provider_search.py
│   ├── support_system.py
│   └── utils.py
└── components/
    ├── rag_system.py
    ├── teachability_manager.py
    └── group_chat_manager.py
```

## Development

### Running the Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker

```bash
# Build the Docker image
docker build -f Dockerfile.backend -t counseling-backend .

# Run the container
docker run -p 8000:8000 counseling-backend
```

## Architecture Benefits

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Maintainability**: Easier to locate and modify specific functionality
3. **Testability**: Individual components can be tested in isolation
4. **Reusability**: Components can be reused in different contexts
5. **Readability**: Smaller, focused files are easier to understand
6. **Scalability**: Modular design allows for easy extension and modification

## Migration Notes

The system has been refactored from a monolithic structure to a modular architecture. Key changes:
- Agent functionality split into specialized classes
- RAG system duplicated in both agents/ and components/ directories
- Tools moved to dedicated tools/ directory
- Configuration centralized in config/ directory
- Services separated into services/ directory
- Background tasks moved to tasks/ directory
