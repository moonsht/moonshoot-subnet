import signal
from datetime import datetime

import redis
import uvicorn
from communex.compat.key import classic_load_key
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from loguru import logger

from src.subnet.validator._config import ValidatorSettings, load_environment, SettingsManager
from src.subnet.validator.database.models.miner_discovery import MinerDiscoveryManager
from src.subnet.validator.database.models.miner_receipt import MinerReceiptManager
from src.subnet.validator.database.session_manager import DatabaseSessionManager
from src.subnet.validator.rate_limiter import RateLimiterMiddleware


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m subnet.validator.leaderboard <environment> ; where <environment> is 'testnet' or 'mainnet'")
        sys.exit(1)

    env = sys.argv[1]
    use_testnet = env == 'testnet'
    load_environment(env)

    settings_manager = SettingsManager.get_instance()
    settings = settings_manager.get_settings()
    keypair = classic_load_key(settings.VALIDATOR_KEY)

    def patch_record(record):
        record["extra"]["validator_key"] = keypair.ss58_address
        record["extra"]["service"] = 'leaderboard'
        record["extra"]["timestamp"] = datetime.utcnow().isoformat()
        record["extra"]["level"] = record['level'].name
        return True

    logger.remove()
    logger.add(
        "../../logs/leaderboard.log",
        rotation="500 MB",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        filter=patch_record
    )

    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <blue>{message}</blue> | {extra}",
        level="DEBUG",
        filter=patch_record
    )

    session_manager = DatabaseSessionManager()
    session_manager.init(settings.DATABASE_URL)
    redis_client = redis.asyncio.from_url(settings.REDIS_URL)

    miner_discovery_manager = MinerDiscoveryManager(session_manager)
    miner_receipt_manager = MinerReceiptManager(session_manager)

    # Sample data
    entries = [
        {
            "id": 8,
            "miner_key": "5DqE84CcLFnqUZhbo2gpiiqffErwMh6bhDRWGvZnm8dg9ETN",
            "tweet_id": "1837886288025800829",
            "tweet_created_at": "2024-09-22 16:06:51.000000",
            "tweet_retweet_count": 0,
            "tweet_reply_count": 0,
            "tweet_like_count": 1,
            "tweet_quote_count": 0,
            "tweet_bookmark_count": 0,
            "tweet_impression_count": 197,
            "score": 3,
            "timestamp": "2024-09-24 12:18:28.989460",
            "user_id": "1281521441025011715",
            "user_name": "0xGuava",
            "miner_name": "miner1",
            "tweet_content": "The rewards for our latest quest have been distributed to all winners. Stay tuned for upcoming giveaways and exciting new quests!",
            "similarity": 0
        },
        {
            "id": 9,
            "miner_key": "5DqE84CcLFnqUZhbo2gpiiqffErwMh6bhDRWGvZnm8dg9ETN",
            "tweet_id": "1838517472040763851",
            "tweet_created_at": "2024-09-24 09:54:57.000000",
            "tweet_retweet_count": 1,
            "tweet_reply_count": 2,
            "tweet_like_count": 4,
            "tweet_quote_count": 0,
            "tweet_bookmark_count": 0,
            "tweet_impression_count": 89,
            "score": 11,
            "timestamp": "2024-09-24 12:20:31.692123",
            "user_id": "1281521441025011715",
            "user_name": "0xGuava",
            "miner_name": "miner1",
            "tweet_content": "CM is how we say GM in #CommuneAI",
            "similarity": 0.1515151560306549
        }
        # Add more records if necessary
    ]

    # New data for the second page
    user_stats = [
        {
            "id": 37,
            "uid": 0,
            "miner_key": "5DqE84CcLFnqUZhbo2gpiiqffErwMh6bhDRWGvZnm8dg9ETN",
            "user_id": "1281521441025011715",
            "timestamp": "2024-09-24 12:20:31.643963",
            "emission": 0,
            "followers": 789,
            "following": 544,
            "tweets": 13691,
            "likes": 8373,
            "listed": 14,
            "user_name": "0xGuava",
            "miner_name": "miner1"
        }
        # Add more records if necessary
    ]

    # Sort entries by "timestamp" in descending order (newest first)
    sorted_entries = sorted(entries, key=lambda x: datetime.strptime(x['timestamp'], "%Y-%m-%d %H:%M:%S.%f"),
                            reverse=True)

    app = FastAPI(title="Leaderboard", description="Leaderboard for Subnet Miners")
    app.add_middleware(
        RateLimiterMiddleware,
        redis_url=settings.REDIS_URL,
        max_requests=settings.API_RATE_LIMIT,
        window_seconds=60,
    )

    templates = Jinja2Templates(directory="dashboard/templates")
    app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

    import math

    @app.get("/")
    async def master_page(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/receipts")
    async def read_entries(request: Request, page: int = Query(1, gt=0), per_page: int = Query(5, gt=0)):
        # Pagination logic
        total_entries = len(sorted_entries)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_entries = sorted_entries[start:end]

        total_pages = math.ceil(total_entries / per_page)

        return templates.TemplateResponse("receipts.html", {
            "request": request,
            "entries": paginated_entries,
            "page": page,
            "total_pages": total_pages
        })

    @app.get("/miners")
    async def read_miners(request: Request, page: int = Query(1, gt=0), per_page: int = Query(5, gt=0)):
        total_stats = len(user_stats)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_stats = user_stats[start:end]

        total_pages = math.ceil(total_stats / per_page)

        return templates.TemplateResponse("miners.html", {
            "request": request,
            "user_stats": paginated_stats,
            "page": page,
            "total_pages": total_pages
        })

    def shutdown_handler(signal, frame):
        logger.debug("Shutdown handler started")
        settings_manager.stop_reloader()
        uvicorn_server.should_exit = True
        uvicorn_server.force_exit = True
        logger.debug("Shutdown handler finished")

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    uvicorn_server = uvicorn.Server(config=uvicorn.Config(app, host="0.0.0.0", port=settings.PORT + 1, workers=settings.WORKERS))
    uvicorn_server.run()
