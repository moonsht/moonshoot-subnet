import signal
from datetime import datetime
import redis
import uvicorn
from communex.compat.key import classic_load_key
from fastapi import FastAPI, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from loguru import logger
from src.subnet.validator._config import load_environment, SettingsManager
from src.subnet.validator.database.models.miner_discovery import MinerDiscoveryManager
from src.subnet.validator.database.models.miner_receipt import MinerReceiptManager
from src.subnet.validator.database.session_manager import DatabaseSessionManager
from src.subnet.validator.rate_limiter import RateLimiterMiddleware


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m validator_dashboard <environment> ; where <environment> is 'testnet' or 'mainnet'")
        sys.exit(1)

    env = sys.argv[1]
    use_testnet = env == 'testnet'
    load_environment(env)

    settings_manager = SettingsManager.get_instance()
    settings = settings_manager.get_settings()
    keypair = classic_load_key(settings.VALIDATOR_KEY)

    def patch_record(record):
        record["extra"]["validator_key"] = keypair.ss58_address
        record["extra"]["service"] = 'validator_dashboard'
        record["extra"]["timestamp"] = datetime.utcnow().isoformat()
        record["extra"]["level"] = record['level'].name
        return True

    logger.remove()
    logger.add(
        "../../logs/validator_dashboard.log",
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

    app = FastAPI(title="Validator Dashboard", description="Validator Dashboard")
    app.add_middleware(
        RateLimiterMiddleware,
        redis_url=settings.REDIS_URL,
        max_requests=settings.API_RATE_LIMIT,
        window_seconds=60,
    )

    templates = Jinja2Templates(directory="subnet/validator_dashboard/templates")
    app.mount("/static", StaticFiles(directory="subnet/validator_dashboard/static"), name="static")

    import math

    @app.get("/")
    async def master_page(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/receipts")
    async def read_entries(request: Request, page: int = Query(1, gt=0), per_page: int = Query(5, gt=0)):
        data = await miner_receipt_manager.get_receipts_by_miner_key(page=page, page_size=per_page, miner_key=None, user_id=None, user_name=None)
        return templates.TemplateResponse("list_tweets.html", {
            "request": request,
            "receipts": data["receipts"],
            "page": page,
            "total_pages": data["total_pages"]
        })

    @app.get("/miners")
    async def read_miners(request: Request, page: int = Query(1, gt=0), per_page: int = Query(5, gt=0)):
        data = await miner_discovery_manager.get_discoveries_by_miner_key(page=page, page_size=per_page, miner_key=None, user_id=None, user_name=None)
        return templates.TemplateResponse("miners.html", {
            "request": request,
            "discoveries": data["discoveries"],
            "page": page,
            "total_pages": data["total_pages"]
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
