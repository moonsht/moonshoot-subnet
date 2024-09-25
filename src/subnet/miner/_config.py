from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os


def load_environment(env: str):
    if env == 'mainnet':
        dotenv_path = os.path.abspath('../env/.env.miner.mainnet')
    elif env == 'testnet':
        dotenv_path = os.path.abspath('../env/.env.miner.testnet')
    else:
        raise ValueError(f"Unknown environment: {env}")

    load_dotenv(dotenv_path=dotenv_path)


class MinerSettings(BaseSettings):
    NET_UID: int
    MINER_KEY: str
    MINER_NAME: str
    PORT: int = 9962
    WORKERS: int = 1
    DATABASE_URL: str

    USER_ID: str
    DASHBOARD_USER_NAME: str
    DASHBOARD_USER_PASSWORD_HASH: str

    class Config:
        extra = 'ignore'
