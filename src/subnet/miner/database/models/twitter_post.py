from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from datetime import datetime, timedelta
from src.subnet.miner.database import OrmBase
from src.subnet.miner.database.base_model import to_dict
from src.subnet.miner.database.session_manager import DatabaseSessionManager

Base = declarative_base()


class TwitterPost(OrmBase):
    __tablename__ = 'twitter_posts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tweet_id = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False)
    preview_content = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint('tweet_id', name='uq_tweet_id'),
    )


class TwitterPostManager:
    def __init__(self, session_manager: DatabaseSessionManager):
        self.session_manager = session_manager

    async def get_last_tweets(self):
        async with self.session_manager.session() as session:
            result = await session.execute(
                select(TwitterPost)
                .where(TwitterPost.created_at >= datetime.utcnow() - timedelta(hours=48))
                .order_by(TwitterPost.created_at)
            )
            return [to_dict(result) for result in result.scalars().all()]