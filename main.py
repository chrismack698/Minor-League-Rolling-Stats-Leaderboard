import streamlit as st
import pandas as pd
import plotly.express as px

# === Page Configuration ===
st.set_page_config(page_title="Minor League Splits Leaderboard", layout="wide")

# === Data Loading Functions ===
@st.cache_data(ttl=3600)
def load_hitters_data():
    url = "https://raw.githubusercontent.com/chrismack698/Minor-League-Rolling-Stats-Leaderboard/main/data/hitters/leaderboard_data.csv"
    return pd.read_csv(url)

@st.cache_data(ttl=3600)
def load_pitchers_data():
    url = "https://raw.githubusercontent.com/chrismack698/Minor-League-Rolling-Stats-Leaderboard/main/data/pitchers/leaderboard_pitch_data.csv"
    return pd.read_csv(url)

# === Utility Functions ===
# (No utility functions needed since percentages are already numeric)

# === Main App ===
st.title("🧢 Minor League Advanced Splits Leaderboard")
st.caption("Stats scraped from FanGraphs | Built with ❤️ + 🐍 | App by Christian Mack")

# Create tabs
tab1, tab2 = st.tabs(["⚾ Hitters Splits Leaderboard", "⚾ Pitchers Splits Leaderboard"])

# === HITTERS TAB ===
with tab1:
    # Load hitters data
    df_hitters = load_hitters_data()
    
    # === Sidebar Filters for Hitters ===
    st.sidebar.header("📊 Hitters Filters")
    
    # Timeframe
    timeframe_label_map = {
        "last_7": "Last 7 Days",
        "last_15": "Last 15 Days",
        "last_30": "Last 30 Days",
        "last_45": "Last 45 Days"
    }
    
    available_timeframes = [tf for tf in timeframe_label_map if tf in df_hitters['timeframe'].unique()]
    sorted_timeframes = sorted(available_timeframes, key=lambda x: int(x.split('_')[1]))
    display_labels = [timeframe_label_map[tf] for tf in sorted_timeframes]
    selected_label = st.sidebar.selectbox("Timeframe", display_labels, key="hitters_timeframe")
    selected_timeframe = {v: k for k, v in timeframe_label_map.items()}[selected_label]
    
    # Plate Appearances
    min_pa = int(df_hitters.get("PA", pd.Series([0])).min())
    max_pa = int(df_hitters.get("PA", pd.Series([100])).max())
    pa_range = st.sidebar.slider("Plate Appearances (PA)", min_pa, max_pa, (min_pa, max_pa), key="hitters_pa")
    
    # Qualification checkbox
    qualification_thresholds = {
        "last_7": 15,
        "last_15": 30,
        "last_30": 50,
        "last_45": 75
    }
    qualified_only = st.sidebar.checkbox("Only show qualified hitters", key="hitters_qualified")
    
    # Age
    min_age_h = int(df_hitters['Age'].min())
    max_age_h = int(df_hitters['Age'].max())
    age_range_h = st.sidebar.slider("Age", min_age_h, max_age_h, (min_age_h, max_age_h), key="hitters_age")
    
    # K% and BB%
    k_filter_h = st.sidebar.slider("K%", 0.0, 100.0, (0.0, 100.0), key="hitters_k")
    bb_filter_h = st.sidebar.slider("BB%", 0.0, 100.0, (0.0, 100.0), key="hitters_bb")
    
    # Level
    level_options_h = sorted(df_hitters['aLevel'].dropna().unique())
    selected_levels_h = st.sidebar.multiselect("Level", level_options_h, default=level_options_h, key="hitters_level")
    
    # Player Name Filter
    name_query_h = st.sidebar.text_input("Search by Player Name", key="hitters_name").strip().lower()
    
    # === Process Hitters Data ===
    df_hitters['K%'] = pd.to_numeric(df_hitters['K%'], errors='coerce')
    df_hitters['BB%'] = pd.to_numeric(df_hitters['BB%'], errors='coerce')
    df_hitters['PA'] = pd.to_numeric(df_hitters['PA'], errors='coerce')
    df_hitters['wRC+'] = pd.to_numeric(df_hitters['wRC+'], errors='coerce')
    df_hitters['Age'] = pd.to_numeric(df_hitters['Age'], errors='coerce')
    df_hitters['HR'] = pd.to_numeric(df_hitters['HR'], errors='coerce')
    
    # Apply filters
    pa_condition = (
        (df_hitters['PA'] >= qualification_thresholds[selected_timeframe])
        if qualified_only else True
    )
    
    filtered_df_h = df_hitters[
        (df_hitters['timeframe'] == selected_timeframe) &
        (df_hitters['aLevel'].isin(selected_levels_h)) &
        (df_hitters['PA'] >= pa_range[0]) & (df_hitters['PA'] <= pa_range[1]) &
        (df_hitters['Age'] >= age_range_h[0]) & (df_hitters['Age'] <= age_range_h[1]) &
        (df_hitters['K%'] >= k_filter_h[0]) & (df_hitters['K%'] <= k_filter_h[1]) &
        (df_hitters['player_name'].str.lower().str.contains(name_query_h) if name_query_h else True) &
        (df_hitters['BB%'] >= bb_filter_h[0]) & (df_hitters['BB%'] <= bb_filter_h[1]) &
        pa_condition
    ]
    
    # Display hitters leaderboard
    columns_to_display_h = [
        "player_name", "TeamName", "aLevel", "Age", "AB", "PA", "2B", "3B", "HR",
        "R", "RBI", "SB", "K%", "BB%", "AVG", "OBP", "SLG", "OPS", "ISO", "wRC+", "wOBA", "BABIP"
    ]
    
    renamed_columns_h = {
        "player_name": "Name",
        "TeamName": "Team",
        "aLevel": "Level"
    }
    
    st.dataframe(
        filtered_df_h.sort_values("wRC+", ascending=False).reset_index(drop=True)[columns_to_display_h].rename(columns=renamed_columns_h),
        use_container_width=True
    )
    
    # Hitters bubble chart
    plot_df_h = filtered_df_h.dropna(subset=['K%', 'wRC+', 'HR'])
    
    fig_h = px.scatter(
        plot_df_h,
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
    
    fig_h.update_layout(
        xaxis_title="Strikeout Rate (K%)",
        yaxis_title="Weighted Runs Created (wRC+)",
        legend_title="Level",
        margin=dict(l=40, r=20, t=40, b=40)
    )
    
    st.plotly_chart(fig_h, use_container_width=True)

# === PITCHERS TAB ===
with tab2:
    # Load pitchers data
    df_pitchers = load_pitchers_data()
    
    # === Sidebar Filters for Pitchers ===
    st.sidebar.header("📊 Pitchers Filters")
    
    # Level
    level_options_p = sorted(df_pitchers['aLevel'].dropna().unique())
    selected_levels_p = st.sidebar.multiselect("Level", level_options_p, default=level_options_p, key="pitchers_level")
    
    # Age
    min_age_p = int(df_pitchers['Age'].min())
    max_age_p = int(df_pitchers['Age'].max())
    age_range_p = st.sidebar.slider("Age", min_age_p, max_age_p, (min_age_p, max_age_p), key="pitchers_age")
    
    # IP (Innings Pitched)
    min_ip = float(df_pitchers['IP'].min())
    max_ip = float(df_pitchers['IP'].max())
    ip_range = st.sidebar.slider("Innings Pitched (IP)", min_ip, max_ip, (min_ip, max_ip), key="pitchers_ip")
    
    # K%
    k_filter_p = st.sidebar.slider("K%", 0.0, 100.0, (0.0, 100.0), key="pitchers_k")
    
    # BB%
    bb_filter_p = st.sidebar.slider("BB%", 0.0, 100.0, (0.0, 100.0), key="pitchers_bb")
    
    # K-BB%
    min_kbb = float(df_pitchers['K-BB%'].min())
    max_kbb = float(df_pitchers['K-BB%'].max())
    kbb_range = st.sidebar.slider("K-BB%", min_kbb, max_kbb, (min_kbb, max_kbb), key="pitchers_kbb")
    
    # Player Name Filter
    name_query_p = st.sidebar.text_input("Search by Player Name", key="pitchers_name").strip().lower()
    
    # === Process Pitchers Data ===
    df_pitchers['K%'] = pd.to_numeric(df_pitchers['K%'], errors='coerce')
    df_pitchers['BB%'] = pd.to_numeric(df_pitchers['BB%'], errors='coerce')
    df_pitchers['K-BB%'] = pd.to_numeric(df_pitchers['K-BB%'], errors='coerce')
    df_pitchers['Age'] = pd.to_numeric(df_pitchers['Age'], errors='coerce')
    df_pitchers['IP'] = pd.to_numeric(df_pitchers['IP'], errors='coerce')
    df_pitchers['ERA'] = pd.to_numeric(df_pitchers['ERA'], errors='coerce')
    df_pitchers['FIP'] = pd.to_numeric(df_pitchers['FIP'], errors='coerce')
    df_pitchers['WHIP'] = pd.to_numeric(df_pitchers['WHIP'], errors='coerce')
    
    # Apply filters
    filtered_df_p = df_pitchers[
        (df_pitchers['aLevel'].isin(selected_levels_p)) &
        (df_pitchers['Age'] >= age_range_p[0]) & (df_pitchers['Age'] <= age_range_p[1]) &
        (df_pitchers['IP'] >= ip_range[0]) & (df_pitchers['IP'] <= ip_range[1]) &
        (df_pitchers['K%'] >= k_filter_p[0]) & (df_pitchers['K%'] <= k_filter_p[1]) &
        (df_pitchers['BB%'] >= bb_filter_p[0]) & (df_pitchers['BB%'] <= bb_filter_p[1]) &
        (df_pitchers['K-BB%'] >= kbb_range[0]) & (df_pitchers['K-BB%'] <= kbb_range[1]) &
        (df_pitchers['player_name'].str.lower().str.contains(name_query_p) if name_query_p else True)
    ]
    
    # Display pitchers leaderboard
    columns_to_display_p = [
        "player_name", "TeamName", "aLevel", "Age", "GS", "IP", "W", "L", "SO",
        "ERA", "WHIP", "FIP", "K/9", "K%", "BB%", "K-BB%", "BABIP", "LOB%"
    ]
    
    renamed_columns_p = {
        "player_name": "Name",
        "TeamName": "Team",
        "aLevel": "Level"
    }
    
    st.dataframe(
        filtered_df_p.sort_values("FIP", ascending=True).reset_index(drop=True)[columns_to_display_p].rename(columns=renamed_columns_p),
        use_container_width=True
    )
    
    # Pitchers scatter plot
    plot_df_p = filtered_df_p.dropna(subset=['K%', 'BB%', 'FIP'])
    
    fig_p = px.scatter(
        plot_df_p,
        x='BB%',
        y='K%',
        size='IP',
        color='FIP',
        hover_name='player_name',
        hover_data=['TeamName', 'Age', 'ERA', 'WHIP'],
        title="K% vs. BB% (Bubble Size = IP, Color = FIP)",
        size_max=40,
        height=600,
        color_continuous_scale='RdYlBu_r'  # Red = high FIP (bad), Blue = low FIP (good)
    )
    
    fig_p.update_layout(
        xaxis_title="Walk Rate (BB%)",
        yaxis_title="Strikeout Rate (K%)",
        margin=dict(l=40, r=20, t=40, b=40)
    )
    
    st.plotly_chart(fig_p, use_container_width=True)

# === Tip Jar (appears in sidebar for both tabs) ===
st.sidebar.markdown("---")
st.sidebar.markdown("💸 **Enjoying this app?** [Send a tip](https://coff.ee/christianmack)")
