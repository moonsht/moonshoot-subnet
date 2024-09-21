from pydantic import BaseModel


class Discovery(BaseModel):
    user_id: str
    tweet_id: str
    tweet_text: str


class ChallengeResult(BaseModel):
    user_id: str
    miner_key: str
    user_followers: int
    user_following: int
    user_tweets: int
    user_likes: int
    user_listed: int
    tweet_id: str
    tweet_text: str
    similarity: float
    tweet_retweets: int
    tweet_replies: int
    tweet_likes: int
    tweet_quotes: int
    tweet_bookmarks: int
    tweet_impressions: int
