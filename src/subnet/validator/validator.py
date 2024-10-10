import traceback
import asyncio
import re
import threading
import time
from datetime import datetime, timedelta
from typing import cast, Dict, List
from communex.client import CommuneClient  # type: ignore
from communex.misc import get_map_modules
from communex.module.client import ModuleClient  # type: ignore
from communex.module.module import Module  # type: ignore
from communex.types import Ss58Address  # type: ignore
from loguru import logger
from substrateinterface import Keypair  # type: ignore
from ._config import ValidatorSettings
from .helpers import raise_exception_if_not_registered, get_ip_port, cut_to_max_allowed_weights
from .llm.base_llm import BaseLLM
from .scoring import ScoreCalculator
from .twitter import TwitterService, TwitterUser
from .weights_storage import WeightsStorage
from src.subnet.validator.database.models.miner_discovery import MinerDiscoveryManager
from src.subnet.validator.database.models.miner_receipt import MinerReceiptManager
from ..protocol import TwitterPost, TwitterPostMetadata


class Validator(Module):

    def __init__(
            self,
            key: Keypair,
            netuid: int,
            client: CommuneClient,
            weights_storage: WeightsStorage,
            miner_discovery_manager: MinerDiscoveryManager,
            miner_receipt_manager: MinerReceiptManager,
            score_calculator: ScoreCalculator,
            llm: BaseLLM,
            twitter_service: TwitterService,
            query_timeout: int = 60,

    ) -> None:
        super().__init__()

        self.miner_receipt_manager = miner_receipt_manager
        self.client = client
        self.key = key
        self.netuid = netuid
        self.llm = llm
        self.query_timeout = query_timeout
        self.weights_storage = weights_storage
        self.miner_discovery_manager = miner_discovery_manager
        self.score_calculator = score_calculator
        self.twitter_service = twitter_service
        self.terminate_event = threading.Event()
        self.miner_blacklist = []

    @staticmethod
    def get_addresses(client: CommuneClient, netuid: int) -> dict[int, str]:
        modules_adresses = client.query_map_address(netuid)
        for id, addr in modules_adresses.items():
            if addr.startswith('None'):
                port = addr.split(':')[1]
                modules_adresses[id] = f'0.0.0.0:{port}'
        logger.debug(f"Got modules addresses", modules_adresses=modules_adresses)
        return modules_adresses

    async def _get_twitter_posts(self, client, miner_key) -> List[TwitterPost]:
        try:
            twitter_posts = await client.call(
                "twitter_posts",
                miner_key,
                {},
                timeout=self.query_timeout,
            )

            logger.debug(f"Miner got discovery", miner_key=miner_key, twitter_posts=twitter_posts)

            return [TwitterPost(**post) for post in twitter_posts]
        except Exception as e:
            logger.warning(f"Miner failed to get discovery", error=e, miner_key=miner_key, traceback=traceback.format_exc())
            return None

    async def _challenge_miner(self, miner_info):
        start_time = time.time()
        try:
            connection, miner_metadata = miner_info
            module_ip, module_port = connection
            miner_key = miner_metadata['key']
            client = ModuleClient(module_ip, int(module_port), self.key)

            logger.info(f"Challenging miner", miner_key=miner_key)

            if miner_key in self.miner_blacklist:
                logger.info(f"Miner is blacklisted, skipping", miner_key=miner_key)
                return None

            twitter_posts: List[TwitterPost] = await self._get_twitter_posts(client, miner_key)
            if not twitter_posts:
                logger.info(f"Miner has no posts", miner_key=miner_key)
                return None

            filtered_posts = [
                post for post in twitter_posts
                if not await self.miner_receipt_manager.check_if_tweet_was_scored(post.tweet_id)
            ]

            if not filtered_posts:
                logger.info(f"No new posts to challenge", miner_key=miner_key)
                return None

            twitter_post = filtered_posts[0]

            user: TwitterUser = self.twitter_service.get_user(twitter_post.user_id)
            if not user.verified:
                self.miner_blacklist.append(miner_key)
                logger.info(f"User is not verified, blacklisting", miner_key=miner_key)
                return None

            addresses = re.findall(r'(?:1|5)[A-HJ-NP-Za-km-z1-9]{47}', user.description)
            if len(addresses) > 1:
                self.miner_blacklist.append(miner_key)
                logger.info(f"More than one address in user description, blacklisting", miner_key=miner_key)
                return None

            if miner_key.lower().strip() not in [address.lower().strip() for address in addresses]:
                self.miner_blacklist.append(miner_key)
                logger.info(f"Miner key not in description, blacklisting", miner_key=miner_key)
                return None

            tweet_details = self.twitter_service.get_tweet_details(twitter_post.tweet_id)
            if not tweet_details:
                self.miner_blacklist.append(miner_key)
                logger.info(f"Failed to get tweet details, blacklisting", miner_key=miner_key)
                return None

            positivity = self.llm.get_tweet_sentiment(tweet_details.tweet_text)
            similarity = await self.miner_receipt_manager.check_tweet_similarity(tweet_details.tweet_text)

            challenge_json = {
                "user_id": twitter_post.user_id,
                "user_name": user.user_name,
                "miner_key": miner_key,

                "user_followers": user.followers_count,
                "user_following": user.following_count,
                "user_tweets": user.tweet_count,
                "user_likes": user.like_count,
                "user_listed": user.listed_count,

                "tweet_id": tweet_details.tweet_id,
                "tweet_text": tweet_details.tweet_text,
                "created_at": tweet_details.created_at,
                "similarity": similarity,
                "positivity": positivity,
                "tweet_retweets": tweet_details.retweet_count,
                "tweet_replies": tweet_details.reply_count,
                "tweet_likes": tweet_details.like_count,
                "tweet_quotes": tweet_details.quote_count,
                "tweet_bookmarks": tweet_details.bookmark_count,
                "tweet_impressions": tweet_details.impression_count,
            }

            return TwitterPostMetadata(**challenge_json)

        except Exception as e:
            logger.error(f"Failed to challenge miner", error=e, miner_key=miner_key, traceback=traceback.format_exc())
            return None
        finally:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.info(f"Execution time for challenge_miner", execution_time=execution_time, miner_key=miner_key)

    async def validate_step(self, netuid: int, settings: ValidatorSettings) -> None:

        score_dict: dict[int, float] = {}
        miners_module_info = {}

        modules = cast(dict[str, Dict], get_map_modules(self.client, netuid=netuid, include_balances=False))
        modules_addresses = self.get_addresses(self.client, netuid)
        ip_ports = get_ip_port(modules_addresses)

        raise_exception_if_not_registered(self.key, modules)

        for key in modules.keys():
            module_meta_data = modules[key]
            uid = module_meta_data['uid']
            if uid not in ip_ports:
                continue
            module_addr = ip_ports[uid]
            miners_module_info[uid] = (module_addr, modules[key])

        for uid, miner_info in miners_module_info.items():
            score_dict[uid] = 0

        logger.info(f"Found miners", miners_module_info=miners_module_info.keys())

        for _, miner_metadata in miners_module_info.values():
            await self.miner_discovery_manager.update_miner_rank(miner_metadata['key'], miner_metadata['name'], miner_metadata['emission'])

        challenge_tasks = []
        for uid, miner_info in miners_module_info.items():
            challenge_tasks.append(self._challenge_miner(miner_info))

        responses = await asyncio.gather(*challenge_tasks)

        for uid, miner_info, response in zip(miners_module_info.keys(), miners_module_info.values(), responses):
            if not response:
                score_dict[uid] = 0
                continue

            if isinstance(response, TwitterPostMetadata):
                _, miner_metadata = miner_info
                miner_key = miner_metadata['key']
                miner_name = miner_metadata['name']
                score = await self.score_calculator.calculate_overall_score(response)
                assert score <= 100
                score_dict[uid] = score

                await self.miner_discovery_manager.store_miner_metadata(
                    uid,
                    miner_key,
                    miner_name,
                    response.user_id,
                    response.user_name,
                    response.user_followers,
                    response.user_following,
                    response.user_tweets,
                    response.user_likes,
                    response.user_listed
                )
                await self.miner_receipt_manager.store_miner_receipt(
                    miner_key,
                    miner_name,
                    response.user_id,
                    response.user_name,
                    response.tweet_id,
                    response.tweet_text,
                    datetime.strptime(response.created_at, '%Y-%m-%dT%H:%M:%S.%fZ'),
                    response.tweet_retweets,
                    response.tweet_replies,
                    response.tweet_likes,
                    response.tweet_quotes,
                    response.tweet_bookmarks,
                    response.tweet_impressions,
                    score,
                    response.similarity,
                )

        if not score_dict:
            logger.info("No miner managed to give an answer")
            return

        try:
            self.set_weights(settings, score_dict, self.netuid, self.client, self.key)
        except Exception as e:
            logger.error(f"Failed to set weights", error=e, traceback=traceback.format_exc())

    def set_weights(self,
                    settings: ValidatorSettings,
                    score_dict: dict[
                        int, float
                    ],
                    netuid: int,
                    client: CommuneClient,
                    key: Keypair,
                    ) -> None:

        score_dict = cut_to_max_allowed_weights(score_dict, settings.MAX_ALLOWED_WEIGHTS)
        self.weights_storage.setup()
        weighted_scores: dict[int, int] = self.weights_storage.read()

        logger.debug(f"Setting weights for scores", score_dict=score_dict)
        score_sum = sum(score_dict.values())

        for uid, score in score_dict.items():
            if score_sum == 0:
                weight = 0
                weighted_scores[uid] = weight
            else:

                logger.debug(f"int(score * 1000 / score_sum)", score=score, score_sum=score_sum)
                logger.debug(f"int(score * 1000 / score_sum)", weight=int(score * 1000 / score_sum))
                logger.debug(f"int(score * 100 / score_sum)", weight=int(score * 100 / score_sum))

                weight = int(score * 1000 / score_sum)
                weighted_scores[uid] = weight

        weighted_scores = {k: v for k, v in weighted_scores.items() if k in score_dict}
        logger.info(f"Set weights for scores", weighted_scores=weighted_scores)

        self.weights_storage.store(weighted_scores)

        uids = list(weighted_scores.keys())
        weights = list(weighted_scores.values())

        if len(weighted_scores) > 0:
            client.vote(key=key, uids=uids, weights=weights, netuid=netuid)

        logger.info("Set weights", action="set_weight", timestamp=datetime.utcnow().isoformat(), weighted_scores=weighted_scores)

    async def validation_loop(self, settings: ValidatorSettings) -> None:
        while not self.terminate_event.is_set():
            start_time = time.time()
            await self.validate_step(self.netuid, settings)
            if self.terminate_event.is_set():
                logger.info("Terminating validation loop")
                break

            elapsed = time.time() - start_time
            if elapsed < settings.ITERATION_INTERVAL:
                sleep_time = settings.ITERATION_INTERVAL - elapsed
                logger.info(f"Sleeping for {sleep_time}")
                self.terminate_event.wait(sleep_time)
                if self.terminate_event.is_set():
                    logger.info("Terminating validation loop")
                    break
