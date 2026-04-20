import requests
import time
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import datetime

# --- 1. CONFIGURATION ---
POLYGON_API_KEY = 'XDGANgUgBLyThvlBdHJJBEExuAymiCmf'
# TICKERS = ['SPY', "QQQ", "NVDA", "TSLA", "GLD", "IWM"] # A mix of large-cap stocks and ETFs for testing
TICKERS = ["META", "COIN", "NVDA", "TSLA", "SMCI", "IWM", "AMD"] # A mix of large-cap stocks and ETFs for testing
TICKERS = ['COIN', 'TSLA', 'CRWD']
TICKERS = ['SPOT', 'UBER', 'DDOG']
START_DATE = '2024-04-05'
END_DATE = '2026-04-05'
INVESTMENT_PER_TRADE = 1000.00

def fetch_polygon_data_with_sleep(ticker, start_date, end_date):
    """
    Fetches historical data from Polygon using direct requests to explicitly
    manage rate limits (max 5 requests per minute).
    """
    print(f"📡 Fetching data for {ticker} from Polygon (Free Tier - 5 req/min)...")
    time.sleep(13)
    
    all_results = []
    # Base URL for 5-minute aggregates
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/5/minute/{start_date}/{end_date}?adjusted=true&sort=asc&limit=50000&apiKey={POLYGON_API_KEY}"
    
    while url:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'results' in data:
                all_results.extend(data['results'])
                print(f"   ✅ Fetched {len(data['results'])} candles...")
            
            # Check if there is more data to fetch (pagination)
            if 'next_url' in data:
                url = data['next_url'] + f"&apiKey={POLYGON_API_KEY}"
                print("   ⏳ Paginating... sleeping for 13 seconds to respect rate limits.")
                time.sleep(13) 
            else:
                url = None # Exits the loop
                
        # Catch the 429 Too Many Requests error just in case
        elif response.status_code == 429:
            print("   ⚠️ Rate limited! Sleeping for 60 seconds before retrying...")
            time.sleep(60)
            
        else:
            print(f"   ❌ Error: {response.status_code}")
            print(response.text)
            break
            
    # --- PROCESS THE DATA ---
    if all_results:
        df = pd.DataFrame(all_results)
        # Pandas tz_convert safely handles Daylight Saving Time!
        df['timestamp'] = pd.to_datetime(df['t'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('America/New_York')
        
        df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume', 'vw': 'vwap'}, inplace=True)
        df.set_index('timestamp', inplace=True)
        
        print(f"📦 Successfully loaded {len(df)} total candles for {ticker}.")
        return df
    
    return pd.DataFrame()

def fetch_polygon_daily_sma(ticker, end_date):
    """Fetches daily data to calculate the 50-day SMA."""
    print(f"📈 Fetching Daily Data for {ticker} SMA from Polygon...")
    
    # Start a year earlier to ensure we have at least 50 days to calculate the SMA
    start_date = (pd.to_datetime(end_date) - pd.Timedelta(days=365)).strftime('%Y-%m-%d')
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}?adjusted=true&sort=asc&limit=50000&apiKey={POLYGON_API_KEY}"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'results' in data:
            df = pd.DataFrame(data['results'])
            df['date'] = pd.to_datetime(df['t'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('America/New_York').dt.strftime('%Y-%m-%d')
            
            # Calculate 50 SMA and shift it by 1 so today's trading uses yesterday's closing SMA
            df['sma_50'] = df['c'].rolling(window=50).mean().shift(1)
            return dict(zip(df['date'], df['sma_50']))
            
    print("   ⚠️ Failed to fetch daily SMA.")
    return {}

# --- 2. STRATEGY LOGIC (FIXED LOOK-AHEAD BIAS) ---
def identify_trend_and_zones(df, consolidation_period=7):
    df = df.copy()
    
    # 1. Calculate ATR
    df['prev_close'] = df['close'].shift(1)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = (df['high'] - df['prev_close']).abs()
    df['tr3'] = (df['low'] - df['prev_close']).abs()
    df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr'] = df['true_range'].rolling(window=14).mean()
    df.drop(columns=['prev_close', 'tr1', 'tr2', 'tr3', 'true_range'], inplace=True)
    
    # 2. Trend Logic (EMAs)
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['uptrend'] = (df['ema_50'] > df['ema_200']) & (df['close'] > df['ema_50']) & (df['close'] > df['vwap'])
    
    # 3. Normalized Demand Zone Logic (CORRECTED)
    df['rolling_std'] = df['close'].rolling(window=consolidation_period).std()
    
    # Did we consolidate BEFORE this candle? (Shift by 1)
    consolidation_mask = df['rolling_std'].shift(1) < df['rolling_std'].rolling(50).median().shift(1)
    
    # Did THIS candle break out? (Using absolute past return, not future)
    df['past_return_abs'] = (df['close'] - df['close'].shift(1)).abs()
    breakout_mask = df['past_return_abs'] > (df['atr'].shift(1) * 1.5)
    
    df['is_demand_zone_formation'] = consolidation_mask & breakout_mask
    
    # Zones are generated based on the past consolidation
    df['dz_upper'] = np.where(df['is_demand_zone_formation'], df['high'].shift(1).rolling(consolidation_period).max(), np.nan)
    df['dz_lower'] = np.where(df['is_demand_zone_formation'], df['low'].shift(1).rolling(consolidation_period).min(), np.nan)
    df['active_dz_upper'] = df['dz_upper'].ffill()
    df['active_dz_lower'] = df['dz_lower'].ffill()
    
    return df

# --- 3. BACKTEST ENGINE ---
def run_backtest(df, daily_sma_dict):
    in_position = False
    entry_price = 0
    stop_loss = 0
    risk_per_share = 0
    entry_index_time = None 
    trades = []
    
    SLIPPAGE = 0.02 
    MARKET_OPEN = datetime.time(13, 00)      
    LUNCH_START = datetime.time(12, 00)      
    LUNCH_END = datetime.time(13, 00)        
    BLACKOUT_START = datetime.time(14, 00)   
    BLACKOUT_END = datetime.time(14, 30)     
    NEW_ENTRY_CUTOFF = datetime.time(15, 15) 
    EOD_EXIT_TIME = datetime.time(15, 45)    
    
    for index, row in df.iterrows():
        current_time = index.time()
        current_date_str = index.strftime('%Y-%m-%d')
        day_of_week = index.dayofweek 
        
        today_daily_sma = daily_sma_dict.get(current_date_str, 0)
        
        # --- 1. EOD CUTOFF ---
        if current_time >= EOD_EXIT_TIME:
            if in_position:
                in_position = False
                trades.append({'action': 'SELL', 'price': row['close'] - SLIPPAGE, 'time': index, 'reason': 'EOD Cutoff'})
            continue 
            
        # --- 2. TRAILING STOP & EXIT LOGIC ---
        if in_position:
            current_profit_per_share = row['close'] - entry_price
            
            # Target Exit (3R)
            if current_profit_per_share >= (risk_per_share * 3.0):
                in_position = False
                trades.append({'action': 'SELL', 'price': row['close'] - SLIPPAGE, 'time': index, 'reason': 'TP (3R Target)'})
                continue

            # Stop Loss Exit
            if row['close'] <= stop_loss: 
                in_position = False
                trades.append({'action': 'SELL', 'price': row['close'] - SLIPPAGE, 'time': index, 'reason': 'SL / Trail Exit'})
                continue
                
            # Time-Based Exit
            time_in_trade = index - entry_index_time
            if time_in_trade >= pd.Timedelta(minutes=60) and current_profit_per_share <= 0:
                in_position = False
                trades.append({'action': 'SELL', 'price': row['close'] - SLIPPAGE, 'time': index, 'reason': 'Time Stop (Stagnant)'})
                continue
                
            # Trailing Logic
            if current_profit_per_share >= (risk_per_share * 1.0):
                if stop_loss < entry_price: stop_loss = entry_price 
                
            if current_profit_per_share >= (risk_per_share * 1.5):
                locked_profit_stop = entry_price + (risk_per_share * 0.5)
                if stop_loss < locked_profit_stop: stop_loss = locked_profit_stop
            
            if current_profit_per_share >= (risk_per_share * 2.0):
                locked_profit_stop = entry_price + (risk_per_share * 1.0)
                if stop_loss < locked_profit_stop: stop_loss = locked_profit_stop

        # --- 3. ENTRY LOGIC ---
        is_valid_time = (MARKET_OPEN <= current_time <= NEW_ENTRY_CUTOFF) and not (BLACKOUT_START <= current_time < BLACKOUT_END) and not (LUNCH_START <= current_time < LUNCH_END)
        is_not_friday = day_of_week != 4 
        is_above_daily_sma = row['close'] > today_daily_sma
        
        if not in_position and is_valid_time and is_above_daily_sma and is_not_friday:
            if row['uptrend']:
                if pd.notna(row['active_dz_upper']) and (row['low'] <= row['active_dz_upper'] and row['high'] >= row['active_dz_lower']):
                    in_position = True
                    entry_price = row['close'] + SLIPPAGE 
                    entry_index_time = index 
                    
                    # Make sure we don't divide by zero or have a 0 ATR
                    risk_per_share = max(row['atr'] * 1.5, 0.01)
                    stop_loss = entry_price - risk_per_share
                    
                    trades.append({'action': 'BUY', 'price': entry_price, 'time': index})
                    
    return trades

# --- EXECUTION ---
if __name__ == "__main__":
    grand_total_pnl = 0
    grand_total_trades = 0
    all_detailed_trades = []

    print(f"🚀 Starting Multi-Ticker Backtest (${INVESTMENT_PER_TRADE} per trade)")
    print("=" * 50)

    for ticker in TICKERS:
        print(f"\n--- Testing {ticker} ---")
        
        daily_sma_dict = fetch_polygon_daily_sma(ticker, END_DATE)
        market_data = fetch_polygon_data_with_sleep(ticker, START_DATE, END_DATE)
        
        if market_data.empty:
            print(f"⚠️ No data fetched for {ticker}. Skipping.")
            continue
            
        market_data.dropna(inplace=True) 
        analyzed_data = identify_trend_and_zones(market_data, consolidation_period=7)
        trade_results = run_backtest(analyzed_data, daily_sma_dict)
        
        ticker_profits = 0
        total_trades = len(trade_results) // 2
        
        for i in range(1, len(trade_results), 2):
            if i < len(trade_results):
                buy_trade = trade_results[i-1]
                sell_trade = trade_results[i]
                
                buy_price = buy_trade['price']
                sell_price = sell_trade['price']
                
                shares = INVESTMENT_PER_TRADE / buy_price
                trade_profit = shares * (sell_price - buy_price)
                ticker_profits += trade_profit
                
                all_detailed_trades.append({
                    'Ticker': ticker,
                    'Entry Time': buy_trade['time'],
                    'Exit Time': sell_trade['time'],
                    'Entry Price': round(buy_price, 2),
                    'Exit Price': round(sell_price, 2),
                    'Exit Reason': sell_trade.get('reason', 'Unknown'),
                    'Shares': round(shares, 4),
                    'PnL': round(trade_profit, 2)
                })
                
        print(f"🏁 {ticker} Totals | Trades: {total_trades} | Net PnL: ${ticker_profits:.2f}")
        
        grand_total_trades += total_trades
        grand_total_pnl += ticker_profits

    print("\n" + "=" * 50)
    print(f"🏆 GRAND TOTALS (All Tickers)")
    print(f"Total Trades: {grand_total_trades}")
    print(f"Total Net PnL: ${grand_total_pnl:.2f} (Based on ${INVESTMENT_PER_TRADE} per trade)")
    print("=" * 50)

    # --- EXPORT THE LOG ---
    if all_detailed_trades:
        log_df = pd.DataFrame(all_detailed_trades)
        log_df.to_csv("detailed_trade_log.csv", index=False)
        print(f"\n💾 SUCCESS! {len(log_df)} trades have been logged to 'detailed_trade_log.csv'.")
    else:
        print("\n⚠️ No trades were taken, so no CSV was created.")