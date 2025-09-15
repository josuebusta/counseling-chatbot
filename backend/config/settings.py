"""
Project settings and environment variables for the HIV PrEP Counselor system.
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv("../.env")

# Set tokenizers parallelism to false to avoid warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class Settings:
    """Project settings and configuration management."""

    def __init__(self):
        self._api_key = None
        self._client = None

    @property
    def api_key(self) -> str:
        """Get OpenAI API key from environment."""
        if self._api_key is None:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError(
                    "API key not found. Please set OPENAI_API_KEY in your "
                    ".env file."
                )
            self._api_key = api_key
        return self._api_key

    @property
    def openai_client(self) -> OpenAI:
        """Get OpenAI client instance."""
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    # Database settings
    @property
    def database_url(self) -> str:
        """Get database URL from environment."""
        return os.getenv('DATABASE_URL', 'sqlite:///./counseling_chatbot.db')

    # Vector store settings
    @property
    def vector_store_path(self) -> str:
        """Get vector store path."""
        return os.getenv('VECTOR_STORE_PATH', './data/vector_store')

    # Database path settings
    @property
    def database_paths(self) -> dict:
        """Get database paths configuration."""
        base_dir = os.path.abspath(self.vector_store_path)
        return {
            "rag_chroma_db": os.path.join(base_dir, "chroma_db"),
            "teachability_base": os.path.join(
                base_dir, "tmp", "interactive", "teachability_db"
            ),
            "teachable_agent_db": os.path.join(
                base_dir, "tmp", "teachable_agent_db"
            ),
            "counselor_db": os.path.join(base_dir, "tmp", "counselor_db"),
        }

    def get_database_path(self, db_type: str) -> str:
        """Get the absolute path for a specific database type."""
        if db_type not in self.database_paths:
            available_types = list(self.database_paths.keys())
            raise ValueError(
                f"Unknown database type: {db_type}. "
                f"Available types: {available_types}"
            )

        path = self.database_paths[db_type]
        os.makedirs(path, exist_ok=True)
        return path

    def get_user_teachability_path(self, user_id: str) -> str:
        """Get the teachability database path for a specific user."""
        base_path = self.get_database_path("teachability_base")
        user_path = os.path.join(base_path, f"user_{user_id}")
        os.makedirs(user_path, exist_ok=True)
        return user_path

    # General application settings
    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled."""
        return os.getenv('DEBUG', 'false').lower() == 'true'

    @property
    def log_level(self) -> str:
        """Get log level from environment."""
        return os.getenv('LOG_LEVEL', 'INFO')

    # CORS settings for API
    @property
    def allowed_origins(self) -> list:
        """Get allowed CORS origins."""
        origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000')
        return [origin.strip() for origin in origins.split(',')]

    # Rate limiting settings
    @property
    def rate_limit_requests(self) -> int:
        """Get rate limit for requests per minute."""
        return int(os.getenv('RATE_LIMIT_REQUESTS', '60'))

    @property
    def rate_limit_window(self) -> int:
        """Get rate limit window in minutes."""
        return int(os.getenv('RATE_LIMIT_WINDOW', '1'))

    # Autogen configuration
    @property
    def config_list(self) -> list:
        """Get autogen config list for model configuration."""
        return [
            {
                "model": "gpt-4o",
                "api_key": self.api_key
            }
        ]

    @property
    def model_name(self) -> str:
        """Get the default model name."""
        return os.getenv('MODEL_NAME', 'gpt-4o')


# Global settings instance
settings = Settings()
