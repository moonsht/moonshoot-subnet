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

    async def store_miner_metadata(self, uid: int, miner_key: str, user_id: str, user_name: str, followers: int, following: int, tweets: int, likes: int, listed: int):
        async with self.session_manager.session() as session:
            async with session.begin():
                stmt = insert(MinerDiscovery).values(
                    uid=uid,
                    miner_key=miner_key,
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
                    func.max(MinerDiscovery.followers).label('max_followers'),
                    func.max(MinerDiscovery.following).label('max_following'),
                    func.max(MinerDiscovery.tweets).label('max_tweets'),
                    func.max(MinerDiscovery.likes).label('max_likes'),
                    func.max(MinerDiscovery.listed).label('max_listed')
                )
                .where(MinerDiscovery.timestamp >= one_month_ago)
            )

            row = result.fetchone()

            return {
                "max_followers": row.max_followers if row.max_followers is not None else 100000,
                "max_following": row.max_following if row.max_following is not None else 10000,
                "max_tweets": row.max_tweets if row.max_tweets is not None else 10000,
                "max_likes": row.max_likes if row.max_likes is not None else 100000,
                "max_listed": row.max_listed if row.max_listed is not None else 1000
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