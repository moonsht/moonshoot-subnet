from sqlalchemy import Column, String, DateTime, insert, BigInteger, select, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
from src.subnet.validator.database import OrmBase
from src.subnet.validator.database.session_manager import DatabaseSessionManager

Base = declarative_base()


class MinerTwitterPostBlacklist(OrmBase):
    __tablename__ = 'miner_twitter_posts_blacklist'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tweet_id = Column(String, nullable=False, unique=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    reason = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint('tweet_id', name='uq_tweet_id'),
    )


class MinerTwitterPostBlacklistManager:
    def __init__(self, session_manager: DatabaseSessionManager):
        self.session_manager = session_manager

    async def check_if_tweet_is_blacklisted(self, tweet_id: str) -> bool:
        async with self.session_manager.session() as session:
            result = await session.execute(
                select(MinerTwitterPostBlacklist).where(MinerTwitterPostBlacklist.tweet_id == tweet_id)
            )
            tweet = result.scalars().first()
            return tweet is not None

    async def blacklist_tweet(self, user_id, user_name, tweet_id: str, reason: str):
        async with self.session_manager.session() as session:
            async with session.begin():
                stmt = insert(MinerTwitterPostBlacklist).values(
                    tweet_id=tweet_id,
                    user_id=user_id,
                    user_name=user_name,
                    timestamp=datetime.utcnow(),
                    reason=reason
                ).on_conflict_do_nothing()
                await session.execute(stmt)