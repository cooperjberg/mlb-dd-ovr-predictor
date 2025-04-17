
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pybaseball import batting_stats, pitching_stats

st.set_page_config(page_title="Diamond Dynasty Elite Predictor", layout="wide")
st.title("💎 Elite MLB The Show OVR Predictor (Attribute-Based)")

@st.cache_data
def load_data():
    # Load season stats
    return batting_stats(2025), pitching_stats(2025)

@st.cache_data
def scrape_showzone(max_pages=2):
    # Scrape ShowZone.gg for live market data and true OVR floors
    cards = []
    for page in range(1, max_pages+1):
        url = f"https://showzone.gg/players?page={page}"
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table")
        if not table:
            break
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 6:
                continue
            name = cols[0].text.strip()
            try:
                true_ovr = int(cols[1].text.strip())
            except:
                true_ovr = None
            tier = cols[2].text.strip()
            buy = cols[4].text.strip().replace(",", "").replace("Stubs", "").strip()
            sell = cols[5].text.strip().replace(",", "").replace("Stubs", "").strip()
            buy = int(buy) if buy.isnumeric() else None
            sell = int(sell) if sell.isnumeric() else None
            cards.append({"Name": name, "TrueOVR": true_ovr, "Tier": tier,
                          "BuyNow": buy, "SellNow": sell})
    return pd.DataFrame(cards)

batting_df, pitching_df = load_data()
showzone_df = scrape_showzone()

# Helper: get ShowZone true OVR floor
def get_true_floor(name):
    match = showzone_df[showzone_df["Name"].str.casefold() == name.casefold()]
    if not match.empty and match.iloc[0]["TrueOVR"]:
        return match.iloc[0]["TrueOVR"]
    return 0

# Core attribute-based scoring
def hitter_score_attr(row):
    # Placeholder for splits: use overall values
    c_r = row.get("AVG", 0)      # Contact vs RHP
    c_l = row.get("AVG", 0)      # Contact vs LHP
    p_r = row.get("ISO", 0)      # Power vs RHP
    p_l = row.get("ISO", 0)      # Power vs LHP
    vision = 1 - row.get("K%", 0)
    discipline = row.get("BB%", 0)
    clutch = row.get("AVG", 0)   # w/ RISP not available
    # Simple boosts (if known)
    speed = row.get("Sprint Speed", 0) / 30  # normalize to 0–1
    defense = row.get("OAA", 0) / 10        # placeholder
    # Weighted sum
    weights = {
        "c_r": 0.12, "c_l": 0.08,
        "p_r": 0.12, "p_l": 0.08,
        "vision": 0.10, "discipline": 0.05,
        "clutch": 0.05,
        "speed": 0.20, "defense": 0.20
    }
    score = (c_r * weights["c_r"] + c_l * weights["c_l"] +
             p_r * weights["p_r"] + p_l * weights["p_l"] +
             vision * weights["vision"] + discipline * weights["discipline"] +
             clutch * weights["clutch"] + speed * weights["speed"] +
             defense * weights["defense"])
    return score

def pitcher_score_attr(row):
    h9 = max(0, 1 - row.get("H/9", 0)/10)
    k9 = row.get("K/9", 0)/15
    bb9 = max(0, 1 - row.get("BB/9", 0)/5)
    hr9 = max(0, 1 - row.get("HR/9", 0)/3)  # assume max 3 HR/9
    velo = (row.get("FBv", 90) - 85)/15
    control = max(0, 1 - row.get("BB/9", 0)/5)
    # FIP for clutch
    fip = max(0, 1 - row.get("FIP", row.get("ERA",5))/5)
    # Weighted sum
    weights = {
        "h9":0.15, "k9":0.20, "bb9":0.10, "hr9":0.10,
        "velo":0.15, "control":0.15, "fip":0.15
    }
    score = (h9*weights["h9"] + k9*weights["k9"] + bb9*weights["bb9"] +
             hr9*weights["hr9"] + velo*weights["velo"] +
             control*weights["control"] + fip*weights["fip"])
    return score

# Convert score to OVR tiers
def score_to_ovr(score, name):
    raw_ovr = 90 if score>=0.85 else 85 if score>=0.75 else 80 if score>=0.6 else 75 if score>=0.5 else 70
    floor = get_true_floor(name)
    return max(raw_ovr, floor)

# Quick sell lookup
QS = {91:9000,90:8000,89:7000,88:5500,87:4500,86:4000,85:3000,
      84:1500,83:1200,82:900,81:600,80:400,79:150,78:125,77:100,76:75,75:50}

# Tabs
tab1, tab2, tab3 = st.tabs(["🎯 Predict One Player", "📈 ShowZone Market", "🔍 Bulk Predict"])

with tab1:
    st.subheader("🎯 Predict One Player")
    name = st.text_input("Player Name", value="Corbin Carroll")
    if name:
        found = False
        # Hitter?
        if name in batting_df["Name"].values:
            row = batting_df[batting_df["Name"]==name].iloc[0]
            # Borrow speed/OAA if available in df
            row["Sprint Speed"] = row.get("Sprint Speed", 29.5)  # placeholder
            row["OAA"] = row.get("OAA", 5)  # placeholder
            score = hitter_score_attr(row)
            ovr = score_to_ovr(score, name)
            try:
        ovr_key = int(round(float(ovr)))
    except:
        ovr_key = 0
    qs = QS.get(ovr_key, 25)
            st.success(f"{name} (Hitter)")
            st.write({
                "Contact RHP": round(row["AVG"],3), "Contact LHP":round(row["AVG"],3),
                "Power RHP": round(row["ISO"],3), "Power LHP": round(row["ISO"],3),
                "Vision": round(1-row["K%"],3), "Discipline": round(row["BB%"],3),
                "Clutch": round(row["AVG"],3), "Speed": row["Sprint Speed"],
                "Fielding (OAA)": row["OAA"]
            })
            st.metric("🔥 Predicted OVR", ovr)
            st.metric("💰 Quick Sell", qs)
            found = True
        # Pitcher?
        if "Name" in pitching_df.columns and name in pitching_df["Name"].values:
            row = pitching_df[pitching_df["Name"]==name].iloc[0]
            score = pitcher_score_attr(row)
            ovr = score_to_ovr(score, name)
            try:
        ovr_key = int(round(float(ovr)))
    except:
        ovr_key = 0
    qs = QS.get(ovr_key, 25)
            st.success(f"{name} (Pitcher)")
            st.write({
                "H/9":round(row["H/9"],2), "K/9":round(row["K/9"],2),
                "BB/9":round(row["BB/9"],2), "HR/9": round(row.get("HR/9",0),2),
                "Velocity":round(row.get("FBv",0),1),
                "Control (1-BB/9)": round(max(0,1-row["BB/9"]/5),2),
                "FIP Component": round(max(0,1-row.get("FIP",row["ERA"])/5),2)
            })
            st.metric("🔥 Predicted OVR", ovr)
            st.metric("💰 Quick Sell", qs)
            found = True
        # ShowZone info
        sz = showzone_df[showzone_df["Name"].str.casefold()==name.casefold()]
        if not sz.empty:
            st.subheader("ShowZone Card Info")
            st.dataframe(sz, use_container_width=True)
        if not found and sz.empty:
            st.error("Player not found.")

with tab2:
    st.subheader("📈 ShowZone Live Market")
    st.dataframe(showzone_df, use_container_width=True)

with tab3:
    st.subheader("🔍 Bulk Predict")
    # Example bulk predict for top 50 hitters and pitchers
    hitters = batting_df[batting_df["PA"]>30].copy()
    hitters["Score"] = hitters.apply(hitter_score_attr, axis=1)
    hitters["OVR"] = hitters.apply(lambda r: score_to_ovr(r["Score"], r["Name"]), axis=1)
    pitchers = pitching_df[pitching_df["IP"]>10].copy()
    pitchers["Score"] = pitchers.apply(pitcher_score_attr, axis=1)
    pitchers["OVR"] = pitchers.apply(lambda r: score_to_ovr(r["Score"], r["Name"]), axis=1)
    bulk = pd.concat([
        hitters[["Name","Team","OVR"]].assign(Type="Hitter"),
        pitchers[["Name","Team","OVR"]].assign(Type="Pitcher")
    ])
    st.dataframe(bulk.sort_values("OVR", ascending=False).head(100), use_container_width=True)
