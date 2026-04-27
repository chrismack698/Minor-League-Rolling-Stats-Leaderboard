# Minor-League-Rolling-Stats-Leaderboard

Rolling MiLB hitter and pitcher leaderboards for a Streamlit dashboard.

## MLB Stats API Pipeline

`mlb_stats_pipeline.py` replaces the high-volume FanGraphs player-page scraping
approach. It pulls completed MiLB games from MLB Stats API, caches one JSON file
per game, builds local player game logs, then calculates rolling leaderboard
CSV files for the dashboard.

Run:

```powershell
python mlb_stats_pipeline.py --season 2026 --end-date 2026-04-27
```

Before a full refresh, run a small smoke test:

```powershell
python mlb_stats_pipeline.py --season 2025 --end-date 2025-07-01 --sport-ids 11 --limit-games 3
```

The full refresh can take a while because it fetches one cached JSON file per
completed MiLB game in the rolling window. The script prints progress for each
game and writes request/parse failures to `data/mlb_stats_api_errors.csv`.

Outputs:

```text
data/hitters/player_game_logs.csv
data/hitters/leaderboard_data.csv
data/pitchers/player_pitching_game_logs.csv
data/pitchers/leaderboard_pitch_data.csv
```

The script caches raw API responses under `data/raw/mlb_stats_api` so repeated
runs do not re-download the same games. Use `--force-refresh` only when you need
to re-fetch already cached schedules or boxscores.

Rookie leagues are separated in the dashboard `Level` field when MLB's API
identifies the league as Dominican Summer League, Arizona Complex League, or
Florida Complex League. Those appear as `DSL`, `ACL`, and `FCL` instead of a
generic `R`.

## Formula Notes

The pipeline computes league/window baselines from downloaded MiLB game logs.
Baselines are grouped by MLB Stats API MiLB league id over each rolling window.

For hitters, the dashboard can hide `wOBA`, but `wRC+` still uses weighted
offensive events internally:

```text
wOBA =
(wBB*BB + wHBP*HBP + w1B*1B + w2B*2B + w3B*3B + wHR*HR)
/
(AB + BB - IBB + SF + HBP)

wRAA = ((player_wOBA - league_wOBA) / wOBA_scale) * PA

wRC+ = ((wRAA / PA + league_R_per_PA) / league_R_per_PA) * 100
```

The event weights come from FanGraphs' public seasonal Guts constants. League
`wOBA` and `R/PA` are calculated from the local MiLB logs for the same rolling
window. Park factors are intentionally omitted.

For pitchers:

```text
raw_FIP = (13*HR + 3*(BB + HBP) - 2*K) / IP

league_FIP_constant =
league_ERA - ((13*league_HR + 3*(league_BB + league_HBP) - 2*league_K) / league_IP)

FIP = raw_FIP + league_FIP_constant
```

## Legacy FanGraphs Scripts

`scraper.py` and `pitch_scraper.py` are left in place for reference, but they
make a very large number of FanGraphs requests and should not be used for normal
refreshes.
