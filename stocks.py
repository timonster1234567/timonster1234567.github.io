
pip install polygon-api-client

from polygon import RESTClient

client = RESTClient("YOUR_API_KEY")

bars = client.get_aggs(
    ticker="AAPL",
    multiplier=1,
    timespan="minute",
    from_="2025-01-01",
    to="2025-01-02"
)

for bar in bars:
    print(bar.timestamp, bar.open, bar.high, bar.low, bar.close)

    
import yfinance as yf
import pandas as pd
import numpy as np

def test_strategy(ticker):

    data = yf.download(ticker, period="30d", interval="1m")

    if data.empty:
        return []

    trades = []

    for date, day in data.groupby(data.index.date):

        day = day.between_time("09:30", "16:00")
        if len(day) < 50:
            continue

        open_price = day.iloc[0]['Open']
        if open_price >= 2:
            continue

        morning = day.between_time("09:30", "12:00")
        peak_price = morning['High'].max()

        # 10x spike condition
        if peak_price < open_price * 10:
            continue

        peak_time = morning['High'].idxmax()

        after_peak = day.loc[peak_time:]

        # Look for 3 consecutive red candles
        red_count = 0
        entry_price = None
        entry_time = None

        for i in range(1, len(after_peak)):
            candle = after_peak.iloc[i]

            if candle['Close'] < candle['Open']:
                red_count += 1
            else:
                red_count = 0

            if red_count == 3:
                entry_price = candle['Close']
                entry_time = after_peak.index[i]
                break

        if entry_price is None:
            continue

        # Exit logic
        fade_target = peak_price * 0.5
        remaining = day.loc[entry_time:]

        exit_price = None
        exit_time = None

        for i in range(len(remaining)):
            low = remaining.iloc[i]['Low']
            time = remaining.index[i]

            # Profit target
            if low <= fade_target:
                exit_price = fade_target
                exit_time = time
                break

        # If target not hit, exit at close
        if exit_price is None:
            exit_price = remaining.iloc[-1]['Close']
            exit_time = remaining.index[-1]

        pnl = entry_price - exit_price  # short profit

        trades.append({
            "date": date,
            "entry": entry_price,
            "exit": exit_price,
            "pnl": pnl
        })

    return trades