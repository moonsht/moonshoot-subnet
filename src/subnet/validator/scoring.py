from src.subnet.protocol import ChallengeResult

user_weights = {
    "followers": 0.4,
    "following": 0.1,
    "tweets": 0.2,
    "likes": 0.2,
    "listed": 0.1
}

tweet_weights = {
    "retweets": 0.3,
    "replies": 0.2,
    "likes": 0.2,
    "quotes": 0.1,
    "bookmarks": 0.1,
    "impressions": 0.1
}

similarity_weight = 0.3

max_values = {
    "user_followers": 100000,
    "user_following": 10000,
    "user_tweets": 10000,
    "user_likes": 100000,
    "user_listed": 1000,
    "tweet_retweets": 10000,
    "tweet_replies": 5000,
    "tweet_likes": 100000,
    "tweet_quotes": 2000,
    "tweet_bookmarks": 5000,
    "tweet_impressions": 1000000
}


def normalize(value, max_value):
    """Normalize values to a 0-1 range."""
    if max_value == 0:
        return 0
    return value / max_value


def calculate_user_power_score(user_followers, user_following, user_tweets, user_likes, user_listed):
    followers_score = normalize(user_followers, max_values['user_followers']) * user_weights['followers']
    following_score = normalize(user_following, max_values['user_following']) * user_weights['following']
    tweets_score = normalize(user_tweets, max_values['user_tweets']) * user_weights['tweets']
    likes_score = normalize(user_likes, max_values['user_likes']) * user_weights['likes']
    listed_score = normalize(user_listed, max_values['user_listed']) * user_weights['listed']

    user_power_score = followers_score + following_score + tweets_score + likes_score + listed_score
    return user_power_score


def calculate_tweet_success_score(tweet_retweets, tweet_replies, tweet_likes, tweet_quotes, tweet_bookmarks, tweet_impressions):
    retweets_score = normalize(tweet_retweets, max_values['tweet_retweets']) * tweet_weights['retweets']
    replies_score = normalize(tweet_replies, max_values['tweet_replies']) * tweet_weights['replies']
    likes_score = normalize(tweet_likes, max_values['tweet_likes']) * tweet_weights['likes']
    quotes_score = normalize(tweet_quotes, max_values['tweet_quotes']) * tweet_weights['quotes']
    bookmarks_score = normalize(tweet_bookmarks, max_values['tweet_bookmarks']) * tweet_weights['bookmarks']
    impressions_score = normalize(tweet_impressions, max_values['tweet_impressions']) * tweet_weights['impressions']

    tweet_success_score = retweets_score + replies_score + likes_score + quotes_score + bookmarks_score + impressions_score
    return tweet_success_score


def calculate_similarity_score(similarity):
    return similarity * similarity_weight


def calculate_overall_score(challenge_data: ChallengeResult):
    user_power_score = calculate_user_power_score(
        challenge_data.user_followers,
        challenge_data.user_following,
        challenge_data.user_tweets,
        challenge_data.user_likes,
        challenge_data.user_listed
    )

    tweet_success_score = calculate_tweet_success_score(
        challenge_data.tweet_retweets,
        challenge_data.tweet_replies,
        challenge_data.tweet_likes,
        challenge_data.tweet_quotes,
        challenge_data.tweet_bookmarks,
        challenge_data.tweet_impressions
    )

    similarity_score = calculate_similarity_score(
        challenge_data.similarity
    )

    total_score = (user_power_score * 0.4) + (tweet_success_score * 0.5) + (similarity_score * 0.1)
    scaled_score = total_score * 100  # The score is already normalized, so just scale by 100
    return min(max(scaled_score, 0), 100)  # Clamping between 0 and 100
