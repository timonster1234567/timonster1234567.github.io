import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time as dt_time
import time
import math
import pytz

# --- Configuration ---
TRADIER_BASE_URL = "https://sandbox.tradier.com/v1" 
TRADIER_TOKEN = "PXy5iP0UE4giSbTtabAFamFxtBTH"
TRADIER_ACCOUNT_ID = "VA24296623"

HEADERS = {
    'Authorization': f'Bearer {TRADIER_TOKEN}',
    'Accept': 'application/json'
}

# Strategy Parameters
ACCOUNT_SIZE = 4000.00
TARGET_RISK = ACCOUNT_SIZE * 0.015   # Risking $60 per trade
MAX_INVESTMENT = ACCOUNT_SIZE * 0.50 # Cap per trade at $2,000
TICKERS = ["AAPL", "AVGO", "JPM", "AXP", "V", "CAT", "TXN", "MCD", "UNP", "ADI", "MRK", "SYK", "CME", "NSC", "ECL", "AON"]

SMA_WINDOW = 20            
STD_DEV_MULTIPLIER = 2   

# ==========================================
# TRADIER API HELPER FUNCTIONS
# ==========================================

def get_account_balances():
    url = f"{TRADIER_BASE_URL}/accounts/{TRADIER_ACCOUNT_ID}/balances"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return float(response.json()['balances'].get('total_cash', 0.0))
    return 0.0

def get_open_positions():
    url = f"{TRADIER_BASE_URL}/accounts/{TRADIER_ACCOUNT_ID}/positions"
    response = requests.get(url, headers=HEADERS)
    open_tickers = []
    if response.status_code == 200:
        positions = response.json().get('position')
        if positions:
            if isinstance(positions, dict):
                positions = [positions]
            open_tickers = [p['symbol'] for p in positions]
    return open_tickers

def get_intraday_data(ticker):
    """Fetches 5-minute intraday data for the last 3 days to calculate indicators."""
    now = datetime.now()
    start_date = (now - timedelta(days=4)).strftime('%Y-%m-%d %H:%M')
    end_date = now.strftime('%Y-%m-%d %H:%M')
    
    url = f"{TRADIER_BASE_URL}/markets/history"
    params = {'symbol': ticker, 'interval': '5min', 'start': start_date, 'end': end_date}
    
    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        data = response.json().get('history', {}).get('day')
        if data:
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            # Ensure timezone is Eastern
            df.index = df.index.tz_localize('UTC').tz_convert('US/Eastern')
            return df
    return pd.DataFrame()

def submit_bracket_order(ticker, shares, current_price, tp_price, sl_price):
    url = f"{TRADIER_BASE_URL}/accounts/{TRADIER_ACCOUNT_ID}/orders"
    entry_limit_price = current_price * 1.001 # 0.1% Slippage buffer ceiling
    
    payload = {
        'class': 'otoco',
        'symbol': ticker,
        'duration': 'day', # Day orders! Cancel at 4:00PM if not filled
        'type[0]': 'limit',
        'side[0]': 'buy',
        'quantity[0]': str(shares),
        'price[0]': str(round(entry_limit_price, 2)),
        'type[1]': 'limit',
        'side[1]': 'sell',
        'quantity[1]': str(shares),
        'price[1]': str(round(tp_price, 2)),
        'type[2]': 'stop',
        'side[2]': 'sell',
        'quantity[2]': str(shares),
        'stop[2]': str(round(sl_price, 2))
    }
    response = requests.post(url, headers=HEADERS, data=payload)
    if response.status_code == 200:
        print(f"   ✅ SUCCESS: Intraday Bracket Order placed for {shares} shares of {ticker}!")
    else:
        print(f"   ❌ ERROR: Order failed for {ticker}: {response.text}")

def close_position_market(ticker):
    """Panic button: Sells a position immediately at market price."""
    # Note: In a production bot, you must cancel the bracket's stop loss first! 
    # For this paper MVP, we assume the broker handles the override.
    url = f"{TRADIER_BASE_URL}/accounts/{TRADIER_ACCOUNT_ID}/orders"
    payload = {
        'class': 'equity',
        'symbol': ticker,
        'duration': 'day',
        'side': 'sell_short' if False else 'sell', # Simplify for MVP
        'quantity': 'all', # Tradier allows liquidating the position
        'type': 'market'
    }
    requests.post(url, headers=HEADERS, data=payload)
    print(f"   🚨 EOD FLATTEN: Liquidated {ticker} to cash.")

# ==========================================
# INDICATORS
# ==========================================

def calculate_indicators(df):
    df = df.copy()
    
    df['sma'] = df['close'].rolling(window=SMA_WINDOW).mean()
    df['std'] = df['close'].rolling(window=SMA_WINDOW).std()
    df['lower_band'] = df['sma'] - (df['std'] * STD_DEV_MULTIPLIER)

    delta = df['close'].diff()
    gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(com=13, adjust=False).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    df['calendar_date'] = df.index.date
    df['pv'] = df['close'] * df['volume']
    df['cumulative_pv'] = df.groupby('calendar_date')['pv'].cumsum()
    df['cumulative_vol'] = df.groupby('calendar_date')['volume'].cumsum()
    df['daily_vwap'] = df['cumulative_pv'] / df['cumulative_vol'].replace(0, pd.NA)
    df['daily_vwap'] = df['daily_vwap'].ffill()

    df['sma_50'] = df['close'].rolling(window=50).mean()

    return df.dropna()

# ==========================================
# MAIN INTRADAY LOOP
# ==========================================

def run_day_trade_bot():
    tz = pytz.timezone('US/Eastern')
    
    print("--- TRADIER DAY TRADING BOT ONLINE ---")
    
    while True:
        now = datetime.now(tz)
        market_time = now.time()
        
        # 1. Market Closed Check
        if market_time < dt_time(9, 30) or market_time > dt_time(16, 0):
            print(f"[{now.strftime('%H:%M:%S')}] Market Closed. Sleeping for 5 minutes...")
            time.sleep(300)
            continue
            
        # 2. EOD Flatten Protocol (3:58 PM)
        if market_time >= dt_time(15, 58):
            print("\n🚨 INITIATING EOD FLATTEN PROTOCOL 🚨")
            open_positions = get_open_positions()
            for ticker in open_positions:
                close_position_market(ticker)
            print("All positions flattened. Sleeping until tomorrow...")
            time.sleep(43200) # Sleep 12 hours
            continue
            
        # 3. Check "Golden Hours"
        morning_session = dt_time(9, 45) <= market_time <= dt_time(11, 15)
        afternoon_session = dt_time(14, 0) <= market_time <= dt_time(15, 0)
        
        if not (morning_session or afternoon_session):
            print(f"[{now.strftime('%H:%M:%S')}] Outside Golden Hours. Waiting...")
            time.sleep(60) # Wake up every minute to check time
            continue

        # 4. ACTIVE SCANNING 
        # Only run the heavy math when the minute ends in 0 or 5 (e.g., 10:05, 10:10)
        if now.minute % 5 == 0:
            print(f"\n[{now.strftime('%H:%M:%S')}] --- NEW 5-MIN CANDLE: SCANNING ---")
            available_cash = get_account_balances()
            open_positions = get_open_positions()
            
            for ticker in TICKERS:
                if ticker in open_positions:
                    continue # Already trading this ticker
                    
                df = get_intraday_data(ticker)
                if df.empty:
                    continue
                    
                df = calculate_indicators(df)
                if df.empty:
                    continue
                    
                today = df.iloc[-1]
                current_price = today['close']
                
                # --- ENTRY LOGIC ---
                if current_price < today['lower_band'] and current_price < today['daily_vwap'] and today['rsi'] < 30 and today['sma'] > today['sma_50']:
                    print(f"   🚨 MEAN REVERSION SIGNAL DETECTED for {ticker} at ${current_price:.2f}!")
                    
                    reward_distance = today['sma'] - current_price
                    stop_loss_distance = reward_distance / 1.5
                    
                    tp_price = current_price + (reward_distance * 0.85)
                    sl_price = current_price - stop_loss_distance
                    
                    required_shares_float = TARGET_RISK / stop_loss_distance
                    required_investment = required_shares_float * current_price
                    
                    if required_investment > MAX_INVESTMENT:
                        shares = math.floor(MAX_INVESTMENT / current_price)
                    else:
                        shares = math.floor(required_shares_float)
                        
                    capital_needed = shares * current_price
                    
                    if shares > 0 and available_cash >= capital_needed:
                        print(f"   -> Executing: Buying {shares} shares (Cost: ${capital_needed:.2f})")
                        submit_bracket_order(ticker, shares, current_price, tp_price, sl_price)
                        available_cash -= capital_needed 
                    else:
                        print(f"   -> ⚠️ Insufficient Cash or Risk Math failed.")

            # Sleep for 4.5 minutes so we don't spam the API until the next candle is almost ready
            time.sleep(270) 
        else:
            # Check the clock every 10 seconds until the next 5-minute mark
            time.sleep(10)

if __name__ == "__main__":
    # Start the infinite loop!
    run_day_trade_bot()