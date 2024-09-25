from fastapi import HTTPException
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint, func, update, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from datetime import datetime
from src.subnet.miner.database import OrmBase
from src.subnet.miner.database.base_model import to_dict
from src.subnet.miner.database.session_manager import DatabaseSessionManager

Base = declarative_base()


class TwitterPost(OrmBase):
    __tablename__ = 'twitter_posts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    tweet_id = Column(String, nullable=False, unique=True)
    dispatch_after = Column(DateTime, nullable=False)
    __table_args__ = (
        UniqueConstraint('tweet_id', name='uq_tweet_id'),
    )


class TwitterPostManager:
    def __init__(self, session_manager: DatabaseSessionManager):
        self.session_manager = session_manager

    async def get_last_tweets(self):
        async with self.session_manager.session() as session:
            now = datetime.utcnow()
            result = await session.execute(
                select(TwitterPost)
                .where(
                    TwitterPost.dispatch_after <= now,
                )
                .order_by(TwitterPost.dispatch_after)
            )

            return [to_dict(tweet) for tweet in result.scalars().all()]

    async def get_tweets(self, page: int = 1, page_size: int = 10):
        async with self.session_manager.session() as session:
            offset = (page - 1) * page_size
            base_query = select(TwitterPost)
            count_query = select(func.count(TwitterPost.id))
            total_items_result = await session.execute(count_query)
            total_items = total_items_result.scalar()
            total_pages = (total_items + page_size - 1) // page_size
            result = await session.execute(
                base_query
                .order_by(TwitterPost.dispatch_after.desc())
                .limit(page_size)
                .offset(offset)
            )
            tweets = result.scalars().all()
            return {
                "tweets": [to_dict(tweet) for tweet in tweets],
                "total_pages": total_pages,
                "total_items": total_items
            }

    async def add_tweet(self, user_id: str, tweet_id: str, dispatch_after: datetime):
        try:
            async with self.session_manager.session() as session:
                async with session.begin():
                    new_tweet = TwitterPost(
                        user_id=user_id,
                        tweet_id=tweet_id,
                        dispatch_after=dispatch_after
                    )
                    session.add(new_tweet)
                    await session.commit()
                    return to_dict(new_tweet)
        except SQLAlchemyError as e:
            raise HTTPException(status_code=500, detail="Error adding tweet to the database")

    async def edit_tweet(self, tweet_id: str, new_dispatch_after: datetime):
        try:
            async with self.session_manager.session() as session:
                async with session.begin():
                    stmt = update(TwitterPost).where(
                        TwitterPost.tweet_id == tweet_id
                    ).values(
                        dispatch_after=new_dispatch_after
                    )
                    result = await session.execute(stmt)
                    await session.commit()
                    if result.rowcount == 0:
                        raise HTTPException(status_code=404, detail="Tweet not found")
        except SQLAlchemyError as e:
            raise HTTPException(status_code=500, detail="Error editing the tweet")

    async def delete_tweet(self, tweet_id: str):
        try:
            async with self.session_manager.session() as session:
                async with session.begin():
                    stmt = delete(TwitterPost).where(
                        TwitterPost.tweet_id == tweet_id
                    )
                    result = await session.execute(stmt)
                    await session.commit()
                    if result.rowcount == 0:
                        raise HTTPException(status_code=404, detail="Tweet not found")
        except SQLAlchemyError as e:
            raise HTTPException(status_code=500, detail="Error deleting the tweet")

    async def get_tweet_by_id(self, tweet_id: str):
        try:
            async with self.session_manager.session() as session:
                result = await session.execute(
                    select(TwitterPost).where(TwitterPost.tweet_id == tweet_id)
                )
                tweet = result.scalar_one_or_none()
                if not tweet:
                    raise HTTPException(status_code=404, detail="Tweet not found")
                return to_dict(tweet)
        except SQLAlchemyError as e:
            raise HTTPException(status_code=500, detail="Error retrieving tweet")