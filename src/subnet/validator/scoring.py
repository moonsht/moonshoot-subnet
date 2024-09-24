from datetime import datetime, timedelta

from src.subnet.protocol import TwitterPostMetadata
from src.subnet.validator.database.models.miner_discovery import MinerDiscoveryManager
from src.subnet.validator.database.models.miner_receipt import MinerReceiptManager

user_weights = {
    "followers": 0.4,
    "following": 0.1,
    "tweets": 0.2,
    "likes": 0.2,
    "listed": 0.1
}

tweet_weights = {
    "retweets": 0.2,
    "replies": 0.2,
    "likes": 0.2,
    "quotes": 0.2,
    "bookmarks": 0.1,
    "impressions": 0.1
}

similarity_weight = 0.2
positivity_weight = 0.1


def normalize(value, max_value):
    """Normalize values to a 0-1 range."""
    if max_value == 0:
        return 0
    return value / max_value


class ScoreCalculator:

    def __init__(self, miner_discovery_manager: MinerDiscoveryManager, miner_receipt_manager: MinerReceiptManager):
        self.miner_discovery_manager = miner_discovery_manager
        self.miner_receipt_manager = miner_receipt_manager

    async def calculate_user_power_score(self, user_followers, user_following, user_tweets, user_likes, user_listed):
        max_metrics = await self.miner_discovery_manager.get_max_metrics_last_month()

        followers_score = normalize(user_followers, max_metrics['followers']) * user_weights['followers']
        following_score = normalize(user_following, max_metrics['following']) * user_weights['following']
        tweets_score = normalize(user_tweets, max_metrics['tweets']) * user_weights['tweets']
        likes_score = normalize(user_likes, max_metrics['likes']) * user_weights['likes']
        listed_score = normalize(user_listed, max_metrics['listed']) * user_weights['listed']

        user_power_score = followers_score + following_score + tweets_score + likes_score + listed_score
        return user_power_score

    async def calculate_tweet_success_score(self, tweet_retweets, tweet_replies, tweet_likes, tweet_quotes, tweet_bookmarks, tweet_impressions):

        max_metrics = await self.miner_receipt_manager.get_max_metrics_last_month_receipt()

        retweets_score = normalize(tweet_retweets, max_metrics['retweets']) * tweet_weights['retweets']
        replies_score = normalize(tweet_replies, max_metrics['replies']) * tweet_weights['replies']
        likes_score = normalize(tweet_likes, max_metrics['likes']) * tweet_weights['likes']
        quotes_score = normalize(tweet_quotes, max_metrics['quotes']) * tweet_weights['quotes']
        bookmarks_score = normalize(tweet_bookmarks, max_metrics['bookmarks']) * tweet_weights['bookmarks']
        impressions_score = normalize(tweet_impressions, max_metrics['impressions']) * tweet_weights['impressions']

        tweet_success_score = retweets_score + replies_score + likes_score + quotes_score + bookmarks_score + impressions_score
        return tweet_success_score

    @staticmethod
    def calculate_similarity_score(similarity):
        return similarity * similarity_weight

    @staticmethod
    def calculate_time_decay_multiplier(created_at):
        created_at = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%fZ')
        now = datetime.utcnow()
        tweet_age = now - created_at
        hours_36 = timedelta(hours=36)
        days_7 = timedelta(days=7)

        if tweet_age <= hours_36:
            return 1.0
        elif tweet_age >= days_7:
            return 0.0
        else:
            total_decay_range = days_7 - hours_36
            decay_time = tweet_age - hours_36
            return max(0.0, 1.0 - (decay_time.total_seconds() / total_decay_range.total_seconds()))

    async def calculate_overall_score(self, metadata: TwitterPostMetadata):
        user_power_score = await self.calculate_user_power_score(
            metadata.user_followers,
            metadata.user_following,
            metadata.user_tweets,
            metadata.user_likes,
            metadata.user_listed
        )

        tweet_success_score = await self.calculate_tweet_success_score(
            metadata.tweet_retweets,
            metadata.tweet_replies,
            metadata.tweet_likes,
            metadata.tweet_quotes,
            metadata.tweet_bookmarks,
            metadata.tweet_impressions
        )

        similarity_score = self.calculate_similarity_score(
            1 - metadata.similarity
        )

        positivity_score = metadata.positivity / 100

        time_decay_multiplier = self.calculate_time_decay_multiplier(metadata.created_at)
        total_score = (tweet_success_score * 0.8) + (user_power_score * 0.2)
        scaled_score = total_score * 100 * time_decay_multiplier * similarity_score * positivity_score
        return min(max(scaled_score, 0), 100)  # Clamping between 0 and 100
