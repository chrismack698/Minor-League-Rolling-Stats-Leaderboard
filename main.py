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
def clean_percentage(series):
    return pd.to_numeric(series.str.replace('%', '', regex=False), errors='coerce')

# === Main App ===
st.title("🧢 Minor League Advanced Splits Leaderboard")
st.caption("Stats scraped from FanGraphs | Built with ❤️ + 🐍 | App by Christian Mack")

# Initialize session state for active tab
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 'Hitters'

# Tab selection buttons
col1, col2 = st.columns(2)
with col1:
    if st.button("⚾ Hitters Splits Leaderboard", use_container_width=True, 
                 type="primary" if st.session_state.active_tab == 'Hitters' else "secondary"):
        st.session_state.active_tab = 'Hitters'
with col2:
    if st.button("⚾ Pitchers Splits Leaderboard", use_container_width=True,
                 type="primary" if st.session_state.active_tab == 'Pitchers' else "secondary"):
        st.session_state.active_tab = 'Pitchers'

# === Dynamic Sidebar Based on Active Tab ===
with st.sidebar:
    st.header(f"📊 {st.session_state.active_tab} Filters")
    
    # Common timeframe mapping
    timeframe_label_map = {
        "last_7": "Last 7 Days",
        "last_15": "Last 15 Days",
        "last_30": "Last 30 Days",
        "last_45": "Last 45 Days",
        "last_60": "Last 60 Days"
    }
    
    if st.session_state.active_tab == 'Hitters':
        # Load hitters data for filter setup
        df_hitters = load_hitters_data()
        
        # === HITTERS FILTERS ===
        # Timeframe
        available_timeframes = [tf for tf in timeframe_label_map if tf in df_hitters['timeframe'].unique()]
        sorted_timeframes = sorted(available_timeframes, key=lambda x: int(x.split('_')[1]))
        display_labels = [timeframe_label_map[tf] for tf in sorted_timeframes]
        selected_label = st.selectbox("Timeframe", display_labels, key="hitters_timeframe")
        selected_timeframe = {v: k for k, v in timeframe_label_map.items()}[selected_label]
        
        # Plate Appearances
        min_pa = int(df_hitters.get("PA", pd.Series([0])).min())
        max_pa = int(df_hitters.get("PA", pd.Series([100])).max())
        pa_range = st.slider("Plate Appearances (PA)", min_pa, max_pa, (min_pa, max_pa), key="hitters_pa")
        
        # Qualification checkbox
        qualification_thresholds = {
            "last_7": 15,
            "last_15": 30,
            "last_30": 50,
            "last_45": 75
        }
        qualified_only = st.checkbox("Only show qualified hitters", key="hitters_qualified")
        
        # Age
        min_age_h = int(df_hitters['Age'].min())
        max_age_h = int(df_hitters['Age'].max())
        age_range_h = st.slider("Age", min_age_h, max_age_h, (min_age_h, max_age_h), key="hitters_age")
        
        # K% and BB%
        k_filter_h = st.slider("K%", 0.0, 100.0, (0.0, 100.0), key="hitters_k")
        bb_filter_h = st.slider("BB%", 0.0, 100.0, (0.0, 100.0), key="hitters_bb")
        
        # Level
        level_options_h = sorted(df_hitters['aLevel'].dropna().unique())
        selected_levels_h = st.multiselect("Level", level_options_h, default=level_options_h, key="hitters_level")

        select_all_h = st.sidebar.checkbox("Select All Players", value=True, key="select_all_players_h")
        
        # Player Name Filter
        name_options_h = sorted(df_hitters['player_name'].dropna().unique())
        selected_names_h = st.multiselect("Player Name", name_options_h, default=name_options_h if select_all_h else [], key="hitters_name")

    
    else:  # Pitchers tab
        # Load pitchers data for filter setup
        df_pitchers = load_pitchers_data()
        
        # Process pitchers data for filters
        df_pitchers['K%'] = clean_percentage(df_pitchers['K%'])
        df_pitchers['BB%'] = clean_percentage(df_pitchers['BB%'])
        df_pitchers['K-BB%'] = clean_percentage(df_pitchers['K-BB%'])
        df_pitchers['Age'] = pd.to_numeric(df_pitchers['Age'], errors='coerce')
        df_pitchers['IP'] = pd.to_numeric(df_pitchers['IP'], errors='coerce')
        df_pitchers['ERA'] = pd.to_numeric(df_pitchers['ERA'], errors='coerce')
        df_pitchers['FIP'] = pd.to_numeric(df_pitchers['FIP'], errors='coerce')
        df_pitchers['WHIP'] = pd.to_numeric(df_pitchers['WHIP'], errors='coerce')
        
        # === PITCHERS FILTERS ===
        # Timeframe
        available_timeframes_p = [tf for tf in timeframe_label_map if tf in df_pitchers['timeframe'].unique()]
        sorted_timeframes_p = sorted(available_timeframes_p, key=lambda x: int(x.split('_')[1]))
        display_labels_p = [timeframe_label_map[tf] for tf in sorted_timeframes_p]
        selected_label_p = st.selectbox("Timeframe", display_labels_p, key="pitchers_timeframe")
        selected_timeframe_p = {v: k for k, v in timeframe_label_map.items()}[selected_label_p]
        
        # Age
        min_age_p = int(df_pitchers['Age'].min())
        max_age_p = int(df_pitchers['Age'].max())
        age_range_p = st.slider("Age", min_age_p, max_age_p, (min_age_p, max_age_p), key="pitchers_age")
        
        # IP (Innings Pitched)
        min_ip = df_pitchers['IP'].min()
        max_ip = df_pitchers['IP'].max()
        ip_range = st.slider("Innings Pitched (IP)", min_ip, max_ip, (min_ip, max_ip), key="pitchers_ip")

        # GS
        min_gs = df_pitchers['GS'].min()
        max_gs = df_pitchers['GS'].max()
        gs_range = st.slider("Games Started (GS)", min_gs, max_gs, (min_gs, max_gs), key="pitchers_gs")
        
        # K%
        min_k_p = float(df_pitchers['K%'].min())
        max_k_p = float(df_pitchers['K%'].max())
        k_filter_p = st.slider("K%", min_k_p, max_k_p, (min_k_p, max_k_p), key="pitchers_k")
        
        # BB%
        min_bb_p = float(df_pitchers['BB%'].min())
        max_bb_p = float(df_pitchers['BB%'].max())
        bb_filter_p = st.slider("BB%", min_bb_p, max_bb_p, (min_bb_p, max_bb_p), key="pitchers_bb")
        
        # K-BB%
        min_kbb = float(df_pitchers['K-BB%'].min())
        max_kbb = float(df_pitchers['K-BB%'].max())
        kbb_range = st.slider("K-BB%", min_kbb, max_kbb, (min_kbb, max_kbb), key="pitchers_kbb")
        
        # Level
        level_options_p = sorted(df_pitchers['aLevel'].dropna().unique())
        selected_levels_p = st.multiselect("Level", level_options_p, default=level_options_p, key="pitchers_level")

        select_all_p = st.sidebar.checkbox("Select All Players", value=True, key="select_all_players_p")
        
        # Player Name Filter
        name_options_p = sorted(df_pitchers['player_name'].dropna().unique())
        selected_names_p = st.multiselect("Player Name", name_options_p, default=name_options_p if select_all_p else [], key="pitchers_name")

        

# === Main Content Based on Active Tab ===
if st.session_state.active_tab == 'Hitters':
    # === HITTERS CONTENT ===
    # Process hitters data
    df_hitters['K%'] = clean_percentage(df_hitters['K%'])
    df_hitters['BB%'] = clean_percentage(df_hitters['BB%'])
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
        ((df_hitters['player_name'].isin(selected_names_h))) &
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

else:  # Pitchers tab
    # === PITCHERS CONTENT ===
    # Apply filters
    filtered_df_p = df_pitchers[
        (df_pitchers['aLevel'].isin(selected_levels_p)) &
        (df_pitchers['timeframe'] == selected_timeframe_p) &
        (df_pitchers['Age'] >= age_range_p[0]) & (df_pitchers['Age'] <= age_range_p[1]) &
        (df_pitchers['IP'] >= ip_range[0]) & (df_pitchers['IP'] <= ip_range[1]) &
        (df_pitchers['K%'] >= k_filter_p[0]) & (df_pitchers['K%'] <= k_filter_p[1]) &
        (df_pitchers['BB%'] >= bb_filter_p[0]) & (df_pitchers['BB%'] <= bb_filter_p[1]) &
        (df_pitchers['K-BB%'] >= kbb_range[0]) & (df_pitchers['K-BB%'] <= kbb_range[1]) &
        (df_pitchers['GS'] >= gs_range[0]) & (df_pitchers['GS'] <= gs_range[1]) &
        ((df_pitchers['player_name'].isin(selected_names_p)))
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
        filtered_df_p.sort_values("K-BB%", ascending=False).reset_index(drop=True)[columns_to_display_p].rename(columns=renamed_columns_p),
        use_container_width=True
    )
    
    # Pitchers bubble chart
    fig_p = px.scatter(
        filtered_df_p,
        x='K-BB%',
        y='FIP',
        size='IP',
        color='aLevel',
        hover_name='player_name',
        hover_data=['TeamName', 'Age', 'ERA', 'WHIP'],
        title="K-BB% vs FIP (Bubble Size = IP, Color = Level)",
        size_max=40,
        height=600
    )
    
    fig_p.update_layout(
        xaxis_title="K-BB%",
        yaxis_title="FIP",
        margin=dict(l=40, r=20, t=40, b=40)
    )
    
    st.plotly_chart(fig_p, use_container_width=True)

# === Tip Jar (appears in sidebar for both tabs) ===
with st.sidebar:
    st.markdown("---")
    st.markdown("💸 **Enjoying this app?** [Send a tip](https://coff.ee/christianmack)")
