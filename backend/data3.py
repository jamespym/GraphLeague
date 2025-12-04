import pandas as pd
import numpy as np

# 1. Load and Clean
df = pd.read_csv('backend/2025_LoL_esports_match_data_from_OraclesElixir.csv')
df = df[df['position'] != 'team'].copy()

# 2. Prepare Matchups (Self-Join)
matchups = pd.merge(
    df, df, 
    on=['gameid', 'position'], 
    suffixes=('', '_opp')
)
matchups = matchups[matchups['teamid'] != matchups['teamid_opp']]

# Calculate Metrics
matchups['gold_diff_15'] = matchups['goldat15'] - matchups['goldat15_opp']

# 3. Aggregate Matchup Stats
# Filter: You likely want to ignore matchups with very few games to reduce noise
matchup_stats = matchups.groupby(['champion', 'champion_opp', 'position']).agg({
    'gameid': 'count',
    'result': 'mean',
    'gold_diff_15': 'mean'
}).reset_index()

matchup_stats.rename(columns={'gameid': 'games', 'result': 'win_rate', 'gold_diff_15': 'avg_gold_diff'}, inplace=True)

# OPTIONAL: Filter for sample size (e.g., keep only matchups with > 10 games)
matchup_stats = matchup_stats[matchup_stats['games'] >= 10]

# --- 4. Define Threshold X ---
# We calculate X based on the dataset's volatility
std_dev = matchup_stats['avg_gold_diff'].std()
COUNTER_THRESHOLD = 500  # You can manually set this to 1000, or use std_dev * 1.0

print(f"Defining 'COUNTERS' as Gold Diff > {COUNTER_THRESHOLD}")

# --- 5. Build Edge List ---
edges = []

for _, row in matchup_stats.iterrows():
    source = row['champion']
    target = row['champion_opp']
    
    # EDGE TYPE 1: PLAYED_AGAINST (Base connectivity layer)
    # We add this for everyone so the graph is connected
    edges.append({
        'source': source,
        'target': target,
        'type': 'PLAYED_AGAINST',
        'lane': row['position'],
        'weight': row['games'],
        'gold_diff': row['avg_gold_diff'],
        'win_rate': row['win_rate']
    })
    
    # EDGE TYPE 2: COUNTERS (High signal layer)
    # Only add this if Source is stomping Target
    if row['avg_gold_diff'] > COUNTER_THRESHOLD:
        edges.append({
            'source': source,
            'target': target,
            'type': 'COUNTERS',
            'lane': row['position'],
            'weight': row['avg_gold_diff'], # Weight counter edges by severity of stomp
            'win_rate': row['win_rate']
        })

df_edges = pd.DataFrame(edges)

# --- 6. Build Node List ---
# Good to have properties on nodes (e.g., their main role, overall winrate)
node_stats = df.groupby('champion').agg({
    'result': 'mean', 
    'gameid': 'count',
    'position': lambda x: x.mode()[0] # Most played role
}).reset_index()
node_stats.columns = ['id', 'overall_winrate', 'total_games', 'main_role']
node_stats['label'] = 'Champion'

# --- 7. Export ---
df_edges.to_csv('graph_edges.csv', index=False)
node_stats.to_csv('graph_nodes.csv', index=False)

print("Graph generation complete.")
print(f"Nodes: {len(node_stats)}")
print(f"Edges: {len(df_edges)}")
print(df_edges.head())


import matplotlib.pyplot as plt

# 1. Generate the histogram
matchup_stats['win_rate'].hist()

# 2. Add labels and a title for clarity
plt.title('Distribution of Win Rates')
plt.xlabel('Win Rate')
plt.ylabel('Frequency')

# 3. Explicitly display the plot
plt.show()