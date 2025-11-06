"""Configuration management for GraphSPG."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Memgraph connection
    memgraph_uri: str = "bolt://localhost:7687"
    memgraph_user: str = ""
    memgraph_password: str = ""

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_title: str = "GraphSPG API"
    api_version: str = "0.1.0"

    # Application settings
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


settings = Settings()
