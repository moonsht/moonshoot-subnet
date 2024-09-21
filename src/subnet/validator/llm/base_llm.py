from abc import ABC, abstractmethod
from src.subnet.validator._config import ValidatorSettings


class BaseLLM(ABC):
    @abstractmethod
    def __init__(self, settings: ValidatorSettings) -> None:
        """
        Initialize LLM
        """

    @abstractmethod
    def is_tweet_sentiment_positive(self, tweet_text: str) -> bool:
        """
        Get sentiment of tweet
        """
        pass
