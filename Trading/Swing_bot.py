import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import math
import time
import pytz
import pandas_market_calendars as mcal

# --- Configuration ---
# Use 'https://sandbox.tradier.com/v1' for paper trading
# Use 'https://api.tradier.com/v1' for real money
TRADIER_BASE_URL = "https://sandbox.tradier.com/v1" 
TRADIER_TOKEN = "PXy5iP0UE4giSbTtabAFamFxtBTH"
TRADIER_ACCOUNT_ID = "VA24296623"

HEADERS = {
    'Authorization': f'Bearer {TRADIER_TOKEN}',
    'Accept': 'application/json'
}

# Strategy Parameters
ACCOUNT_SIZE = 6000.00
TARGET_RISK = ACCOUNT_SIZE * 0.015   # Risking $90 per trade
MAX_INVESTMENT = ACCOUNT_SIZE * 0.25 # Cap per trade at $1,500
TICKERS = ["NSC", "ECL", "UNP", "JPM", "AXP", "CME", "AVGO", "MCD", "AAPL", "CAT"]

# ==========================================
# TRADIER API HELPER FUNCTIONS
# ==========================================

def get_account_balances():
    """Fetches available cash from Tradier with error handling."""
    url = f"{TRADIER_BASE_URL}/accounts/{TRADIER_ACCOUNT_ID}/balances"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json().get('balances', {})
        return float(data.get('total_cash', 0.0))
    except requests.exceptions.RequestException as e:
        print(f"❌ Network Error fetching balances: {e}")
        return 0.0

def get_open_positions():
    """Fetches a list of tickers we currently own, handling Tradier's 'null' string quirk."""
    url = f"{TRADIER_BASE_URL}/accounts/{TRADIER_ACCOUNT_ID}/positions"
    open_tickers = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json().get('positions')
        
        # Tradier literally returns the string 'null' if there are no open positions
        if data and data != 'null':
            positions = data.get('position')
            if positions:
                if isinstance(positions, dict):
                    positions = [positions]
                open_tickers = [p['symbol'] for p in positions]
        return open_tickers
    except requests.exceptions.RequestException as e:
        print(f"❌ Network Error fetching positions: {e}")
        return []

def get_historical_data(ticker, current_time):
    """Fetches daily historical data using the timezone-aware current time."""
    end_date = current_time.strftime('%Y-%m-%d')
    start_date = (current_time - timedelta(days=150)).strftime('%Y-%m-%d')
    
    url = f"{TRADIER_BASE_URL}/markets/history"
    params = {'symbol': ticker, 'interval': 'daily', 'start': start_date, 'end': end_date}
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        response.raise_for_status()
        data = response.json().get('history', {}).get('day')
        if data:
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            return df
    except requests.exceptions.RequestException as e:
        print(f"   -> ❌ Network Error fetching history for {ticker}: {e}")
    return pd.DataFrame()

def get_realtime_quote(ticker):
    """Fetches the real-time bid/ask so our risk math isn't using delayed daily candle data."""
    url = f"{TRADIER_BASE_URL}/markets/quotes"
    params = {'symbols': ticker}
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        quote_data = response.json().get('quotes', {}).get('quote', {})
        # Prioritize the 'ask' price since we are buying, fallback to 'last' price
        return float(quote_data.get('ask', quote_data.get('last', 0.0)))
    except requests.exceptions.RequestException as e:
        print(f"   -> ❌ Network Error fetching quote for {ticker}: {e}")
        return 0.0

def submit_bracket_order(ticker, shares, current_price, tp_price, sl_price):
    """Submits the OTOCO (One-Triggers-a-One-Cancels-Other) order."""
    url = f"{TRADIER_BASE_URL}/accounts/{TRADIER_ACCOUNT_ID}/orders"
    
    # Widened slippage buffer to 0.25% to ensure EOD execution
    entry_limit_price = current_price * 1.0025 
    
    payload = {
        'class': 'otoco',
        'symbol': ticker,
        'duration': 'gtc',
        
        # Order 1: The Entry
        'type[0]': 'limit',
        'side[0]': 'buy',
        'quantity[0]': str(shares),
        'price[0]': str(round(entry_limit_price, 2)),
        
        # Order 2: The Take Profit
        'type[1]': 'limit',
        'side[1]': 'sell',
        'quantity[1]': str(shares),
        'price[1]': str(round(tp_price, 2)),
        
        # Order 3: The Stop Loss
        'type[2]': 'stop',
        'side[2]': 'sell',
        'quantity[2]': str(shares),
        'stop[2]': str(round(sl_price, 2))
    }
    
    try:
        response = requests.post(url, headers=HEADERS, data=payload, timeout=10)
        response.raise_for_status()
        print(f"   ✅ SUCCESS: Bracket Order placed for {shares} shares of {ticker}!")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ ERROR: Order failed for {ticker}: {e}")
        if response is not None:
            print(f"      Tradier Response: {response.text}")

# ==========================================
# INDICATORS & STRATEGY LOGIC
# ==========================================

def calculate_indicators(df):
    """Calculates EMA Crossovers and ATR."""
    df = df.copy()
    df['ema_10'] = df['close'].ewm(span=10, adjust=False).mean()
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    
    df['prev_close'] = df['close'].shift(1)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['prev_close'])
    df['tr3'] = abs(df['low'] - df['prev_close'])
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=14).mean()

    df['trend'] = np.where(df['ema_10'] > df['ema_21'], 1, -1)
    df['crossover'] = df['trend'].diff() 
    return df

def run_swing_bot(current_time):
    """Main scanning and execution logic."""
    print(f"--- STARTING TRADIER SWING BOT: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')} ---")
    
    available_cash = get_account_balances()
    open_positions = get_open_positions()
    
    print(f"Available Cash: ${available_cash:.2f}")
    print(f"Current Open Positions: {open_positions}\n")
    
    if available_cash <= 0:
        print("Not enough cash to trade. Aborting scan.")
        return

    # "Turnaround Tuesday" Filter using the timezone-aware time
    if current_time.weekday() == 1:
        print("Today is Tuesday. The 'Turnaround Tuesday' filter is active. Skipping entries today.")
        return

    for ticker in TICKERS:
        if ticker in open_positions:
            print(f"[{ticker}] Already holding. Skipping.")
            continue
            
        print(f"[{ticker}] Scanning setups...")
        df = get_historical_data(ticker, current_time)
        
        if df.empty or len(df) < 50:
            print(f"   -> Insufficient data. Skipping.")
            continue
            
        df = calculate_indicators(df)
        today = df.iloc[-1]
        
        # --- ENTRY LOGIC ---
        if today['crossover'] == 2.0 and today['close'] > today['sma_50']:
            
            # Fetch real-time price for accurate math, fallback to history close if it fails
            rt_price = get_realtime_quote(ticker)
            execution_price = rt_price if rt_price > 0 else today['close']
            
            print(f"   🚨 BUY SIGNAL DETECTED for {ticker} at ~${execution_price:.2f}!")
            
            # --- RISK MANAGEMENT & MATH ---
            stop_loss_distance = today['atr'] * 2.0
            sl_price = execution_price - stop_loss_distance
            tp_price = execution_price + (stop_loss_distance * 2.0)
            
            # Catch edge cases where ATR is somehow 0 or broken
            if stop_loss_distance <= 0:
                print("   -> ⚠️ Invalid ATR. Skipping.")
                continue
                
            required_shares_float = TARGET_RISK / stop_loss_distance
            required_investment = required_shares_float * execution_price
            
            if required_investment > MAX_INVESTMENT:
                shares = math.floor(MAX_INVESTMENT / execution_price)
            else:
                shares = math.floor(required_shares_float)
                
            # Use round() to avoid floating point precision bugs
            capital_needed = round(shares * execution_price, 2)
            
            if shares <= 0:
                print("   -> Risk math resulted in 0 shares. Skipping.")
                continue
                
            # --- PRE-TRADE CASH CHECK ---
            if available_cash >= capital_needed:
                print(f"   -> Executing: Buying {shares} shares (Cost: ${capital_needed:.2f})")
                print(f"   -> Targets: SL: ${sl_price:.2f} | TP: ${tp_price:.2f}")
                
                # Critical Fix: Added execution_price to the argument list!
                submit_bracket_order(ticker, shares, execution_price, tp_price, sl_price)
                
                # Deduct to protect subsequent loops
                available_cash -= capital_needed 
            else:
                print(f"   -> ⚠️ Insufficient Cash! Need ${capital_needed:.2f}, but only have ${available_cash:.2f}. Skipping.")
        else:
            print(f"   -> No setup today.")

    print("\n--- SCAN COMPLETE ---")


def run_continuous_swing_bot():
    """Keeps the bot alive, dynamically checking market hours and triggering 15 mins before close."""
    tz = pytz.timezone('US/Eastern')
    nyse = mcal.get_calendar('NYSE')
    
    print("--- SWING BOT ONLINE: WAITING FOR MARKET CLOSE ---")
    
    while True:
        now = datetime.now(tz)
        
        # Pull today's market schedule
        schedule = nyse.schedule(start_date=now.date(), end_date=now.date())
        
        if schedule.empty:
            print(f"[{now.strftime('%Y-%m-%d')}] Market is closed today (Weekend/Holiday). Sleeping for 12 hours.")
            time.sleep(43200) # Sleep 12 hours
            continue
            
        # Get the official close time for today (timezone aware)
        market_close = schedule.iloc[0]['market_close']
        
        # We want to run 15 minutes before the bell
        trigger_time = market_close - timedelta(minutes=15)
        
        # Convert trigger_time to US/Eastern to match `now`
        trigger_time = trigger_time.astimezone(tz)
        
        if now < trigger_time:
            # Calculate seconds until trigger
            wait_seconds = (trigger_time - now).total_seconds()
            
            # If we are far away, sleep in chunks. If close, sleep the exact remainder.
            if wait_seconds > 300:
                time.sleep(300) # Wake up every 5 minutes to check
            else:
                print(f"\nApproaching trigger time. Sleeping {int(wait_seconds)} seconds...")
                time.sleep(wait_seconds)
                
        elif now >= trigger_time and now < market_close:
            print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] Market closing soon! Running daily scan...")
            
            # Pass the timezone-aware 'now' into the bot!
            run_swing_bot(now) 
            
            # Sleep until the market is officially closed so we don't run twice
            sleep_until_close = (market_close.astimezone(tz) - datetime.now(tz)).total_seconds()
            if sleep_until_close > 0:
                time.sleep(sleep_until_close + 60) # Sleep until 1 min past close
        else:
            # Market is already closed for the day. Sleep for a few hours.
            time.sleep(14400) # Sleep 4 hours

if __name__ == "__main__":
    run_continuous_swing_bot()