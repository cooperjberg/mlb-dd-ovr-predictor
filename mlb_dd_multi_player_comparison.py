import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pybaseball import batting_stats, pitching_stats

st.set_page_config(page_title="Diamond Dynasty + SDS Floors", layout="wide")
st.title("💎 Diamond Dynasty OVR Tracker with SDS Tier Floors")

@st.cache_data
def load_data():
    return batting_stats(2025), pitching_stats(2025)

@st.cache_data
def scrape_showzone_cards(max_pages=2):
    base_url = "https://showzone.gg/players?page="
    all_cards = []
    for page in range(1, max_pages + 1):
        url = f"{base_url}{page}"
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        table = soup.find("table")
        if not table:
            continue
        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 6:
                continue
            name = cols[0].text.strip()
            ovr = cols[1].text.strip()
            tier = cols[2].text.strip()
            set_type = cols[3].text.strip()
            buy_now = cols[4].text.strip().replace(",", "").replace("Stubs", "").strip()
            sell_now = cols[5].text.strip().replace(",", "").replace("Stubs", "").strip()
            try:
                card = {
                    "Name": name,
                    "OVR": int(ovr),
                    "Tier": tier,
                    "Set": set_type,
                    "Buy Now": int(buy_now) if buy_now.isnumeric() else None,
                    "Sell Now": int(sell_now) if sell_now.isnumeric() else None
                }
                all_cards.append(card)
            except:
                continue
    return pd.DataFrame(all_cards)

batting_df, pitching_df = load_data()
showzone_df = scrape_showzone_cards()

# SDS tier floor overrides
tier_floors = {
    "Corbin Carroll": 80,
    "Luis Robert Jr.": 80,
    "Yordan Alvarez": 85,
    "Ronald Acuna Jr.": 90,
    "Shohei Ohtani": 90,
    "Juan Soto": 85,
    "Freddie Freeman": 85,
    "Aaron Judge": 90,
    "Mookie Betts": 85,
    "Corey Seager": 85,
    "Gerrit Cole": 85,
    "Zac Gallen": 80
}

def predict_ovr(score, player_name):
    if score >= 0.85: raw_ovr = 90
    elif score >= 0.75: raw_ovr = 85
    elif score >= 0.6: raw_ovr = 80
    elif score >= 0.5: raw_ovr = 75
    else: raw_ovr = 70
    return max(raw_ovr, tier_floors.get(player_name, 0))

def quick_sell_value(ovr):
    table = {
        91: 9000, 90: 8000, 89: 7000, 88: 5500, 87: 4500, 86: 4000, 85: 3000,
        84: 1500, 83: 1200, 82: 900, 81: 600, 80: 400,
        79: 150, 78: 125, 77: 100, 76: 75, 75: 50
    }
    return table.get(ovr, 25)

def hitter_score(row):
    try:
        vals = {
            "AVG": row.get("AVG", 0),
            "ISO": row.get("ISO", 0),
            "K%": 1 - row.get("K%", 0),
            "BB%": row.get("BB%", 0),
            "SLG": row.get("SLG", 0),
            "wOBA": row.get("wOBA", 0)
        }
        weights = {"AVG": 0.25, "ISO": 0.2, "K%": 0.15, "BB%": 0.1, "SLG": 0.15, "wOBA": 0.15}
        return sum(vals[k] * weights[k] for k in vals)
    except:
        return 0

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

tab1, tab2 = st.tabs(["🎯 Predict One Player", "📈 ShowZone Live Market"])

with tab1:
    st.subheader("🎯 Predict One Player (Stat + SDS Floor + Market)")
    search_name = st.text_input("Enter full player name (case sensitive)", value="Corbin Carroll")
    if search_name:
        found = False
        if search_name in pitching_df["Name"].values:
            row = pitching_df[pitching_df["Name"] == search_name].iloc[0]
            score = pitcher_score(row)
            ovr = predict_ovr(score, search_name)
            qs = quick_sell_value(ovr)
            st.success(f"{search_name} (Pitcher)")
            st.metric("ERA", round(row["ERA"], 2))
            st.metric("K/9", round(row["K/9"], 2))
            st.metric("BB/9", round(row["BB/9"], 2))
            st.metric("🔥 Projected OVR", ovr)
            st.metric("💰 QS Value", qs)
            found = True
        elif search_name in batting_df["Name"].values:
            row = batting_df[batting_df["Name"] == search_name].iloc[0]
            score = hitter_score(row)
            ovr = predict_ovr(score, search_name)
            qs = quick_sell_value(ovr)
            st.success(f"{search_name} (Hitter)")
            st.metric("AVG", round(row.get("AVG", 0), 3))
            st.metric("ISO", round(row.get("ISO", 0), 3))
            st.metric("K%", round(row.get("K%", 0), 3))
            st.metric("BB%", round(row.get("BB%", 0), 3))
            st.metric("🔥 Projected OVR", ovr)
            st.metric("💰 QS Value", qs)
            found = True
        sz_match = showzone_df[showzone_df["Name"].str.contains(search_name, case=False, na=False)]
        if not sz_match.empty:
            st.subheader("ShowZone Card Info")
            st.dataframe(sz_match.reset_index(drop=True), use_container_width=True)
        if not found and sz_match.empty:
            st.error("Player not found. Please check the spelling or try another.")

with tab2:
    st.subheader("📈 ShowZone Live Market")
    st.dataframe(showzone_df, use_container_width=True)
