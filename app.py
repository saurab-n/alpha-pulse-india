import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go
import feedparser
import urllib.parse

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AlphaPulse V3 | Retail Investor Research & Peer Analyzer",
    layout="wide",
    page_icon="📊"
)

st.title("📊 AlphaPulse V3: Complete Retail Investor Research Portal")
st.caption("3–6M & 1–2Y Horizon Checklists • Promoter/FII/DII Shareholding • Automated Peer Comparison • Easy Financials • SEBI Broker Consensus")

# --- CURATED STOCKS & SECTOR PEER GROUPS ---
POPULAR_STOCKS = {
    "Reliance Industries (RELIANCE.NS)": "RELIANCE.NS",
    "TCS (TCS.NS)": "TCS.NS",
    "Infosys (INFY.NS)": "INFY.NS",
    "HDFC Bank (HDFCBANK.NS)": "HDFCBANK.NS",
    "ICICI Bank (ICICIBANK.NS)": "ICICIBANK.NS",
    "State Bank of India (SBIN.NS)": "SBIN.NS",
    "Tata Motors (TATAMOTORS.NS)": "TATAMOTORS.NS",
    "Mahindra & Mahindra (M&M.NS)": "M&M.NS",
    "ITC Limited (ITC.NS)": "ITC.NS",
    "Larsen & Toubro (LT.NS)": "LT.NS",
    "Sun Pharma (SUNPHARMA.NS)": "SUNPHARMA.NS",
    "Hindustan Aeronautics (HAL.NS)": "HAL.NS",
    "Bajaj Finance (BAJFINANCE.NS)": "BAJFINANCE.NS",
    "Bharti Airtel (BHARTIARTL.NS)": "BHARTIARTL.NS",
    "Zomato / Eternal (ZOMATO.NS)": "ZOMATO.NS",
    "Custom NSE Ticker (Type Any Stock Below)": "CUSTOM"
}

SECTOR_PEERS_MAP = {
    "Technology": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", "LTIM.NS"],
    "Financial Services": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS", "BAJFINANCE.NS"],
    "Consumer Cyclical": ["TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "BAJAJ-AUTO.NS", "TRENT.NS", "TITAN.NS"],
    "Consumer Defensive": ["ITC.NS", "HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS", "TATACONSUM.NS"],
    "Energy": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "COALINDIA.NS", "TATAPOWER.NS"],
    "Industrials": ["LT.NS", "HAL.NS", "BEL.NS", "SIEMENS.NS", "ABB.NS", "ADANIPORTS.NS"],
    "Healthcare": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "DIVISLAB.NS", "APOLLOHOSP.NS"],
    "Communication Services": ["BHARTIARTL.NS", "INDUSINDBK.NS", "IDEA.NS", "TATACOMM.NS"],
    "Basic Materials": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "ULTRACEMCO.NS", "GRASIM.NS"]
}

TOP_10_SEBI_BROKERS = [
    {"Firm": "Motilal Oswal Financial Services", "SEBI Reg No": "INH000000412", "Focus": "Earnings & Multibagger Growth"},
    {"Firm": "ICICI Securities (ICICI Direct)", "SEBI Reg No": "INH000000990", "Focus": "Techno-Funda & Institutional Picks"},
    {"Firm": "Kotak Institutional Equities", "SEBI Reg No": "INH000000586", "Focus": "Sector Valuation & Governance"},
    {"Firm": "HDFC Securities", "SEBI Reg No": "INH000002475", "Focus": "Core Portfolio Compounders"},
    {"Firm": "Prabhudas Lilladher", "SEBI Reg No": "INH000000271", "Focus": "3–6M Swing & Mid-Cap Research"},
    {"Firm": "Axis Securities", "SEBI Reg No": "INH000000297", "Focus": "Quarterly Results & Momentum Picks"},
    {"Firm": "Nuvama Institutional Equities", "SEBI Reg No": "INH000000172", "Focus": "Macro & Sector Rotation"},
    {"Firm": "Sharekhan by BNP Paribas", "SEBI Reg No": "INH000000303", "Focus": "Retail Swing & Value Picks"},
    {"Firm": "JM Financial Institutional", "SEBI Reg No": "INH000001196", "Focus": "Deep-Dive Fundamental Research"},
    {"Firm": "Emkay Global Financial Services", "SEBI Reg No": "INH000000354", "Focus": "Small/Mid-Cap Alpha Discovery"}
]

# --- SIDEBAR CONTROLS ---
st.sidebar.header("🔍 1. Select or Search Stock")
selected_label = st.sidebar.selectbox("Choose a Stock:", list(POPULAR_STOCKS.keys()))

if POPULAR_STOCKS[selected_label] == "CUSTOM":
    raw_ticker = st.sidebar.text_input("Type NSE Symbol (e.g. TATAPOWER, WIPRO, IRCTC, BEL):", "TATAPOWER").strip().upper()
    ticker = f"{raw_ticker}.NS" if (not raw_ticker.endswith((".NS", ".BO")) and len(raw_ticker) > 0) else raw_ticker
else:
    ticker = POPULAR_STOCKS[selected_label]

st.sidebar.divider()
st.sidebar.header("🛡️ 2. Capital & Risk Calculator")
capital = st.sidebar.number_input("Your Investment Capital (₹)", min_value=5000, value=100000, step=10000)
risk_pct = st.sidebar.slider("Max Risk Per Trade (%)", min_value=0.5, max_value=3.0, value=1.5, step=0.5)

# --- SAFE HELPER FUNCTIONS (PREVENTS NONE/TYPE ERRORS) ---
def to_crores(val):
    if pd.isna(val) or val is None:
        return None
    try:
        return round(float(val) / 1e7, 2)
    except Exception:
        return None

def fmt_price(val, curr="₹"):
    """Safely formats any price or target value without crashing if None."""
    if val is None or pd.isna(val):
        return "N/A (Not Covered)"
    try:
        return f"{curr}{float(val):,.2f}"
    except Exception:
        return "N/A"

@st.cache_data(ttl=900)
def load_stock_bundle(symbol):
    stock = yf.Ticker(symbol)
    try:
        info = stock.info or {}
    except Exception:
        info = {}
    hist = yf.download(symbol, period="2y", interval="1d", progress=False)
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)
    try:
        q_income = stock.quarterly_income_stmt
    except Exception:
        q_income = pd.DataFrame()
    return info, hist, q_income

@st.cache_data(ttl=1800)
def fetch_peer_comparison(main_ticker, sector_name):
    peer_list = SECTOR_PEERS_MAP.get(sector_name, ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ITC.NS"])
    if main_ticker not in peer_list:
        peer_list = [main_ticker] + peer_list[:5]
    rows = []
    for sym in peer_list:
        try:
            inf = yf.Ticker(sym).info or {}
            pe = inf.get("trailingPE")
            pb = inf.get("priceToBook")
            roe = inf.get("returnOnEquity")
            de = inf.get("debtToEquity")
            rev_g = inf.get("revenueGrowth")
            op_m = inf.get("operatingMargins")
            mcap = to_crores(inf.get("marketCap"))
            rows.append({
                "Ticker": sym.replace(".NS", ""),
                "Company": (inf.get("shortName") or sym)[:22],
                "Price (₹)": round(float(inf.get("currentPrice") or inf.get("regularMarketPrice") or 0), 1),
                "Market Cap (₹ Cr)": f"{mcap:,.0f}" if mcap else "N/A",
                "P/E Ratio": round(float(pe), 1) if pe else np.nan,
                "P/B Ratio": round(float(pb), 1) if pb else np.nan,
                "ROE (%)": round(float(roe) * 100, 1) if roe else np.nan,
                "Operating Margin (%)": round(float(op_m) * 100, 1) if op_m else np.nan,
                "YoY Sales Growth (%)": round(float(rev_g) * 100, 1) if rev_g else np.nan,
                "Debt/Equity (%)": round(float(de), 1) if de is not None else np.nan
            })
        except Exception:
            continue
    return pd.DataFrame(rows)

@st.cache_data(ttl=600)
def fetch_live_news(company_name, symbol, query_suffix="stock NSE"):
    clean_sym = symbol.replace(".NS", "").replace(".BO", "")
    search_query = f"{company_name} {clean_sym} {query_suffix}"
    encoded_query = urllib.parse.quote(search_query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(rss_url)
    articles = []
    for entry in feed.entries[:10]:
        articles.append({
            "title": entry.get("title", "No Title"),
            "link": entry.get("link", "#"),
            "published": entry.get("published", ""),
            "source": entry.get("source", {}).get("title", "Financial Media") if isinstance(entry.get("source"), dict) else "Financial News"
        })
    return articles

# --- LOAD DATA ---
with st.spinner(f"Running 360° Retail Investor Analysis on {ticker}..."):
    info, hist, q_income = load_stock_bundle(ticker)

company_name = info.get("longName") or info.get("shortName") or ticker.replace(".NS", "")
raw_price = info.get("currentPrice") or info.get("regularMarketPrice") or (float(hist['Close'].iloc[-1]) if not hist.empty else 0.0)
curr_price = float(raw_price) if raw_price else 0.0
sector_name = info.get("sector", "Industrials")
currency = "₹" if ticker.endswith((".NS", ".BO")) else "$"

# --- COMPUTE CORE SCORES FOR LAYER-1 TRAFFIC LIGHT BAR ---
pe_val = info.get("trailingPE")
roe_val = float(info.get("returnOnEquity") or 0.0) * 100
de_val = info.get("debtToEquity")
rev_g_val = float(info.get("revenueGrowth") or 0.0) * 100
insiders_pct = round(float(info.get("heldPercentInsiders") or 0.0) * 100, 2)
inst_pct = round(float(info.get("heldPercentInstitutions") or 0.0) * 100, 2)
public_pct = round(max(0.0, 100.0 - insiders_pct - inst_pct), 2)

# Technical calculations
if not hist.empty and len(hist) >= 200:
    close_s = hist['Close']
    ema20 = float(ta.trend.EMAIndicator(close_s, window=20).ema_indicator().iloc[-1])
    sma50 = float(ta.trend.SMAIndicator(close_s, window=50).sma_indicator().iloc[-1])
    sma200 = float(ta.trend.SMAIndicator(close_s, window=200).sma_indicator().iloc[-1])
    rsi14 = float(ta.momentum.RSIIndicator(close_s, window=14).rsi().iloc[-1])
    macd_l = float(ta.trend.MACD(close_s).macd().iloc[-1])
    macd_s = float(ta.trend.MACD(close_s).macd_signal().iloc[-1])
    atr14 = float(ta.volatility.AverageTrueRange(hist['High'], hist['Low'], close_s, window=14).average_true_range().iloc[-1])
    vol_surge = float(hist['Volume'].iloc[-1] / hist['Volume'].rolling(20).mean().iloc[-1])
    ret_3m = float((curr_price / float(close_s.iloc[-63]) - 1) * 100) if len(close_s) > 63 else 0.0
    ret_1y = float((curr_price / float(close_s.iloc[-250]) - 1) * 100) if len(close_s) > 250 else 0.0
else:
    ema20 = sma50 = sma200 = curr_price
    rsi14 = 50.0
    macd_l = macd_s = atr14 = 1.0
    vol_surge = 1.0
    ret_3m = ret_1y = 0.0

# 3-6M Score (Out of 5)
score_3_6m = sum([
    curr_price > sma50,
    curr_price > ema20,
    50 <= rsi14 <= 72,
    macd_l >= macd_s,
    rev_g_val > 8
])

# 1-2Y Score (Out of 5)
score_1_2y = sum([
    roe_val >= 15,
    (de_val is None or de_val < 75),
    rev_g_val >= 10,
    curr_price > sma200,
    (insiders_pct + inst_pct) >= 50
])

# ==============================================================================
# LAYER 1: 5-SECOND TRAFFIC-LIGHT SUMMARY BAR
# ==============================================================================
st.markdown(f"### ⚡ 5-Second Investor Scorecard: **{company_name}** (`{ticker}`)")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Current Share Price", fmt_price(curr_price, currency), f"{ret_3m:+.1f}% (3M Return)")
m2.metric("3–6 Month Swing Score", f"{score_3_6m}/5 Criteria", "🟢 Bullish Swing" if score_3_6m >= 4 else ("🟡 Watchlist" if score_3_6m == 3 else "🔴 Avoid Short-Term"))
m3.metric("1–2 Year Wealth Score", f"{score_1_2y}/5 Criteria", "🟢 High Conviction" if score_1_2y >= 4 else ("🟡 Moderate" if score_1_2y == 3 else "🔴 Weak Quality"))
m4.metric("Promoter + FII/DII Stake", f"{insiders_pct + inst_pct:.1f}%", "🟢 Strong Backing" if (insiders_pct + inst_pct) >= 55 else "🟡 High Retail Float")
m5.metric("Balance Sheet Risk", "Low Risk 🟢" if (de_val is None or de_val < 60) else "High Debt 🔴", f"D/E: {float(de_val):.1f}%" if de_val is not None else "Financial/Bank")

st.divider()

# ==============================================================================
# LAYER 2: 6 TASK-BASED STORY TABS
# ==============================================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🎯 1. 3–6M vs 1–2Y Picker",
    "🤝 2. Shareholding & Peer Comparison",
    "📘 3. Easy Balance Sheet & Quarterly Results",
    "🏛️ 4. Top 10 SEBI Analyst Consensus",
    "📈 5. Technical Chart & Action Levels",
    "📰 6. Live Stock News"
])

# ==============================================================================
# TAB 1: RETAIL INVESTOR'S 3-6 MONTH VS 1-2 YEAR DECISION ENGINE
# ==============================================================================
with tab1:
    st.subheader(f"🎯 Should You Buy {company_name} for 3–6 Months or 1–2 Years?")
    st.caption("Designed from a Retail Investor's perspective: combines technical entry timing with fundamental safety.")

    col_short, col_long = st.columns(2)

    with col_short:
        st.markdown("### ⚡ Horizon A: Short-to-Medium Term (3 to 6 Months)")
        st.markdown("*Goal: Capture a 15%–25% swing move driven by quarterly earnings momentum and institutional chart breakouts.*")
        st.info(f"**3–6 Month Verdict:** {'🟢 **FAVORABLE SWING SETUP**' if score_3_6m >= 4 else ('🟡 **WAIT FOR DIP OR BREAKOUT**' if score_3_6m == 3 else '🔴 **NOT READY FOR SHORT-TERM BUY**')} ({score_3_6m}/5 Passed)")

        st.markdown(f"""
        1. **Medium-Term Trend (Price vs 50 DMA `{fmt_price(sma50, currency)}`):** {'✅ **Passed** — Stock is trading above its 50-day average.' if curr_price > sma50 else '❌ **Failed** — Trading below 50-day average (weak medium-term trend).'}
        2. **Near-Term Momentum (Price vs 20 EMA `{fmt_price(ema20, currency)}`):** {'✅ **Passed** — Buyers are actively supporting the stock on dips.' if curr_price > ema20 else '❌ **Failed** — Short-term selling pressure active.'}
        3. **RSI Strength (`{rsi14:.1f}`):** {'✅ **Passed** — In the sweet spot (50–72) where big rallies happen.' if 50 <= rsi14 <= 72 else ('⚠️ **Overheated (>72)** — Wait for a 3-5% pullback before entering.' if rsi14 > 72 else '❌ **Weak Momentum (<50)** — Wait for buyers to return.')}
        4. **MACD Trend Signal:** {'✅ **Passed** — Bullish MACD alignment.' if macd_l >= macd_s else '❌ **Failed** — Bearish MACD crossover.'}
        5. **Quarterly Sales Catalyst (`{rev_g_val:+.1f}%` YoY):** {'✅ **Passed** — Positive revenue growth supports a 3–6 month re-rating.' if rev_g_val > 8 else '⚠️ **Slow Growth** — Lacks a strong earnings trigger.'}
        """)

        # 3-6 Month Position Sizing Box
        stop_3_6m = round(curr_price - (2.5 * atr14), 2)
        target_3_6m = round(curr_price + (5.5 * atr14), 2)
        risk_amt = capital * (risk_pct / 100.0)
        shares_to_buy = int(risk_amt // max(curr_price - stop_3_6m, 1.0)) if curr_price > 0 else 0
        upside_swing_pct = ((target_3_6m / curr_price) - 1) * 100 if curr_price > 0 else 0.0

        st.success(f"""
        **🛡️ Retail Investor Trade Plan (Based on ₹{capital:,.0f} Capital & {risk_pct}% Risk):**
        * **Ideal Entry Zone:** `{fmt_price(curr_price * 0.98, currency)}` to `{fmt_price(curr_price, currency)}`
        * **3–6 Month Stop-Loss (2.5x ATR):** `{fmt_price(stop_3_6m, currency)}` *(Maximum loss if wrong: ₹{risk_amt:,.0f})*
        * **3–6 Month Swing Target:** `{fmt_price(target_3_6m, currency)}` *(+{upside_swing_pct:.1f}% upside)*
        * **Recommended Quantity to Buy:** **{shares_to_buy} Shares** *(Total Investment: ₹{shares_to_buy * curr_price:,.0f})*
        """)

    with col_long:
        st.markdown("### 🏛️ Horizon B: Positional Wealth Builder (1 to 2 Years)")
        st.markdown("*Goal: Compound wealth by owning high-ROE, low-debt sector leaders backed by Promoters and Mutual Funds/FIIs.*")
        st.success(f"**1–2 Year Verdict:** {'🟢 **STRONG WEALTH COMPOUNDER**' if score_1_2y >= 4 else ('🟡 **HOLD / ACCUMULATE ON BIG DIPS**' if score_1_2y == 3 else '🔴 **AVOID FOR LONG-TERM CORE PORTFOLIO**')} ({score_1_2y}/5 Passed)")

        eps = info.get("trailingEps")
        bvps = info.get("bookValue")
        graham_num = round(float(np.sqrt(22.5 * float(eps) * float(bvps))), 2) if (eps and bvps and float(eps) > 0 and float(bvps) > 0) else None
        target_consensus = info.get("targetMeanPrice")

        st.markdown(f"""
        1. **Capital Efficiency (ROE = `{roe_val:.1f}%`):** {'✅ **Passed** — Beats the 15% institutional hurdle rate (far better than a 7% bank FD).' if roe_val >= 15 else '❌ **Failed** — ROE is below 15%.'}
        2. **Balance Sheet Safety (Debt/Equity = `{f"{float(de_val):.1f}%" if de_val is not None else "Bank/NBFC"}`):** {'✅ **Passed** — Low debt ensures the company survives market downturns.' if (de_val is None or de_val < 75) else '❌ **Failed** — High debt burden (>75% D/E).'}
        3. **Business Expansion (YoY Revenue Growth = `{rev_g_val:+.1f}%`):** {'✅ **Passed** — Double-digit top-line expansion.' if rev_g_val >= 10 else '⚠️ **Slowing Sales** — Revenue growth under 10%.'}
        4. **Structural Bull Trend (Price vs 200 DMA `{fmt_price(sma200, currency)}`):** {'✅ **Passed** — Trading above its 200-Day Moving Average.' if curr_price > sma200 else '⚠️ **Below 200 DMA** — In a long-term correction; accumulate slowly via SIP.'}
        5. **Promoter + Institutional Conviction (`{insiders_pct + inst_pct:.1f}%`):** {'✅ **Passed** — Over 50% of the company is locked with Promoters & FII/DIIs.' if (insiders_pct + inst_pct) >= 50 else '⚠️ **High Public Float** — Less institutional skin in the game.'}
        """)

        st.info(f"""
        **💎 1–2 Year Accumulation & Valuation Guide:**
        * **Best SIP / Dip Accumulation Zone (Near 200 DMA):** `{fmt_price(sma200 * 0.98, currency)}` to `{fmt_price(sma50, currency)}`
        * **Wall Street / Dalal Street 12M Mean Target:** `{fmt_price(target_consensus, currency)}`
        * **Benjamin Graham Intrinsic Value:** `{fmt_price(graham_num, currency)}` *(Classic value floor)*
        * **1-Year Past Return:** `{ret_1y:+.1f}%`
        """)

# ==============================================================================
# TAB 2: PROMOTER / FII / DII SHAREHOLDING & AUTOMATED PEER COMPARISON
# ==============================================================================
with tab2:
    st.subheader(f"🤝 Who Owns {company_name}? (Shareholding Pattern) & How Does It Compare to Rivals?")

    col_sh1, col_sh2 = st.columns([1, 1.15])

    with col_sh1:
        st.markdown("### 🥧 Promoter vs. Institutional (FII/DII) vs. Public Holding")
        fig_pie = go.Figure(data=[go.Pie(
            labels=["Promoters & Insiders", "Institutions (FII + DII / Mutual Funds)", "Retail & Public Shareholders"],
            values=[insiders_pct, inst_pct, public_pct],
            hole=0.45,
            marker=dict(colors=["#00CC96", "#636EFA", "#FFA15A"])
        )])
        fig_pie.update_layout(height=340, margin=dict(t=20, b=20, l=10, r=10), template="plotly_dark")
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_sh2:
        st.markdown("### 🗣️ Plain-English Shareholding Analysis for Beginners")
        st.markdown(f"""
        * **1. Promoters / Founders (`{insiders_pct}%`):**
          {'🟢 **High Skin in the Game:** The founders/promoters own a massive chunk of the company. When promoters own >45%, their personal wealth grows only when your stock price grows!' if insiders_pct >= 45 else ('🟡 **Moderate/Professional Ownership:** Typical for professionally managed giants (like ICICI Bank, ITC, or L&T) where ownership is spread across institutions.' if inst_pct >= 35 else '🔴 **Low Promoter Stake:** Both promoter and institutional ownership are low—proceed with caution.')}
        * **2. Smart Money — FIIs & Domestic Mutual Funds (`{inst_pct}%`):**
          {'🟢 **Strong Institutional Confidence:** Foreign Institutional Investors (FIIs) and Domestic Mutual Funds (DIIs) hold over 20% of the company. These fund managers employ forensic accountants to verify the company before buying.' if inst_pct >= 20 else '🟡 **Moderate Institutional Holding:** Fewer big mutual funds currently own this stock.'}
        * **3. Retail / General Public (`{public_pct}%`):**
          {'✅ **Controlled Retail Float:** Since big hands (Promoters + Institutions) hold most of the shares, supply in the market is tight.' if public_pct < 45 else '⚠️ **High Retail Ownership (>45%):** When too many small traders own a stock instead of promoters or mutual funds, the stock can fall sharply during market panics.'}
        """)

    st.divider()
    st.markdown(f"### ⚔️ Automated Sector Peer Comparison ({sector_name})")
    st.caption(f"Before buying `{ticker}`, a smart investor always checks if a competitor in the same sector offers higher ROE or a cheaper P/E ratio:")

    df_peers = fetch_peer_comparison(ticker, sector_name)
    if not df_peers.empty:
        sector_median_pe = df_peers["P/E Ratio"].median()
        sector_median_roe = df_peers["ROE (%)"].median()

        if pe_val and not pd.isna(sector_median_pe) and sector_median_pe > 0:
            diff_pct = ((float(pe_val) - sector_median_pe) / sector_median_pe) * 100
            if diff_pct < -5:
                val_verdict = f"🟢 **Undervalued vs. Peers:** `{company_name}` trades at a P/E of **{float(pe_val):.1f}x**, which is **{abs(diff_pct):.1f}% CHEAPER** than its sector peer median P/E of **{sector_median_pe:.1f}x**."
            elif diff_pct > 10:
                val_verdict = f"🟠 **Premium Valuation vs. Peers:** `{company_name}` trades at a P/E of **{float(pe_val):.1f}x**, which is **{diff_pct:.1f}% MORE EXPENSIVE** than its sector peer median P/E of **{sector_median_pe:.1f}x** (The market pays a premium if ROE `{roe_val:.1f}%` is higher than the peer median `{sector_median_roe:.1f}%`)."
            else:
                val_verdict = f"🟡 **Fairly Valued vs. Peers:** `{company_name}` trades at a P/E of **{float(pe_val):.1f}x**, right in line with the sector peer median P/E of **{sector_median_pe:.1f}x**."
            st.info(val_verdict)

        st.dataframe(df_peers, use_container_width=True, hide_index=True)

# ==============================================================================
# TAB 3: BEGINNER-FRIENDLY BALANCE SHEET & QUARTERLY RESULTS
# ==============================================================================
with tab3:
    st.subheader(f"📘 {company_name} — Balance Sheet & Quarterly Results in Plain English")
    col_q, col_b = st.columns(2)

    with col_q:
        st.markdown("### 🗓️ Latest Quarterly Results (3-Month Payslip)")
        if not q_income.empty and q_income.shape[1] >= 2:
            q_cols = q_income.columns[:4]
            rev_key = next((k for k in ["Total Revenue", "Operating Revenue"] if k in q_income.index), None)
            prof_key = next((k for k in ["Net Income", "Net Income Common Stockholders"] if k in q_income.index), None)
            op_key = next((k for k in ["Operating Income", "EBIT"] if k in q_income.index), None)

            if rev_key and prof_key:
                latest_q, prev_q = q_cols[0], q_cols[1]
                rev_now, rev_prev = to_crores(q_income.loc[rev_key, latest_q]), to_crores(q_income.loc[rev_key, prev_q])
                prof_now, prof_prev = to_crores(q_income.loc[prof_key, latest_q]), to_crores(q_income.loc[prof_key, prev_q])
                rev_chg = ((rev_now - rev_prev) / abs(rev_prev) * 100) if (rev_now and rev_prev and rev_prev != 0) else 0.0
                prof_chg = ((prof_now - prof_prev) / abs(prof_prev) * 100) if (prof_now and prof_prev and prof_prev != 0) else 0.0
                margin = (prof_now / rev_now * 100) if (rev_now and prof_now and rev_now > 0) else 0.0

                rev_now_str = f"{currency}{rev_now:,.1f} Crore" if rev_now is not None else "N/A"
                prof_now_str = f"{currency}{prof_now:,.1f} Crore" if prof_now is not None else "N/A"

                st.success(f"""
                **🗣️ 3-Month Payslip Translation ({latest_q.strftime('%b %Y')}):**
                * **Sales (Money Coming In):** **{rev_now_str}** ({'up 📈' if rev_chg >= 0 else 'down 📉'} **{rev_chg:.1f}%** vs previous quarter).
                * **Net Profit (Pure Take-Home Savings):** **{prof_now_str}** ({'up 📈' if prof_chg >= 0 else 'down 📉'} **{prof_chg:.1f}%** vs previous quarter).
                * **Profit Pocketed per ₹100 of Sales:** For every **₹100** of products sold, the company keeps **₹{margin:.1f}** in pure profit.
                """)

                q_table = []
                for c in q_cols:
                    q_table.append({
                        "Quarter": c.strftime("%b %Y"),
                        f"Sales ({currency} Cr)": to_crores(q_income.loc[rev_key, c]),
                        f"Operating Profit ({currency} Cr)": to_crores(q_income.loc[op_key, c]) if op_key else "N/A",
                        f"Net Profit ({currency} Cr)": to_crores(q_income.loc[prof_key, c])
                    })
                st.dataframe(pd.DataFrame(q_table), use_container_width=True, hide_index=True)
        else:
            st.info("Quarterly breakdown table not available from feed for this ticker.")

    with col_b:
        st.markdown("### 🏦 Balance Sheet (Company Locker vs. Bank Loans)")
        total_cash = to_crores(info.get("totalCash"))
        total_debt = to_crores(info.get("totalDebt"))
        if total_cash is not None and total_debt is not None:
            if total_cash >= total_debt:
                bs_msg = f"🟢 **Fortress Balance Sheet:** Cash in bank (**{currency}{total_cash:,.0f} Cr**) exceeds total borrowings (**{currency}{total_debt:,.0f} Cr**)."
            elif de_val is not None and de_val < 60:
                bs_msg = f"🟢 **Safe Loan Level:** Total Debt (**{currency}{total_debt:,.0f} Cr**) is well under control with a Debt-to-Equity ratio of `{float(de_val):.1f}%`."
            else:
                bs_msg = f"🟠 **Watch Debt Levels:** Total Debt (**{currency}{total_debt:,.0f} Cr**) is significantly higher than cash (**{currency}{total_cash:,.0f} Cr**)."
        else:
            bs_msg = "ℹ️ Standard corporate debt metrics do not apply to Banks/Financial institutions."

        st.info(f"**🗣️ Balance Sheet Verdict:** {bs_msg}")
        bs_df = pd.DataFrame([
            {"Item": "Cash & Bank Balance", "Figure": f"{currency}{total_cash:,.0f} Cr" if total_cash is not None else "N/A", "Beginner Meaning": "Liquid cash available for emergencies or expansion"},
            {"Item": "Total Debt (Loans)", "Figure": f"{currency}{total_debt:,.0f} Cr" if total_debt is not None else "N/A", "Beginner Meaning": "Money borrowed that must be repaid with interest"},
            {"Item": "Debt-to-Equity Ratio", "Figure": f"{float(de_val):.1f}%" if de_val is not None else "N/A", "Beginner Meaning": "Below 50% is very safe; over 100% is heavy debt"},
            {"Item": "Return on Equity (ROE)", "Figure": f"{roe_val:.1f}%", "Beginner Meaning": "Annual return generated on shareholder capital (>15% is strong)"}
        ])
        st.dataframe(bs_df, use_container_width=True, hide_index=True)

# ==============================================================================
# TAB 4: TOP 10 SEBI-REGISTERED ANALYST CONSENSUS & BROKER TARGETS
# ==============================================================================
with tab4:
    st.subheader(f"🏛️ Institutional Consensus & Top 10 SEBI-Registered Brokerage Research")
    num_an = info.get("numberOfAnalystOpinions") or 0
    rec = (info.get("recommendationKey") or "none").replace("_", " ").upper()
    t_mean = info.get("targetMeanPrice")
    t_high = info.get("targetHighPrice")
    t_low = info.get("targetLowPrice")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Analysts Covering Stock", f"{num_an} Analysts")
    k2.metric("Institutional Rating", rec)
    if t_mean and curr_price > 0:
        up_pct = ((float(t_mean) - curr_price) / curr_price) * 100
        k3.metric("Consensus 12M Target", fmt_price(t_mean, currency), f"{up_pct:+.1f}% Potential")
    else:
        k3.metric("Consensus 12M Target", "N/A")
    k4.metric("Target Range (High / Low)", f"{fmt_price(t_high, currency)} / {fmt_price(t_low, currency)}" if t_high else "N/A")

    st.divider()
    ca, cb = st.columns([1.1, 1])
    with ca:
        st.markdown("### 📰 Live Brokerage Research Calls (Motilal, ICICI Direct, Kotak, Axis, etc.)")
        b_news = fetch_live_news(company_name, ticker, query_suffix="target price buy hold Motilal ICICI Kotak Axis Prabhudas Nuvama")
        for item in b_news[:7]:
            st.markdown(f"- **[{item['title']}]({item['link']})**  \n  *{item['source']} • {item['published']}*")
    with cb:
        st.markdown("### 📋 Top 10 SEBI-Registered Research Houses Reference")
        st.dataframe(pd.DataFrame(TOP_10_SEBI_BROKERS), use_container_width=True, hide_index=True)

# ==============================================================================
# TAB 5: TECHNICAL CHART & SUPPORT/RESISTANCE ACTION LEVELS
# ==============================================================================
with tab5:
    st.subheader(f"📈 Interactive Price Chart & Key Action Levels ({ticker})")
    if not hist.empty:
        hist['EMA20'] = hist['Close'].ewm(span=20).mean()
        hist['SMA50'] = hist['Close'].rolling(50).mean()
        hist['SMA200'] = hist['Close'].rolling(200).mean()

        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name="Price"))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA20'], line=dict(color='orange', width=1.5), name="20 EMA (Short-Term)"))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA50'], line=dict(color='cyan', width=1.5), name="50 SMA (3-6M Trend)"))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA200'], line=dict(color='red', width=2.2), name="200 SMA (1-2Y Bull/Bear Line)"))
        fig.update_layout(height=520, xaxis_rangeslider_visible=False, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# TAB 6: LATEST LIVE STOCK NEWS
# ==============================================================================
with tab6:
    st.subheader(f"📰 Latest Financial News for {company_name}")
    n_list = fetch_live_news(company_name, ticker, query_suffix="share price NSE news results")
    for i, a in enumerate(n_list, 1):
        st.markdown(f"**{i}. [{a['title']}]({a['link']})**")
        st.caption(f"🗞️ {a['source']} | 🕒 {a['published']}")
        st.divider()

st.caption("⚠️ **SEBI Regulatory Disclaimer:** This tool is an automated educational stock screener and financial translator. It does not provide personalized investment advice. Consult a SEBI-registered Investment Adviser before investing.")
