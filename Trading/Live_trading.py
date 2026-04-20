import time
import requests
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
import datetime

# ===========================
# CREDENTIALS & CONFIG
# ===========================
# Get these from your Alpaca Dashboard (Paper Trading)
ALPACA_KEY = "YOUR_PAPER_KEY"
ALPACA_SECRET = "YOUR_PAPER_SECRET"
DISCORD_WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_URL"

# Initialize Clients
trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)
data_client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)

# Strategy Settings
TICKER = "XWEL"
QTY = 10  # Start very small!
SPIKE_THRESHOLD = 1.20 

def send_notification(message):
    payload = {"content": f"🚀 **TradeBot Alert**: {message}"}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def get_live_stats(symbol):
    # Fetch the last 15 minutes of data to check for spikes/red candles
    now = datetime.datetime.now(datetime.timezone.utc)
    request_params = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame.Minute,
        start=now - datetime.timedelta(minutes=15)
    )
    bars = data_client.get_stock_bars(request_params)
    return bars.df

# ===========================
# THE LIVE LOOP
# ===========================
print("Bot started... monitoring market.")
send_notification("Bot is now ONLINE and monitoring " + TICKER)

while True:
    try:
        df = get_live_stats(TICKER)
        if df.empty:
            continue
            
        current_price = df.iloc[-1]['close']
        open_price = df.iloc[0]['open'] # Simplified for example
        
        # 1. LOGIC: Check for 20% Spike
        if current_price >= (open_price * SPIKE_THRESHOLD):
            
            # 2. LOGIC: Check for 3 Red Candles
            last_3 = df.tail(3)
            if all(last_3['close'] < last_3['open']):
                
                print(f"Conditions met for {TICKER}! Executing Short...")
                
                # 3. EXECUTION: Submit Market Order (Short)
                order_data = MarketOrderRequest(
                    symbol=TICKER,
                    qty=QTY,
                    side=OrderSide.SELL, # 'Sell' opens a short position
                    time_in_force=TimeInForce.DAY
                )
                
                order = trading_client.submit_order(order_data)
                
                # 4. NOTIFY: Ping Discord
                send_notification(f"ENTRY: Shorted {QTY} shares of {TICKER} at ${current_price}")
                
                # Sleep to avoid double-entry (Wait 30 mins after a trade)
                time.sleep(1800) 

    except Exception as e:
        print(f"Error: {e}")
        
    time.sleep(60) # Check every minute