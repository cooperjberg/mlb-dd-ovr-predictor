import streamlit as st
from pybaseball import batting_stats, pitching_stats
import pandas as pd
import numpy as np

st.set_page_config(page_title="Diamond Dynasty OVR Predictor", layout="wide")

st.title("💎 Diamond Dynasty OVR Predictor with Investment Tracking")

@st.cache_data
def load_data():
    return batting_stats(2025), pitching_stats(2025)

batting_df, pitching_df = load_data()

# Session state for investment tracking
if "investments" not in st.session_state:
    st.session_state.investments = []

def predict_ovr(score):
    if score >= 0.85: return 90
    elif score >= 0.75: return 85
    elif score >= 0.6: return 80
    elif score >= 0.5: return 75
    else: return 70

def quick_sell_value(ovr):
    table = {
        91: 9000, 90: 8000, 89: 7000, 88: 5500, 87: 4500, 86: 4000, 85: 3000,
        84: 1500, 83: 1200, 82: 900, 81: 600, 80: 400,
        79: 150, 78: 125, 77: 100, 76: 75, 75: 50
    }
    return table.get(ovr, 25)

def hitter_score(row):
    vals = {
        "AVG": row["AVG"],
        "ISO": row["ISO"],
        "K%": 1 - row["K%"],
        "BB%": row["BB%"],
        "SLG": row["SLG"],
        "wOBA": row["wOBA"]
    }
    weights = {"AVG": 0.25, "ISO": 0.2, "K%": 0.15, "BB%": 0.1, "SLG": 0.15, "wOBA": 0.15}
    return sum(vals[k] * weights[k] for k in vals)

def pitcher_score(row):
    vals = {
        "ERA": 1 - row["ERA"] / 5,
        "K/9": row["K/9"] / 15,
        "BB/9": 1 - row["BB/9"] / 5,
        "H/9": 1 - row["H/9"] / 10,
        "FIP": 1 - row.get("FIP", row["ERA"]) / 5,
        "FBv": (row.get("FBv", 90) - 85) / 10
    }
    weights = {"ERA": 0.25, "K/9": 0.2, "BB/9": 0.15, "H/9": 0.15, "FIP": 0.15, "FBv": 0.1}
    return sum(vals[k] * weights[k] for k in vals)

tab1, tab2 = st.tabs(["📈 Leaderboard", "💸 Investment Tracker"])

with tab1:
    st.subheader("🏆 Best Value Buy Leaderboard")
    df_hitters = batting_df.copy()
    df_hitters = df_hitters[df_hitters["PA"] > 30]
    df_hitters = df_hitters[df_hitters.columns.intersection(["Name", "Team", "AVG", "ISO", "K%", "BB%", "SLG", "wOBA"])]
    df_hitters["Score"] = df_hitters.apply(hitter_score, axis=1)
    df_hitters["Projected OVR"] = df_hitters["Score"].apply(predict_ovr)
    df_hitters["QS Value"] = df_hitters["Projected OVR"].apply(quick_sell_value)
    df_hitters["Type"] = "Hitter"

    df_pitchers = pitching_df.copy()
    df_pitchers = df_pitchers[df_pitchers["IP"] > 5]
    df_pitchers["Score"] = df_pitchers.apply(pitcher_score, axis=1)
    df_pitchers["Projected OVR"] = df_pitchers["Score"].apply(predict_ovr)
    df_pitchers["QS Value"] = df_pitchers["Projected OVR"].apply(quick_sell_value)
    df_pitchers["Type"] = "Pitcher"

    full_df = pd.concat([df_hitters[["Name", "Team", "Projected OVR", "QS Value", "Type"]],
                         df_pitchers[["Name", "Team", "Projected OVR", "QS Value", "Type"]]])

    best_value = full_df[full_df["Projected OVR"] >= 80].sort_values(by="QS Value", ascending=False)
    st.dataframe(best_value.head(20), use_container_width=True)

with tab2:
    st.subheader("📊 Track Your Investments (Session Only)")
    with st.form("investment_form"):
        name = st.text_input("Player Name")
        buy_price = st.number_input("Buy Price (stubs)", min_value=0, value=0)
        projected_ovr = st.number_input("Projected OVR", min_value=65, max_value=99, value=75)
        submit = st.form_submit_button("Add Investment")
        if submit:
            qs_val = quick_sell_value(projected_ovr)
            profit = qs_val - buy_price
            st.session_state.investments.append({
                "Player": name,
                "Buy Price": buy_price,
                "Projected OVR": projected_ovr,
                "QS Value": qs_val,
                "Estimated Profit": profit
            })

    if st.session_state.investments:
        inv_df = pd.DataFrame(st.session_state.investments)
        st.dataframe(inv_df.sort_values(by="Estimated Profit", ascending=False), use_container_width=True)
