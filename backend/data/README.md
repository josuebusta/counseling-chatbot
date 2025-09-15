# Data Directory

This directory contains data files used by the counseling chatbot application.

## Structure

```
data/
├── vector_store/
│   ├── chroma_db/          # ChromaDB vector database for RAG system
│   │   └── chroma.sqlite3  # SQLite database with document embeddings
│   └── tmp/                # Temporary data and teachability databases
│       └── interactive/
│           └── teachability_db/  # User conversation memories
│               └── chroma.sqlite3
└── README.md               # This file
```

## Vector Store

The `vector_store/` directory contains all vector databases used by the system:

### RAG System (`chroma_db/`)
- Document embeddings for semantic search
- Document metadata and chunk information
- Index data for fast similarity search

### Teachability System (`tmp/interactive/teachability_db/`)
- User-specific conversation memories
- Stored teachings and learnings from interactions
- ChromaDB databases for each user

**Note**: Both directories are ignored by Git (see `.gitignore`) as they contain generated data that can be recreated from source documents and user interactions.

## Usage

- **RAG System**: Automatically loads the vector database when initializing. If the database doesn't exist, it will be created from the configured source documents.
- **Teachability System**: Creates user-specific databases for storing conversation memories and learnings.
