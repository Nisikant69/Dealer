from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # SMTP Settings
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_SENDER_NAME: str
    
    OLLAMA_API_ENDPOINT: Optional[str] = None

    VAPI_API_KEY: Optional[str] = None
    VAPI_ASSISTANT_ID: Optional[str] = None

    REDIS_URL: str 
    
    class Config:
        # This tells Pydantic to load the variables from a .env file
        env_file = ".env"

# Create a single settings instance to be used across the application
settings = Settings()
