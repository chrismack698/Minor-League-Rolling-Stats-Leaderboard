import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

# === Load All Data ===
@st.cache_data(ttl=3600)
def load_all_data():
    return {
        "hitters_splits": pd.read_csv("https://raw.githubusercontent.com/chrismack698/Minor-League-Rolling-Stats-Leaderboard/main/data/hitters/leaderboard_data.csv"),
        "pitchers_splits": pd.read_csv("https://raw.githubusercontent.com/chrismack698/Minor-League-Rolling-Stats-Leaderboard/main/data/pitchers/leaderboard_pitch_data.csv"),
        "hitters_full": pd.read_csv("https://raw.githubusercontent.com/chrismack698/Minor-League-Rolling-Stats-Leaderboard/main/data/hitters/full_season_data.csv"),
        "pitchers_full": pd.read_csv("https://raw.githubusercontent.com/chrismack698/Minor-League-Rolling-Stats-Leaderboard/main/data/pitchers/full_season_pitch_data.csv")
    }

data = load_all_data()

# === Tip Jar ===
st.sidebar.markdown("---")
st.sidebar.markdown("💸 **Enjoying this app?** [Send a tip](https://coff.ee/christianmack)")

# === Tabs ===
tab1, tab2, tab3, tab4 = st.tabs([
    "🧢 Hitter Splits Leaderboard",
    "⚾ Pitcher Splits Leaderboard",
    "🧢 Full Season Hitting Leaderboard",
    "⚾ Full Season Pitching Leaderboard"
])

# === Common Utilities ===
def clean_percent(series):
    return pd.to_numeric(series.str.replace('%', '', regex=False), errors='coerce')

def filter_common(df, level_col, age_col, name_col):
    levels = sorted(df[level_col].dropna().unique())
    selected_levels = st.sidebar.multiselect("Level", levels, default=levels, key=level_col)
    min_age = int(df[age_col].min())
    max_age = int(df[age_col].max())
    age_range = st.sidebar.slider("Age", min_age, max_age, (min_age, max_age))
    name_query = st.sidebar.text_input("Search by Player Name").strip().lower()

    df = df[
        (df[level_col].isin(selected_levels)) &
        (df[age_col] >= age_range[0]) & (df[age_col] <= age_range[1]) &
        (df[name_col].str.lower().str.contains(name_query) if name_query else True)
    ]
    return df

# === Hitter Splits Tab ===
with tab1:
    df = data["hitters_splits"]
    st.sidebar.header("⚾ Full Season Pitchers Filters")
    df['K%'] = clean_percent(df['K%'])
    df['BB%'] = clean_percent(df['BB%'])
    df['K-BB%'] = clean_percent(df['K-BB%'])
    df['IP'] = pd.to_numeric(df['IP'], errors='coerce')
    df = filter_common(df, 'aLevel', 'Age', 'player_name')
    columns = ["player_name", "TeamName", "aLevel", "Age", "GS", "IP", "W", "L", "SO", "ERA", "WHIP", "FIP", "K/9", "K%", "BB%", "K-BB%", "BABIP", "LOB%"]
    st.dataframe(df[columns].sort_values("K-BB%", ascending=False).reset_index(drop=True), use_container_width=True)
