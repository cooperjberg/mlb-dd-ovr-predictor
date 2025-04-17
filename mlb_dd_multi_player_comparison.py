
import streamlit as st
from pybaseball import batting_stats, pitching_stats
import pandas as pd

st.set_page_config(page_title="MLB The Show Ovr Comparison", layout="wide")
st.title("📊 Multi-Player Diamond Dynasty OVR Predictor")

# Load data (cached)
@st.cache_data
def load_data():
    return batting_stats(2025), pitching_stats(2025)

batting_df, pitching_df = load_data()

# Input box for multiple players
players_input = st.text_area("Enter player names (one per line):", value="Chris Bassitt\nCedric Mullins\nLogan Webb")

players = [name.strip() for name in players_input.splitlines() if name.strip()]

results = []

for player in players:
    if player in pitching_df["Name"].values:
        row = pitching_df[pitching_df["Name"] == player].iloc[0]
        score = 100*(1-row["H/9"]/10) + 200*(row["K/9"]/15) + 100*(1-row["BB/9"]/5) + 150*((row["FBv"]-85)/10) + 250*(1-row["ERA"]/5)
        if score >= 550:
            ovr = 91
        elif score >= 500:
            ovr = 87
        elif score >= 450:
            ovr = 83
        elif score >= 400:
            ovr = 79
        else:
            ovr = 74
        results.append({
            "Player": player,
            "Type": "Pitcher",
            "ERA": round(row["ERA"], 2),
            "K/9": round(row["K/9"], 2),
            "BB/9": round(row["BB/9"], 2),
            "H/9": round(row["H/9"], 2),
            "Velocity": round(row["FBv"], 1) if "FBv" in row else "N/A",
            "Projected OVR": ovr
        })
    elif player in batting_df["Name"].values:
        row = batting_df[batting_df["Name"] == player].iloc[0]
        score = 300*row["AVG"] + 250*row["ISO"] + 100*(1-row["K%"]) + 100*row["BB%"] + 150*row["AVG"]
        if score >= 350:
            ovr = 85
        elif score >= 325:
            ovr = 80
        elif score >= 300:
            ovr = 75
        elif score >= 275:
            ovr = 70
        else:
            ovr = 65
        results.append({
            "Player": player,
            "Type": "Hitter",
            "AVG": round(row["AVG"], 3),
            "ISO": round(row["ISO"], 3),
            "K%": round(row["K%"], 3),
            "BB%": round(row["BB%"], 3),
            "Projected OVR": ovr
        })
    else:
        results.append({"Player": player, "Type": "Not found", "Projected OVR": "N/A"})

# Convert to DataFrame and display
results_df = pd.DataFrame(results)
st.dataframe(results_df, use_container_width=True)
