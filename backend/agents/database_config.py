"""
Centralized database path configuration to prevent duplication.
"""
import os

# Base directory for all database files
BASE_DB_DIR = os.path.abspath("./data/vector_store")

# Specific database paths
DATABASE_PATHS = {
    "rag_chroma_db": os.path.join(BASE_DB_DIR, "chroma_db"),
    "teachability_base": os.path.join(BASE_DB_DIR, "tmp", "interactive", "teachability_db"),
    "teachable_agent_db": os.path.join(BASE_DB_DIR, "tmp", "teachable_agent_db"),
    "counselor_db": os.path.join(BASE_DB_DIR, "tmp", "counselor_db"),
}

def get_database_path(db_type: str) -> str:
    """Get the absolute path for a specific database type."""
    if db_type not in DATABASE_PATHS:
        raise ValueError(f"Unknown database type: {db_type}. Available types: {list(DATABASE_PATHS.keys())}")
    
    path = DATABASE_PATHS[db_type]
    os.makedirs(path, exist_ok=True)
    return path

def get_user_teachability_path(user_id: str) -> str:
    """Get the teachability database path for a specific user."""
    base_path = get_database_path("teachability_base")
    user_path = os.path.join(base_path, f"user_{user_id}")
    os.makedirs(user_path, exist_ok=True)
    return user_path

def cleanup_duplicate_databases():
    """Remove duplicate database files from incorrect locations."""
    # List of paths that should be cleaned up
    cleanup_paths = [
        "./chroma_db",  # Root level chroma_db
        "./tmp",        # Root level tmp
    ]
    
    for path in cleanup_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            print(f"Found duplicate database at: {abs_path}")
            print(f"Consider removing this directory to avoid confusion")
            print(f"Files in this directory:")
            try:
                for root, dirs, files in os.walk(abs_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, abs_path)
                        print(f"  - {rel_path}")
            except Exception as e:
                print(f"  Error listing files: {e}")
            print()
