from pydantic_settings import BaseSettings, SettingsConfigDict


class MigrationSettings(BaseSettings):
    DATABASE_URL_MINER: str
    DATABASE_URL_VALIDATOR: str
    model_config = SettingsConfigDict(extra='allow')
