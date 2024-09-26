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

