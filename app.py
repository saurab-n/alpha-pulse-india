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
    page_title="AlphaPulse Pro | Stock Research, News & Plain-English Financials",
    layout="wide",
    page_icon="📈"
)

st.title("📈 AlphaPulse Pro: Complete Stock Research & Beginner's Financial Guide")
st.caption("Live Stock News • SEBI-Registered Broker Consensus • Plain-English Balance Sheet & Quarterly Results • Short & Long-Term Technicals")

# --- POPULAR STOCK SEARCH DICTIONARY ---
POPULAR_STOCKS = {
    "Reliance Industries (RELIANCE.NS)": "RELIANCE.NS",
    "TCS (TCS.NS)": "TCS.NS",
    "HDFC Bank (HDFCBANK.NS)": "HDFCBANK.NS",
    "Infosys (INFY.NS)": "INFY.NS",
    "ICICI Bank (ICICIBANK.NS)": "ICICIBANK.NS",
    "State Bank of India (SBIN.NS)": "SBIN.NS",
    "Bharti Airtel (BHARTIARTL.NS)": "BHARTIARTL.NS",
    "Larsen & Toubro (LT.NS)": "LT.NS",
    "ITC Limited (ITC.NS)": "ITC.NS",
    "Tata Motors (TATAMOTORS.NS)": "TATAMOTORS.NS",
    "Mahindra & Mahindra (M&M.NS)": "M&M.NS",
    "Hindustan Aeronautics (HAL.NS)": "HAL.NS",
    "Zomato / Eternal (ZOMATO.NS)": "ZOMATO.NS",
    "Bajaj Finance (BAJFINANCE.NS)": "BAJFINANCE.NS",
    "Sun Pharma (SUNPHARMA.NS)": "SUNPHARMA.NS",
    "Custom Ticker (Type Any Stock Below)": "CUSTOM"
}

# --- TOP 10 SEBI-REGISTERED INSTITUTIONAL RESEARCH HOUSES REFERENCE ---
TOP_10_SEBI_BROKERS = [
    {"Firm": "Motilal Oswal Financial Services", "SEBI Reg No": "INH000000412", "Specialty": "Fundamental & Earnings Growth"},
    {"Firm": "ICICI Securities (ICICI Direct)", "SEBI Reg No": "INH000000990", "Specialty": "Institutional Fundamental & Techno-Funda Picks"},
    {"Firm": "Kotak Institutional Equities", "SEBI Reg No": "INH000000586", "Specialty": "Deep-Dive Sector & Large-Cap Valuation"},
    {"Firm": "HDFC Securities", "SEBI Reg No": "INH000002475", "Specialty": "Retail & Long-Term Wealth Compounders"},
    {"Firm": "Prabhudas Lilladher", "SEBI Reg No": "INH000000271", "Specialty": "Technical Breakouts & Mid-Cap Fundamentals"},
    {"Firm": "Axis Securities", "SEBI Reg No": "INH000000297", "Specialty": "Short-Term Momentum & Quarterly Earnings Plays"},
    {"Firm": "Nuvama Institutional Equities (Edelweiss)", "SEBI Reg No": "INH000000172", "Specialty": "Macro, Mid-Cap & Derivatives Strategy"},
    {"Firm": "Sharekhan by BNP Paribas", "SEBI Reg No": "INH000000303", "Specialty": "Swing Trading & Value Investing"},
    {"Firm": "JM Financial Institutional Securities", "SEBI Reg No": "INH000001196", "Specialty": "Corporate Actions & Institutional Research"},
    {"Firm": "Emkay Global Financial Services", "SEBI Reg No": "INH000000354", "Specialty": "Small/Mid-Cap Discovery & Sector Rotation"}
]

# --- SIDEBAR: SEARCH ANY STOCK ---
st.sidebar.header("🔍 Search Any Stock")
selected_label = st.sidebar.selectbox("Pick a Popular Stock:", list(POPULAR_STOCKS.keys()))

if POPULAR_STOCKS[selected_label] == "CUSTOM":
    raw_ticker = st.sidebar.text_input("Enter NSE Symbol (e.g. TATAPOWER, WIPRO, IRCTC):", "TATAPOWER").strip().upper()
    if not raw_ticker.endswith(".NS") and not raw_ticker.endswith(".BO") and len(raw_ticker) > 0:
        ticker = f"{raw_ticker}.NS"
    else:
        ticker = raw_ticker
else:
    ticker = POPULAR_STOCKS[selected_label]

st.sidebar.info(f"**Currently Analyzing:** `{ticker}`")

# --- HELPER: FORMAT INDIAN CRORES ---
def to_crores(val):
    if pd.isna(val) or val is None:
        return None
    return round(float(val) / 1e7, 2)  # 1 Crore = 10,000,000

# --- DATA LOADER ---
@st.cache_data(ttl=900)
def load_stock_bundle(symbol):
    stock = yf.Ticker(symbol)
    info = stock.info
    hist = yf.download(symbol, period="2y", interval="1d", progress=False)
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)
    
    try:
        q_income = stock.quarterly_income_stmt
    except Exception:
        q_income = pd.DataFrame()
        
    try:
        balance_sheet = stock.balance_sheet
    except Exception:
        balance_sheet = pd.DataFrame()

    return info, hist, q_income, balance_sheet

# --- NEWS LOADER (GOOGLE NEWS RSS FOR INDIA STOCKS) ---
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

# Load Data
with st.spinner(f"Fetching live market data, financial statements, and news for {ticker}..."):
    info, hist, q_income, balance_sheet = load_stock_bundle(ticker)

company_name = info.get("longName") or info.get("shortName") or ticker.replace(".NS", "")
curr_price = info.get("currentPrice") or info.get("regularMarketPrice") or (float(hist['Close'].iloc[-1]) if not hist.empty else 0)
currency = "₹" if ticker.endswith((".NS", ".BO")) else "$"

# --- TOP SUMMARY BANNER ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Company Name", company_name)
col2.metric("Current Share Price", f"{currency}{curr_price:,.2f}" if curr_price else "N/A")
col3.metric("52-Week High / Low", f"{currency}{info.get('fiftyTwoWeekHigh', 'N/A')} / {currency}{info.get('fiftyTwoWeekLow', 'N/A')}")
col4.metric("Sector", info.get("sector", "N/A"))

st.divider()

# --- 4 MAIN FEATURE TABS ---
tab_easy, tab_analysts, tab_tech, tab_news = st.tabs([
    "📘 1. Easy Balance Sheet & Quarterly Results (Beginner Guide)",
    "🏛️ 2. Top 10 SEBI Analyst Consensus & Targets",
    "📈 3. Short-Term & Long-Term Technical Analysis",
    "📰 4. Latest Live Stock News"
])

# ==============================================================================
# TAB 1: BEGINNER-FRIENDLY BALANCE SHEET & QUARTERLY RESULTS
# ==============================================================================
with tab_easy:
    st.subheader(f"📘 {company_name} — Financial Health Explained Like a Household Budget")
    st.markdown("""
    **New to stock investing?** Don't worry about complex accounting jargon. Think of a company just like a family household:
    * **Quarterly Results (Income Statement)** = The family's **Monthly Salary Payslip** (How much money came in over the last 3 months, and how much was left over after paying bills).
    * **Balance Sheet** = The family's **Net Worth Statement** (How much cash and property they own inside their bank locker vs. how much bank loan they have to pay back).
    """)

    col_q, col_b = st.columns(2)

    # --- PART A: QUARTERLY RESULTS EXPLAINED ---
    with col_q:
        st.markdown("### 🗓️ Part 1: Latest Quarterly Results (3-Month Payslip)")
        if not q_income.empty and q_income.shape[1] >= 2:
            # Extract latest two quarters
            q_cols = q_income.columns[:4]
            df_q_clean = pd.DataFrame()

            rev_key = next((k for k in ["Total Revenue", "Operating Revenue"] if k in q_income.index), None)
            prof_key = next((k for k in ["Net Income", "Net Income Common Stockholders"] if k in q_income.index), None)
            op_key = next((k for k in ["Operating Income", "EBIT"] if k in q_income.index), None)

            if rev_key and prof_key:
                latest_q = q_cols[0]
                prev_q = q_cols[1]

                rev_now = to_crores(q_income.loc[rev_key, latest_q])
                rev_prev = to_crores(q_income.loc[rev_key, prev_q])
                prof_now = to_crores(q_income.loc[prof_key, latest_q])
                prof_prev = to_crores(q_income.loc[prof_key, prev_q])

                rev_change = ((rev_now - rev_prev) / abs(rev_prev) * 100) if (rev_now and rev_prev) else 0
                prof_change = ((prof_now - prof_prev) / abs(prof_prev) * 100) if (prof_now and prof_prev) else 0
                profit_margin = (prof_now / rev_now * 100) if (rev_now and prof_now and rev_now > 0) else 0

                st.success(f"""
                **🗣️ Plain-English Summary of Latest Quarter ({latest_q.strftime('%b %Y')}):**
                1. **Total Sales (Revenue):** The company sold **{currency}{rev_now:,.2f} Crore** worth of goods/services in these 3 months ({'up 📈' if rev_change >= 0 else 'down 📉'} **{rev_change:.1f}%** compared to the previous quarter).
                2. **Take-Home Profit (Net Profit):** After paying salaries, raw materials, interest, and taxes, the company kept **{currency}{prof_now:,.2f} Crore** in pure profit ({'up 📈' if prof_change >= 0 else 'down 📉'} **{prof_change:.1f}%** vs. last quarter).
                3. **Profit Efficiency:** For every **₹100** of sales this company makes, it keeps **₹{profit_margin:.1f}** as pure profit in its pocket.
                """)

                # Show clean table of last 4 quarters
                q_table = []
                for c in q_cols:
                    q_table.append({
                        "Quarter Ended": c.strftime("%b %Y"),
                        f"Sales / Revenue ({currency} Cr)": to_crores(q_income.loc[rev_key, c]),
                        f"Operating Profit ({currency} Cr)": to_crores(q_income.loc[op_key, c]) if op_key else "N/A",
                        f"Net Take-Home Profit ({currency} Cr)": to_crores(q_income.loc[prof_key, c])
                    })
                st.dataframe(pd.DataFrame(q_table), use_container_width=True, hide_index=True)
            else:
                st.info("Quarterly breakdown rows vary for this financial institution. Check key metrics below.")
        else:
            st.warning("Quarterly statement data is currently unavailable from the exchange feed for this ticker.")

    # --- PART B: BALANCE SHEET EXPLAINED ---
    with col_b:
        st.markdown("### 🏦 Part 2: Balance Sheet (Savings vs. Loans)")
        total_cash = to_crores(info.get("totalCash"))
        total_debt = to_crores(info.get("totalDebt"))
        de_ratio = info.get("debtToEquity")
        roe = info.get("returnOnEquity")
        current_ratio = info.get("currentRatio")

        # Plain-English translation
        if total_cash is not None and total_debt is not None:
            if total_cash >= total_debt:
                debt_story = f"🟢 **Debt-Free / Cash Rich Strength:** This company has **{currency}{total_cash:,.0f} Crore** in cash/bank balance, which is **MORE** than its total borrowings of **{currency}{total_debt:,.0f} Crore**. Just like a family that has more savings than home loans, it has very low bankruptcy risk."
            elif de_ratio and de_ratio < 50:
                debt_story = f"🟢 **Comfortable Loan Level:** The company has **{currency}{total_debt:,.0f} Crore** in loans and **{currency}{total_cash:,.0f} Crore** in cash. Its Debt-to-Equity ratio is `{de_ratio:.1f}%` (meaning less than ₹50 of loan for every ₹100 of its own money), which is healthy."
            else:
                debt_story = f"🟠 **High Debt Alert:** The company carries **{currency}{total_debt:,.0f} Crore** in loans compared to only **{currency}{total_cash:,.0f} Crore** in cash. High loans mean a big chunk of its quarterly profit goes toward paying bank interest."
        else:
            debt_story = "ℹ️ *Note: Banks and NBFCs use customer deposits as their raw material, so standard corporate debt ratios do not apply to them.*"

        roe_pct = round(roe * 100, 1) if roe else None
        if roe_pct:
            if roe_pct >= 15:
                roe_story = f"🟢 **Money-Compounding Machine (ROE = {roe_pct}%):** Return on Equity (ROE) measures how fast the company grows shareholders' money. Compare this to a **7% bank FD**—for every ₹100 invested inside the business, management generates **₹{roe_pct}** per year!"
            else:
                roe_story = f"🟡 **Moderate Efficiency (ROE = {roe_pct}%):** For every ₹100 of shareholder money inside the business, the company earns **₹{roe_pct}** per year (Ideally, long-term investors look for 15%+)."
        else:
            roe_story = "ℹ️ Return on Equity (ROE) data not reported in current feed."

        st.info(f"""
        **🗣️ Plain-English Balance Sheet Verdict:**
        * {debt_story}
        * {roe_story}
        """)

        bs_metrics = pd.DataFrame([
            {"Financial Term": "Cash in Bank (Total Cash)", "Value": f"{currency}{total_cash:,.0f} Cr" if total_cash else "N/A", "What It Means for a Beginner": "Emergency savings sitting in the company's bank account"},
            {"Financial Term": "Total Borrowings (Total Debt)", "Value": f"{currency}{total_debt:,.0f} Cr" if total_debt else "N/A", "What It Means for a Beginner": "Total bank loans & bonds the company must repay"},
            {"Financial Term": "Debt-to-Equity Ratio (%)", "Value": f"{round(de_ratio, 1)}%" if de_ratio is not None else "N/A", "What It Means for a Beginner": "Under 50% is safe; above 100% means heavy borrowing"},
            {"Financial Term": "Return on Equity (ROE %)", "Value": f"{roe_pct}%" if roe_pct else "N/A", "What It Means for a Beginner": "How much profit the company makes on ₹100 of shareholder money (15%+ is great)"},
            {"Financial Term": "P/E Ratio (Valuation)", "Value": f"{round(info.get('trailingPE', 0), 1)}x" if info.get('trailingPE') else "N/A", "What It Means for a Beginner": "How many rupees you pay today for ₹1 of the company's annual profit"}
        ])
        st.dataframe(bs_metrics, use_container_width=True, hide_index=True)

# ==============================================================================
# TAB 2: TOP 10 SEBI-REGISTERED ANALYST CONSENSUS & BROKER TARGETS
# ==============================================================================
with tab_analysts:
    st.subheader(f"🏛️ Institutional Analyst Consensus & SEBI-Registered Brokerage Coverage for {company_name}")

    num_analysts = info.get("numberOfAnalystOpinions", 0)
    rec_key = info.get("recommendationKey", "none").replace("_", " ").upper()
    target_mean = info.get("targetMeanPrice")
    target_high = info.get("targetHighPrice")
    target_low = info.get("targetLowPrice")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Institutional Analysts Tracking", f"{num_analysts} Analysts" if num_analysts else "N/A")
    c2.metric("Consensus Verdict", rec_key)
    if target_mean and curr_price:
        upside = ((target_mean - curr_price) / curr_price) * 100
        c3.metric("Average 12M Target Price", f"{currency}{target_mean:,.2f}", f"{upside:+.1f}% Upside/Downside")
    else:
        c3.metric("Average 12M Target Price", "N/A")
    c4.metric("Highest / Lowest Analyst Target", f"{currency}{target_high} / {currency}{target_low}" if target_high else "N/A")

    st.divider()
    col_a1, col_a2 = st.columns([1.1, 1])

    with col_a1:
        st.markdown("### 📰 Latest Published Broker Research Calls & Target Updates")
        st.caption("Live aggregation of public research calls from SEBI-registered brokerages (Motilal Oswal, ICICI Direct, Kotak, Axis, Prabhudas Lilladher, Nuvama, etc.):")
        broker_news = fetch_live_news(company_name, ticker, query_suffix="target price buy hold Motilal ICICI Kotak Axis Nuvama Prabhudas")
        if broker_news:
            for item in broker_news[:7]:
                st.markdown(f"- **[{item['title']}]({item['link']})**  \n  *Source: {item['source']} • {item['published']}*")
        else:
            st.info("No recent public brokerage target revisions found in the news feed this week.")

    with col_a2:
        st.markdown("### 📋 Top 10 SEBI-Registered Institutional Research Houses Directory")
        st.caption("Reference directory of India's top 10 SEBI-registered institutional research firms whose estimates form the market consensus:")
        st.dataframe(pd.DataFrame(TOP_10_SEBI_BROKERS), use_container_width=True, hide_index=True)

# ==============================================================================
# TAB 3: SHORT-TERM & LONG-TERM TECHNICAL ANALYSIS (ALGO + EXPERT RULES)
# ==============================================================================
with tab_tech:
    st.subheader(f"📈 Professional Technical Analysis Checklist: {company_name}")
    if not hist.empty and len(hist) >= 200:
        close = hist['Close']
        high = hist['High']
        low = hist['Low']
        vol = hist['Volume']

        # Calculate Technical Indicators used by SEBI CMT/Technical Analysts
        ema20 = float(ta.trend.EMAIndicator(close, window=20).ema_indicator().iloc[-1])
        sma50 = float(ta.trend.SMAIndicator(close, window=50).sma_indicator().iloc[-1])
        sma200 = float(ta.trend.SMAIndicator(close, window=200).sma_indicator().iloc[-1])
        rsi14 = float(ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1])
        macd_line = float(ta.trend.MACD(close).macd().iloc[-1])
        macd_sig = float(ta.trend.MACD(close).macd_signal().iloc[-1])
        atr14 = float(ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1])
        vol_ratio = float(vol.iloc[-1] / vol.rolling(20).mean().iloc[-1])

        support_20d = float(low.tail(20).min())
        resistance_20d = float(high.tail(20).max())

        col_st, col_lt = st.columns(2)

        with col_st:
            st.markdown("### ⚡ Short-Term Technical Analysis (1 to 4 Weeks Swing)")
            st_bullish_points = 0
            if curr_price > ema20: st_bullish_points += 1
            if 50 <= rsi14 <= 70: st_bullish_points += 1
            if macd_line > macd_sig: st_bullish_points += 1
            if vol_ratio > 1.2: st_bullish_points += 1

            st_verdict = "🟢 BULLISH SWING SETUP" if st_bullish_points >= 3 else ("🟡 SIDEWAYS / WAIT FOR BREAKOUT" if st_bullish_points == 2 else "🔴 BEARISH / AVOID SHORT-TERM")
            st.info(f"**Short-Term Technical Score: {st_bullish_points}/4 Criteria Met — {st_verdict}**")

            st.markdown(f"""
            * **1. 20-Day Exponential Moving Average (`{currency}{ema20:,.2f}`):** {'✅ Price is trading ABOVE the 20 EMA (Short-term buyers are in control).' if curr_price > ema20 else '❌ Price is BELOW the 20 EMA (Short-term weakness).'}
            * **2. RSI Momentum (`{rsi14:.1f}`):** {'✅ Healthy Bullish Momentum (50–70 zone).' if 50 <= rsi14 <= 70 else ('⚠️ Overbought (>70) — Wait for a dip.' if rsi14 > 70 else ('💎 Oversold (<35) — Watch for reversal bounce.' if rsi14 < 35 else '⏳ Neutral Momentum (35–50).'))}
            * **3. MACD Crossover:** {'✅ Bullish Crossover (MACD line is above Signal line).' if macd_line > macd_sig else '❌ Bearish Crossover (MACD line is below Signal line).'}
            * **4. Volume Activity (`{vol_ratio:.2f}x` of 20-Day Avg):** {'✅ Strong Institutional Volume Buying (>1.2x average).' if vol_ratio >= 1.2 else '⏳ Normal/Low Volume participation.'}
            ---
            **🎯 Key Short-Term Action Levels:**
            * **Immediate Support Floor (20-Day Low):** `{currency}{support_20d:,.2f}`
            * **Immediate Breakout Ceiling (20-Day High):** `{currency}{resistance_20d:,.2f}`
            * **Algo Volatility Stop-Loss (2x ATR):** `{currency}{curr_price - (2*atr14):,.2f}`
            * **Algo Swing Target (1:2 Risk-Reward):** `{currency}{curr_price + (4*atr14):,.2f}`
            """)

        with col_lt:
            st.markdown("### 🏛️ Long-Term Structural Trend Analysis (1 to 5+ Years)")
            lt_bullish_points = 0
            if curr_price > sma200: lt_bullish_points += 1
            if sma50 > sma200: lt_bullish_points += 1
            if curr_price > sma50: lt_bullish_points += 1

            lt_verdict = "🟢 STRONG MULTI-MONTH UPTREND" if lt_bullish_points == 3 else ("🟡 LONG-TERM PULLBACK / ACCUMULATION ZONE" if curr_price > sma200 else "🔴 LONG-TERM DOWNTREND (BELOW 200 DMA)")
            st.success(f"**Long-Term Trend Score: {lt_bullish_points}/3 Criteria Met — {lt_verdict}**")

            st.markdown(f"""
            * **1. 200-Day Moving Average (`{currency}{sma200:,.2f}`):** {'✅ Trading ABOVE the 200 DMA. Institutional fund managers consider the 200 DMA the ultimate dividing line between a Bull Market and a Bear Market.' if curr_price > sma200 else '❌ Trading BELOW the 200 DMA. Long-term trend is currently weak.'}
            * **2. Golden Cross vs. Death Cross (50 DMA `{currency}{sma50:,.2f}` vs 200 DMA `{currency}{sma200:,.2f}`):** {'✅ **Golden Cross Active** (50 DMA is above 200 DMA — confirms a structural long-term bull trend).' if sma50 > sma200 else '❌ **Death Cross Active** (50 DMA is below 200 DMA — indicates multi-month corrective phase).'}
            * **3. Medium-Term Trend (50 DMA `{currency}{sma50:,.2f}`):** {'✅ Holding firmly above the 50-day institutional support line.' if curr_price > sma50 else '⚠️ Currently testing/below the 50-day average.'}
            ---
            **💡 Beginner's Takeaway for Long-Term Investing:**
            * When a fundamentally strong stock (high ROE, low debt in Tab 1) pulls back near its **200-Day Moving Average (`{currency}{sma200:,.2f}`)** while the Golden Cross is active, long-term investors use it as a staggered accumulation zone.
            """)

        # Interactive Candlestick Chart
        st.markdown("### 📊 Interactive Price Chart with 20 EMA, 50 SMA & 200 SMA")
        hist['EMA20'] = hist['Close'].ewm(span=20).mean()
        hist['SMA50'] = hist['Close'].rolling(50).mean()
        hist['SMA200'] = hist['Close'].rolling(200).mean()

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=hist.index, open=hist['Open'], high=hist['High'],
            low=hist['Low'], close=hist['Close'], name="Daily Price"
        ))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA20'], line=dict(color='orange', width=1.5), name="20 EMA (Short-Term)"))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA50'], line=dict(color='cyan', width=1.5), name="50 SMA (Medium-Term)"))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA200'], line=dict(color='red', width=2.2), name="200 SMA (Long-Term Bull/Bear Line)"))
        fig.update_layout(height=520, xaxis_rangeslider_visible=False, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Not enough historical trading days to compute 200-day technical indicators.")

# ==============================================================================
# TAB 4: LATEST LIVE NEWS ON THE SEARCHED STOCK
# ==============================================================================
with tab_news:
    st.subheader(f"📰 Latest Live Financial News for {company_name} ({ticker})")
    news_items = fetch_live_news(company_name, ticker, query_suffix="share price NSE results news")
    if news_items:
        for idx, art in enumerate(news_items, 1):
            st.markdown(f"**{idx}. [{art['title']}]({art['link']})**")
            st.caption(f"🗞️ Publisher: {art['source']}  |  🕒 Published: {art['published']}")
            st.divider()
    else:
        st.info("No recent news articles found for this stock right now.")

st.caption("⚠️ **SEBI Regulatory Disclaimer:** This platform aggregates public exchange data, financial media feeds, and mathematical technical indicators strictly for educational purposes. It does not constitute personalized investment advice. Please consult a SEBI-registered Investment Adviser before making financial decisions.")
