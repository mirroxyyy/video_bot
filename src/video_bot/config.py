from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevels(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Config(BaseSettings):
    LOG_LEVEL: LogLevels = LogLevels.INFO

    BOT_TOKEN: str
    OPENAI_KEY: str
    OPENAI_URL: str

    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASS: str

    @property
    def DB_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


_config_instance = None


def get_config() -> Config:
    global _config_instance

    if _config_instance is None:
        _config_instance = Config()  # type: ignore
    return _config_instance
