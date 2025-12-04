import pandas as pd

# 1. Load the data
df = pd.read_csv('backend/2025_LoL_esports_match_data_from_OraclesElixir.csv')

# 2. Filter data
# Remove 'team' rows to focus on individual positions
df_clean = df[df['position'] != 'team'].copy()

# ---------------------------------------------------------
# PART A: General Champion Statistics
# ---------------------------------------------------------
general_stats = df_clean.groupby('champion').agg({
    'result': ['count', 'mean'],      # count = games played, mean = winrate
    'kills': 'mean',
    'deaths': 'mean',
    'assists': 'mean',
    'goldat15': 'mean'
}).reset_index()

# Rename columns for clarity
general_stats.columns = ['champion', 'games', 'win_rate', 'avg_kills', 'avg_deaths', 'avg_assists', 'avg_gold15']

# Calculate KDA: (K + A) / D (avoiding divide by zero)
general_stats['kda'] = (general_stats['avg_kills'] + general_stats['avg_assists']) / general_stats['avg_deaths'].replace(0, 1)

# Sort by most played
general_stats = general_stats.sort_values('games', ascending=False)

# ---------------------------------------------------------
# PART B: Champion Matchups (Counters)
# ---------------------------------------------------------
# Self-merge on Game ID and Position to pair players in the same lane
matchups = pd.merge(
    df_clean,
    df_clean,
    on=['gameid', 'position'],
    suffixes=('', '_opp') # Suffix for the opponent columns
)

# Filter out "Self" matches (rows matching with themselves)
# We ensure the team IDs are different to get the true opponent
matchups = matchups[matchups['teamid'] != matchups['teamid_opp']]

# Calculate Differences (Player - Opponent)
# Positive Gold Diff means the player is winning the lane
matchups['gold_diff_10'] = matchups['goldat10'] - matchups['goldat10_opp']
matchups['gold_diff_15'] = matchups['goldat15'] - matchups['goldat15_opp']
matchups['xp_diff_15'] = matchups['xpat15'] - matchups['xpat15_opp']
matchups['kill_diff'] = matchups['kills'] - matchups['kills_opp']

# Group by the specific matchup (e.g., Azir vs Orianna)
matchup_stats = matchups.groupby(['champion', 'champion_opp']).agg({
    'gameid': 'count',        # Number of times this matchup happened
    'result': 'mean',         # Winrate for the main champion in this matchup
    'gold_diff_10': 'mean',   # Avg Gold Lead at 10 min
    'gold_diff_15': 'mean',   # Avg Gold Lead at 15 min
    'xp_diff_15': 'mean',     # Avg XP Lead at 15 min
    'kills': 'mean',          # Avg Kills
    'deaths': 'mean',
    'assists': 'mean'
}).reset_index()

matchup_stats.rename(columns={'gameid': 'games', 'result': 'win_rate'}, inplace=True)

# ---------------------------------------------------------
# PART C: Inspecting Results
# ---------------------------------------------------------
# 1. View General Stats
print("--- Top 5 Champions by Play Rate ---")
print(general_stats.head(5).to_string(index=False))

# 2. View Specific Matchup (e.g., Azir vs Orianna)
print("\n--- Matchup ---")
target_matchup = matchup_stats[
    (matchup_stats['champion'] == 'Xayah') & 
    (matchup_stats['champion_opp'] == 'Caitlyn')
]
if not target_matchup.empty:
    print(target_matchup.to_string(index=False))
else:
    print("Matchup not found in dataset.")

# 3. Find "Hard Counters" (e.g., min 10 games, sorted by lowest Gold Diff)
# Note: For your full dataset, increase the games filter (e.g., > 20)
print("\n--- Strongest Counters (Lowest Gold Diff @ 15 for the player) ---")
strong_counters = matchup_stats[matchup_stats['games'] >= 20].sort_values('gold_diff_15', ascending=True)
print(strong_counters[['champion', 'champion_opp', 'games', 'gold_diff_15', 'win_rate']].head(5).to_string(index=False))