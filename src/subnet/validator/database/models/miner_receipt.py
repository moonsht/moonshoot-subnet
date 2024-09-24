from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, update, insert, BigInteger, Boolean, UniqueConstraint, Text, select, \
    func, text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timedelta
from src.subnet.validator.database import OrmBase
from src.subnet.validator.database.session_manager import DatabaseSessionManager

Base = declarative_base()


class MinerReceipt(OrmBase):
    __tablename__ = 'miner_receipts'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    miner_key = Column(String, nullable=False)
    miner_name = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    tweet_id = Column(String, nullable=False, unique=True)
    tweet_created_at = Column(DateTime, nullable=False)
    tweet_retweet_count = Column(BigInteger, nullable=False)
    tweet_reply_count = Column(BigInteger, nullable=False)
    tweet_like_count = Column(BigInteger, nullable=False)
    tweet_quote_count = Column(BigInteger, nullable=False)
    tweet_bookmark_count = Column(BigInteger, nullable=False)
    tweet_impression_count = Column(BigInteger, nullable=False)
    tweet_content = Column(Text, nullable=False)
    score = Column(BigInteger, nullable=False)
    similarity = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('miner_key', 'tweet_id', name='uq_miner_key_tweet_id'),
    )


class MinerReceiptManager:
    def __init__(self, session_manager: DatabaseSessionManager):
        self.session_manager = session_manager

    async def store_miner_receipt(self, miner_key: str, miner_name: str, user_id: str, user_name: str, tweet_id: str, tweet_content:str,  tweet_created_at: datetime, tweet_retweet_count: int, tweet_reply_count: int, tweet_like_count: int, tweet_quote_count: int, tweet_bookmark_count: int, tweet_impression_count: int, score: int, similarity: float):
        async with self.session_manager.session() as session:
            async with session.begin():
                stmt = insert(MinerReceipt).values(
                    miner_key=miner_key,
                    miner_name=miner_name,
                    user_id=user_id,
                    user_name=user_name,

                    tweet_id=tweet_id,
                    tweet_content=tweet_content,
                    tweet_created_at=tweet_created_at,
                    tweet_retweet_count=tweet_retweet_count,
                    tweet_reply_count=tweet_reply_count,
                    tweet_like_count=tweet_like_count,
                    tweet_quote_count=tweet_quote_count,
                    tweet_bookmark_count=tweet_bookmark_count,
                    tweet_impression_count=tweet_impression_count,
                    score=score,
                    similarity=similarity,
                    timestamp=datetime.utcnow()
                ).on_conflict_do_nothing()
                await session.execute(stmt)

    async def check_if_tweet_was_scored(self, tweet_id: str) -> bool:
        async with self.session_manager.session() as session:
            result = await session.execute(
                select(MinerReceipt).where(MinerReceipt.tweet_id == tweet_id)
            )
            return result.scalar() is not None

    async def check_tweet_similarity(self, tweet_content) -> float:
        async with self.session_manager.session() as session:
            query = text("""
                SELECT similarity(tweet_content, :tweet_content) as similarity_score
                    FROM miner_receipts
                    WHERE timestamp >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'
                    ORDER BY similarity_score DESC
                    LIMIT 1;
            """)

            result = await session.execute(query, {"tweet_content": tweet_content} )
            ratio = result.scalar()
            if ratio is None:
                return 0
            return ratio

    async def get_receipts_by_miner_key(self, miner_key: Optional[str], user_id: Optional[str], user_name: Optional[str], page: int = 1, page_size: int = 10):
        async with self.session_manager.session() as session:
            offset = (page - 1) * page_size
            base_query = select(MinerReceipt)
            count_query = select(func.count(MinerReceipt.id))

            if miner_key:
                base_query = base_query.where(MinerReceipt.miner_key == miner_key)
                count_query = count_query.where(MinerReceipt.miner_key == miner_key)

            elif user_id:
                base_query = base_query.where(MinerReceipt.user_id == user_id)
                count_query = count_query.where(MinerReceipt.user_id == user_id)

            elif user_name:
                base_query = base_query.where(MinerReceipt.user_name == user_name)
                count_query = count_query.where(MinerReceipt.user_name == user_name)

            total_items_result = await session.execute(count_query)
            total_items = total_items_result.scalar()

            total_pages = (total_items + page_size - 1) // page_size

            result = await session.execute(
                base_query
                .order_by(MinerReceipt.timestamp.desc())
                .limit(page_size)
                .offset(offset)
            )
            receipts = result.scalars().all()

            return {
                "receipts": receipts,
                "total_pages": total_pages,
                "total_items": total_items
            }

    async def get_max_metrics_last_month_receipt(self):
        async with self.session_manager.session() as session:
            # Calculate the date range for the last month
            now = datetime.utcnow()
            one_month_ago = now - timedelta(days=30)

            result = await session.execute(
                select(
                    func.max(MinerReceipt.tweet_retweet_count).label('retweets'),
                    func.max(MinerReceipt.tweet_reply_count).label('replies'),
                    func.max(MinerReceipt.tweet_like_count).label('likes'),
                    func.max(MinerReceipt.tweet_quote_count).label('quotes'),
                    func.max(MinerReceipt.tweet_bookmark_count).label('bookmarks'),
                    func.max(MinerReceipt.tweet_impression_count).label('impressions')
                )
                .where(MinerReceipt.timestamp >= one_month_ago)  # Filter for the last month
            )

            row = result.fetchone()
            return {
                "retweets": row.retweets if row.retweets is not None else 10000,
                "replies": row.replies if row.replies is not None else 5000,
                "likes": row.likes if row.likes is not None else 100000,
                "quotes": row.quotes if row.quotes is not None else 2000,
                "bookmarks": row.bookmarks if row.bookmarks is not None else 5000,
                "impressions": row.impressions if row.impressions is not None else 1000000,
            }