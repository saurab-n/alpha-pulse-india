import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta
import plotly.graph_objects as go

# --- PAGE SETUP ---
st.set_page_config(page_title="AlphaPulse India | Quant & Fundamental Screener", layout="wide", page_icon="📊")

st.title("📊 AlphaPulse: Institutional Stock Screener & Algo Analyzer")
st.caption("Quantitative Technical Scans • Fundamental Quality Scoring • ATR Risk & Position Sizing")

# --- CURATED WATCHLISTS ---
NIFTY_WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "BHARTIARTL.NS", "ITC.NS", "SBIN.NS", "LT.NS", "SUNPHARMA.NS",
    "TATAMOTORS.NS", "M&M.NS", "NTPC.NS", "AXISBANK.NS", "BAJFINANCE.NS",
    "HAL.NS", "TRENT.NS", "BEL.NS", "TITAN.NS", "MARUTI.NS"
]

US_WATCHLIST = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "LLY", "JPM"]

# --- SIDEBAR CONTROLS ---
st.sidebar.header("⚙️ Control Panel")
market_choice = st.sidebar.selectbox("1. Select Market Universe", ["Nifty Top 20 (NSE India)", "US Tech & Bluechips", "Custom Watchlist"])

if market_choice == "Nifty Top 20 (NSE India)":
    default_list = ", ".join(NIFTY_WATCHLIST)
    currency = "₹"
elif market_choice == "US Tech & Bluechips":
    default_list = ", ".join(US_WATCHLIST)
    currency = "$"
else:
    default_list = "RELIANCE.NS, TCS.NS, ZOMATO.NS, TATAPOWER.NS"
    currency = "₹"

tickers_input = st.sidebar.text_area("Edit Tickers (Add .NS for NSE India stocks):", default_list, height=110)
tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

st.sidebar.divider()
st.sidebar.subheader("🛡️ Risk Management Settings")
capital = st.sidebar.number_input(f"Total Trading Capital ({currency})", min_value=1000, value=100000, step=10000)
risk_pct = st.sidebar.slider("Max Risk Per Trade (%)", min_value=0.5, max_value=3.0, value=1.0, step=0.5)

# --- 1. MARKET REGIME ENGINE ---
@st.cache_data(ttl=900)
def get_market_regime(is_india=True):
    index_symbol = "^NSEI" if is_india else "^GSPC"
    index_name = "NIFTY 50" if is_india else "S&P 500"
    try:
        df = yf.download(index_symbol, period="1y", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df['Close']
        curr = float(close.iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        sma200 = float(close.rolling(200).mean().iloc[-1])
        if curr > sma50 > sma200:
            status = "🟢 BULLISH REGIME (Ideal for Breakouts & Swing Trades)"
        elif curr < sma50 and curr > sma200:
            status = "🟡 PULLBACK / CONSOLIDATION (Be Selective, Buy on Dips)"
        else:
            status = "🔴 BEARISH REGIME (Protect Capital, Focus on Long-Term SIPs)"
        return index_name, round(curr, 2), round(sma50, 2), round(sma200, 2), status
    except Exception:
        return index_name, 0, 0, 0, "⚪ Market Data Loading..."

idx_name, idx_price, idx_50, idx_200, regime_status = get_market_regime("US" not in market_choice)
st.info(f"**Market Pulse ({idx_name}: {idx_price})** — 50 DMA: `{idx_50}` | 200 DMA: `{idx_200}`  $\longrightarrow$  **{regime_status}**")

# --- 2. SHORT-TERM ALGO ENGINE ---
@st.cache_data(ttl=900)
def run_short_term_algo(ticker_list, total_cap, risk_percent):
    rows = []
    max_risk_amt = total_cap * (risk_percent / 100.0)
    for sym in ticker_list:
        try:
            df = yf.download(sym, period="1y", interval="1d", progress=False)
            if df.empty or len(df) < 200:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            close = df['Close']
            high = df['High']
            low = df['Low']
            vol = df['Volume']

            curr_price = float(close.iloc[-1])
            ema20 = float(ta.trend.EMAIndicator(close, window=20).ema_indicator().iloc[-1])
            sma50 = float(ta.trend.SMAIndicator(close, window=50).sma_indicator().iloc[-1])
            sma200 = float(ta.trend.SMAIndicator(close, window=200).sma_indicator().iloc[-1])
            rsi = float(ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1])
            atr = float(ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1])
            vol_ratio = float(vol.iloc[-1] / vol.rolling(20).mean().iloc[-1])

            # ATR-Based Stop Loss & Target (1:2 Risk-Reward)
            stop_loss = round(curr_price - (2.0 * atr), 2)
            target = round(curr_price + (4.0 * atr), 2)
            risk_per_share = max(curr_price - stop_loss, 0.01)
            qty = int(max_risk_amt // risk_per_share)

            # Quantitative Setup Classification
            if curr_price > ema20 > sma50 > sma200 and 55 <= rsi <= 72 and vol_ratio >= 1.2:
                setup = "🔥 High-Conviction Breakout"
            elif curr_price > sma50 > sma200 and 45 <= rsi < 55:
                setup = "📈 Uptrend Pullback"
            elif rsi < 32 and curr_price > sma200:
                setup = "💎 Oversold Bounce Zone"
            elif rsi > 75:
                setup = "⚠️ Overbought (Book Profits)"
            else:
                setup = "⏳ Neutral / Sideways"

            rows.append({
                "Ticker": sym,
                "Price": round(curr_price, 2),
                "Setup Classification": setup,
                "RSI (14)": round(rsi, 1),
                "Vol Surge (vs 20d)": f"{round(vol_ratio, 2)}x",
                "Algo Stop-Loss (2x ATR)": stop_loss,
                "Algo Target (1:2 R:R)": target,
                "Suggested Qty (1% Risk)": qty
            })
        except Exception:
            continue
    return pd.DataFrame(rows)

# --- 3. LONG-TERM FUNDAMENTAL ENGINE ---
@st.cache_data(ttl=3600)
def run_long_term_algo(ticker_list):
    rows = []
    for sym in ticker_list:
        try:
            info = yf.Ticker(sym).info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            pe = info.get("trailingPE")
            roe = info.get("returnOnEquity")
            de = info.get("debtToEquity")
            rev_g = info.get("revenueGrowth")
            op_m = info.get("operatingMargins")
            eps = info.get("trailingEps")
            bvps = info.get("bookValue")

            # 100-Point Institutional Quality Scoring
            score = 0
            if roe and roe > 0.15: score += 25
            elif roe and roe > 0.10: score += 12

            if pe and 0 < pe <= 30: score += 25
            elif pe and 30 < pe <= 45: score += 12

            if de is not None and de < 50: score += 20
            elif de is not None and de < 100: score += 10

            if rev_g and rev_g > 0.12: score += 20
            elif rev_g and rev_g > 0.06: score += 10

            if op_m and op_m > 0.15: score += 10

            # Benjamin Graham Intrinsic Value Calculation
            if eps and bvps and eps > 0 and bvps > 0:
                graham_val = round(float(np.sqrt(22.5 * eps * bvps)), 2)
            else:
                graham_val = None

            if score >= 75:
                grade = "🏆 Tier-1 Compounder"
            elif score >= 50:
                grade = "✅ Solid Fundamentals"
            else:
                grade = "⚠️ Weak / High Valuation"

            rows.append({
                "Ticker": sym,
                "Price": round(price, 2) if price else "N/A",
                "Quality Score": f"{score}/100",
                "Fundamental Grade": grade,
                "P/E Ratio": round(pe, 1) if pe else "N/A",
                "ROE (%)": round(roe * 100, 1) if roe else "N/A",
                "Debt/Equity (%)": round(de, 1) if de is not None else "N/A",
                "Rev Growth YoY (%)": round(rev_g * 100, 1) if rev_g else "N/A",
                "Graham Fair Value": graham_val if graham_val else "N/A"
            })
        except Exception:
            continue
    return pd.DataFrame(rows)

# --- MAIN DASHBOARD TABS ---
tab1, tab2, tab3 = st.tabs([
    "⚡ Short-Term Swing & Momentum Scanner",
    "🏛️ Long-Term Multibagger & Value Scanner",
    "🔍 Single-Stock X-Ray & Interactive Chart"
])

with tab1:
    st.subheader("⚡ Short-Term Quantitative Momentum & ATR Risk Scanner")
    st.markdown(f"Automatically calculates **Stop-Loss (2x ATR)**, **Target (1:2 Risk-Reward)**, and **Position Size** based on your **{currency}{capital:,.0f}** capital and **{risk_pct}%** risk rule.")
    df_short = run_short_term_algo(tickers, capital, risk_pct)
    st.dataframe(df_short, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("🏛️ Long-Term Fundamental Quality & Graham Intrinsic Value")
    st.markdown("Evaluates companies out of **100 points** across Profitability (ROE), Valuation (P/E), Balance Sheet (Debt/Equity), Growth, and Operating Margins.")
    df_long = run_long_term_algo(tickers)
    st.dataframe(df_long, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("🔍 Deep-Dive Technical Chart (Candlesticks + 20 EMA & 50/200 SMA)")
    selected_stock = st.selectbox("Choose a Stock to Inspect:", tickers)
    if selected_stock:
        hist = yf.download(selected_stock, period="1y", interval="1d", progress=False)
        if not hist.empty:
            if isinstance(hist.columns, pd.MultiIndex):
                hist.columns = hist.columns.get_level_values(0)
            hist['EMA20'] = hist['Close'].ewm(span=20).mean()
            hist['SMA50'] = hist['Close'].rolling(50).mean()
            hist['SMA200'] = hist['Close'].rolling(200).mean()

            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=hist.index, open=hist['Open'], high=hist['High'],
                low=hist['Low'], close=hist['Close'], name="Price"
            ))
            fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA20'], line=dict(color='orange', width=1.5), name="20 EMA (Swing Trend)"))
            fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA50'], line=dict(color='blue', width=1.5), name="50 SMA (Medium Trend)"))
            fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA200'], line=dict(color='red', width=2), name="200 SMA (Long-Term Trend)"))
            fig.update_layout(height=550, xaxis_rangeslider_visible=False, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption("⚠️ **SEBI Compliance & Regulatory Disclaimer:** This web application is an automated quantitative and fundamental data screening tool built strictly for educational and informational purposes. None of the classifications, scores, or algorithmic risk levels constitute investment advice or a recommendation to buy or sell securities. Always consult a SEBI-registered Investment Adviser before investing.")
