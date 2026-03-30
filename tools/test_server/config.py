"""Configuration models for the modular PlaySEM test server."""

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """Runtime configuration for the FastAPI test server."""

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8090, ge=1, le=65535)
    debug: bool = Field(default=False)
    app_title: str = Field(default="PlaySEM Test Server")
