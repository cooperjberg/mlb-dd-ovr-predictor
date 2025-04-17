# data_utils.py
from pybaseball import batting_stats
import pandas as pd

def get_player_data(name):
    try:
        stats_df = batting_stats(2024, qual=50)
        stats_df["Name"] = stats_df["Name"].str.strip()

        player_row = stats_df[stats_df["Name"].str.lower() == name.lower()]
        if player_row.empty:
            return None, None

        stats = player_row.iloc[0].to_dict()
        card_info = {
            "Speed": 75,  # placeholder until we add ShowZone
            "Fielding": 75,
        }
        return stats, card_info

    except Exception as e:
        print(f"Error: {e}")
        return None, None
