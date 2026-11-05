import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

# 1. Get user search ticker
ticker = st.text_input("Search Stock Ticker:", value="TCS.NS")

# 2. Fetch live data for the searched ticker
@st.cache_data(ttl=600)
def get_stock_data(symbol):
    df = yf.download(symbol, period="1y", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

hist = get_stock_data(ticker)

if not hist.empty:
    st.subheader(f"📊 Live Price Graph & Technical Analysis for {ticker}")

    # 3. Build Interactive Plotly Candlestick & Moving Average Graph
    fig = go.Figure()

    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=hist.index,
        open=hist['Open'],
        high=hist['High'],
        low=hist['Low'],
        close=hist['Close'],
        name="Price (OHLC)"
    ))

    # Add 50-day and 200-day moving averages as trend lines
    hist['SMA50'] = hist['Close'].rolling(window=50).mean()
    hist['SMA200'] = hist['Close'].rolling(window=200).mean()

    fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA50'], line=dict(color='orange', width=1.5), name="50 DMA"))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['SMA200'], line=dict(color='red', width=1.8), name="200 DMA"))

    # Layout styling for clean presentation
    fig.update_layout(
        height=500,
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        margin=dict(l=10, r=10, t=30, b=10)
    )

    # 4. Render the graph dynamically inside the app
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error(f"Could not load graph data for {ticker}. Please check the symbol.")
