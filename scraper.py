import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# === 1. Set up date ranges ===
today = datetime.today().date()
date_ranges = {
    "last_45": (today - timedelta(days=45)).strftime("%Y-%m-%d"),
    "last_30": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
    "last_15": (today - timedelta(days=15)).strftime("%Y-%m-%d"),
    "last_7":  (today - timedelta(days=7)).strftime("%Y-%m-%d"),
}
today_str = today.strftime("%Y-%m-%d")

# === 2. Normalize player names for URL ===
def normalize_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\s\-\.]", "", name)
    cleaned = cleaned.replace(".", "")
    cleaned = re.sub(r"\s+", " ", cleaned.strip())
    return cleaned.lower().replace(" ", "-")

# === 3. Get advanced stat row (type=-2) ===
def get_advanced_row(player_name, player_id, start_date, end_date):
    try:
        url_name = normalize_name(player_name)
        url = (
            f"https://www.fangraphs.com/players/{url_name}/{player_id}/"
            f"game-log?position=OF&gds={start_date}&gde={end_date}&type=-2"
        )
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6321.91 Safari/537.36 Edg/124.0.2478.51'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        for tr in soup.find_all('tr'):
            date_cell = tr.find('td', {'data-stat': 'Date'})
            if date_cell and date_cell.get_text(strip=True) == 'Total':
                return {
                    td['data-stat']: td.get_text(strip=True)
                    for td in tr.find_all('td')
                    if td.get('data-stat') and td['data-stat'] != 'divider'
                }
        raise ValueError("Total row not found (advanced)")
    except Exception as e:
        return {"adv_error": str(e)}

# === 4. Get standard stat row (type=-1) ===
def get_standard_row(player_name, player_id, start_date, end_date):
    try:
        url_name = normalize_name(player_name)
        url = (
            f"https://www.fangraphs.com/players/{url_name}/{player_id}/"
            f"game-log?position=OF&gds={start_date}&gde={end_date}&type=-1"
        )
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        for tr in soup.find_all('tr'):
            date_cell = tr.find('td', {'data-stat': 'Date'})
            if date_cell and date_cell.get_text(strip=True) == 'Total':
                return {
                    f"{td['data-stat']}": td.get_text(strip=True)
                    for td in tr.find_all('td')
                    if td.get('data-stat') and td['data-stat'] != 'divider'
                }
        raise ValueError("Total row not found (standard)")
    except Exception as e:
        return {"std_error": str(e)}

# === 5. Worker to combine rows ===
def worker(task):
    advanced = get_advanced_row(
        player_name=task['PlayerName'],
        player_id=task['minormasterid'],
        start_date=task['start_date'],
        end_date=task['end_date']
    )

    standard = get_standard_row(
        player_name=task['PlayerName'],
        player_id=task['minormasterid'],
        start_date=task['start_date'],
        end_date=task['end_date']
    )

    # If either failed, return error row
    if 'adv_error' in advanced or 'std_error' in standard:
        return {
            "player_name": task['PlayerName'],
            "player_id": task['minormasterid'],
            "timeframe": task['timeframe'],
            "aLevel": task['meta'].get("aLevel"),
            "Age": task['meta'].get("Age"),
            "TeamName": task['meta'].get("TeamName"),
            "error": advanced.get("adv_error", "") + " | " + standard.get("std_error", "")
        }

    # Order: metadata → standard → advanced
    return {
        "player_name": task['PlayerName'],
        "player_id": task['minormasterid'],
        "timeframe": task['timeframe'],
        "aLevel": task['meta'].get("aLevel"),
        "Age": task['meta'].get("Age"),
        "TeamName": task['meta'].get("TeamName"),
        **standard,
        **advanced
    }

# === 6. Pull data from Fangraphs API ===
levels = [1, 2, 3, 4, 7, 8]
dfs_hit = []

for lvl in levels:
    hit_url = (
        f'https://www.fangraphs.com/api/leaders/minor-league/data?pos=all'
        f'&level={lvl}&lg=2,4,5,6,7,8,9,10,11,14,12,13,15,16,17,18,30,32,33'
        f'&stats=bat&qual=10&type=0&team=&season=2025&seasonEnd=2025'
    )
    r = requests.get(hit_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    df = pd.DataFrame(json.loads(r.text))
    dfs_hit.append(df)

minor_league_hit_df = pd.concat(dfs_hit).drop_duplicates()

# === 7. Build metadata and tasks ===
metadata = (
    minor_league_hit_df[['minormasterid', 'aLevel', 'Age', 'TeamName']]
    .drop_duplicates(subset='minormasterid')
    .set_index('minormasterid')
    .to_dict('index')
)

records = minor_league_hit_df[['PlayerName', 'minormasterid']].dropna().to_dict('records')

tasks = []
for rec in records:
    for label, start_date in date_ranges.items():
        tasks.append({
            'PlayerName': rec['PlayerName'],
            'minormasterid': rec['minormasterid'],
            'start_date': start_date,
            'end_date': today_str,
            'timeframe': label,
            'meta': metadata.get(rec['minormasterid'], {})
        })

# === 8. Run threaded scraping ===
summary_rows = []
error_log = []

with ThreadPoolExecutor(max_workers=15) as executor:
    futures = [executor.submit(worker, task) for task in tasks]
    for future in as_completed(futures):
        result = future.result()
        if 'error' in result:
            error_log.append(result)
        else:
            summary_rows.append(result)

# === 9. Save or display output ===
df_summary = pd.DataFrame(summary_rows)
df_summary = df_summary.drop_duplicates(subset=['player_id', 'timeframe'])
df_errors = pd.DataFrame(error_log)

df_summary.to_csv("leaderboard_data.csv", index=False)
minor_league_hit_df.to_csv("full_season_data.csv", index=False)
df_errors.to_csv("scrape_errors.csv", index=False)

