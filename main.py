import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

# === 1. Load Data Functions ===
@st.cache_data(ttl=3600)
def load_hitters_splits_data():
    url = "https://raw.githubusercontent.com/chrismack698/Minor-League-Rolling-Stats-Leaderboard/main/data/hitters/leaderboard_data.csv"
    return pd.read_csv(url)

@st.cache_data(ttl=3600)
def load_pitchers_splits_data():
    url = "https://raw.githubusercontent.com/chrismack698/Minor-League-Rolling-Stats-Leaderboard/main/data/pitchers/leaderboard_pitch_data.csv"
    return pd.read_csv(url)

@st.cache_data(ttl=3600)
def load_hitters_full_season_data():
    url = "https://raw.githubusercontent.com/chrismack698/Minor-League-Rolling-Stats-Leaderboard/main/data/hitters/full_season_data.csv"
    return pd.read_csv(url)

@st.cache_data(ttl=3600)
def load_pitchers_full_season_data():
    url = "https://raw.githubusercontent.com/chrismack698/Minor-League-Rolling-Stats-Leaderboard/main/data/pitchers/full_season_pitch_data.csv"
    return pd.read_csv(url)

# === 2. Data Cleaning Functions ===
def clean_percentage(series):
    # Check if the series contains string values with '%' symbols
    if series.dtype == 'object':
        return pd.to_numeric(series.str.replace('%', '', regex=False), errors='coerce')
    else:
        # Already numeric, just ensure it's numeric type
        return pd.to_numeric(series, errors='coerce')

def clean_hitters_data(df):
    df['K%'] = clean_percentage(df['K%'])
    df['BB%'] = clean_percentage(df['BB%'])
    df['PA'] = pd.to_numeric(df['PA'], errors='coerce')
    df['wRC+'] = pd.to_numeric(df['wRC+'], errors='coerce')
    df['Age'] = pd.to_numeric(df['Age'], errors='coerce')
    df['HR'] = pd.to_numeric(df['HR'], errors='coerce')
    return df

def clean_pitchers_data(df):
    df['K%'] = clean_percentage(df['K%'])
    df['BB%'] = clean_percentage(df['BB%'])
    df['K-BB%'] = clean_percentage(df['K-BB%'])
    df['Age'] = pd.to_numeric(df['Age'], errors='coerce')
    df['IP'] = pd.to_numeric(df['IP'], errors='coerce')
    df['ERA'] = pd.to_numeric(df['ERA'], errors='coerce')
    df['WHIP'] = pd.to_numeric(df['WHIP'], errors='coerce')
    df['FIP'] = pd.to_numeric(df['FIP'], errors='coerce')
    df['K/9'] = pd.to_numeric(df['K/9'], errors='coerce')
    return df

# === 3. Main App ===
st.title("🧢 Minor League Advanced Stats Leaderboard")
st.caption("Stats scraped from FanGraphs | Built with ❤️ + 🐍 | App by Christian Mack")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["Hitters Splits Leaderboard", "Pitcher Splits Leaderboard", "Full Season Hitting Leaderboard", "Full Season Pitching Leaderboard"])

# === TAB 1: HITTERS SPLITS LEADERBOARD ===
with tab1:
    df = load_hitters_splits_data()
    df = clean_hitters_data(df)
    
    # Sidebar Filters
    st.sidebar.header("📊 Hitters Splits Filters")
    
    # Timeframe
    timeframe_label_map = {
        "last_7": "Last 7 Days",
        "last_15": "Last 15 Days",
        "last_30": "Last 30 Days",
        "last_45": "Last 45 Days"
    }
    
    available_timeframes = [tf for tf in timeframe_label_map if tf in df['timeframe'].unique()]
    sorted_timeframes = sorted(available_timeframes, key=lambda x: int(x.split('_')[1]))
    display_labels = [timeframe_label_map[tf] for tf in sorted_timeframes]
    selected_label = st.sidebar.selectbox("Timeframe", display_labels, key="hitters_splits_timeframe")
    selected_timeframe = {v: k for k, v in timeframe_label_map.items()}[selected_label]
    
    # Plate Appearances
    min_pa = int(df.get("PA", pd.Series([0])).min())
    max_pa = int(df.get("PA", pd.Series([100])).max())
    pa_range = st.sidebar.slider("Plate Appearances (PA)", min_pa, max_pa, (min_pa, max_pa), key="hitters_splits_pa")
    
    # Qualification threshold
    qualification_thresholds = {
        "last_7": 15,
        "last_15": 30,
        "last_30": 50,
        "last_45": 75
    }
    qualified_only = st.sidebar.checkbox("Only show qualified hitters", key="hitters_splits_qualified")
    
    # Age
    min_age = int(df['Age'].min())
    max_age = int(df['Age'].max())
    age_range = st.sidebar.slider("Age", min_age, max_age, (min_age, max_age), key="hitters_splits_age")
    
    # K%
    k_filter = st.sidebar.slider("K%", 0.0, 100.0, (0.0, 100.0), key="hitters_splits_k")
    
    # BB%
    bb_filter = st.sidebar.slider("BB%", 0.0, 100.0, (0.0, 100.0), key="hitters_splits_bb")
    
    # Level
    level_options = sorted(df['aLevel'].dropna().unique())
    selected_levels = st.sidebar.multiselect("Level", level_options, default=level_options, key="hitters_splits_level")
    
    # Player Name Filter
    name_query = st.sidebar.text_input("Search by Player Name", key="hitters_splits_name").strip().lower()
    
    # Apply Filters
    pa_condition = (
        (df['PA'] >= qualification_thresholds[selected_timeframe])
        if qualified_only else True
    )
    
    filtered_df = df[
        (df['timeframe'] == selected_timeframe) &
        (df['aLevel'].isin(selected_levels)) &
        (df['PA'] >= pa_range[0]) & (df['PA'] <= pa_range[1]) &
        (df['Age'] >= age_range[0]) & (df['Age'] <= age_range[1]) &
        (df['K%'] >= k_filter[0]) & (df['K%'] <= k_filter[1]) &
        (df['player_name'].str.lower().str.contains(name_query) if name_query else True) &
        (df['BB%'] >= bb_filter[0]) & (df['BB%'] <= bb_filter[1]) &
        pa_condition
    ]
    
    # Display
    columns_to_display = [
        "player_name", "TeamName", "aLevel", "Age", "AB", "PA", "2B", "3B", "HR",
        "R", "RBI", "SB", "K%", "BB%", "AVG", "OBP", "SLG", "OPS", "ISO", "wRC+", "wOBA", "BABIP"
    ]
    
    renamed_columns = {
        "player_name": "Name",
        "TeamName": "Team",
        "aLevel": "Level"
    }
    
    st.dataframe(
        filtered_df.sort_values("wRC+", ascending=False).reset_index(drop=True)[columns_to_display].rename(columns=renamed_columns),
        use_container_width=True
    )
    
    # Bubble Chart
    plot_df = filtered_df.dropna(subset=['K%', 'wRC+', 'HR'])
    
    fig = px.scatter(
        plot_df,
        x='K%',
        y='wRC+',
        size='HR',
        color='aLevel',
        hover_name='player_name',
        hover_data=['TeamName', 'Age', 'PA'],
        title="wRC+ vs. K% (Bubble Size = HR)",
        size_max=40,
        height=600
    )
    
    fig.update_layout(
        xaxis_title="Strikeout Rate (K%)",
        yaxis_title="Weighted Runs Created (wRC+)",
        legend_title="Level",
        margin=dict(l=40, r=20, t=40, b=40)
    )
    
    st.plotly_chart(fig, use_container_width=True)

# === TAB 2: PITCHER SPLITS LEADERBOARD ===
with tab2:
    df_pitch = load_pitchers_splits_data()
    df_pitch = clean_pitchers_data(df_pitch)
    
    # Sidebar Filters
    st.sidebar.header("⚾ Pitcher Splits Filters")
    
    # Age
    min_age_pitch = int(df_pitch['Age'].min())
    max_age_pitch = int(df_pitch['Age'].max())
    age_range_pitch = st.sidebar.slider("Age", min_age_pitch, max_age_pitch, (min_age_pitch, max_age_pitch), key="pitcher_splits_age")
    
    # IP
    min_ip = float(df_pitch['IP'].min())
    max_ip = float(df_pitch['IP'].max())
    ip_range = st.sidebar.slider("Innings Pitched (IP)", min_ip, max_ip, (min_ip, max_ip), key="pitcher_splits_ip")
    
    # K%
    k_filter_pitch = st.sidebar.slider("K%", 0.0, 100.0, (0.0, 100.0), key="pitcher_splits_k")
    
    # BB%
    bb_filter_pitch = st.sidebar.slider("BB%", 0.0, 100.0, (0.0, 100.0), key="pitcher_splits_bb")
    
    # K-BB%
    kbb_min = float(df_pitch['K-BB%'].min())
    kbb_max = float(df_pitch['K-BB%'].max())
    kbb_filter = st.sidebar.slider("K-BB%", kbb_min, kbb_max, (kbb_min, kbb_max), key="pitcher_splits_kbb")
    
    # Level
    level_options_pitch = sorted(df_pitch['aLevel'].dropna().unique())
    selected_levels_pitch = st.sidebar.multiselect("Level", level_options_pitch, default=level_options_pitch, key="pitcher_splits_level")
    
    # Player Name Filter
    name_query_pitch = st.sidebar.text_input("Search by Player Name", key="pitcher_splits_name").strip().lower()
    
    # Apply Filters
    filtered_df_pitch = df_pitch[
        (df_pitch['aLevel'].isin(selected_levels_pitch)) &
        (df_pitch['Age'] >= age_range_pitch[0]) & (df_pitch['Age'] <= age_range_pitch[1]) &
        (df_pitch['IP'] >= ip_range[0]) & (df_pitch['IP'] <= ip_range[1]) &
        (df_pitch['K%'] >= k_filter_pitch[0]) & (df_pitch['K%'] <= k_filter_pitch[1]) &
        (df_pitch['BB%'] >= bb_filter_pitch[0]) & (df_pitch['BB%'] <= bb_filter_pitch[1]) &
        (df_pitch['K-BB%'] >= kbb_filter[0]) & (df_pitch['K-BB%'] <= kbb_filter[1]) &
        (df_pitch['player_name'].str.lower().str.contains(name_query_pitch) if name_query_pitch else True)
    ]
    
    # Display
    columns_to_display_pitch = [
        "player_name", "TeamName", "aLevel", "Age", "GS", "IP", "W", "L", "SO",
        "ERA", "WHIP", "FIP", "K/9", "K%", "BB%", "K-BB%", "BABIP", "LOB%"
    ]
    
    renamed_columns_pitch = {
        "player_name": "Name",
        "TeamName": "Team",
        "aLevel": "Level"
    }
    
    st.dataframe(
        filtered_df_pitch.sort_values("FIP", ascending=True).reset_index(drop=True)[columns_to_display_pitch].rename(columns=renamed_columns_pitch),
        use_container_width=True
    )
    
    # Scatter Plot for Pitchers
    plot_df_pitch = filtered_df_pitch.dropna(subset=['K%', 'BB%', 'FIP'])
    
    fig_pitch = px.scatter(
        plot_df_pitch,
        x='BB%',
        y='K%',
        size='IP',
        color='aLevel',
        hover_name='player_name',
        hover_data=['TeamName', 'Age', 'FIP', 'ERA'],
        title="K% vs. BB% (Bubble Size = IP)",
        size_max=40,
        height=600
    )
    
    fig_pitch.update_layout(
        xaxis_title="Walk Rate (BB%)",
        yaxis_title="Strikeout Rate (K%)",
        legend_title="Level",
        margin=dict(l=40, r=20, t=40, b=40)
    )
    
    st.plotly_chart(fig_pitch, use_container_width=True)

# === TAB 3: FULL SEASON HITTING LEADERBOARD ===
with tab3:
    df_full_hit = load_hitters_full_season_data()
    df_full_hit = clean_hitters_data(df_full_hit)
    
    # Sidebar Filters
    st.sidebar.header("🏆 Full Season Hitting Filters")
    
    # Age
    min_age_full_hit = int(df_full_hit['Age'].min())
    max_age_full_hit = int(df_full_hit['Age'].max())
    age_range_full_hit = st.sidebar.slider("Age", min_age_full_hit, max_age_full_hit, (min_age_full_hit, max_age_full_hit), key="full_hit_age")
    
    # Plate Appearances
    min_pa_full = int(df_full_hit.get("PA", pd.Series([0])).min())
    max_pa_full = int(df_full_hit.get("PA", pd.Series([600])).max())
    pa_range_full = st.sidebar.slider("Plate Appearances (PA)", min_pa_full, max_pa_full, (min_pa_full, max_pa_full), key="full_hit_pa")
    
    # K%
    k_filter_full_hit = st.sidebar.slider("K%", 0.0, 100.0, (0.0, 100.0), key="full_hit_k")
    
    # BB%
    bb_filter_full_hit = st.sidebar.slider("BB%", 0.0, 100.0, (0.0, 100.0), key="full_hit_bb")
    
    # Level
    level_options_full_hit = sorted(df_full_hit['aLevel'].dropna().unique())
    selected_levels_full_hit = st.sidebar.multiselect("Level", level_options_full_hit, default=level_options_full_hit, key="full_hit_level")
    
    # Player Name Filter
    name_query_full_hit = st.sidebar.text_input("Search by Player Name", key="full_hit_name").strip().lower()
    
    # Apply Filters
    filtered_df_full_hit = df_full_hit[
        (df_full_hit['aLevel'].isin(selected_levels_full_hit)) &
        (df_full_hit['Age'] >= age_range_full_hit[0]) & (df_full_hit['Age'] <= age_range_full_hit[1]) &
        (df_full_hit['PA'] >= pa_range_full[0]) & (df_full_hit['PA'] <= pa_range_full[1]) &
        (df_full_hit['K%'] >= k_filter_full_hit[0]) & (df_full_hit['K%'] <= k_filter_full_hit[1]) &
        (df_full_hit['BB%'] >= bb_filter_full_hit[0]) & (df_full_hit['BB%'] <= bb_filter_full_hit[1]) &
        (df_full_hit['PlayerName'].str.lower().str.contains(name_query_full_hit) if name_query_full_hit else True)
    ]
    
    # Display
    columns_to_display_full_hit = [
        "PlayerName", "TeamName", "aLevel", "Age", "AB", "PA", "2B", "3B", "HR",
        "R", "RBI", "SB", "K%", "BB%", "AVG", "OBP", "SLG", "OPS", "ISO", "wRC+", "wOBA", "BABIP"
    ]
    
    renamed_columns_full_hit = {
        "PlayerName": "Name",
        "TeamName": "Team",
        "aLevel": "Level"
    }
    
    st.dataframe(
        filtered_df_full_hit.sort_values("wRC+", ascending=False).reset_index(drop=True)[columns_to_display_full_hit].rename(columns=renamed_columns_full_hit),
        use_container_width=True
    )

# === TAB 4: FULL SEASON PITCHING LEADERBOARD ===
with tab4:
    df_full_pitch = load_pitchers_full_season_data()
    df_full_pitch = clean_pitchers_data(df_full_pitch)
    
    # Sidebar Filters
    st.sidebar.header("🏆 Full Season Pitching Filters")
    
    # Age
    min_age_full_pitch = int(df_full_pitch['Age'].min())
    max_age_full_pitch = int(df_full_pitch['Age'].max())
    age_range_full_pitch = st.sidebar.slider("Age", min_age_full_pitch, max_age_full_pitch, (min_age_full_pitch, max_age_full_pitch), key="full_pitch_age")
    
    # IP
    min_ip_full = float(df_full_pitch['IP'].min())
    max_ip_full = float(df_full_pitch['IP'].max())
    ip_range_full = st.sidebar.slider("Innings Pitched (IP)", min_ip_full, max_ip_full, (min_ip_full, max_ip_full), key="full_pitch_ip")
    
    # K%
    k_filter_full_pitch = st.sidebar.slider("K%", 0.0, 100.0, (0.0, 100.0), key="full_pitch_k")
    
    # BB%
    bb_filter_full_pitch = st.sidebar.slider("BB%", 0.0, 100.0, (0.0, 100.0), key="full_pitch_bb")
    
    # K-BB%
    kbb_min_full = float(df_full_pitch['K-BB%'].min())
    kbb_max_full = float(df_full_pitch['K-BB%'].max())
    kbb_filter_full = st.sidebar.slider("K-BB%", kbb_min_full, kbb_max_full, (kbb_min_full, kbb_max_full), key="full_pitch_kbb")
    
    # Level
    level_options_full_pitch = sorted(df_full_pitch['aLevel'].dropna().unique())
    selected_levels_full_pitch = st.sidebar.multiselect("Level", level_options_full_pitch, default=level_options_full_pitch, key="full_pitch_level")
    
    # Player Name Filter
    name_query_full_pitch = st.sidebar.text_input("Search by Player Name", key="full_pitch_name").strip().lower()
    
    # Apply Filters
    filtered_df_full_pitch = df_full_pitch[
        (df_full_pitch['aLevel'].isin(selected_levels_full_pitch)) &
        (df_full_pitch['Age'] >= age_range_full_pitch[0]) & (df_full_pitch['Age'] <= age_range_full_pitch[1]) &
        (df_full_pitch['IP'] >= ip_range_full[0]) & (df_full_pitch['IP'] <= ip_range_full[1]) &
        (df_full_pitch['K%'] >= k_filter_full_pitch[0]) & (df_full_pitch['K%'] <= k_filter_full_pitch[1]) &
        (df_full_pitch['BB%'] >= bb_filter_full_pitch[0]) & (df_full_pitch['BB%'] <= bb_filter_full_pitch[1]) &
        (df_full_pitch['K-BB%'] >= kbb_filter_full[0]) & (df_full_pitch['K-BB%'] <= kbb_filter_full[1]) &
        (df_full_pitch['PlayerName'].str.lower().str.contains(name_query_full_pitch) if name_query_full_pitch else True)
    ]
    
    # Display
    columns_to_display_full_pitch = [
        "PlayerName", "TeamName", "aLevel", "Age", "GS", "IP", "W", "L", "SO",
        "ERA", "WHIP", "FIP", "K/9", "K%", "BB%", "K-BB%", "BABIP", "LOB%"
    ]
    
    renamed_columns_full_pitch = {
        "PlayerName": "Name",
        "TeamName": "Team",
        "aLevel": "Level"
    }
    
    st.dataframe(
        filtered_df_full_pitch.sort_values("FIP", ascending=True).reset_index(drop=True)[columns_to_display_full_pitch].rename(columns=renamed_columns_full_pitch),
        use_container_width=True
    )

# === Tip Jar ===
st.sidebar.markdown("---")
st.sidebar.markdown("💸 **Enjoying this app?** [Send a tip](https://coff.ee/christianmack)")
