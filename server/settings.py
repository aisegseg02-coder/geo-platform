from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    Centralized Configuration System.
    Validates types strictly to prevent misconfigurations from bringing down production.
    """
    ENV: str = "development"
    DEBUG: bool = True
    
    # Database Layer
    DATABASE_URL: str = "sqlite:///output/app.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Third-Party APIs
    OPENAI_API_KEY: Optional[str] = None
    PERPLEXITY_KEY: Optional[str] = None
    SERPAPI_KEY: Optional[str] = None
    DATAFORSEO_LOGIN: Optional[str] = None
    DATAFORSEO_PASSWORD: Optional[str] = None
    
    # Internal Protections
    MAX_CRAWL_PAGES: int = 50
    API_RATE_LIMIT: str = "30/minute"
    
    # Circuit Breaker Thresholds
    API_FAILURE_THRESHOLD: int = 5
    API_RECOVERY_TIMEOUT_SEC: int = 60
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

config = Settings()
