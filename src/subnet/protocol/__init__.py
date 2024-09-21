from pydantic import BaseModel


class Discovery(BaseModel):
    user_id: str


class ChallengeResult(BaseModel):
    user_id: str
    user_verified: bool
    user_followers_count: int
    user_following_count: int
    user_tweet_count: int
    user_listed_count: int
    user_like_count: int