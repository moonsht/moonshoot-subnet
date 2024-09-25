from typing import Optional

from sqlalchemy import Column, Integer, String, Float, DateTime, update, insert, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import delete
from datetime import datetime, timedelta
from src.subnet.validator.database import OrmBase
from src.subnet.validator.database.base_model import to_dict
from src.subnet.validator.database.session_manager import DatabaseSessionManager

Base = declarative_base()


class MinerDiscovery(OrmBase):
    __tablename__ = 'miner_discoveries'
    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(Integer, nullable=False)
    miner_key = Column(String, nullable=False, unique=True)
    miner_name = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    emission = Column(Float, nullable=False, default=0.0)
    followers = Column(Integer, nullable=False, default=0)
    following = Column(Integer, nullable=False, default=0)
    tweets = Column(Integer, nullable=False, default=0)
    likes = Column(Integer, nullable=False, default=0)
    listed = Column(Integer, nullable=False, default=0)


class MinerDiscoveryManager:
    def __init__(self, session_manager: DatabaseSessionManager):
        self.session_manager = session_manager

    async def store_miner_metadata(self, uid: int, miner_key: str, miner_name: str, user_id: str, user_name: str, followers: int, following: int, tweets: int, likes: int, listed: int):
        async with self.session_manager.session() as session:
            async with session.begin():
                stmt = insert(MinerDiscovery).values(
                    uid=uid,
                    miner_key=miner_key,
                    miner_name=miner_name,
                    user_id=user_id,
                    user_name=user_name,
                    timestamp=datetime.utcnow(),
                    followers=followers,
                    following=following,
                    tweets=tweets,
                    likes=likes,
                    listed=listed
                ).on_conflict_do_update(
                    index_elements=['miner_key'],
                    set_={
                        'uid': uid,
                        'user_id': user_id,
                        'timestamp': datetime.utcnow(),
                        'followers': followers,
                        'following': following,
                        'tweets': tweets,
                        'likes': likes,
                        'listed': listed
                    }
                )
                await session.execute(stmt)

    async def update_miner_rank(self, miner_key: str, miner_name: float, emission: float):
        async with self.session_manager.session() as session:
            async with session.begin():
                stmt = update(MinerDiscovery).where(
                    MinerDiscovery.miner_key == miner_key
                ).values(
                    miner_name=miner_name,
                    emission=emission
                )
                await session.execute(stmt)

    async def get_max_metrics_last_month(self):
        async with self.session_manager.session() as session:
            now = datetime.utcnow()
            one_month_ago = now - timedelta(days=30)
            result = await session.execute(
                select(
                    func.max(MinerDiscovery.followers).label('followers'),
                    func.max(MinerDiscovery.following).label('following'),
                    func.max(MinerDiscovery.tweets).label('tweets'),
                    func.max(MinerDiscovery.likes).label('likes'),
                    func.max(MinerDiscovery.listed).label('listed')
                )
                .where(MinerDiscovery.timestamp >= one_month_ago)
            )

            row = result.fetchone()

            return {
                "followers": row.followers if row.followers is not None else 100000,
                "following": row.following if row.following is not None else 10000,
                "tweets": row.tweets if row.tweets is not None else 10000,
                "likes": row.likes if row.likes is not None else 100000,
                "listed": row.listed if row.listed is not None else 1000
            }

    async def get_discoveries_by_miner_key(self, miner_key: Optional[str], user_id: Optional[str], user_name: Optional[str], page: int = 1, page_size: int = 10):
        async with self.session_manager.session() as session:
            offset = (page - 1) * page_size
            base_query = select(MinerDiscovery)
            count_query = select(func.count(MinerDiscovery.id))

            if miner_key:
                base_query = base_query.where(MinerDiscovery.miner_key == miner_key)
                count_query = count_query.where(MinerDiscovery.miner_key == miner_key)

            elif user_id:
                base_query = base_query.where(MinerDiscovery.user_id == user_id)
                count_query = count_query.where(MinerDiscovery.user_id == user_id)

            elif user_name:
                base_query = base_query.where(MinerDiscovery.user_name == user_name)
                count_query = count_query.where(MinerDiscovery.user_name == user_name)

            # Execute count query to get total items
            total_items_result = await session.execute(count_query)
            total_items = total_items_result.scalar()

            # Calculate total pages
            total_pages = (total_items + page_size - 1) // page_size

            # Execute the main query for paginated data
            result = await session.execute(
                base_query
                .order_by(MinerDiscovery.timestamp.desc())
                .limit(page_size)
                .offset(offset)
            )
            discoveries = result.scalars().all()

            return {
                "discoveries": discoveries,
                "total_pages": total_pages,
                "total_items": total_items
            }

    async def remove_all_records(self):
        async with self.session_manager.session() as session:
            async with session.begin():
                await session.execute(delete(MinerDiscovery))

    async def remove_miner_by_key(self, miner_key: str):
        async with self.session_manager.session() as session:
            async with session.begin():
                await session.execute(
                    delete(MinerDiscovery).where(MinerDiscovery.miner_key == miner_key)
                )