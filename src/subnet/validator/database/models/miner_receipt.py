from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, update, insert, BigInteger, Boolean, UniqueConstraint, Text, select, \
    func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
from src.subnet.validator.database import OrmBase
from src.subnet.validator.database.session_manager import DatabaseSessionManager

Base = declarative_base()


class MinerReceipt(OrmBase):
    __tablename__ = 'miner_receipts'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    miner_key = Column(String, nullable=False)
    tweet_id = Column(String, nullable=False, unique=True)
    tweet_created_at = Column(DateTime, nullable=False)
    tweet_user_name = Column(String, nullable=False)
    tweet_retweet_count = Column(BigInteger, nullable=False)
    tweet_reply_count = Column(BigInteger, nullable=False)
    tweet_like_count = Column(BigInteger, nullable=False)
    tweet_quote_count = Column(BigInteger, nullable=False)
    tweet_bookmark_count = Column(BigInteger, nullable=False)
    tweet_impression_count = Column(BigInteger, nullable=False)
    tweet_content = Column(Text, nullable=False)
    score = Column(BigInteger, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint('miner_key', 'tweet_id', name='uq_miner_key_tweet_id'),
    )


class ReceiptMinerRank(BaseModel):
    miner_ratio: float
    miner_rank: int


class MinerReceiptManager:
    def __init__(self, session_manager: DatabaseSessionManager):
        self.session_manager = session_manager

    async def store_miner_receipt(self, miner_key: str, tweet_id: str, tweet_created_at: datetime, tweet_user_name: str, tweet_retweet_count: int, tweet_reply_count: int, tweet_like_count: int, tweet_quote_count: int, tweet_bookmark_count: int, tweet_impression_count: int, score: int):
        async with self.session_manager.session() as session:
            async with session.begin():
                stmt = insert(MinerReceipt).values(
                    miner_key=miner_key,
                    tweet_id=tweet_id,
                    tweet_created_at=tweet_created_at,
                    tweet_user_name=tweet_user_name,
                    tweet_retweet_count=tweet_retweet_count,
                    tweet_reply_count=tweet_reply_count,
                    tweet_like_count=tweet_like_count,
                    tweet_quote_count=tweet_quote_count,
                    tweet_bookmark_count=tweet_bookmark_count,
                    tweet_impression_count=tweet_impression_count,
                    score=score,
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
                SELECT similarity(tweet_content, :tweet_content) as ratio
                    FROM miner_receipts
                    WHERE timestamp >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'
                    ORDER BY similarity_score DESC
                    LIMIT 1;
            """)

            result = await session.execute(query, {"tweet_content": tweet_content} )
            ratio = result.scalar()
            return ratio[0]

    async def get_receipts_by_miner_key(self, miner_key: Optional[str], page: int = 1, page_size: int = 10):
        async with self.session_manager.session() as session:
            offset = (page - 1) * page_size
            base_query = select(MinerReceipt)
            count_query = select(func.count(MinerReceipt.id))

            if miner_key:
                base_query = base_query.where(MinerReceipt.miner_key == miner_key)
                count_query = count_query.where(MinerReceipt.miner_key == miner_key)

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