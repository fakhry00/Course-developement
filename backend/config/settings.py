"""
Configuration settings for the AI Course Generator
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Default to gpt-4o-mini
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "4096"))
    
    # Application Settings
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", 8000))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    
    # File Upload Settings
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
    ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", "pdf,docx,doc").split(",")
    
    # Directory Settings
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    
    # Model-specific settings for different agents
    AGENT_CONFIGS = {
        "ingestion": {
            "model": os.getenv("INGESTION_MODEL", OPENAI_MODEL),
            "temperature": float(os.getenv("INGESTION_TEMPERATURE", "0.1"))
        },
        "planning": {
            "model": os.getenv("PLANNING_MODEL", OPENAI_MODEL),
            "temperature": float(os.getenv("PLANNING_TEMPERATURE", "0.3"))
        },
        "content": {
            "model": os.getenv("CONTENT_MODEL", OPENAI_MODEL),
            "temperature": float(os.getenv("CONTENT_TEMPERATURE", "0.4"))
        },
        "packaging": {
            "model": os.getenv("PACKAGING_MODEL", OPENAI_MODEL),
            "temperature": float(os.getenv("PACKAGING_TEMPERATURE", "0.1"))
        }
    }

settings = Settings()