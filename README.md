# roblox-stat-tracker

I needed a lightweight way to monitor active player counts, voting ratios, and favorite counts on specific Roblox games over time without signing up for bloated third-party SaaS analytics. This tool tracks those metrics using a local SQLite database and Roblox's public APIs.

It handles resolving public place IDs (the ones in the game URL) into internal Roblox universe IDs automatically.

## Installation

1. Clone the repository.
2. Install dependencies:

```cmd
pip install -r requirements.txt
```

## How it runs

All tracking data is stored in `~/.roblox_stats.db` by default.

### Add a game to track
To start tracking a game, add it using its public Place ID (found in the game's web URL):

```cmd
python tracker.py add 185655149
```

### Collect a snapshot
Fetch current stats for all registered games and save them to the database:

```cmd
python tracker.py snapshot
```

*Tip: Set up a Windows Task Scheduler task to run `python tracker.py snapshot` every hour to collect historical data.*

### View history
Show gathered stats in a neat terminal table, including an ASCII sparkline of active player trends:

```cmd
python tracker.py history 185655149
```

<!-- updated: 2026-09-17 -->
