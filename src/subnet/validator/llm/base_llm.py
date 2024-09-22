from abc import ABC, abstractmethod
from src.subnet.validator._config import ValidatorSettings


class BaseLLM(ABC):
    @abstractmethod
    def __init__(self, settings: ValidatorSettings) -> None:
        """
        Initialize LLM
        """

    @abstractmethod
    def get_tweet_sentiment(self, tweet_text: str) -> float:
        """
        Get sentiment of tweet
        """
        pass
