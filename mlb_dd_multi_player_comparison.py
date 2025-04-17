import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pybaseball import batting_stats, pitching_stats

st.set_page_config(page_title="MLB The Show OVR Predictor", layout="wide")
st.title("💎 Fresh Start - MLB The Show OVR Predictor")

@st.cache_data
def load_data():
    return batting_stats(2025), pitching_stats(2025)

@st.cache_data
def scrape_showzone(max_pages=2):
    base_url = "https://showzone.gg/players?page="
    cards = []
    for page in range(1, max_pages+1):
        url = f"{base_url}{page}"
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table")
        if not table:
            continue
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 6:
                continue
            name = cols[0].text.strip()
            try:
                ovr = int(cols[1].text.strip())
            except:
                ovr = None
            cards.append({
                "Name": name,
                "OVR": ovr,
                "Buy Now": cols[4].text.strip(),
                "Sell Now": cols[5].text.strip()
            })
    return pd.DataFrame(cards)

batting_df, pitching_df = load_data()
showzone_df = scrape_showzone()

def get_true_floor(name):
    row = showzone_df[showzone_df["Name"].str.casefold() == name.casefold()]
    if not row.empty and row.iloc[0]["OVR"]:
        return int(row.iloc[0]["OVR"])
    return 0

def hitter_score(row):
    try:
        avg = row.get("AVG", 0)
        iso = row.get("ISO", 0)
        k_pct = 1 - row.get("K%", 0)
        bb_pct = row.get("BB%", 0)
        score = avg * 0.25 + iso * 0.25 + k_pct * 0.25 + bb_pct * 0.25
        return score
    except:
        return 0

def pitcher_score(row):
    try:
        era = 1 - row.get("ERA", 5) / 5
        k9 = row.get("K/9", 0) / 15
        bb9 = 1 - row.get("BB/9", 0) / 5
        score = era * 0.4 + k9 * 0.35 + bb9 * 0.25
        return score
    except:
        return 0

def score_to_ovr(score, name):
    try:
        raw_ovr = 90 if score >= 0.85 else 85 if score >= 0.75 else 80 if score >= 0.6 else 75 if score >= 0.5 else 70
        floor = get_true_floor(name)
        return max(raw_ovr, floor)
    except:
        return 70

QS = {91:9000, 90:8000, 89:7000, 88:5500, 87:4500, 86:4000, 85:3000,
      84:1500, 83:1200, 82:900, 81:600, 80:400,
      79:150, 78:125, 77:100, 76:75, 75:50}

tab1 = st.tabs(["🎯 Predict One Player"])[0]

with tab1:
    st.subheader("🎯 Predict One Player")
    name = st.text_input("Enter a player name", value="Corbin Carroll")
    if name:
        found = False
        if "Name" in batting_df.columns and name in batting_df["Name"].values:
            row = batting_df[batting_df["Name"] == name].iloc[0]
            score = hitter_score(row)
            ovr = score_to_ovr(score, name)
            try:
                qs = QS.get(int(round(ovr)), 25)
            except:
                qs = 25
            st.success(f"{name} (Hitter)")
            st.metric("OVR", ovr)
            st.metric("QS Value", qs)
            found = True

        if "Name" in pitching_df.columns and name in pitching_df["Name"].values:
            row = pitching_df[pitching_df["Name"] == name].iloc[0]
            score = pitcher_score(row)
            ovr = score_to_ovr(score, name)
            try:
                qs = QS.get(int(round(ovr)), 25)
            except:
                qs = 25
            st.success(f"{name} (Pitcher)")
            st.metric("OVR", ovr)
            st.metric("QS Value", qs)
            found = True

        if not found:
            st.warning("Player not found.")
