<div style="display: flex; align-items: center;">
  <img src="docs/subnet_logo.png" alt="subnet_logo" style="width: 60px; height: 60px; margin-right: 10px;">
  <h1 style="margin: 0;">Chain Insights</h1>
</div>

## Table of Contents
 
- [Introduction](#introduction)
- [Subnet Vision](#subnet-vision)
- [Roadmap](#roadmap)
- [Overview](#overview)
- [Subnet Architecture Components](#subnet-architecture-components)
- [Scoring](#scoring)
- [Miner Setup](MINER_SETUP.md)
- [Validator Setup](VALIDATOR_SETUP.md)

# Vision
The vision of the subnet is to promote the CommuneAI project within the crypto Twitter community, leveraging social engagement as a driving force. Miners, referred to as "Commune crypto shillers," are rewarded based on the performance of their tweets. By using a fair and transparent scoring algorithm that evaluates tweet engagement, user influence, and content relevance, the subnet aims to create a competitive and vibrant environment where participants are incentivized to actively support the CommuneAI project, fostering growth, engagement, and community building across crypto Twitter.
 
# Scoring
### Overview

The scoring mechanism for miners evaluates their social media contributions using both **user metrics** and **tweet metrics**. Validators monitor these metrics for all miners and calculate scores to maintain a fair and competitive network. Scores ensure that active, engaging miners are rewarded, while their impact diminishes over time to encourage consistent contributions.

### Key Components

- **User Metrics**: Metrics such as followers, following, tweets, likes, and listed count are weighted and normalized. **Each validator tracks the maximum user metrics** from all miners over the past month, which are then used as the normalization baseline. This comparison ensures that a miner's influence is measured relative to the most impactful users in the subnet.

- **Tweet Metrics**: Similarly, metrics like retweets, replies, likes, quotes, bookmarks, and impressions are evaluated. **Validators track the maximum tweet metrics** across all miners’ tweets over the past month to determine the normalization factors. This ensures a fair comparison of a miner’s tweet success with the best-performing tweets in the subnet.

- **Similarity Score**: This score evaluates how relevant a tweet is to the subnet’s goals, weighted accordingly.

- **Time Decay**: Tweet impact decreases over time, with tweets under 36 hours old receiving full influence and older tweets seeing reduced influence.

- **Positivity Score**: This measures the sentiment positivity of the tweet, scaled as a percentage.

### Score Calculation Process

1. **User Power Score**:
   - User metrics (followers, tweets, etc.) are normalized against the **maximum user metrics tracked by validators across all miners** for the last month.
   - Each metric is weighted and combined to form a miner’s user power score.

2. **Tweet Success Score**:
   - Tweet metrics are normalized against the **maximum tweet metrics from all miners’ tweets**, tracked by validators.
   - The success score is weighted and calculated based on these normalized values.

3. **Similarity Score**:
   - Evaluates the relevance of a miner’s tweet content to the subnet, applying a predefined weight.

4. **Time Decay Multiplier**:
   - A time-decay factor reduces the influence of older tweets, with full impact for tweets under 36 hours old.

5. **Overall Score**:
   - The overall score combines the user power score (20%) and tweet success score (80%), further adjusted by the time decay, similarity, and positivity factors.
   - Final scores are clamped between 0 and 100.

### Example Calculation

For a miner whose tweet sees high engagement within the first 36 hours, the score will be strong, reflecting both tweet performance and their overall influence in the subnet. The final score is adjusted based on comparisons to the best-performing miners over the past month.

# Miner Setup

### Miner Setup

#### Prerequisites

- Ubuntu 22.04 LTS (or similar)
- Python 3.10+
- Node.js 18.x+
- PM2
- Communex
- Git

```shell
sudo apt update
sudo apt upgrade -y
sudo apt install python3-pip python3-venv python3-dev git build-essential libssl-dev libffi-dev

pip install communex

curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install pm2 -g
pm2 startup
```

#### Clone Repository

```shell
git clone https://github.com/moonsht/moonshoot-subnet.git miner
```

#### Env configuration

Navigate to miner directory and copy the `.env.miner.example` file to `.env.miner.mainnet`.
```shell
cd miner
cp /env/.env.miner.example .env.miner.mainnet
```

Create miner dashboard password hash:
```shell
cd src
python -c ./subnet/miner_dashboard/gerate_pwd_hash.py {your password}
```

Now edit the `.env.miner.mainnet` file to set the appropriate configurations:
```shell
NET_UID=22
MINER_KEY=miner
MINER_NAME=miner
PORT=9951
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changeit456$
POSTGRES_HOST=localhost
POSTGRES_PORT=5410
POSTGRES_DB=miner
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
USER_ID= #your twitter account user id, account must have verified status!
DASHBOARD_USER_NAME=#your miner dashboard login
DASHBOARD_USER_PASSWORD_HASH=#your miner dashboard password hash
```
 
#### Miner wallet creation

```shell
comx key create miner1
comx key list
# transfer COMAI to your miner wallet for registration (aprox 10 COMAI are needed)
comx module register miner miner 22 --port 9951
```

### Running the miner and monitoring

```shell
# use pm2 to run the miner
pm2 start ./scripts/run_miner.sh --name miner
pm2 save
```