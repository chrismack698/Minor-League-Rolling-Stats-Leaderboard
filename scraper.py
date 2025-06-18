import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Dates
today = datetime.today().date()
date_ranges = {
    "last_45": (today - timedelta(days=45)).strftime("%Y-%m-%d"),
    "last_30": (today - timedelta(days=30)).strftime("%Y-%m-%d"),
    "last_15": (today - timedelta(days=15)).strftime("%Y-%m-%d"),
    "last_7":  (today - timedelta(days=7)).strftime("%Y-%m-%d"),
}
today_str = today.strftime("%Y-%m-%d")

# Normalize player name for Fangraphs URL
def normalize_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\s\-\.]", "", name)
    cleaned = cleaned.replace(".", "")
    cleaned = re.sub(r"\s+", " ", cleaned.strip())
    return cleaned.lower().replace(" ", "-")

# Scrape function
def get_total_row(player_name, player_id, start_date, end_date, timeframe, meta):
    try:
        url_name = normalize_name(player_name)
        url = (
            f"https://www.fangraphs.com/players/{url_name}/{player_id}/"
            f"game-log?position=OF&gds={start_date}&gde={end_date}&type=-2"
        )

        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        for tr in soup.find_all('tr'):
            date_cell = tr.find('td', {'data-stat': 'Date'})
            if date_cell and date_cell.get_text(strip=True) == 'Total':
                result = {
                    td['data-stat']: td.get_text(strip=True)
                    for td in tr.find_all('td')
                    if td.get('data-stat') and td['data-stat'] != 'divider'
                }
                # Add identity and metadata
                result.update({
                    "player_name": player_name,
                    "player_id": player_id,
                    "timeframe": timeframe,
                    "aLevel": meta.get("aLevel"),
                    "Age": meta.get("Age"),
                    "TeamName": meta.get("TeamName"),
                })
                return result
        raise ValueError("Total row not found")
    except Exception as e:
        return {
            "player_name": player_name,
            "player_id": player_id,
            "timeframe": timeframe,
            "error": str(e)
        }

# Pull raw data from Fangraphs API
var = [1, 2, 3, 4, 7, 8]
dfs_hit = []

for i in var:
    hit_url = (
        f'https://www.fangraphs.com/api/leaders/minor-league/data?pos=all'
        f'&level={i}&lg=2,4,5,6,7,8,9,10,11,14,12,13,15,16,17,18,30,32,33'
        f'&stats=bat&qual=10&type=0&team=&season=2025&seasonEnd=2025'
    )
    r = requests.get(hit_url, headers={'User-Agent': 'Mozilla/5.0'})
    json_data = json.loads(r.text)
    df = pd.DataFrame(json_data)
    dfs_hit.append(df)

minor_league_hit_df = pd.concat(dfs_hit).drop_duplicates()

# Prepare metadata lookup for each player
# metadata = minor_league_hit_df.set_index('minormasterid')[['aLevel', 'Age', 'TeamName']].to_dict('index')
# Clean metadata for player ID lookup
metadata = (
    minor_league_hit_df[['minormasterid', 'aLevel', 'Age', 'TeamName']]
    .drop_duplicates(subset='minormasterid')
    .set_index('minormasterid')
    .to_dict('index')
)
records = minor_league_hit_df[['PlayerName', 'minormasterid']].dropna().to_dict('records')

# Build list of all player-timeframe combinations
tasks = []
for record in records:
    for label, start_date in date_ranges.items():
        tasks.append({
            'PlayerName': record['PlayerName'],
            'minormasterid': record['minormasterid'],
            'start_date': start_date,
            'end_date': today_str,
            'timeframe': label,
            'meta': metadata.get(record['minormasterid'], {})
        })

# Threaded scraping
summary_rows = []
error_log = []

def worker(task):
    return get_total_row(
        player_name=task['PlayerName'],
        player_id=task['minormasterid'],
        start_date=task['start_date'],
        end_date=task['end_date'],
        timeframe=task['timeframe'],
        meta=task['meta']
    )

with ThreadPoolExecutor(max_workers=15) as executor:
    futures = [executor.submit(worker, task) for task in tasks]
    for future in as_completed(futures):
        result = future.result()
        if 'error' in result:
            error_log.append(result)
        else:
            summary_rows.append(result)

# Output
df_summary = pd.DataFrame(summary_rows)
df_errors = pd.DataFrame(error_log)

df_summary.to_csv("leaderboard_data.csv", index=False)
df_errors.to_csv("errors.csv", index=False)
