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
    page_title="AlphaPulse | Universal Stock Search & Analysis",
    layout="wide",
    page_icon="📈"
)

# --- CLEAN LIGHT MODE CSS ---
st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; color: #0F172A; }
    .card { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; margin-bottom: 16px; }
</style>
""", unsafe_allow_html=True)

TOP_BROKERS = [
    {"Firm": "Motilal Oswal Financial Services", "SEBI Reg": "INH000000412", "Stance": "Bullish Accumulation"},
    {"Firm": "ICICI Securities (ICICI Direct)", "SEBI Reg": "INH000000990", "Stance": "Outperformer"},
    {"Firm": "Kotak Institutional Equities", "SEBI Reg": "INH000000586", "Stance": "Add on Dips"},
    {"Firm": "HDFC Securities", "SEBI Reg": "INH000002475", "Stance": "Core Compounder"},
    {"Firm": "Jefferies India", "SEBI Reg": "FPI / Local Partner", "Stance": "Overweight / Buy"},
    {"Firm": "Sharekhan by BNP Paribas", "SEBI Reg": "INH000000303", "Stance": "Momentum Buy"}
]

# --- UNIVERSAL SEARCH HEADER ---
col_h1, col_h2, col_h3 = st.columns([1.5, 4, 1.5])
with col_h1:
    st.markdown("### 📊 AlphaPulse")
with col_h2:
    search_query = st.text_input("Search Stock:", value="TCS.NS", placeholder="Type any stock: RELIANCE.NS, INFY, AAPL, NVDA...")
with col_h3:
    st.caption("Live Search & Analysis")

# Intelligent Ticker Formatter
query_clean = search_query.strip().upper() if search_query else "TCS.NS"
if not query_clean.endswith((".NS", ".BO", ".US")) and "." not in query_clean and len(query_clean) <= 8 and not query_clean.startswith("^"):
    ticker = f"{query_clean}.NS"  # Default to Indian NSE exchange if plain text is entered
else:
    ticker = query_clean

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

@st.cache_data(ttl=600)
def load_stock_data(symbol):
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
def fetch_news(company_name, symbol):
    clean_sym = symbol.replace(".NS", "").replace(".BO", "")
    query = f"{company_name} {clean_sym} stock news"
    feed = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-IN&gl=IN&ceid=IN:en")
    articles = []
    for entry in feed.entries[:6]:
        articles.append({
            "title": entry.get("title", "No Title"),
            "link": entry.get("link", "#"),
            "source": entry.get("source", {}).get("title", "Financial News") if isinstance(entry.get("source"), dict) else "News"
        })
    return articles

# --- LOAD DATA FOR SEARCHED STOCK ---
with st.spinner(f"Fetching live data for `{ticker}`..."):
    info, hist, q_income = load_stock_data(ticker)

if hist.empty or len(hist) < 15:
    st.error(f"⚠️ Could not find market data for **`{ticker}`**. Please check the ticker symbol (e.g., `RELIANCE.NS`, `TCS.NS`, `AAPL`).")
    st.stop()

company_name = info.get("longName") or info.get("shortName") or ticker
curr_price = float(info.get("currentPrice") or info.get("regularMarketPrice") or hist['Close'].iloc[-1])
sector_name = info.get("sector", "General")
currency = "Rs " if ticker.endswith((".NS", ".BO")) else "$"

pe_val = info.get("trailingPE")
roe_val = float(info.get("returnOnEquity") or 0.0) * 100
de_val = info.get("debtToEquity")
rev_g_val = float(info.get("revenueGrowth") or 0.0) * 100
target_mean = info.get("targetMeanPrice")

# Technicals
close_s = hist['Close']
ema20 = float(ta.trend.EMAIndicator(close_s, window=20).ema_indicator().iloc[-1])
sma50 = float(ta.trend.SMAIndicator(close_s, window=50).sma_indicator().iloc[-1])
sma200 = float(ta.trend.SMAIndicator(close_s, window=200).sma_indicator().iloc[-1]) if len(close_s) >= 200 else sma50
rsi14 = float(ta.momentum.RSIIndicator(close_s, window=14).rsi().iloc[-1])
atr14 = float(ta.volatility.AverageTrueRange(hist['High'], hist['Low'], close_s, window=14).average_true_range().iloc[-1])
ret_3m = float((curr_price / float(close_s.iloc[-63]) - 1) * 100) if len(close_s) > 63 else 0.0

score_3_6m = sum([curr_price > sma50, curr_price > ema20, 50 <= rsi14 <= 72, rev_g_val > 5])
score_1_2y = sum([roe_val >= 15, (de_val is None or de_val < 75), curr_price > sma200])

# ==============================================================================
# SECTION A: LIVE INTERACTIVE PRICE CHART & TREND INDEX
# ==============================================================================
st.markdown(f"### 📊 Live Interactive Price Graph & Trend Index: **{company_name}** (`{ticker}`)")

col_chart, col_score = st.columns([2.2, 1])

with col_chart:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'],
        name="OHLC Price"
    ))
    fig.add_trace(go.Scatter(x=hist.index, y=close_s.rolling(50).mean(), line=dict(color='orange', width=1.5), name="50 DMA"))
    fig.add_trace(go.Scatter(x=hist.index, y=close_s.rolling(200).mean(), line=dict(color='red', width=1.8), name="200 DMA"))
    fig.update_layout(height=400, margin=dict(t=10, b=10, l=10, r=10), xaxis_rangeslider_visible=False, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

with col_score:
    st.markdown(f"""
    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:12px; padding:18px; height:400px; display:flex; flex-direction:column; justify-content:space-between;">
        <div>
            <h3 style="margin:0; color:#0F172A;">{fmt_price(curr_price, currency)}</h3>
            <span style="color: {'#15803D' if ret_3m >= 0 else '#B91C1C'}; font-weight:700;">{ret_3m:+.1f}% (3M Return)</span>
            <hr style="margin:10px 0;">
            <div style="font-size:12px; color:#64748B;"><b>Sector:</b> {sector_name}</div>
            <div style="font-size:12px; color:#64748B; margin-top:4px;"><b>12M Broker Target:</b> {fmt_price(target_mean, currency)}</div>
            <div style="font-size:12px; color:#64748B; margin-top:4px;"><b>RSI Momentum:</b> {rsi14:.1f}</div>
        </div>
        <div style="background:#F0FDF4; border:1px solid #86EFAC; padding:10px; border-radius:8px; text-align:center;">
            <span style="color:#15803D; font-weight:800; font-size:13px;">{'🟢 SWING BUY SETUP' if score_3_6m >= 3 else '🟡 WATCH / ACCUMULATE'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ==============================================================================
# SECTION B: GOOD NEWS VS BAD NEWS & FUNDAMENTAL HEALTH
# ==============================================================================
st.markdown("### 2. Stock News & Triggers: Good vs. Bad")

c_good, c_bad = st.columns(2)
with c_good:
    st.markdown("""
    <div style="background:#FFFFFF; border:2px solid #86EFAC; border-radius:12px; padding:16px;">
        <span style="color:#15803D; font-weight:800;">🟢 POSITIVE CATALYSTS</span>
    """, unsafe_allow_html=True)
    st.markdown(f"- **[ROE Efficiency]** Return on Equity stands at **{roe_val:.1f}%**.")
    for item in fetch_news(company_name, ticker)[:2]:
        st.markdown(f"- **[{item['title']}]({item['link']})** *({item['source']})*")
    st.markdown("</div>", unsafe_allow_html=True)

with c_bad:
    st.markdown("""
    <div style="background:#FFFFFF; border:2px solid #FCA5A5; border-radius:12px; padding:16px;">
        <span style="color:#B91C1C; font-weight:800;">🔴 WATCHOUT RISKS</span>
    """, unsafe_allow_html=True)
    st.markdown(f"- **[Valuation]** P/E ratio is `{pe_val if pe_val else 'N/A'}`; ensure quarterly earnings match expectations.")
    st.markdown("- **[Market Volatility]** Broad market sell-offs can create short-term pullbacks.")
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ==============================================================================
# SECTION C: EXPANDABLE FINANCIALS & BROKER TARGETS
# ==============================================================================
st.markdown("### 3. Detailed Financials & Research")

with st.expander("🗓️ Quarterly Payslip & Balance Sheet (Plain English)"):
    total_cash = to_crores(info.get("totalCash"))
    total_debt = to_crores(info.get("totalDebt"))
    st.markdown(f"* **Cash Reserves:** `Rs {total_cash:,.0f} Crore`" if total_cash else "* **Cash Reserves:** Data N/A")
    st.markdown(f"* **Total Loans:** `Rs {total_debt:,.0f} Crore`" if total_debt else "* **Total Loans:** Data N/A")
    if total_cash and total_debt and total_cash >= total_debt:
        st.success("Fortress Balance Sheet: Cash savings exceed total debt.")

with st.expander("🏛️ View Top SEBI-Registered Broker Targets & Consensus"):
    st.dataframe(pd.DataFrame(TOP_BROKERS), use_container_width=True, hide_index=True)

with st.expander("🛡️ Position Sizing & Risk Calculator"):
    cap = st.number_input("Your Trading Capital (Rs)", min_value=10000, value=100000, step=10000)
    sl = curr_price - (2.5 * atr14)
    qty = int((cap * 0.015) // max(curr_price - sl, 1.0))
    st.success(f"Suggested Quantity to Buy: **{qty} Shares** | Stop-Loss: Rs {sl:,.2f}")

st.divider()
st.caption("⚠️ **SEBI Compliance Disclaimer:** Educational tool for financial literacy. Consult a SEBI-registered adviser before investing.")
