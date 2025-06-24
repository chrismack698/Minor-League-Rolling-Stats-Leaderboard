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

def filter_common(df, level_col, age_col, name_col, key_suffix):
    levels = sorted(df[level_col].dropna().unique())
    selected_levels = st.sidebar.multiselect("Level", levels, default=levels, key=f"level_{key_suffix}")
    min_age = int(df[age_col].min())
    max_age = int(df[age_col].max())
    age_range = st.sidebar.slider("Age", min_age, max_age, (min_age, max_age), key=f"age_{key_suffix}")
    name_query = st.sidebar.text_input("Search by Player Name", key=f"name_{key_suffix}").strip().lower()

    df = df[
        (df[level_col].isin(selected_levels)) &
        (df[age_col] >= age_range[0]) & (df[age_col] <= age_range[1]) &
        (df[name_col].str.lower().str.contains(name_query) if name_query else True)
    ]
    return df

# === Hitter Splits Tab ===
with tab1:
    df = data["hitters_splits"]
    st.sidebar.header("🧢 Hitter Splits Filters")

    # Timeframe
    timeframes = df['timeframe'].unique().tolist()
    selected_timeframe = st.sidebar.selectbox("Timeframe", sorted(timeframes, key=lambda x: int(x.split('_')[1])))
    df = df[df['timeframe'] == selected_timeframe]

    # Filters
    df = filter_common(df, 'aLevel', 'Age', 'player_name', key_suffix='tab1')
    df['PA'] = pd.to_numeric(df['PA'], errors='coerce')
    df['K%'] = clean_percent(df['K%'])
    df['BB%'] = clean_percent(df['BB%'])
    df['HR'] = pd.to_numeric(df['HR'], errors='coerce')

    pa_min, pa_max = int(df['PA'].min()), int(df['PA'].max())
    pa_range = st.sidebar.slider("Plate Appearances (PA)", pa_min, pa_max, (pa_min, pa_max))
    k_range = st.sidebar.slider("K%", 0.0, 100.0, (0.0, 100.0), key="k_tab2")
    bb_range = st.sidebar.slider("BB%", 0.0, 100.0, (0.0, 100.0), key="bb_tab2")

    df = df[
        (df['PA'] >= pa_range[0]) & (df['PA'] <= pa_range[1]) &
        (df['K%'] >= k_range[0]) & (df['K%'] <= k_range[1]) &
        (df['BB%'] >= bb_range[0]) & (df['BB%'] <= bb_range[1])
    ]

    columns = ["player_name", "TeamName", "aLevel", "Age", "AB", "PA", "2B", "3B", "HR", "R", "RBI", "SB", "K%", "BB%", "AVG", "OBP", "SLG", "OPS", "ISO", "wRC+", "wOBA", "BABIP"]
    st.dataframe(df[columns].sort_values("wRC+", ascending=False).reset_index(drop=True), use_container_width=True)

    fig = px.scatter(
        df.dropna(subset=["K%", "wRC+", "HR"]),
        x="K%", y="wRC+", size="HR", color="aLevel",
        hover_name="player_name", hover_data=["TeamName", "Age", "PA"],
        title="wRC+ vs. K% (Bubble Size = HR)", size_max=40, height=600
    )
    st.plotly_chart(fig, use_container_width=True)

# === Pitcher Splits Tab ===
with tab2:
    df = data["pitchers_splits"]
    st.sidebar.header("⚾ Pitcher Splits Filters")
    df['K%'] = clean_percent(df['K%'])
    df['BB%'] = clean_percent(df['BB%'])
    df['K-BB%'] = clean_percent(df.get('K-BB%', pd.Series()))
    df['IP'] = pd.to_numeric(df['IP'], errors='coerce')
    df = filter_common(df, 'aLevel', 'Age', 'player_name', key_suffix='tab2')

    ip_range = st.sidebar.slider("Innings Pitched (IP)", float(df['IP'].min()), float(df['IP'].max()), (float(df['IP'].min()), float(df['IP'].max())), key="ip_tab2")), float(df['IP'].max()), (float(df['IP'].min()), float(df['IP'].max())), key="ip_tab2")), float(df['IP'].max()), (float(df['IP'].min()), float(df['IP'].max())))
    k_range = st.sidebar.slider("K%", 0.0, 100.0, (0.0, 100.0), key="k_tab2")
    bb_range = st.sidebar.slider("BB%", 0.0, 100.0, (0.0, 100.0), key="bb_tab2")
    kbb_range = st.sidebar.slider("K-BB%", 0.0, 100.0, (0.0, 100.0), key="kbb_tab2")

    df = df[
        (df['IP'] >= ip_range[0]) & (df['IP'] <= ip_range[1]) &
        (df['K%'] >= k_range[0]) & (df['K%'] <= k_range[1]) &
        (df['BB%'] >= bb_range[0]) & (df['BB%'] <= bb_range[1]) &
        (df['K-BB%'] >= kbb_range[0]) & (df['K-BB%'] <= kbb_range[1])
    ]

    columns = ["player_name", "TeamName", "aLevel", "Age", "GS", "IP", "W", "L", "SO", "ERA", "WHIP", "FIP", "K/9", "K%", "BB%", "K-BB%", "BABIP", "LOB%"]
    st.dataframe(df[columns].sort_values("K-BB%", ascending=False).reset_index(drop=True), use_container_width=True)

# === Full Season Hitters Tab ===
with tab3:
    df = data["hitters_full"]
    st.sidebar.header("🧢 Full Season Hitters Filters")
    df = filter_common(df, 'aLevel', 'Age', 'player_name', key_suffix='tab3')
    df['wRC+'] = pd.to_numeric(df['wRC+'], errors='coerce')
    columns = ["player_name", "TeamName", "aLevel", "Age", "AB", "PA", "2B", "3B", "HR", "R", "RBI", "SB", "K%", "BB%", "AVG", "OBP", "SLG", "OPS", "ISO", "wRC+", "wOBA", "BABIP"]
    st.dataframe(df[columns].sort_values("wRC+", ascending=False).reset_index(drop=True), use_container_width=True)

# === Full Season Pitchers Tab ===
with tab4:
    df = data["pitchers_full"]
    st.sidebar.header("⚾ Full Season Pitchers Filters")
    df['K%'] = clean_percent(df['K%'])
    df['BB%'] = clean_percent(df['BB%'])
    df['K-BB%'] = clean_percent(df.get('K-BB%', pd.Series()))
    df['IP'] = pd.to_numeric(df['IP'], errors='coerce')
    df = filter_common(df, 'aLevel', 'Age', 'player_name', key_suffix='tab4')
    columns = ["player_name", "TeamName", "aLevel", "Age", "GS", "IP", "W", "L", "SO", "ERA", "WHIP", "FIP", "K/9", "K%", "BB%", "K-BB%", "BABIP", "LOB%"]
    st.dataframe(df[columns].sort_values("K-BB%", ascending=False).reset_index(drop=True), use_container_width=True)
