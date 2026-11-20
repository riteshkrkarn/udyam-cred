"""Application settings loaded from environment variables / .env file.

Uses python-dotenv to load a .env file if present, then reads values from the
environment. A plain class (not pydantic-settings) keeps the dependency list to
what is in requirements.txt.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Settings:
    """Runtime configuration. Fields have safe development defaults."""

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./udyamcred.db")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = _get_int("ACCESS_TOKEN_EXPIRE_MINUTES", 15)
    REFRESH_TOKEN_EXPIRE_HOURS: int = _get_int("REFRESH_TOKEN_EXPIRE_HOURS", 1)
    REMEMBER_ME_EXPIRE_HOURS: int = _get_int("REMEMBER_ME_EXPIRE_HOURS", 24)
    APP_ENV: str = os.getenv("APP_ENV", "development")
    SYNTHETIC_SEED: int = _get_int("SYNTHETIC_SEED", 42)
    POLICY_PATH: str = os.getenv("POLICY_PATH", "config/policy.yaml")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
