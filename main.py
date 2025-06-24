import streamlit as st
import pandas as pd
import plotly.express as px

# === Page Configuration ===
st.set_page_config(page_title="Minor League Leaderboards", layout="wide")

# === Data Loading Functions ===
@st.cache_data(ttl=3600)
def load_hitters_splits():
    url = "https://raw.githubusercontent.com/chrismack698/Minor-League-Rolling-Stats-Leaderboard/main/data/hitters/leaderboard_data.csv"
    return pd.read_csv(url)

@st.cache_data(ttl=3600)
def load_pitchers_splits():
    url = "https://raw.githubusercontent.com/chrismack698/Minor-League-Rolling-Stats-Leaderboard/main/data/pitchers/leaderboard_pitch_data.csv"
    return pd.read_csv(url)

@st.cache_data(ttl=3600)
def load_hitters_full_season():
    url = "https://raw.githubusercontent.com/chrismack698/Minor-League-Rolling-Stats-Leaderboard/main/data/hitters/full_season_data.csv"
    return pd.read_csv(url)

@st.cache_data(ttl=3600)
def load_pitchers_full_season():
    url = "https://raw.githubusercontent.com/chrismack698/Minor-League-Rolling-Stats-Leaderboard/main/data/pitchers/full_season_pitch_data.csv"
    return pd.read_csv(url)

# === Data Cleaning Functions ===
def clean_percentage(series):
    """Clean percentage columns - handle both string and numeric formats"""
    if series.dtype == 'object':
        # If it's string/object, remove % signs and convert to numeric
        return pd.to_numeric(series.str.replace('%', '', regex=False), errors='coerce')
    else:
        # If it's already numeric, just ensure it's numeric type
        return pd.to_numeric(series, errors='coerce')

def clean_hitters_data(df):
    """Clean hitters dataframe"""
    df['K%'] = clean_percentage(df['K%'])
    df['BB%'] = clean_percentage(df['BB%'])
    df['PA'] = pd.to_numeric(df['PA'], errors='coerce')
    df['wRC+'] = pd.to_numeric(df['wRC+'], errors='coerce')
    df['Age'] = pd.to_numeric(df['Age'], errors='coerce')
    df['HR'] = pd.to_numeric(df['HR'], errors='coerce')
    return df

def clean_pitchers_data(df):
    """Clean pitchers dataframe"""
    df['K%'] = clean_percentage(df['K%'])
    df['BB%'] = clean_percentage(df['BB%'])
    df['K-BB%'] = clean_percentage(df['K-BB%'])
    df['IP'] = pd.to_numeric(df['IP'], errors='coerce')
    df['Age'] = pd.to_numeric(df['Age'], errors='coerce')
    df['ERA'] = pd.to_numeric(df['ERA'], errors='coerce')
    df['WHIP'] = pd.to_numeric(df['WHIP'], errors='coerce')
    df['FIP'] = pd.to_numeric(df['FIP'], errors='coerce')
    return df

# === Filter Functions ===
def create_hitters_filters(df, key_prefix=""):
    """Create sidebar filters for hitters data"""
    st.sidebar.header("📊 Filters")
    
    filters = {}
    
    # Timeframe filter (only for splits data)
    if 'timeframe' in df.columns:
        timeframe_label_map = {
            "last_7": "Last 7 Days",
            "last_15": "Last 15 Days", 
            "last_30": "Last 30 Days",
            "last_45": "Last 45 Days"
        }
        
        available_timeframes = [tf for tf in timeframe_label_map if tf in df['timeframe'].unique()]
        sorted_timeframes = sorted(available_timeframes, key=lambda x: int(x.split('_')[1]))
        display_labels = [timeframe_label_map[tf] for tf in sorted_timeframes]
        selected_label = st.sidebar.selectbox("Timeframe", display_labels, key=f"{key_prefix}_timeframe")
        filters['timeframe'] = {v: k for k, v in timeframe_label_map.items()}[selected_label]
    
    # Plate Appearances
    min_pa = int(df.get("PA", pd.Series([0])).min())
    max_pa = int(df.get("PA", pd.Series([100])).max())
    filters['pa_range'] = st.sidebar.slider("Plate Appearances (PA)", min_pa, max_pa, (min_pa, max_pa), key=f"{key_prefix}_pa")
    
    # Qualified hitters (only for splits)
    if 'timeframe' in df.columns:
        filters['qualified_only'] = st.sidebar.checkbox("Only show qualified hitters", key=f"{key_prefix}_qualified")
    
    # Age
    min_age = int(df['Age'].min())
    max_age = int(df['Age'].max())
    filters['age_range'] = st.sidebar.slider("Age", min_age, max_age, (min_age, max_age), key=f"{key_prefix}_age")
    
    # K%
    filters['k_filter'] = st.sidebar.slider("K%", 0.0, 100.0, (0.0, 100.0), key=f"{key_prefix}_k")
    
    # BB%
    filters['bb_filter'] = st.sidebar.slider("BB%", 0.0, 100.0, (0.0, 100.0), key=f"{key_prefix}_bb")
    
    # Level
    level_options = sorted(df['aLevel'].dropna().unique())
    filters['selected_levels'] = st.sidebar.multiselect("Level", level_options, default=level_options, key=f"{key_prefix}_level")
    
    # Player Name
    filters['name_query'] = st.sidebar.text_input("Search by Player Name", key=f"{key_prefix}_name").strip().lower()
    
    return filters

def create_pitchers_filters(df, key_prefix=""):
    """Create sidebar filters for pitchers data"""
    st.sidebar.header("📊 Filters")
    
    filters = {}
    
    # Timeframe filter (only for splits data)
    if 'timeframe' in df.columns:
        timeframe_label_map = {
            "last_7": "Last 7 Days",
            "last_15": "Last 15 Days",
            "last_30": "Last 30 Days", 
            "last_45": "Last 45 Days"
        }
        
        available_timeframes = [tf for tf in timeframe_label_map if tf in df['timeframe'].unique()]
        sorted_timeframes = sorted(available_timeframes, key=lambda x: int(x.split('_')[1]))
        display_labels = [timeframe_label_map[tf] for tf in sorted_timeframes]
        selected_label = st.sidebar.selectbox("Timeframe", display_labels, key=f"{key_prefix}_timeframe")
        filters['timeframe'] = {v: k for k, v in timeframe_label_map.items()}[selected_label]
    
    # Level
    level_options = sorted(df['aLevel'].dropna().unique())
    filters['selected_levels'] = st.sidebar.multiselect("Level", level_options, default=level_options, key=f"{key_prefix}_level")
    
    # Age
    min_age = int(df['Age'].min())
    max_age = int(df['Age'].max()) 
    filters['age_range'] = st.sidebar.slider("Age", min_age, max_age, (min_age, max_age), key=f"{key_prefix}_age")
    
    # IP
    min_ip = float(df['IP'].min())
    max_ip = float(df['IP'].max())
    filters['ip_range'] = st.sidebar.slider("Innings Pitched (IP)", min_ip, max_ip, (min_ip, max_ip), key=f"{key_prefix}_ip")
    
    # K%
    filters['k_filter'] = st.sidebar.slider("K%", 0.0, 100.0, (0.0, 100.0), key=f"{key_prefix}_k")
    
    # BB%
    filters['bb_filter'] = st.sidebar.slider("BB%", 0.0, 100.0, (0.0, 100.0), key=f"{key_prefix}_bb")
    
    # K-BB%
    min_kbb = float(df['K-BB%'].min())
    max_kbb = float(df['K-BB%'].max())
    filters['kbb_filter'] = st.sidebar.slider("K-BB%", min_kbb, max_kbb, (min_kbb, max_kbb), key=f"{key_prefix}_kbb")
    
    # Player Name
    filters['name_query'] = st.sidebar.text_input("Search by Player Name", key=f"{key_prefix}_name").strip().lower()
    
    return filters

def apply_hitters_filters(df, filters):
    """Apply filters to hitters dataframe"""
    filtered_df = df.copy()
    
    # Timeframe
    if 'timeframe' in filters:
        filtered_df = filtered_df[filtered_df['timeframe'] == filters['timeframe']]
    
    # Qualification (only for splits)
    if filters.get('qualified_only'):
        qualification_thresholds = {
            "last_7": 15,
            "last_15": 30,
            "last_30": 50,
            "last_45": 75
        }
        min_pa = qualification_thresholds.get(filters.get('timeframe', 'last_30'), 50)
        filtered_df = filtered_df[filtered_df['PA'] >= min_pa]
    
    # Apply all filters
    filtered_df = filtered_df[
        (filtered_df['aLevel'].isin(filters['selected_levels'])) &
        (filtered_df['PA'] >= filters['pa_range'][0]) & (filtered_df['PA'] <= filters['pa_range'][1]) &
        (filtered_df['Age'] >= filters['age_range'][0]) & (filtered_df['Age'] <= filters['age_range'][1]) &
        (filtered_df['K%'] >= filters['k_filter'][0]) & (filtered_df['K%'] <= filters['k_filter'][1]) &
        (filtered_df['BB%'] >= filters['bb_filter'][0]) & (filtered_df['BB%'] <= filters['bb_filter'][1])
    ]
    
    # Name filter
    if filters['name_query']:
        filtered_df = filtered_df[filtered_df['player_name'].str.lower().str.contains(filters['name_query'])]
    
    return filtered_df

def apply_pitchers_filters(df, filters):
    """Apply filters to pitchers dataframe"""
    filtered_df = df.copy()
    
    # Timeframe
    if 'timeframe' in filters:
        filtered_df = filtered_df[filtered_df['timeframe'] == filters['timeframe']]
    
    # Apply filters
    filtered_df = filtered_df[
        (filtered_df['aLevel'].isin(filters['selected_levels'])) &
        (filtered_df['Age'] >= filters['age_range'][0]) & (filtered_df['Age'] <= filters['age_range'][1]) &
        (filtered_df['IP'] >= filters['ip_range'][0]) & (filtered_df['IP'] <= filters['ip_range'][1]) &
        (filtered_df['K%'] >= filters['k_filter'][0]) & (filtered_df['K%'] <= filters['k_filter'][1]) &
        (filtered_df['BB%'] >= filters['bb_filter'][0]) & (filtered_df['BB%'] <= filters['bb_filter'][1]) &
        (filtered_df['K-BB%'] >= filters['kbb_filter'][0]) & (filtered_df['K-BB%'] <= filters['kbb_filter'][1])
    ]
    
    # Name filter
    if filters['name_query']:
        filtered_df = filtered_df[filtered_df['player_name'].str.lower().str.contains(filters['name_query'])]
    
    return filtered_df

# === Display Functions ===
def display_hitters_leaderboard(df, title):
    """Display hitters leaderboard with chart"""
    st.title(title)
    st.caption("Stats scraped from FanGraphs | Built with ❤️ + 🐍 | App by Christian Mack")
    
    columns_to_display = [
        "player_name", "TeamName", "aLevel", "Age", "AB", "PA", "2B", "3B", "HR",
        "R", "RBI", "SB", "K%", "BB%", "AVG", "OBP", "SLG", "OPS", "ISO", "wRC+", "wOBA", "BABIP"
    ]
    
    renamed_columns = {
        "player_name": "Name",
        "TeamName": "Team", 
        "aLevel": "Level"
    }
    
    # Display leaderboard
    st.dataframe(
        df.sort_values("wRC+", ascending=False).reset_index(drop=True)[columns_to_display].rename(columns=renamed_columns),
        use_container_width=True
    )
    
    # Bubble chart
    plot_df = df.dropna(subset=['K%', 'wRC+', 'HR'])
    
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

def display_pitchers_leaderboard(df, title):
    """Display pitchers leaderboard"""
    st.title(title)
    st.caption("Stats scraped from FanGraphs | Built with ❤️ + 🐍 | App by Christian Mack")
    
    columns_to_display = [
        "player_name", "TeamName", "aLevel", "Age", "GS", "IP", "W", "L", "SO", 
        "ERA", "WHIP", "FIP", "K/9", "K%", "BB%", "K-BB%", "BABIP", "LOB%"
    ]
    
    renamed_columns = {
        "player_name": "Name",
        "TeamName": "Team",
        "aLevel": "Level"
    }
    
    # Display leaderboard
    st.dataframe(
        df.sort_values("FIP", ascending=True).reset_index(drop=True)[columns_to_display].rename(columns=renamed_columns),
        use_container_width=True
    )

# === Main App ===
def main():
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🧢 Hitters Splits Leaderboard", 
        "⚾ Pitcher Splits Leaderboard",
        "📊 Full Season Hitting Leaderboard",
        "🎯 Full Season Pitching Leaderboard"
    ])
    
    with tab1:
        # Load and clean hitters splits data
        df = load_hitters_splits()
        df = clean_hitters_data(df)
        
        # Create filters
        filters = create_hitters_filters(df, "hitters_splits")
        
        # Apply filters
        filtered_df = apply_hitters_filters(df, filters)
        
        # Display
        display_hitters_leaderboard(filtered_df, "🧢 Minor League Hitters Splits Leaderboard")
    
    with tab2:
        # Load and clean pitchers splits data
        df = load_pitchers_splits()
        df = clean_pitchers_data(df)
        
        # Create filters
        filters = create_pitchers_filters(df, "pitchers_splits")
        
        # Apply filters
        filtered_df = apply_pitchers_filters(df, filters)
        
        # Display
        display_pitchers_leaderboard(filtered_df, "⚾ Minor League Pitcher Splits Leaderboard")
    
    with tab3:
        # Load and clean full season hitters data
        df = load_hitters_full_season()
        df = clean_hitters_data(df)
        
        # Create filters
        filters = create_hitters_filters(df, "hitters_full")
        
        # Apply filters
        filtered_df = apply_hitters_filters(df, filters)
        
        # Display
        display_hitters_leaderboard(filtered_df, "📊 Full Season Hitting Leaderboard")
    
    with tab4:
        # Load and clean full season pitchers data
        df = load_pitchers_full_season()
        df = clean_pitchers_data(df)
        
        # Create filters
        filters = create_pitchers_filters(df, "pitchers_full")
        
        # Apply filters
        filtered_df = apply_pitchers_filters(df, filters)
        
        # Display
        display_pitchers_leaderboard(filtered_df, "🎯 Full Season Pitching Leaderboard")

    # Tip jar in sidebar (appears on all tabs)
    st.sidebar.markdown("---")
    st.sidebar.markdown("💸 **Enjoying this app?** [Send a tip](https://coff.ee/christianmack)")

if __name__ == "__main__":
    main()
