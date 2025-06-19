import streamlit as st
import pandas as pd
import plotly.express as px

# === 1. Load Data ===
@st.cache_data(ttl=3600)
def load_data():
    url = "https://raw.githubusercontent.com/chrismack698/Minor-League-Rolling-Stats-Leaderboard/main/leaderboard_data.csv"
    return pd.read_csv(url)

df = load_data()

# === 2. Sidebar Filters ===
st.sidebar.header("📊 Filters")

# === Timeframe (Single Select with Friendly Labels) ===

# Mapping from internal keys to friendly labels
timeframe_label_map = {
    "last_7": "Last 7 Days",
    "last_15": "Last 15 Days",
    "last_30": "Last 30 Days",
    "last_45": "Last 45 Days"
}

# Only use available options in the dataset
available_timeframes = [tf for tf in timeframe_label_map if tf in df['timeframe'].unique()]
sorted_timeframes = sorted(available_timeframes, key=lambda x: int(x.split('_')[1]))  # Sort numerically

# Create display label list
display_labels = [timeframe_label_map[tf] for tf in sorted_timeframes]
selected_label = st.sidebar.selectbox("Timeframe", display_labels)

# Reverse map to get actual value
selected_timeframe = {v: k for k, v in timeframe_label_map.items()}[selected_label]

# Plate Appearances
min_pa = int(df.get("PA", pd.Series([0])).min())
max_pa = int(df.get("PA", pd.Series([100])).max())
pa_range = st.sidebar.slider("Plate Appearances (PA)", min_pa, max_pa, (min_pa, max_pa))

# Define minimum PAs to qualify per timeframe
qualification_thresholds = {
    "last_7": 15,
    "last_15": 30,
    "last_30": 50,
    "last_45": 75
}

qualified_only = st.sidebar.checkbox("Only show qualified hitters")

# Age
min_age = int(df['Age'].min())
max_age = int(df['Age'].max())
age_range = st.sidebar.slider("Age", min_age, max_age, (min_age, max_age))

# K%
k_filter = st.sidebar.slider("K%", 0.0, 100.0, (0.0, 100.0))

# BB%
bb_filter = st.sidebar.slider("BB%", 0.0, 100.0, (0.0, 100.0))

# Level
level_options = sorted(df['aLevel'].dropna().unique())
selected_levels = st.sidebar.multiselect("Level", level_options, default=level_options)

# === Player Name Filter ===
name_query = st.sidebar.text_input("Search by Player Name").strip().lower()

# === Tip Jar ===
st.sidebar.markdown("---")
st.sidebar.markdown("💸 **Enjoying this app?** [Send a tip](https://coff.ee/christianmack)")

# === 3. Preprocess Data Types ===
def clean_percentage(series):
    return pd.to_numeric(series.str.replace('%', '', regex=False), errors='coerce')

df['K%'] = clean_percentage(df['K%'])
df['BB%'] = clean_percentage(df['BB%'])
df['PA'] = pd.to_numeric(df['PA'], errors='coerce')
df['wRC+'] = pd.to_numeric(df['wRC+'], errors='coerce')
df['Age'] = pd.to_numeric(df['Age'], errors='coerce')
df['HR'] = pd.to_numeric(df['HR'], errors='coerce')

# === 4. Apply Filters ===

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

# === 5. Display Leaderboard ===
st.title("🧢 Minor League Leaderboard")
st.caption("Stats scraped from FanGraphs | Built with ❤️ + 🐍")
st.set_page_config(layout="wide")

columns_to_display = [
    "player_name", "TeamName", "aLevel", "Age", "AB", "PA", "2B", "3B", "HR",
    "R", "RBI", "SB", "K%", "BB%", "AVG", "OBP", "SLG", "OPS", "ISO", "wRC+", "wOBA", "BABIP"
]

renamed_columns = {
    "player_name": "Name",
    "TeamName": "Team",
    "aLevel": "Level"
}

# Display final filtered and sorted leaderboard
st.dataframe(
    filtered_df.sort_values("wRC+", ascending=False).reset_index(drop=True)[columns_to_display].rename(columns=renamed_columns),
    use_container_width=True
)

# Clean any missing values for plot columns
plot_df = filtered_df.dropna(subset=['K%', 'wRC+', 'HR'])

# Build bubble chart
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

