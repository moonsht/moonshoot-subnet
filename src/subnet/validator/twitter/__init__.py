from itertools import cycle
import requests
from pydantic import BaseModel
from ratelimit import limits, sleep_and_retry
from src.subnet.validator._config import ValidatorSettings


class RoundRobinBearerTokenProvider:
    def __init__(self, settings: ValidatorSettings):
        self.tokens = settings.TWITTER_BEARER_TOKENS.split(";")
        self.tokens_cycle = cycle(self.tokens)

    def get_token(self):
        return next(self.tokens_cycle)


class TwitterClient:
    def __init__(self, token_provider: RoundRobinBearerTokenProvider):
        self.token_provider = token_provider
        self.token_list = token_provider.tokens
        self.token_count = len(self.token_list)

    def create_headers(self):
        bearer_token = self.token_provider.get_token()
        headers = {"Authorization": f"Bearer {bearer_token}"}
        return headers

    @sleep_and_retry
    @limits(calls=15, period=15 * 60)
    def get_user(self, user_id):
        url = f"https://api.twitter.com/2/users/{user_id}"

        # Define the parameters
        params = {
            "user.fields": "created_at,description,entities,id,location,name,pinned_tweet_id,profile_image_url,protected,public_metrics,url,username,verified,verified_type,withheld"
        }

        headers = self.create_headers()
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            raise Exception(f"Request returned an error: {response.status_code} {response.text}")

        return response.json()

    @sleep_and_retry
    @limits(calls=15, period=15 * 60)
    def get_tweet_details(self, tweet_id):
        url = f"https://api.twitter.com/2/tweets/{tweet_id}"

        params = {
            "tweet.fields": "article,attachments,author_id,card_uri,context_annotations,conversation_id,created_at,edit_controls,edit_history_tweet_ids,entities,geo,id,in_reply_to_user_id,lang,note_tweet,possibly_sensitive,public_metrics,referenced_tweets,reply_settings,scopes,source,text,withheld",
            "expansions": "author_id,referenced_tweets.id,referenced_tweets.id.author_id,entities.mentions.username,entities.note.mentions.username,attachments.poll_ids,attachments.media_keys,attachments.media_source_tweet,in_reply_to_user_id,geo.place_id,edit_history_tweet_ids,article.cover_media,article.media_entities",
            "user.fields": "name,username,profile_image_url"
        }

        headers = self.create_headers()
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            raise Exception(f"Request returned an error: {response.status_code} {response.text}")

        return response.json()


class TwitterService:
    def __init__(self, twitter_client):
        self.twitter_client = twitter_client

    def get_user(self, user_id):
        raw_json = self.twitter_client.get_user(user_id)

        """

        {
          "data": {
            "location": "Blockchain",
            "name": "Guava",
            "created_at": "2020-07-10T09:31:47.000Z",
            "verified": false,
            "username": "0xGuava",
            "description": "Blockchain enthusiast 🔗",
            "id": "1281521441025011715",
            "public_metrics": {
              "followers_count": 778,
              "following_count": 532,
              "tweet_count": 13651,
              "listed_count": 14,
              "like_count": 8362
            },
            "profile_image_url": "https://pbs.twimg.com/profile_images/1651483732295942147/yR3HweiQ_normal.jpg",
            "protected": false
          }
        }

        """

        json = {
            "user_id": raw_json["data"]["id"],
            "user_name": raw_json["data"]["username"],
            "verified": raw_json["data"]["verified"],
            "followers_count": raw_json["data"]["public_metrics"]["followers_count"],
            "following_count": raw_json["data"]["public_metrics"]["following_count"],
            "tweet_count": raw_json["data"]["public_metrics"]["tweet_count"],
            "listed_count": raw_json["data"]["public_metrics"]["listed_count"],
            "like_count": raw_json["data"]["public_metrics"]["like_count"],
            "description": raw_json["data"]["description"]
        }

        return TwitterUser(**json)


    def get_tweet_details(self, tweet_id):
        raw_json = self.twitter_client.get_tweet_details(tweet_id)

        """
        {
          "data": {
            "context_annotations": [
              {
                "domain": {
                  "id": "30",
                  "name": "Entities [Entity Service]",
                  "description": "Entity Service top level domain, every item that is in Entity Service should be in this domain"
                },
                "entity": {
                  "id": "781974596752842752",
                  "name": "Services"
                }
              },
              {
                "domain": {
                  "id": "46",
                  "name": "Business Taxonomy",
                  "description": "Categories within Brand Verticals that narrow down the scope of Brands"
                },
                "entity": {
                  "id": "1557696940178935808",
                  "name": "Gaming Business",
                  "description": "Brands, companies, advertisers and every non-person handle with the profit intent related to offline and online games such as gaming consoles, tabletop games, video game publishers"
                }
              },
              {
                "domain": {
                  "id": "48",
                  "name": "Product",
                  "description": "Products created by Brands.  Examples: Ford Explorer, Apple iPhone."
                },
                "entity": {
                  "id": "1412579054855671809",
                  "name": "Google Innovation"
                }
              }
            ],
            "public_metrics": {
              "retweet_count": 4,
              "reply_count": 5,
              "like_count": 6,
              "quote_count": 0,
              "bookmark_count": 0,
              "impression_count": 265
            },
            "created_at": "2024-09-20T19:52:53.000Z",
            "text": "𝗧𝗿𝗮𝗻𝘀𝗳𝗼𝗿𝗺𝗶𝗻𝗴 𝗔𝗜 𝗜𝗻𝗳𝗿𝗮𝘀𝘁𝗿𝘂𝗰𝘁𝘂𝗿𝗲: 𝗖𝗼𝗺𝗺𝘂𝗻𝗲'𝘀 𝗩𝗶𝘀𝗶𝗼𝗻 𝗳𝗼𝗿 𝗮 𝗗𝗲𝗰𝗲𝗻𝘁𝗿𝗮𝗹𝗶𝘇𝗲𝗱 𝗖𝗲𝗻𝘀𝗼𝗿𝘀𝗵𝗶𝗽-𝗥𝗲𝘀𝗶𝘀𝘁𝗮𝗻𝘁 𝗙𝘂𝘁𝘂𝗿𝗲.\n\n@communeaidotorg is a peer-to-peer protocol and stake-based marketplace for modular, on-chain… https://t.co/sKi9bHHlYy https://t.co/G967QMY9pz",
            "edit_controls": {
              "edits_remaining": 5,
              "is_edit_eligible": false,
              "editable_until": "2024-09-20T20:52:53.000Z"
            },
            "entities": {
              "urls": [
                {
                  "start": 194,
                  "end": 217,
                  "url": "https://t.co/sKi9bHHlYy",
                  "expanded_url": "https://twitter.com/i/web/status/1837218394036133951",
                  "display_url": "x.com/i/web/status/1…"
                },
                {
                  "start": 218,
                  "end": 241,
                  "url": "https://t.co/G967QMY9pz",
                  "expanded_url": "https://twitter.com/0xGuava/status/1837218394036133951/photo/1",
                  "display_url": "pic.x.com/g967qmy9pz",
                  "media_key": "3_1837218363501580288"
                }
              ],
              "mentions": [
                {
                  "start": 99,
                  "end": 115,
                  "username": "communeaidotorg",
                  "id": "1620418337854349313"
                }
              ]
            },
            "reply_settings": "everyone",
            "note_tweet": {
              "entities": {
                "mentions": [
                  {
                    "start": 99,
                    "end": 115,
                    "username": "communeaidotorg",
                    "id": "1620418337854349313"
                  }
                ]
              },
              "text": "𝗧𝗿𝗮𝗻𝘀𝗳𝗼𝗿𝗺𝗶𝗻𝗴 𝗔𝗜 𝗜𝗻𝗳𝗿𝗮𝘀𝘁𝗿𝘂𝗰𝘁𝘂𝗿𝗲: 𝗖𝗼𝗺𝗺𝘂𝗻𝗲'𝘀 𝗩𝗶𝘀𝗶𝗼𝗻 𝗳𝗼𝗿 𝗮 𝗗𝗲𝗰𝗲𝗻𝘁𝗿𝗮𝗹𝗶𝘇𝗲𝗱 𝗖𝗲𝗻𝘀𝗼𝗿𝘀𝗵𝗶𝗽-𝗥𝗲𝘀𝗶𝘀𝘁𝗮𝗻𝘁 𝗙𝘂𝘁𝘂𝗿𝗲.\n\n@communeaidotorg is a peer-to-peer protocol and stake-based marketplace for modular, on-chain identifiers (Modules) linked to off-chain computing resources.\n\nWhat are Modules?\n\nModules are flexible, on-chain identifiers that represent:\n- AI models - Datasets - Storage solutions - Data scrapers - Raw computing power - Any computable resource (API-based)"
            },
            "id": "1837218394036133951",
            "edit_history_tweet_ids": [
              "1837218394036133951"
            ],
            "possibly_sensitive": false,
            "conversation_id": "1837218394036133951",
            "attachments": {
              "media_keys": [
                "3_1837218363501580288"
              ]
            },
            "lang": "en",
            "author_id": "1281521441025011715"
          },
          "includes": {
            "media": [
              {
                "media_key": "3_1837218363501580288",
                "type": "photo"
              }
            ],
            "users": [
              {
                "username": "0xGuava",
                "id": "1281521441025011715",
                "profile_image_url": "https://pbs.twimg.com/profile_images/1651483732295942147/yR3HweiQ_normal.jpg",
                "name": "Guava"
              },
              {
                "username": "communeaidotorg",
                "id": "1620418337854349313",
                "profile_image_url": "https://pbs.twimg.com/profile_images/1824202302510579712/wa9JZFTz_normal.jpg",
                "name": "commune.ai"
              }
            ],
            "tweets": [
              {
                "context_annotations": [
                  {
                    "domain": {
                      "id": "30",
                      "name": "Entities [Entity Service]",
                      "description": "Entity Service top level domain, every item that is in Entity Service should be in this domain"
                    },
                    "entity": {
                      "id": "781974596752842752",
                      "name": "Services"
                    }
                  },
                  {
                    "domain": {
                      "id": "46",
                      "name": "Business Taxonomy",
                      "description": "Categories within Brand Verticals that narrow down the scope of Brands"
                    },
                    "entity": {
                      "id": "1557696940178935808",
                      "name": "Gaming Business",
                      "description": "Brands, companies, advertisers and every non-person handle with the profit intent related to offline and online games such as gaming consoles, tabletop games, video game publishers"
                    }
                  },
                  {
                    "domain": {
                      "id": "48",
                      "name": "Product",
                      "description": "Products created by Brands.  Examples: Ford Explorer, Apple iPhone."
                    },
                    "entity": {
                      "id": "1412579054855671809",
                      "name": "Google Innovation"
                    }
                  }
                ],
                "public_metrics": {
                  "retweet_count": 4,
                  "reply_count": 5,
                  "like_count": 6,
                  "quote_count": 0,
                  "bookmark_count": 0,
                  "impression_count": 265
                },
                "created_at": "2024-09-20T19:52:53.000Z",
                "text": "𝗧𝗿𝗮𝗻𝘀𝗳𝗼𝗿𝗺𝗶𝗻𝗴 𝗔𝗜 𝗜𝗻𝗳𝗿𝗮𝘀𝘁𝗿𝘂𝗰𝘁𝘂𝗿𝗲: 𝗖𝗼𝗺𝗺𝘂𝗻𝗲'𝘀 𝗩𝗶𝘀𝗶𝗼𝗻 𝗳𝗼𝗿 𝗮 𝗗𝗲𝗰𝗲𝗻𝘁𝗿𝗮𝗹𝗶𝘇𝗲𝗱 𝗖𝗲𝗻𝘀𝗼𝗿𝘀𝗵𝗶𝗽-𝗥𝗲𝘀𝗶𝘀𝘁𝗮𝗻𝘁 𝗙𝘂𝘁𝘂𝗿𝗲.\n\n@communeaidotorg is a peer-to-peer protocol and stake-based marketplace for modular, on-chain… https://t.co/sKi9bHHlYy https://t.co/G967QMY9pz",
                "edit_controls": {
                  "edits_remaining": 5,
                  "is_edit_eligible": false,
                  "editable_until": "2024-09-20T20:52:53.000Z"
                },
                "entities": {
                  "urls": [
                    {
                      "start": 194,
                      "end": 217,
                      "url": "https://t.co/sKi9bHHlYy",
                      "expanded_url": "https://twitter.com/i/web/status/1837218394036133951",
                      "display_url": "x.com/i/web/status/1…"
                    },
                    {
                      "start": 218,
                      "end": 241,
                      "url": "https://t.co/G967QMY9pz",
                      "expanded_url": "https://twitter.com/0xGuava/status/1837218394036133951/photo/1",
                      "display_url": "pic.x.com/g967qmy9pz",
                      "media_key": "3_1837218363501580288"
                    }
                  ],
                  "mentions": [
                    {
                      "start": 99,
                      "end": 115,
                      "username": "communeaidotorg",
                      "id": "1620418337854349313"
                    }
                  ]
                },
                "reply_settings": "everyone",
                "note_tweet": {
                  "entities": {
                    "mentions": [
                      {
                        "start": 99,
                        "end": 115,
                        "username": "communeaidotorg",
                        "id": "1620418337854349313"
                      }
                    ]
                  },
                  "text": "𝗧𝗿𝗮𝗻𝘀𝗳𝗼𝗿𝗺𝗶𝗻𝗴 𝗔𝗜 𝗜𝗻𝗳𝗿𝗮𝘀𝘁𝗿𝘂𝗰𝘁𝘂𝗿𝗲: 𝗖𝗼𝗺𝗺𝘂𝗻𝗲'𝘀 𝗩𝗶𝘀𝗶𝗼𝗻 𝗳𝗼𝗿 𝗮 𝗗𝗲𝗰𝗲𝗻𝘁𝗿𝗮𝗹𝗶𝘇𝗲𝗱 𝗖𝗲𝗻𝘀𝗼𝗿𝘀𝗵𝗶𝗽-𝗥𝗲𝘀𝗶𝘀𝘁𝗮𝗻𝘁 𝗙𝘂𝘁𝘂𝗿𝗲.\n\n@communeaidotorg is a peer-to-peer protocol and stake-based marketplace for modular, on-chain identifiers (Modules) linked to off-chain computing resources.\n\nWhat are Modules?\n\nModules are flexible, on-chain identifiers that represent:\n- AI models - Datasets - Storage solutions - Data scrapers - Raw computing power - Any computable resource (API-based)"
                },
                "id": "1837218394036133951",
                "edit_history_tweet_ids": [
                  "1837218394036133951"
                ],
                "possibly_sensitive": false,
                "conversation_id": "1837218394036133951",
                "attachments": {
                  "media_keys": [
                    "3_1837218363501580288"
                  ]
                },
                "lang": "en",
                "author_id": "1281521441025011715"
              }
            ]
          }
        }
        """

        tweet_text = raw_json["data"]["text"]
        user_id = raw_json["data"]["author_id"]
        public_metrics = raw_json["data"]["public_metrics"]
        creation_date = raw_json["data"]["created_at"]
        users = raw_json["includes"]["users"]
        username = None
        for user in users:
            if user["id"] == user_id:
                username = f"@{user['username']}"

        json = {
            "tweet_id": tweet_id,
            "creation_date": creation_date,
            "username": username,
            "tweet_text": tweet_text,
            "user_id": user_id,
            "retweet_count": public_metrics["retweet_count"],
            "reply_count": public_metrics["reply_count"],
            "like_count": public_metrics["like_count"],
            "quote_count": public_metrics["quote_count"],
            "bookmark_count": public_metrics["bookmark_count"],
            "impression_count": public_metrics["impression_count"]
        }

        return Tweet(**json)


class TwitterUser(BaseModel):
    user_id: str
    user_name: str
    verified: bool
    followers_count: int
    following_count: int
    tweet_count: int
    listed_count: int
    like_count: int
    description: str


class Tweet(BaseModel):
    tweet_id: str
    creation_date: str
    username: str
    tweet_text: str
    user_id: str
    retweet_count: int
    reply_count: int
    like_count: int
    quote_count: int
    bookmark_count: int
    impression_count: int

