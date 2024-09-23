import asyncio
import signal
import sys
from datetime import datetime
from communex._common import get_node_url
from communex.client import CommuneClient
from communex.compat.key import classic_load_key
from loguru import logger
from src.subnet.validator.database.models.miner_discovery import MinerDiscoveryManager
from src.subnet.validator.database.models.miner_receipt import MinerReceiptManager
from src.subnet.validator.database.models.miner_twitter_posts_blacklist import MinerTwitterPostBlacklistManager
from src.subnet.validator.database.session_manager import DatabaseSessionManager, run_migrations
from src.subnet.validator.llm.factory import LLMFactory
from src.subnet.validator.scoring import ScoreCalculator
from src.subnet.validator.twitter import TwitterService, TwitterClient, RoundRobinBearerTokenProvider
from src.subnet.validator.weights_storage import WeightsStorage
from src.subnet.validator._config import load_environment, SettingsManager
from src.subnet.validator.validator import Validator


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python -m subnet.cli <environment>")
        sys.exit(1)

    environment = sys.argv[1]
    load_environment(environment)

    settings_manager = SettingsManager.get_instance()
    settings = settings_manager.get_settings()
    keypair = classic_load_key(settings.VALIDATOR_KEY)

    def patch_record(record):
        record["extra"]["validator_key"] = keypair.ss58_address
        record["extra"]["service"] = 'validator'
        record["extra"]["timestamp"] = datetime.utcnow().isoformat()
        record["extra"]["level"] = record['level'].name

        return True

    logger.remove()
    logger.add(
        "../logs/validator.log",
        rotation="500 MB",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message} | {extra}",
        level="DEBUG",
        filter=patch_record
    )

    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <blue>{message}</blue> | {extra}",
        level="DEBUG",
        filter=patch_record,
    )

    c_client = CommuneClient(get_node_url(use_testnet=(environment == 'testnet')))
    weights_storage = WeightsStorage(settings.WEIGHTS_FILE_NAME)

    session_manager = DatabaseSessionManager()
    session_manager.init(settings.DATABASE_URL)
    run_migrations()

    miner_discovery_manager = MinerDiscoveryManager(session_manager)
    miner_receipt_manager = MinerReceiptManager(session_manager)
    miner_twitter_post_blacklist_manager = MinerTwitterPostBlacklistManager(session_manager)
    score_calculator = ScoreCalculator(miner_discovery_manager, miner_receipt_manager)

    llm = LLMFactory.create_llm(settings)
    twitter_round_robbin_token_provider = RoundRobinBearerTokenProvider(settings)
    twitter_client = TwitterClient(twitter_round_robbin_token_provider)
    twitter_service = TwitterService(twitter_client)

    validator = Validator(
        keypair,
        settings.NET_UID,
        c_client,
        weights_storage,
        miner_discovery_manager,
        miner_receipt_manager,
        score_calculator,
        miner_twitter_post_blacklist_manager,
        llm,
        twitter_service,
        query_timeout=settings.QUERY_TIMEOUT,
    )


    def shutdown_handler(signal_num, frame):
        logger.info("Received shutdown signal, stopping...")
        validator.terminate_event.set()
        settings_manager.stop_reloader()
        logger.debug("Shutdown handler finished")

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        asyncio.run(validator.validation_loop(settings))
    except KeyboardInterrupt:
        logger.info("Validator loop interrupted")


