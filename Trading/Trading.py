
import pandas as pd
import time
import os
import datetime
from polygon import RESTClient
from tqdm import tqdm

# ===========================
# CONFIG
# ===========================
API_KEY = os.environ.get("HvQaWaWYEHOywp1_whWMXynScr9JBpA5", "XDGANgUgBLyThvlBdHJJBEExuAymiCmf") # Keep this secure!
START_DATE = "2025-11-01"
END_DATE = "2026-02-01"

# Strategy Parameters
SPIKE_MULTIPLE = 1.20
# FADE_RATIO = 0.85
CONSECUTIVE_RED = 2
# STOP_LOSS_MULTIPLE = 1.10
MIN_DAILY_VOLUME = 500000 
STOP_LOSS_PERCENT = 0.05    # Risking 5% of the entry price
TAKE_PROFIT_PERCENT = 0.10  # To make 10% of the entry price

client = RESTClient(api_key=API_KEY)

CSV_FILE = "penny_stocks.csv" 
try:
    stock_df = pd.read_csv(CSV_FILE)
    stock_df.columns = [c.strip() for c in stock_df.columns]
    TICKERS = stock_df['Symbol'].dropna().astype(str).str.strip().tolist()
    print(f"Successfully loaded {len(TICKERS)} tickers from {CSV_FILE}")
except Exception as e:
    print(f"Error loading CSV: {e}")
    TICKERS = []

# ===========================
# STEP 1: FIND THE SPIKE DAYS
# ===========================
def get_spike_dates(ticker):
    try:
        bars = client.list_aggs(
            ticker=ticker,
            multiplier=1,
            timespan="day",
            from_=START_DATE,
            to=END_DATE,
            limit=50000
        )
        records = [b for b in bars]
        if not records:
            return []

        spike_dates = []
        for bar in records:
            if bar.volume >= MIN_DAILY_VOLUME and bar.high >= (bar.open * SPIKE_MULTIPLE):
                date_str = pd.to_datetime(bar.timestamp, unit="ms").strftime('%Y-%m-%d')
                spike_dates.append(date_str)
                
        return spike_dates
    except Exception as e:
        return []

# ===========================
# STEP 2: FETCH MINUTE DATA
# ===========================
def get_minute_data_for_day(ticker, target_date):
    try:
        bars = client.list_aggs(
            ticker=ticker,
            multiplier=1,
            timespan="minute",
            from_=target_date, 
            to=target_date,    
            limit=50000
        )
        records = [b for b in bars]
        if not records:
            return None

        df = pd.DataFrame([
            {
                "timestamp": pd.to_datetime(bar.timestamp, unit="ms"),
                "Open": bar.open,
                "High": bar.high,
                "Low": bar.low,
                "Close": bar.close,
                "Volume": bar.volume
            }
            for bar in records
        ])
        df.set_index("timestamp", inplace=True)
        df.index = df.index.tz_localize("UTC").tz_convert("America/New_York")
        return df
    except Exception as e:
        return None

# ===========================
# STEP 3: STRATEGY LOGIC (ALL UPDATES INCLUDED)
# ===========================
def test_strategy(df, ticker, date):
    trades = []
    
    day = df.between_time("09:30", "16:00")
    if len(day) < 30:
        return trades

    open_price = day.iloc[0]["Open"]
    morning = day.between_time("09:30", "12:00")
    if morning.empty:
        return trades

    # Find the peak
    peak_price = morning["High"].max()
    if peak_price < open_price * SPIKE_MULTIPLE:
        return trades

    peak_time = morning["High"].idxmax()
    
    # ---------------------------------------------------------
    # RULE 1: RELATIVE VOLUME CLIMAX
    # ---------------------------------------------------------
    # The peak volume must be at least 2x the recent average (ignores 9:30 bell trap)
    peak_volume = morning.loc[peak_time, "Volume"]
    start_lookback = peak_time - pd.Timedelta(minutes=15)
    recent_history = day.loc[start_lookback : peak_time - pd.Timedelta(minutes=1)]
    
    if not recent_history.empty:
        avg_recent_volume = recent_history["Volume"].mean()
        if peak_volume < (avg_recent_volume * 2):
            return trades

    after_peak = day.loc[peak_time:]

    entry_price = None
    entry_time = None

    # ---------------------------------------------------------
    # RULE 2: EARLY ENTRY (2 RED CANDLES + LOWER LOW CONFIRMATION)
    # ---------------------------------------------------------
    for i in range(1, len(after_peak)):
        curr_candle = after_peak.iloc[i]
        prev_candle = after_peak.iloc[i-1]
        
        curr_is_red = curr_candle["Close"] < curr_candle["Open"]
        prev_is_red = prev_candle["Close"] < prev_candle["Open"]
        
        # Check for 2 consecutive red candles
        if curr_is_red and prev_is_red:
            # Confirm the second red candle actually pushed to a lower low
            if curr_candle["Low"] < prev_candle["Low"]:
                entry_price = curr_candle["Close"] 
                entry_time = after_peak.index[i]
                break

    if entry_price is None or entry_time is None:
        return trades

    # ---------------------------------------------------------
    # RULE 3: WIDENED TIME OF DAY FILTER
    # ---------------------------------------------------------
    # Avoid first 15 mins of chaos, but cut off at 1:00 PM to avoid afternoon grinders
    entry_clock_time = entry_time.time()
    start_window = datetime.time(9, 45) 
    cutoff_time = datetime.time(13, 0)
    
    if not (start_window <= entry_clock_time <= cutoff_time):
        return trades 

    # ---------------------------------------------------------
    # RULE 4: CHART-BASED RISK/REWARD (1:2)
    # ---------------------------------------------------------
    # Stop loss is placed strictly at the High of Day (the peak)
    stop_loss_target = peak_price 
    risk_per_share = stop_loss_target - entry_price
    
    # If risk is 0 or negative due to weird data, skip the trade safely
    if risk_per_share <= 0:
        return trades
        
    # Take Profit is exactly 2x your risk. Min value of 0.0001 to prevent negative targets.
    fade_target = max(entry_price - (risk_per_share * 2), 0.0001)
    
    remaining = day.loc[entry_time:] 

    exit_price = None
    exit_reason = "EOD"

    for row in remaining.itertuples():
        # Hit our 1:2 profit target
        if row.Low <= fade_target:
            exit_price = fade_target
            exit_reason = "Take Profit"
            break
        # Hit our Stop Loss (It broke the peak)
        elif row.High >= stop_loss_target:
            exit_price = stop_loss_target
            exit_reason = "Stop Loss"
            break
            
    if exit_price is None:
        exit_price = remaining.iloc[-1]["Close"]

    pnl = entry_price - exit_price 
    
    trades.append({
        "date": date,
        "ticker": ticker,
        "entry_time": entry_time.time(),
        "entry": round(entry_price, 4), 
        "exit": round(exit_price, 4),
        "reason": exit_reason,
        "pnl": round(pnl, 4)
    })
    return trades

# ===========================
# STEP 4: RUN EFFICIENT BACKTEST
# ===========================
all_trades = []
SLEEP_BETWEEN_REQUESTS = 13 

print("Scanning for spike dates, then backtesting...")

for ticker in tqdm(TICKERS):
    spike_dates = get_spike_dates(ticker)
    time.sleep(SLEEP_BETWEEN_REQUESTS) 
    
    if not spike_dates:
        continue 
        
    for target_date in spike_dates:
        minute_df = get_minute_data_for_day(ticker, target_date)
        time.sleep(SLEEP_BETWEEN_REQUESTS)
        
        if minute_df is not None and not minute_df.empty:
            trades = test_strategy(minute_df, ticker, target_date)
            all_trades.extend(trades)

# ===========================
# STEP 5: SAVE RESULTS
# ===========================
if all_trades:
    results_df = pd.DataFrame(all_trades)
    print("\nTotal Trades:", len(all_trades))
    
    # Let's add a quick win-rate calculation so you can see if the filters helped!
    wins = len(results_df[results_df['pnl'] > 0])
    win_rate = (wins / len(results_df)) * 100
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total PnL (Per Share): ${results_df['pnl'].sum():.2f}")
    
    print(results_df)
else:
    print("\nNo setups found.")

# API_KEY = "HvQaWaWYEHOywp1_whWMXynScr9JBpA5"
# XDGANgUgBLyThvlBdHJJBEExuAymiCmf






