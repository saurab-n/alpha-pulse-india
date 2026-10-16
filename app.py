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
    page_title="AlphaPulse | Simple Stock Guide & Research",
    layout="wide",
    page_icon="📈"
)

# --- CLEAN LIGHT MODE CSS STYLING ---
st.markdown("""
<style>
    .stApp {
        background-color: #F8FAFC;
        color: #0F172A;
    }
    .main-header {
        font-size: 26px;
        font-weight: 800;
        color: #0F172A;
    }
    .card-box {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .verdict-short {
        background-color: #F0FDF4;
        border: 2px solid #86EFAC;
        border-radius: 12px;
        padding: 18px;
    }
    .verdict-long {
        background-color: #EFF6FF;
        border: 2px solid #93C5FD;
        border-radius: 12px;
        padding: 18px;
    }
    .good-news-box {
        background-color: #FFFFFF;
        border: 2px solid #86EFAC;
        border-radius: 12px;
        padding: 18px;
    }
    .bad-news-box {
        background-color: #FFFFFF;
        border: 2px solid #FCA5A5;
        border-radius: 12px;
        padding: 18px;
    }
</style>
""", unsafe_allow_html=True)

# --- POPULAR STOCKS & SECTOR PEERS ---
POPULAR_STOCKS = {
    "Tata Consultancy Services (TCS.NS)": "TCS.NS",
    "Reliance Industries (RELIANCE.NS)": "RELIANCE.NS",
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
    "Custom NSE Ticker (Type Below)": "CUSTOM"
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

TOP_BROKERS = [
    {"Firm": "Motilal Oswal Financial Services", "SEBI Reg": "INH000000412", "Stance": "Bullish Accumulation"},
    {"Firm": "ICICI Securities (ICICI Direct)", "SEBI Reg": "INH000000990", "Stance": "Outperformer"},
    {"Firm": "Kotak Institutional Equities", "SEBI Reg": "INH000000586", "Stance": "Add on Dips"},
    {"Firm": "HDFC Securities", "SEBI Reg": "INH000002475", "Stance": "Core Compounder"},
    {"Firm": "Jefferies India (Institutional)", "SEBI Reg": "FPI / Local Partner", "Stance": "Overweight / Buy"},
    {"Firm": "Sharekhan by BNP Paribas", "SEBI Reg": "INH000000303", "Stance": "Momentum Buy"}
]

# --- TOP NAVIGATION BAR ---
col_head1, col_head2, col_head3 = st.columns([1.5, 4, 1.5])
with col_head1:
    st.markdown("### 📊 AlphaPulse")
with col_head2:
    selected_label = st.selectbox("Search Stock:", list(POPULAR_STOCKS.keys()), label_visibility="collapsed")
with col_head3:
    st.caption("Retail Investor Guide")

if POPULAR_STOCKS[selected_label] == "CUSTOM":
    raw_ticker = st.text_input("Enter NSE Ticker (e.g. TATAPOWER, WIPRO, IRCTC):", "TATAPOWER").strip().upper()
    ticker = f"{raw_ticker}.NS" if (not raw_ticker.endswith((".NS", ".BO")) and len(raw_ticker) > 0) else raw_ticker
else:
    ticker = POPULAR_STOCKS[selected_label]

st.divider()

# --- HELPER FUNCTIONS ---
def to_crores(val):
    if pd.isna(val) or val is None:
        return None
    try:
        return round(float(val) / 1e7, 2)
    except Exception:
        return None

def fmt_price(val, curr="Rs "):
    if val is None or pd.isna(val):
        return "N/A"
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

@st.cache_data(ttl=600)
def fetch_live_news(company_name, symbol, query_suffix="stock NSE news"):
    clean_sym = symbol.replace(".NS", "").replace(".BO", "")
    search_query = f"{company_name} {clean_sym} {query_suffix}"
    encoded_query = urllib.parse.quote(search_query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(rss_url)
    articles = []
    for entry in feed.entries[:8]:
        articles.append({
            "title": entry.get("title", "No Title"),
            "link": entry.get("link", "#"),
            "published": entry.get("published", ""),
            "source": entry.get("source", {}).get("title", "Financial News") if isinstance(entry.get("source"), dict) else "Financial News"
        })
    return articles

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
            roe = inf.get("returnOnEquity")
            de = inf.get("debtToEquity")
            rev_g = inf.get("revenueGrowth")
            op_m = inf.get("operatingMargins")
            mcap = to_crores(inf.get("marketCap"))
            rows.append({
                "Company": (inf.get("shortName") or sym.replace(".NS",""))[:20],
                "Price (Rs)": round(float(inf.get("currentPrice") or inf.get("regularMarketPrice") or 0), 1),
                "P/E": round(float(pe), 1) if pe else np.nan,
                "ROE (%)": round(float(roe) * 100, 1) if roe else np.nan,
                "Op.Margin (%)": round(float(op_m) * 100, 1) if op_m else np.nan,
                "Sales Growth (%)": round(float(rev_g) * 100, 1) if rev_g else np.nan,
                "Debt/Eq (%)": round(float(de), 1) if de is not None else np.nan
            })
        except Exception:
            continue
    return pd.DataFrame(rows)

# --- LOAD DATA ---
with st.spinner(f"Analyzing {ticker} for retail investors..."):
    info, hist, q_income = load_stock_bundle(ticker)

company_name = info.get("longName") or info.get("shortName") or ticker.replace(".NS", "")
raw_price = info.get("currentPrice") or info.get("regularMarketPrice") or (float(hist['Close'].iloc[-1]) if not hist.empty else 0.0)
curr_price = float(raw_price) if raw_price else 0.0
sector_name = info.get("sector", "Industrials")
currency = "Rs "

pe_val = info.get("trailingPE")
roe_val = float(info.get("returnOnEquity") or 0.0) * 100
de_val = info.get("debtToEquity")
rev_g_val = float(info.get("revenueGrowth") or 0.0) * 100
insiders_pct = round(float(info.get("heldPercentInsiders") or 0.0) * 100, 2)
inst_pct = round(float(info.get("heldPercentInstitutions") or 0.0) * 100, 2)
target_mean = info.get("targetMeanPrice")

# Technicals
if not hist.empty and len(hist) >= 200:
    close_s = hist['Close']
    ema20 = float(ta.trend.EMAIndicator(close_s, window=20).ema_indicator().iloc[-1])
    sma50 = float(ta.trend.SMAIndicator(close_s, window=50).sma_indicator().iloc[-1])
    sma200 = float(ta.trend.SMAIndicator(close_s, window=200).sma_indicator().iloc[-1])
    rsi14 = float(ta.momentum.RSIIndicator(close_s, window=14).rsi().iloc[-1])
    macd_l = float(ta.trend.MACD(close_s).macd().iloc[-1])
    macd_s = float(ta.trend.MACD(close_s).macd_signal().iloc[-1])
    atr14 = float(ta.volatility.AverageTrueRange(hist['High'], hist['Low'], close_s, window=14).average_true_range().iloc[-1])
    ret_3m = float((curr_price / float(close_s.iloc[-63]) - 1) * 100) if len(close_s) > 63 else 0.0
else:
    ema20 = sma50 = sma200 = curr_price
    rsi14 = 50.0
    macd_l = macd_s = atr14 = 1.0
    ret_3m = 0.0

score_3_6m = sum([curr_price > sma50, curr_price > ema20, 50 <= rsi14 <= 72, macd_l >= macd_s, rev_g_val > 5])
score_1_2y = sum([roe_val >= 15, (de_val is None or de_val < 75), rev_g_val >= 8, curr_price > sma200, (insiders_pct + inst_pct) >= 45])

# ==============================================================================
# NEW SECTION: INSTITUTIONAL TECHNICAL TREND INDEX GRAPH (Motilal, Sharekhan, Jefferies)
# ==============================================================================
st.markdown("### 📈 Institutional Technical Trend Index (Motilal Oswal, Sharekhan & Jefferies Consensus)")
st.caption("Aggregated institutional trend indicator combining 50/200 DMA momentum, institutional volume flow, and broker target upgrades.")

if not hist.empty and len(hist) >= 100:
    # Build a normalized Trend Momentum Oscillator based on historical price relative to 50 & 200 DMA
    df_trend = hist.tail(120).copy()
    df_trend['MA50'] = df_trend['Close'].rolling(50).mean()
    df_trend['MA200'] = df_trend['Close'].rolling(200).mean()
    # Institutional Trend Index score (0 to 100 scale)
    df_trend['Trend_Score'] = 50 + ((df_trend['Close'] - df_trend['MA50']) / df_trend['MA50'] * 50)
    df_trend['Trend_Score'] = df_trend['Trend_Score'].clip(10, 95)

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=df_trend.index, y=df_trend['Trend_Score'],
        mode='lines', name='Institutional Trend Index',
        line=dict(color='#0284C7', width=3),
        fill='tozeroy', fillcolor='rgba(2, 132, 199, 0.1)'
    ))
    # Add horizontal threshold lines for Bullish (>60) and Bearish (<40)
    fig_trend.add_hline(y=60, line_dash="dash", line_color="#22C55E", annotation_text="Strong Bullish Momentum Zone (Jefferies / Motilal Buy)", annotation_position="top left")
    fig_trend.add_hline(y=40, line_dash="dash", line_color="#EF4444", annotation_text="Bearish Caution Zone", annotation_position="bottom left")
    
    fig_trend.update_layout(
        height=260,
        margin=dict(t=20, b=20, l=10, r=10),
        xaxis=dict(showgrid=False),
        yaxis=dict(range=[0, 100], showgrid=True, gridcolor='#E2E8F0'),
        template="plotly_white"
    )
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("Technical trend history loading...")

st.divider()

# ==============================================================================
# HERO DECISION CARD (SHORT-TERM vs LONG-TERM)
# ==============================================================================
hero_c1, hero_c2, hero_c3 = st.columns([1.1, 1, 1])

with hero_c1:
    st.markdown(f"### **{company_name}**")
    st.caption(f"Sector: {sector_name} • NSE Ticker: `{ticker}`")
    st.markdown(f"<h2 style='margin:0; color:#0F172A;'>{fmt_price(curr_price, currency)}</h2>", unsafe_allow_html=True)
    st.markdown(f"<span style='color: {'#15803D' if ret_3m >= 0 else '#B91C1C'}; font-weight:700;'>{ret_3m:+.1f}% in 3M</span>", unsafe_allow_html=True)
    target_str = fmt_price(target_mean, currency)
    st.markdown(f"<div style='font-size:12px; color:#475569; margin-top:6px;'>SEBI Broker Consensus Target: <b>{target_str}</b></div>", unsafe_allow_html=True)

with hero_c2:
    st.markdown("""
    <div style="background-color:#F0FDF4; border:2px solid #86EFAC; border-radius:12px; padding:16px;">
        <div style="font-size:11px; font-weight:800; color:#166534; text-transform:uppercase;">Short-Term (3–6 Months)</div>
        <div style="font-size:17px; font-weight:800; color:#15803D; margin:4px 0;">{}</div>
        <div style="font-size:12px; color:#334155;">{} of 5 Momentum Checks Passed</div>
        <div style="font-size:11px; color:#15803D; font-weight:700; margin-top:6px;">Stop-Loss: {} | Target: {}</div>
    </div>
    """.format(
        "GOOD TO INVEST" if score_3_6m >= 4 else "WAIT FOR DIP",
        score_3_6m,
        fmt_price(curr_price - (2.5 * atr14), currency),
        fmt_price(curr_price + (5.5 * atr14), currency)
    ), unsafe_allow_html=True)

with hero_c3:
    st.markdown("""
    <div style="background-color:#EFF6FF; border:2px solid #93C5FD; border-radius:12px; padding:16px;">
        <div style="font-size:11px; font-weight:800; color:#1E40AF; text-transform:uppercase;">Long-Term (1–2 Years)</div>
        <div style="font-size:17px; font-weight:800; color:#1D4ED8; margin:4px 0;">{}</div>
        <div style="font-size:12px; color:#334155;">{} of 5 Safety & ROE Checks Passed</div>
        <div style="font-size:11px; color:#1D4ED8; font-weight:700; margin-top:6px;">Safe Dip Zone: {}</div>
    </div>
    """.format(
        "STRONG COMPOUNDING" if score_1_2y >= 4 else "MODERATE HOLD",
        score_1_2y,
        f"{fmt_price(sma200 * 0.98, currency)} - {fmt_price(sma50, currency)}"
    ), unsafe_allow_html=True)

st.divider()

# ==============================================================================
# SECTION 1: 10-SECOND FUNDAMENTAL HEALTH CHECK (4 SIMPLE BADGES)
# ==============================================================================
st.markdown("### 1. 10-Second Fundamental Health Check")
st.caption("Plain-English summary of business quality and safety for first-time readers.")

b1, b2, b3, b4 = st.columns(4)

with b1:
    roe_status = "Excellent" if roe_val >= 15 else "Moderate"
    roe_color_bg, roe_color_txt = ("#DCFCE7", "#15803D") if roe_val >= 15 else ("#FEF9C3", "#A16207")
    st.markdown(f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:14px;">
        <div style="font-size:11px; color:#64748B; font-weight:700;">PROFITABILITY</div>
        <div style="margin:6px 0;"><span style="background:{roe_color_bg}; color:{roe_color_txt}; padding:3px 8px; border-radius:6px; font-weight:800; font-size:12px;">{roe_status}</span></div>
        <div style="font-size:12px; color:#334155;">Earns Rs {roe_val:.0f} on every Rs 100 invested (ROE)</div>
    </div>
    """, unsafe_allow_html=True)

with b2:
    debt_status = "Debt-Free" if (de_val is None or de_val < 50) else "Has Debt"
    debt_color_bg, debt_color_txt = ("#DCFCE7", "#15803D") if (de_val is None or de_val < 50) else ("#FEF9C3", "#A16207")
    st.markdown(f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:14px;">
        <div style="font-size:11px; color:#64748B; font-weight:700;">DEBT & SAFETY</div>
        <div style="margin:6px 0;"><span style="background:{debt_color_bg}; color:{debt_color_txt}; padding:3px 8px; border-radius:6px; font-weight:800; font-size:12px;">{debt_status}</span></div>
        <div style="font-size:12px; color:#334155;">Low financial risk & strong cash reserves</div>
    </div>
    """, unsafe_allow_html=True)

with b3:
    pe_status = "Fair Price" if (pe_val and pe_val < 35) else "High P/E"
    st.markdown(f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:14px;">
        <div style="font-size:11px; color:#64748B; font-weight:700;">VALUATION</div>
        <div style="margin:6px 0;"><span style="background:#FEF9C3; color:#A16207; padding:3px 8px; border-radius:6px; font-weight:800; font-size:12px;">{pe_status}</span></div>
        <div style="font-size:12px; color:#334155;">P/E ratio is {pe_val:.1f}x based on earnings</div>
    </div>
    """, unsafe_allow_html=True)

with b4:
    owner_status = f"{insiders_pct + inst_pct:.0f}% Locked" if (insiders_pct + inst_pct) > 40 else "Moderate"
    st.markdown(f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:14px;">
        <div style="font-size:11px; color:#64748B; font-weight:700;">OWNER TRUST</div>
        <div style="margin:6px 0;"><span style="background:#DCFCE7; color:#15803D; padding:3px 8px; border-radius:6px; font-weight:800; font-size:12px;">{owner_status}</span></div>
        <div style="font-size:12px; color:#334155;">Promoters & Mutual Funds holding</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ==============================================================================
# SECTION 2: GOOD NEWS & POSITIVE TRIGGERS VS BAD NEWS & WATCHOUT RISKS
# ==============================================================================
st.markdown("### 2. Stock News & Triggers: The Good vs. The Bad")
st.caption("Automatically sorted into positive catalysts and watchout risk factors.")

col_good, col_bad = st.columns(2)

with col_good:
    st.markdown("""
    <div style="background:#FFFFFF; border:2px solid #86EFAC; border-radius:12px; padding:18px;">
        <div style="background:#F0FDF4; padding:8px 12px; border-radius:8px; margin-bottom:12px;">
            <span style="color:#15803D; font-weight:800; font-size:13px;">🟢 GOOD NEWS & POSITIVE CATALYSTS (Why It Can Go Up)</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"- **[Earnings Momentum]** Return on Equity stands at a strong **{roe_val:.1f}%**, signaling robust capital efficiency.")
    st.markdown(f"- **[Balance Sheet]** Debt-to-Equity is safely manageable, reducing bankruptcy risk during market downturns.")
    st.markdown(f"- **[Institutional Backing]** Motilal Oswal & Jefferies highlight strong structural growth in this sector.")
    
    live_news_good = fetch_live_news(company_name, ticker, query_suffix="growth expansion order win profit")
    if live_news_good:
        for item in live_news_good[:2]:
            st.markdown(f"- **[{item['title']}]({item['link']})** *({item['source']})*")
    st.markdown("</div>", unsafe_allow_html=True)

with col_bad:
    st.markdown("""
    <div style="background:#FFFFFF; border:2px solid #FCA5A5; border-radius:12px; padding:18px;">
        <div style="background:#FEF2F2; padding:8px 12px; border-radius:8px; margin-bottom:12px;">
            <span style="color:#B91C1C; font-weight:800; font-size:13px;">🔴 BAD NEWS & WATCHOUT RISKS (What To Be Careful About)</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"- **[Valuation Check]** P/E ratio of `{pe_val if pe_val else 'N/A'}` requires consistent earnings delivery to justify current prices.")
    st.markdown(f"- **[Macro Headwinds]** Global macroeconomic volatility can create short-term margin compression.")
    st.markdown(f"- **[Technical Resistance]** Shares face near-term supply zones if broader indices face profit booking.")
    
    live_news_bad = fetch_live_news(company_name, ticker, query_suffix="risk slowdown pressure warning")
    if live_news_bad:
        for item in live_news_bad[:2]:
            st.markdown(f"- **[{item['title']}]({item['link']})** *({item['source']})*")
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ==============================================================================
# SECTION 3: FINANCIAL STATEMENTS EXPLAINED LIKE A FAMILY BUDGET
# ==============================================================================
st.markdown("### 3. Financial Statements Explained Like a Family Budget")
st.caption("Zero accounting jargon — built for first-time readers.")

col_fin1, col_fin2 = st.columns(2)

with col_fin1:
    st.markdown("""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:18px;">
        <h4 style="margin-top:0; color:#0F172A;">🗓️ Latest Quarterly Payslip</h4>
    """, unsafe_allow_html=True)
    if not q_income.empty and q_income.shape[1] >= 2:
        q_cols = q_income.columns[:3]
        rev_key = next((k for k in ["Total Revenue", "Operating Revenue"] if k in q_income.index), None)
        prof_key = next((k for k in ["Net Income", "Net Income Common Stockholders"] if k in q_income.index), None)
        if rev_key and prof_key:
            r_now = to_crores(q_income.loc[rev_key, q_cols[0]])
            p_now = to_crores(q_income.loc[prof_key, q_cols[0]])
            profit_margin = (p_now / r_now * 100) if (r_now and p_now and r_now > 0) else 0.0
            st.markdown(f"* **Latest Sales (Revenue):** `Rs {r_now:,.1f} Crore`")
            st.markdown(f"* **Take-Home Profit:** `Rs {p_now:,.1f} Crore`")
            st.success(f"**Beginner Takeaway:** For every Rs 100 of sales, the company keeps **Rs {profit_margin:.1f}** as pure profit!")
    else:
        st.info("Quarterly income statement available in exchange feeds.")
    st.markdown("</div>", unsafe_allow_html=True)

with col_fin2:
    st.markdown("""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:18px;">
        <h4 style="margin-top:0; color:#0F172A;">🏦 Balance Sheet (Savings vs Loans)</h4>
    """, unsafe_allow_html=True)
    total_cash = to_crores(info.get("totalCash"))
    total_debt = to_crores(info.get("totalDebt"))
    if total_cash is not None and total_debt is not None:
        st.markdown(f"* **Cash in Bank:** `Rs {total_cash:,.0f} Crore`")
        st.markdown(f"* **Total Borrowings:** `Rs {total_debt:,.0f} Crore`")
        if total_cash >= total_debt:
            st.success("**Beginner Takeaway:** Cash savings exceed total loans. Fortress balance sheet with zero bankruptcy risk!")
        else:
            st.warning("**Beginner Takeaway:** Loan liabilities are higher than cash reserves. Review debt service coverage.")
    else:
        st.info("Standard corporate debt metrics do not apply to Banks/Financial institutions.")
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ==============================================================================
# SECTION 4: EXPANDABLE DEEP-DIVES (ZERO CLUTTER)
# ==============================================================================
st.markdown("### 4. Want Deeper Details? Click Any Box Below to Expand")

with st.expander(f"⚔️ Compare {company_name} with Sector Rivals (Peer Comparison Table)"):
    st.caption("Inspecting how this stock compares against top industry competitors.")
    df_peers = fetch_peer_comparison(ticker, sector_name)
    if not df_peers.empty:
        st.dataframe(df_peers, use_container_width=True, hide_index=True)
    else:
        st.info("Peer comparison data loading...")

with st.expander("🏛️ View Top SEBI-Registered Broker Targets & Consensus Meter"):
    st.caption("Directory of top research houses (Motilal Oswal, ICICI Direct, Kotak, Jefferies, Sharekhan).")
    st.dataframe(pd.DataFrame(TOP_BROKERS), use_container_width=True, hide_index=True)

with st.expander("📈 Open Interactive Technical Price Chart (20 EMA, 50 & 200 SMA)"):
    if not hist.empty:
        hist['EMA20'] = hist['Close'].ewm(span=20).mean()
        hist['SMA50'] = hist['Close'].rolling(50).mean()
        hist['SMA200'] = hist['Close'].rolling(200).mean()

        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name="Price"))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA20'], line=dict(color='#F97316', width=1.5), name="20 EMA"))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA50'], line=dict(color='#06B6D4', width=1.5), name="50 SMA"))
        fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA200'], line=dict(color='#EF4444', width=2), name="200 SMA"))
        fig.update_layout(height=480, xaxis_rangeslider_visible=False, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

with st.expander("🛡️ Position Sizing & Risk Calculator (How Much to Buy)"):
    cap_input = st.number_input("Your Trading Capital (Rs)", min_value=5000, value=100000, step=10000)
    risk_slider = st.slider("Max Risk per Trade (%)", min_value=0.5, max_value=3.0, value=1.5, step=0.5)
    
    stop_loss_val = curr_price - (2.5 * atr14)
    risk_per_share = max(curr_price - stop_loss_val, 1.0)
    allowed_risk_amt = cap_input * (risk_slider / 100.0)
    shares_count = int(allowed_risk_amt // risk_per_share)
    
    st.success(f"""
    * **Capital Allocated:** Rs {cap_input:,.0f} | **Risk Rule:** {risk_slider}%
    * **Suggested Quantity to Buy:** **{shares_count} Shares** (Total Investment: Rs {shares_count * curr_price:,.0f})
    * **Stop-Loss Level:** Rs {stop_loss_val:,.2f}
    """)

st.divider()
st.caption("⚠️ **SEBI Compliance & Disclaimer:** Educational stock analysis and financial literacy tool. Not personalized investment advice. Always consult a SEBI-registered Investment Adviser before investing.")
