from __future__ import annotations

import argparse
import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests


BASE_URL = "https://statsapi.mlb.com/api/v1"
LIVE_URL = "https://statsapi.mlb.com/api/v1.1"
PROJECT_ROOT = Path(__file__).resolve().parent

SPORT_LEVELS = {
    11: "AAA",
    12: "AA",
    13: "A+",
    14: "A",
    16: "R",
}

DEFAULT_SPORT_IDS = tuple(SPORT_LEVELS)
DEFAULT_WINDOWS = (7, 15, 30, 45, 60)

# FanGraphs public seasonal constants. These are used as event weights only;
# league/window baselines are calculated from the downloaded MiLB game logs.
WOBA_CONSTANTS = {
    2025: {
        "woba": 0.313,
        "scale": 1.232,
        "wBB": 0.691,
        "wHBP": 0.722,
        "w1B": 0.882,
        "w2B": 1.252,
        "w3B": 1.584,
        "wHR": 2.037,
    },
    2026: {
        "woba": 0.318,
        "scale": 1.280,
        "wBB": 0.711,
        "wHBP": 0.743,
        "w1B": 0.910,
        "w2B": 1.294,
        "w3B": 1.639,
        "wHR": 2.110,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build rolling MiLB leaderboards from MLB Stats API game boxscores."
    )
    parser.add_argument("--season", type=int, default=date.today().year)
    parser.add_argument("--end-date", default=date.today().isoformat())
    parser.add_argument("--max-window", type=int, default=max(DEFAULT_WINDOWS))
    parser.add_argument("--cache-dir", default="data/raw/mlb_stats_api")
    parser.add_argument("--delay", type=float, default=0.15)
    parser.add_argument("--request-timeout", type=float, default=12.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument(
        "--sport-ids",
        default=",".join(str(sport_id) for sport_id in DEFAULT_SPORT_IDS),
        help="Comma-separated MLB Stats API sport IDs. Default: 11,12,13,14,16.",
    )
    parser.add_argument(
        "--limit-games",
        type=int,
        default=0,
        help="Stop after this many completed games. Useful for smoke tests.",
    )
    parser.add_argument("--force-refresh", action="store_true")
    return parser.parse_args()


def resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def request_json(
    url: str,
    cache_path: Path,
    delay: float,
    force_refresh: bool,
    request_timeout: float,
    retries: int,
) -> dict[str, Any]:
    if cache_path.exists() and not force_refresh:
        return json.loads(cache_path.read_text(encoding="utf-8"))

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "milb-rolling-leaderboard/1.0"},
                timeout=(5, request_timeout),
            )
            response.raise_for_status()
            data = response.json()
            temp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
            temp_path.write_text(json.dumps(data), encoding="utf-8")
            temp_path.replace(cache_path)
            if delay:
                time.sleep(delay)
            return data
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < retries:
                sleep_for = min(2 ** (attempt - 1), 8)
                print(f"Request failed ({attempt}/{retries}); retrying in {sleep_for}s: {url}", flush=True)
                time.sleep(sleep_for)

    raise RuntimeError(f"Failed after {retries} attempts: {url}") from last_error


def get_schedule(
    sport_id: int,
    start_date: date,
    end_date: date,
    cache_dir: Path,
    delay: float,
    force_refresh: bool,
    request_timeout: float,
    retries: int,
) -> list[dict[str, Any]]:
    url = (
        f"{BASE_URL}/schedule?sportId={sport_id}"
        f"&startDate={start_date.isoformat()}&endDate={end_date.isoformat()}"
        "&gameType=R&hydrate=team,venue"
    )
    cache_path = cache_dir / "schedules" / f"{sport_id}_{start_date}_{end_date}.json"
    data = request_json(url, cache_path, delay, force_refresh, request_timeout, retries)
    games: list[dict[str, Any]] = []
    for day in data.get("dates", []):
        games.extend(day.get("games", []))
    return games


def is_final_game(game: dict[str, Any]) -> bool:
    status = game.get("status", {})
    abstract_state = status.get("abstractGameState", "")
    detailed_state = status.get("detailedState", "")
    return abstract_state == "Final" or detailed_state in {"Final", "Completed Early"}


def team_context(game: dict[str, Any], side: str, sport_id: int) -> dict[str, Any]:
    team = game["teams"][side]["team"]
    league = team.get("league", {})
    league_name = league.get("name") or SPORT_LEVELS.get(sport_id)
    return {
        "team_id": team.get("id"),
        "team_name": team.get("name") or team.get("teamName"),
        "team_abbreviation": team.get("abbreviation") or team.get("fileCode"),
        "league_id": league.get("id"),
        "league_name": league_name,
        "aLevel": display_level(sport_id, league_name),
    }


def display_level(sport_id: int, league_name: str | None) -> str:
    if sport_id != 16 or not league_name:
        return SPORT_LEVELS.get(sport_id, str(sport_id))

    normalized = league_name.lower()
    if "dominican summer" in normalized:
        return "DSL"
    if "arizona complex" in normalized:
        return "ACL"
    if "florida complex" in normalized:
        return "FCL"
    return "R"


def boxscore_for_game(
    game_pk: int,
    cache_dir: Path,
    delay: float,
    force_refresh: bool,
    request_timeout: float,
    retries: int,
) -> dict[str, Any]:
    url = f"{LIVE_URL}/game/{game_pk}/feed/live"
    cache_path = cache_dir / "games" / f"{game_pk}.json"
    return request_json(url, cache_path, delay, force_refresh, request_timeout, retries)


def int_stat(stats: dict[str, Any], key: str) -> int:
    value = stats.get(key, 0)
    if value in ("", None, "-.--"):
        return 0
    return int(float(value))


def parse_ip_to_outs(value: Any) -> int:
    if value in ("", None, "-.--"):
        return 0
    whole, _, frac = str(value).partition(".")
    return int(whole or 0) * 3 + int(frac or 0)


def outs_to_ip(outs: int) -> str:
    return f"{outs // 3}.{outs % 3}"


def outs_to_innings(outs: int) -> float:
    return outs / 3 if outs else 0.0


def player_age(person: dict[str, Any], game_date: date) -> float | None:
    birth = person.get("birthDate")
    if not birth:
        return None
    try:
        born = datetime.strptime(birth, "%Y-%m-%d").date()
    except ValueError:
        return None
    return round((game_date - born).days / 365.25, 1)


def extract_game_logs(
    game: dict[str, Any],
    live_data: dict[str, Any],
    sport_id: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    game_pk = game["gamePk"]
    game_date = datetime.fromisoformat(game["gameDate"].replace("Z", "+00:00")).date()
    boxscore = live_data.get("liveData", {}).get("boxscore", {})
    teams = boxscore.get("teams", {})

    hitter_rows: list[dict[str, Any]] = []
    pitcher_rows: list[dict[str, Any]] = []

    for side in ("away", "home"):
        context = team_context(game, side, sport_id)
        opponent_context = team_context(game, "home" if side == "away" else "away", sport_id)
        team_box = teams.get(side, {})
        for player_blob in team_box.get("players", {}).values():
            person = player_blob.get("person", {})
            person_id = person.get("id")
            if not person_id:
                continue

            common = {
                "game_pk": game_pk,
                "game_date": game_date,
                "player_id": person_id,
                "player_name": person.get("fullName"),
                "Age": player_age(person, game_date),
                "TeamName": context["team_name"],
                "Team": context["team_abbreviation"] or context["team_name"],
                "Opp": opponent_context["team_abbreviation"] or opponent_context["team_name"],
                "aLevel": context["aLevel"],
                "league_id": context["league_id"] or sport_id,
                "league_name": context["league_name"],
            }

            batting = player_blob.get("stats", {}).get("batting", {})
            if batting and int_stat(batting, "plateAppearances") > 0:
                h = int_stat(batting, "hits")
                doubles = int_stat(batting, "doubles")
                triples = int_stat(batting, "triples")
                hr = int_stat(batting, "homeRuns")
                hitter_rows.append(
                    {
                        **common,
                        "G": int_stat(batting, "gamesPlayed") or 1,
                        "AB": int_stat(batting, "atBats"),
                        "PA": int_stat(batting, "plateAppearances"),
                        "H": h,
                        "1B": max(h - doubles - triples - hr, 0),
                        "2B": doubles,
                        "3B": triples,
                        "HR": hr,
                        "R": int_stat(batting, "runs"),
                        "RBI": int_stat(batting, "rbi"),
                        "BB": int_stat(batting, "baseOnBalls"),
                        "IBB": int_stat(batting, "intentionalWalks"),
                        "SO": int_stat(batting, "strikeOuts"),
                        "HBP": int_stat(batting, "hitByPitch"),
                        "SF": int_stat(batting, "sacFlies"),
                        "SH": int_stat(batting, "sacBunts"),
                        "GDP": int_stat(batting, "groundIntoDoublePlay"),
                        "SB": int_stat(batting, "stolenBases"),
                        "CS": int_stat(batting, "caughtStealing"),
                    }
                )

            pitching = player_blob.get("stats", {}).get("pitching", {})
            if pitching and parse_ip_to_outs(pitching.get("inningsPitched")) > 0:
                pitcher_rows.append(
                    {
                        **common,
                        "GS": int_stat(pitching, "gamesStarted"),
                        "W": int_stat(pitching, "wins"),
                        "L": int_stat(pitching, "losses"),
                        "CG": int_stat(pitching, "completeGames"),
                        "ShO": int_stat(pitching, "shutouts"),
                        "SV": int_stat(pitching, "saves"),
                        "outs": parse_ip_to_outs(pitching.get("inningsPitched")),
                        "TBF": int_stat(pitching, "battersFaced"),
                        "H": int_stat(pitching, "hits"),
                        "R": int_stat(pitching, "runs"),
                        "ER": int_stat(pitching, "earnedRuns"),
                        "HR": int_stat(pitching, "homeRuns"),
                        "BB": int_stat(pitching, "baseOnBalls"),
                        "IBB": int_stat(pitching, "intentionalWalks"),
                        "HBP": int_stat(pitching, "hitByPitch"),
                        "WP": int_stat(pitching, "wildPitches"),
                        "BK": int_stat(pitching, "balks"),
                        "SO": int_stat(pitching, "strikeOuts"),
                    }
                )

    return hitter_rows, pitcher_rows


def safe_div(numerator: float, denominator: float) -> float | None:
    if not denominator:
        return None
    return numerator / denominator


def fmt_decimal(value: float | None, places: int = 3) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{value:.{places}f}".replace("0.", ".")


def fmt_percent(value: float | None, places: int = 1) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{value * 100:.{places}f}%"


def current_constants(season: int) -> dict[str, float]:
    return WOBA_CONSTANTS.get(season) or WOBA_CONSTANTS[max(WOBA_CONSTANTS)]


def add_hitter_rates(df: pd.DataFrame, season: int) -> pd.DataFrame:
    constants = current_constants(season)
    df = df.copy()
    df["woba_num"] = (
        constants["wBB"] * (df["BB"] - df["IBB"])
        + constants["wHBP"] * df["HBP"]
        + constants["w1B"] * df["1B"]
        + constants["w2B"] * df["2B"]
        + constants["w3B"] * df["3B"]
        + constants["wHR"] * df["HR"]
    )
    df["woba_den"] = df["AB"] + df["BB"] - df["IBB"] + df["SF"] + df["HBP"]
    df["wOBA_raw"] = df.apply(lambda row: safe_div(row["woba_num"], row["woba_den"]), axis=1)
    return df


def aggregate_with_first(df: pd.DataFrame, group_cols: list[str], sum_cols: list[str]) -> pd.DataFrame:
    first_cols = [
        col
        for col in ["player_name", "Age", "TeamName", "Team", "aLevel", "league_id", "league_name"]
        if col in df.columns and col not in group_cols
    ]
    agg: dict[str, str] = {col: "sum" for col in sum_cols}
    agg.update({col: "last" for col in first_cols})
    if "game_date" in df.columns:
        df = df.sort_values("game_date")
    return df.groupby(group_cols, as_index=False).agg(agg)


def rolling_hitters(game_logs: pd.DataFrame, end_date: date, windows: tuple[int, ...], season: int) -> pd.DataFrame:
    if game_logs.empty:
        return pd.DataFrame()

    numeric_cols = [
        "G",
        "AB",
        "PA",
        "H",
        "1B",
        "2B",
        "3B",
        "HR",
        "R",
        "RBI",
        "BB",
        "IBB",
        "SO",
        "HBP",
        "SF",
        "SH",
        "GDP",
        "SB",
        "CS",
    ]
    rows = []
    constants = current_constants(season)

    for window in windows:
        start = end_date - timedelta(days=window)
        frame = game_logs[(game_logs["game_date"] >= start) & (game_logs["game_date"] <= end_date)]
        if frame.empty:
            continue

        frame = add_hitter_rates(frame, season)
        league = frame.groupby(["league_id"], as_index=False).agg(
            {
                "woba_num": "sum",
                "woba_den": "sum",
                "R": "sum",
                "PA": "sum",
            }
        )
        league["league_woba"] = league.apply(lambda row: safe_div(row["woba_num"], row["woba_den"]), axis=1)
        league["league_r_pa"] = league.apply(lambda row: safe_div(row["R"], row["PA"]), axis=1)

        by_player_league = aggregate_with_first(
            frame,
            ["player_id", "league_id"],
            numeric_cols + ["woba_num", "woba_den"],
        ).merge(league[["league_id", "league_woba", "league_r_pa"]], on="league_id", how="left")

        by_player_league["segment_woba"] = by_player_league.apply(
            lambda row: safe_div(row["woba_num"], row["woba_den"]), axis=1
        )
        by_player_league["segment_wraa"] = by_player_league.apply(
            lambda row: (
                ((row["segment_woba"] - row["league_woba"]) / constants["scale"]) * row["PA"]
                if row["segment_woba"] is not None and row["league_woba"] is not None
                else 0
            ),
            axis=1,
        )
        by_player_league["weighted_lg_r_pa"] = by_player_league["league_r_pa"] * by_player_league["PA"]

        player = aggregate_with_first(
            by_player_league,
            ["player_id"],
            numeric_cols + ["woba_num", "woba_den", "segment_wraa", "weighted_lg_r_pa"],
        )
        player["timeframe"] = f"last_{window}"
        player["Date"] = "Total"
        player["Opp"] = "- - -"
        player["BO"] = ""
        player["Pos"] = ""
        player["AVG"] = player.apply(lambda r: fmt_decimal(safe_div(r["H"], r["AB"])), axis=1)
        player["BB%"] = player.apply(lambda r: fmt_percent(safe_div(r["BB"], r["PA"])), axis=1)
        player["K%"] = player.apply(lambda r: fmt_percent(safe_div(r["SO"], r["PA"])), axis=1)
        player["BB/K"] = player.apply(lambda r: fmt_decimal(safe_div(r["BB"], r["SO"])), axis=1)
        player["OBP"] = player.apply(
            lambda r: fmt_decimal(safe_div(r["H"] + r["BB"] + r["HBP"], r["AB"] + r["BB"] + r["HBP"] + r["SF"])),
            axis=1,
        )
        player["SLG"] = player.apply(
            lambda r: fmt_decimal(safe_div(r["1B"] + 2 * r["2B"] + 3 * r["3B"] + 4 * r["HR"], r["AB"])),
            axis=1,
        )
        player["OPS"] = player.apply(
            lambda r: fmt_decimal(
                (safe_div(r["H"] + r["BB"] + r["HBP"], r["AB"] + r["BB"] + r["HBP"] + r["SF"]) or 0)
                + (safe_div(r["1B"] + 2 * r["2B"] + 3 * r["3B"] + 4 * r["HR"], r["AB"]) or 0)
            ),
            axis=1,
        )
        player["ISO"] = player.apply(
            lambda r: fmt_decimal(
                (safe_div(r["1B"] + 2 * r["2B"] + 3 * r["3B"] + 4 * r["HR"], r["AB"]) or 0)
                - (safe_div(r["H"], r["AB"]) or 0)
            ),
            axis=1,
        )
        player["Spd"] = ""
        player["BABIP"] = player.apply(
            lambda r: fmt_decimal(safe_div(r["H"] - r["HR"], r["AB"] - r["SO"] - r["HR"] + r["SF"])),
            axis=1,
        )
        player["wSB"] = ""
        player["wRAA"] = player["segment_wraa"].round(1)
        player["wOBA"] = player.apply(lambda r: fmt_decimal(safe_div(r["woba_num"], r["woba_den"])), axis=1)
        player["wRC"] = player.apply(
            lambda r: round(((r["segment_wraa"] / r["PA"]) + safe_div(r["weighted_lg_r_pa"], r["PA"])) * r["PA"], 1)
            if r["PA"]
            else "",
            axis=1,
        )
        player["wRC+"] = player.apply(
            lambda r: round(
                (((r["segment_wraa"] / r["PA"]) + safe_div(r["weighted_lg_r_pa"], r["PA"]))
                 / safe_div(r["weighted_lg_r_pa"], r["PA"]))
                * 100
            )
            if r["PA"] and safe_div(r["weighted_lg_r_pa"], r["PA"])
            else "",
            axis=1,
        )
        rows.append(player)

    result = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return result[
        [
            "player_name",
            "player_id",
            "timeframe",
            "aLevel",
            "Age",
            "TeamName",
            "Date",
            "Team",
            "Opp",
            "BO",
            "Pos",
            "G",
            "AB",
            "PA",
            "H",
            "1B",
            "2B",
            "3B",
            "HR",
            "R",
            "RBI",
            "BB",
            "IBB",
            "SO",
            "HBP",
            "SF",
            "SH",
            "GDP",
            "SB",
            "CS",
            "AVG",
            "BB%",
            "K%",
            "BB/K",
            "OBP",
            "SLG",
            "OPS",
            "ISO",
            "Spd",
            "BABIP",
            "wSB",
            "wRC",
            "wRAA",
            "wOBA",
            "wRC+",
        ]
    ]


def rolling_pitchers(game_logs: pd.DataFrame, end_date: date, windows: tuple[int, ...]) -> pd.DataFrame:
    if game_logs.empty:
        return pd.DataFrame()

    numeric_cols = [
        "GS",
        "W",
        "L",
        "CG",
        "ShO",
        "SV",
        "outs",
        "TBF",
        "H",
        "R",
        "ER",
        "HR",
        "BB",
        "IBB",
        "HBP",
        "WP",
        "BK",
        "SO",
    ]
    rows = []

    for window in windows:
        start = end_date - timedelta(days=window)
        frame = game_logs[(game_logs["game_date"] >= start) & (game_logs["game_date"] <= end_date)]
        if frame.empty:
            continue

        league = frame.groupby(["league_id"], as_index=False).agg(
            {"ER": "sum", "HR": "sum", "BB": "sum", "HBP": "sum", "SO": "sum", "outs": "sum"}
        )
        league["league_era"] = league.apply(
            lambda r: safe_div(r["ER"] * 27, r["outs"]),
            axis=1,
        )
        league["league_raw_fip"] = league.apply(
            lambda r: safe_div(13 * r["HR"] + 3 * (r["BB"] + r["HBP"]) - 2 * r["SO"], outs_to_innings(r["outs"])),
            axis=1,
        )
        league["fip_constant"] = league["league_era"] - league["league_raw_fip"]

        by_player_league = aggregate_with_first(frame, ["player_id", "league_id"], numeric_cols)
        by_player_league = by_player_league.merge(
            league[["league_id", "fip_constant"]], on="league_id", how="left"
        )
        by_player_league["weighted_fip_constant"] = (
            by_player_league["fip_constant"] * by_player_league["outs"]
        )

        player = aggregate_with_first(
            by_player_league,
            ["player_id"],
            numeric_cols + ["weighted_fip_constant"],
        )
        player["timeframe"] = f"last_{window}"
        player["Date"] = "Total"
        player["Opp"] = "- - -"
        player["IP"] = player["outs"].apply(outs_to_ip)
        player["ERA"] = player.apply(lambda r: fmt_decimal(safe_div(r["ER"] * 27, r["outs"]), 2), axis=1)
        player["WHIP"] = player.apply(
            lambda r: fmt_decimal(safe_div(r["BB"] + r["H"], outs_to_innings(r["outs"])), 2),
            axis=1,
        )
        player["K/9"] = player.apply(lambda r: fmt_decimal(safe_div(r["SO"] * 27, r["outs"]), 2), axis=1)
        player["BB/9"] = player.apply(lambda r: fmt_decimal(safe_div(r["BB"] * 27, r["outs"]), 2), axis=1)
        player["K/BB"] = player.apply(lambda r: fmt_decimal(safe_div(r["SO"], r["BB"]), 2), axis=1)
        player["HR/9"] = player.apply(lambda r: fmt_decimal(safe_div(r["HR"] * 27, r["outs"]), 2), axis=1)
        player["K%"] = player.apply(lambda r: fmt_percent(safe_div(r["SO"], r["TBF"])), axis=1)
        player["BB%"] = player.apply(lambda r: fmt_percent(safe_div(r["BB"], r["TBF"])), axis=1)
        player["K-BB%"] = player.apply(lambda r: fmt_percent(safe_div(r["SO"] - r["BB"], r["TBF"])), axis=1)
        player["AVG"] = player.apply(lambda r: fmt_decimal(safe_div(r["H"], max(r["TBF"] - r["BB"] - r["HBP"], 0))), axis=1)
        player["BABIP"] = ""
        player["LOB%"] = ""
        player["FIP"] = player.apply(
            lambda r: fmt_decimal(
                safe_div(13 * r["HR"] + 3 * (r["BB"] + r["HBP"]) - 2 * r["SO"], outs_to_innings(r["outs"]))
                + safe_div(r["weighted_fip_constant"], r["outs"]),
                2,
            )
            if r["outs"] and pd.notna(r["weighted_fip_constant"])
            else "",
            axis=1,
        )
        rows.append(player)

    result = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return result[
        [
            "player_name",
            "player_id",
            "timeframe",
            "aLevel",
            "Age",
            "TeamName",
            "Date",
            "Team",
            "Opp",
            "GS",
            "W",
            "L",
            "ERA",
            "CG",
            "ShO",
            "SV",
            "IP",
            "TBF",
            "H",
            "R",
            "ER",
            "HR",
            "BB",
            "IBB",
            "HBP",
            "WP",
            "BK",
            "SO",
            "K/9",
            "BB/9",
            "K/BB",
            "HR/9",
            "K%",
            "BB%",
            "K-BB%",
            "AVG",
            "WHIP",
            "BABIP",
            "LOB%",
            "FIP",
        ]
    ]


def main() -> None:
    args = parse_args()
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    start_date = end_date - timedelta(days=args.max_window)
    cache_dir = resolve_project_path(args.cache_dir)
    sport_ids = tuple(int(value.strip()) for value in args.sport_ids.split(",") if value.strip())

    hitter_rows: list[dict[str, Any]] = []
    pitcher_rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []
    seen_games: set[int] = set()

    print(
        f"Fetching MiLB games from {start_date} through {end_date} for sport IDs {sport_ids}",
        flush=True,
    )

    stop_requested = False
    for sport_id in sport_ids:
        try:
            games = get_schedule(
                sport_id,
                start_date,
                end_date,
                cache_dir,
                args.delay,
                args.force_refresh,
                args.request_timeout,
                args.retries,
            )
        except Exception as exc:
            print(f"Skipping sportId {sport_id}: schedule fetch failed: {exc}", flush=True)
            error_rows.append({"scope": "schedule", "sport_id": sport_id, "game_pk": "", "error": str(exc)})
            continue

        final_games = [
            game
            for game in games
            if game.get("gamePk") and game.get("gamePk") not in seen_games and is_final_game(game)
        ]
        print(f"sportId {sport_id}: {len(final_games)} completed games to process", flush=True)

        for index, game in enumerate(final_games, start=1):
            game_pk = game.get("gamePk")
            if not game_pk or game_pk in seen_games:
                continue
            seen_games.add(game_pk)

            away = game.get("teams", {}).get("away", {}).get("team", {}).get("name", "Away")
            home = game.get("teams", {}).get("home", {}).get("team", {}).get("name", "Home")
            print(
                f"  [{index}/{len(final_games)}] gamePk {game_pk}: {away} at {home}",
                flush=True,
            )

            try:
                live_data = boxscore_for_game(
                    game_pk,
                    cache_dir,
                    args.delay,
                    args.force_refresh,
                    args.request_timeout,
                    args.retries,
                )
                hitters, pitchers = extract_game_logs(game, live_data, sport_id)
            except Exception as exc:
                print(f"    skipped gamePk {game_pk}: {exc}", flush=True)
                error_rows.append(
                    {"scope": "game", "sport_id": sport_id, "game_pk": game_pk, "error": str(exc)}
                )
                continue

            hitter_rows.extend(hitters)
            pitcher_rows.extend(pitchers)

            if args.limit_games and len(seen_games) >= args.limit_games:
                print(f"Reached --limit-games {args.limit_games}; stopping early.", flush=True)
                stop_requested = True
                break

        if stop_requested:
            break

    hitters_df = pd.DataFrame(hitter_rows)
    pitchers_df = pd.DataFrame(pitcher_rows)

    output_hitters = rolling_hitters(hitters_df, end_date, DEFAULT_WINDOWS, args.season)
    output_pitchers = rolling_pitchers(pitchers_df, end_date, DEFAULT_WINDOWS)

    hitters_dir = PROJECT_ROOT / "data" / "hitters"
    pitchers_dir = PROJECT_ROOT / "data" / "pitchers"
    hitters_dir.mkdir(parents=True, exist_ok=True)
    pitchers_dir.mkdir(parents=True, exist_ok=True)

    if not output_hitters.empty:
        output_hitters.to_csv(hitters_dir / "leaderboard_data.csv", index=False)
        hitters_df.to_csv(hitters_dir / "player_game_logs.csv", index=False)
    if not output_pitchers.empty:
        output_pitchers.to_csv(pitchers_dir / "leaderboard_pitch_data.csv", index=False)
        pitchers_df.to_csv(pitchers_dir / "player_pitching_game_logs.csv", index=False)
    if error_rows:
        pd.DataFrame(error_rows).to_csv(PROJECT_ROOT / "data" / "mlb_stats_api_errors.csv", index=False)

    print(f"Games processed: {len(seen_games)}")
    print(f"Fetch/parse errors: {len(error_rows)}")
    print(f"Hitter game rows: {len(hitters_df)}")
    print(f"Pitcher game rows: {len(pitchers_df)}")
    print(f"Hitter leaderboard rows: {len(output_hitters)}")
    print(f"Pitcher leaderboard rows: {len(output_pitchers)}")


if __name__ == "__main__":
    main()
