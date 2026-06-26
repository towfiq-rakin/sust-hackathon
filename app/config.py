import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_TIMEOUT_SECONDS: int = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "12"))
    USE_GEMINI: bool = os.getenv("USE_GEMINI", "true").lower() in ("true", "1", "yes")
    
    # Vertex AI Configuration
    USE_VERTEXAI: bool = os.getenv("USE_VERTEXAI", "true").lower() in ("true", "1", "yes")
    VERTEX_PROJECT_ID: str = os.getenv("VERTEX_PROJECT_ID", "agent-studio-498807")
    VERTEX_LOCATION: str = os.getenv("VERTEX_LOCATION", "us-central1")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    VERTEX_SERVICE_ACCOUNT_JSON: str = os.getenv("VERTEX_SERVICE_ACCOUNT_JSON", "")

settings = Settings()
