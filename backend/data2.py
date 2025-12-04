import pandas as pd

# 1. Load Data
df = pd.read_csv('backend/2025_LoL_esports_match_data_from_OraclesElixir.csv')

# 2. Filter for Players only (remove team stats)
df_clean = df[df['position'] != 'team'].copy()

print(f"Total Matches in dataset: {df_clean['gameid'].nunique()}")

# 3. Create Matchups (Self-Join)
# This aligns every player with their direct opponent (same game, same position)
matchups = pd.merge(
    df_clean, 
    df_clean, 
    on=['gameid', 'position'], 
    suffixes=('', '_opp')
)

# Filter out self-matches (Blue vs Blue)
matchups = matchups[matchups['teamid'] != matchups['teamid_opp']]

# 4. Calculate Advantage Metrics (Player - Opponent)
matchups['gold_diff_15'] = matchups['goldat15'] - matchups['goldat15_opp']
matchups['cs_diff_15'] = matchups['csat15'] - matchups['csat15_opp']
matchups['xp_diff_15'] = matchups['xpat15'] - matchups['xpat15_opp']

# --- Statistical Threshold Analysis ---
gold_std = matchups['gold_diff_15'].std()
cs_std = matchups['cs_diff_15'].std()
print(f"\n--- Counter Thresholds (Based on 1 Standard Deviation) ---")
print(f"Significant Gold Lead @ 15: > {gold_std:.0f} gold")
print(f"Significant CS Lead @ 15:   > {cs_std:.0f} CS")

# 5. Aggregate Stats per Matchup
# We group by Champion AND Position (because Top Azir != Mid Azir)
matchup_stats = matchups.groupby(['champion', 'position', 'champion_opp']).agg({
    'gameid': 'count',
    'result': 'mean',         # Win Rate
    'gold_diff_15': 'mean',
    'cs_diff_15': 'mean',
    'xp_diff_15': 'mean'
}).reset_index()

matchup_stats.rename(columns={
    'gameid': 'games', 
    'result': 'win_rate',
    'gold_diff_15': 'avg_gold_diff_15',
    'cs_diff_15': 'avg_cs_diff_15'
}, inplace=True)

# OPTIONAL: Filter for sample size (e.g., at least 5 games played)
# matchup_stats = matchup_stats[matchup_stats['games'] >= 5]

# 6. Generate "Adjacency List" Format for GraphRAG
# Creates a string like: "Ahri (WR:0.45, GD:-200); Sylas (WR:0.55, GD:+150)"
def format_matchups(group):
    lines = []
    for _, row in group.iterrows():
        # You can customize this text format for your LLM/GraphRAG
        lines.append(f"{row['champion_opp']} (WinRate: {row['win_rate']:.2f}, GoldDiff15: {row['avg_gold_diff_15']:.0f})")
    return "; ".join(lines)

adj_list = matchup_stats.groupby(['champion', 'position']).apply(format_matchups).reset_index(name='matchup_list')

# 7. Save Outputs
matchup_stats.to_csv('league_matchups_detailed.csv', index=False)
adj_list.to_csv('league_champion_adjacency.csv', index=False)

print("\nFiles Saved:")
print("1. league_matchups_detailed.csv (Rows: Champion -> Opponent with stats)")
print("2. league_champion_adjacency.csv (Rows: Champion -> List of all Opponents)")