import pandas as pd
# from polygon import RESTClient
import numpy as np
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta, time as dt_time
# import time

# --- Configuration ---
API_KEY = "XDGANgUgBLyThvlBdHJJBEExuAymiCmf"

ALPACA_API_KEY = "PKS6FFEPOBJVJ4SD7ERATDEA43"
ALPACA_SECRET_KEY = "HH4hKrMc5BNSSLn7kJ8QGWvKzcmZ7ASdBU1L7sCgnCJe"

START_DATE = "2023-04-08"
END_DATE = "2026-05-13"    

# Strategy Parameters
ACCOUNT_SIZE = 6000
# TARGET_RISK = 50.00         # Risk exactly $5 per trade
TARGET_RISK = ACCOUNT_SIZE*0.015
# MAX_INVESTMENT = 2500.00   # Cap the max capital used per trade at $1,000
# MAX_INVESTMENT = ACCOUNT_SIZE*0.25
MAX_INVESTMENT = ACCOUNT_SIZE*0.2
SMA_WINDOW = 20            
STD_DEV_MULTIPLIER = 2   
SLIPPAGE_PER_SHARE = 0.04  # Simulates losing 2 cents on the buy, and 2 cents on the sell round-trip

# Initialize Alpaca Client
alpaca_client = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, 'https://paper-api.alpaca.markets', api_version='v2')

def fetch_historical_data(ticker, start, end):
    """Fetches 5-minute historical data using Alpaca."""
    print(f"      -> Downloading 5-minute data for {ticker} from Alpaca...")
    
    try:
        start_iso = pd.to_datetime(start).tz_localize('America/New_York').isoformat()
        end_iso = pd.to_datetime(end).tz_localize('America/New_York').isoformat()

        bars = alpaca_client.get_bars(
            ticker,
            tradeapi.TimeFrame(1, tradeapi.TimeFrameUnit.Day),
            start=start_iso,
            end=end_iso,
            adjustment='all' 
        ).df

        if bars.empty:
            print(f"   -> WARNING: Alpaca returned no data for {ticker}.")
            return None

        bars.index = bars.index.tz_convert('US/Eastern')
        
        if 'vwap' in bars.columns:
            bars = bars.rename(columns={'vwap': 'bar_vwap'})
            
        print(f"   -> Total data ready: {len(bars)} 5-minute candles.")
        return bars

    except Exception as e:
        print(f"      Error fetching data from Alpaca: {e}")
        return None

def calculate_indicators(df):
    df = df.copy()
    
    # 1. Swing Trading Moving Averages
    df['ema_10'] = df['close'].ewm(span=10, adjust=False).mean()
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    
    # 2. Daily ATR (For wide, safe Stop Losses)
    df['prev_close'] = df['close'].shift(1)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['prev_close'])
    df['tr3'] = abs(df['low'] - df['prev_close'])
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=14).mean()

    # 3. Crossover Math
    df['trend'] = np.where(df['ema_10'] > df['ema_21'], 1, -1)
    df['crossover'] = df['trend'].diff() 

    df = df.dropna(subset=['ema_10', 'ema_21', 'sma_50', 'atr', 'crossover'])
    return df


def run_backtest(df, ticker):
    in_trade = False
    entry_price = 0.0
    entry_date = None
    shares = 0
    target_sl = 0.0
    target_tp = 0.0
    trade_log = [] 
    
    for row in df.itertuples():
        current_price = row.close
        
        # --- SWING ENTRY LOGIC ---
        # 1. 10 EMA crosses ABOVE 21 EMA (crossover == 2.0)
        # 2. Price is safely above the 50-Day Moving Average (Macro Uptrend)
        if not in_trade and row.crossover == 2.0 and current_price > row.sma_50 and row.Index.dayofweek != 1:
        # if not in_trade and row.crossover == 2.0 and row.Index.dayofweek != 1:
            in_trade = True
            entry_price = current_price
            entry_date = row.Index
            
            # --- WIDE SWING STOP LOSS ---
            # Give the stock 2 full days of maximum average volatility to breathe
            stop_loss_distance = row.atr * 2.0 
            target_sl = entry_price - stop_loss_distance
            
            # Upgrade to a 2.0x Reward Target!
            target_tp = entry_price + (stop_loss_distance * 2.0)
            
            # Position Sizing
            required_shares = TARGET_RISK / stop_loss_distance
            required_investment = required_shares * entry_price
            
            if required_investment > MAX_INVESTMENT:
                shares = MAX_INVESTMENT / entry_price
            else:
                shares = required_shares
                
        # --- SWING EXIT LOGIC ---
        elif in_trade:
            # We are holding overnight! We only check if the High hit our Target, 
            # or if the Low hit our Stop Loss on this specific day.

            # 1. TAKE PROFIT
            if row.high >= target_tp:
                # We assume we get filled exactly at our target price
                exit_price = target_tp 
                pnl = ((exit_price - entry_price) * shares) - (shares * SLIPPAGE_PER_SHARE) 
                trade_log.append(log_trade(ticker, entry_date, entry_price, row.Index, exit_price, pnl, 'Take Profit'))
                in_trade = False
                
            # 2. STOP LOSS
            elif row.low <= target_sl:
                # If a stock gaps down overnight, we might get filled lower than our Stop Loss.
                # We take the worse of the two prices (The Open, or the Stop Target).
                exit_price = min(row.open, target_sl) 
                pnl = ((exit_price - entry_price) * shares) - (shares * SLIPPAGE_PER_SHARE)
                trade_log.append(log_trade(ticker, entry_date, entry_price, row.Index, exit_price, pnl, 'Stop Loss'))
                in_trade = False
                
            # 3. TREND REVERSAL EXIT (Safety Net)
            # If the 10 EMA crosses back below the 21 EMA before our targets are hit, 
            # the bull trend is officially dead. Cut the trade immediately.
            # elif row.crossover == -2.0:
            #     exit_price = row.close
            #     pnl = ((exit_price - entry_price) * shares) - (shares * SLIPPAGE_PER_SHARE)
            #     trade_log.append(log_trade(ticker, entry_date, entry_price, row.Index, exit_price, pnl, 'Trend Reversal Exit'))
            #     in_trade = False

    return trade_log

def log_trade(ticker, entry_time, entry_price, exit_time, exit_price, pnl, reason):
    return {
        'Ticker': ticker,
        'Entry_Time': entry_time,
        'Entry_Price': round(entry_price, 2),
        'Exit_Time': exit_time,
        'Exit_Price': round(exit_price, 2),
        'PnL_Dollars': round(pnl, 2),
        'Exit_Reason': reason
    }

if __name__ == "__main__":
    # The Holy Trinity!
    tickers_to_test = [
        "WMT", "XOM", "ECL", "NSC", "CME", "COST", 
        "AXP", "UNP", "JPM", "CAT", "AVGO", "AAPL", "MCD"
    ]
    # tickers_to_test = ["UNH", "LLY", "ABBV", "SYK", "WMT", "COST", "PG", "XOM", "CVX", "LMT", "RTX"]
    all_trade_results = [] 
    
    print(f"Running Multi-Year Backtest from {START_DATE} to {END_DATE}")
    print(f"Risk Params: Risk ${TARGET_RISK} per trade, Max Investment ${MAX_INVESTMENT}")
    
    for i, current_ticker in enumerate(tickers_to_test):
        print(f"[{i+1}/{len(tickers_to_test)}] Processing {current_ticker}...")
        
        historical_data = fetch_historical_data(current_ticker, START_DATE, END_DATE)
        
        if historical_data is not None and not historical_data.empty:
            processed_data = calculate_indicators(historical_data)
            ticker_trades = run_backtest(processed_data, current_ticker)
            all_trade_results.extend(ticker_trades)
            print(f"   -> Found {len(ticker_trades)} trades for {current_ticker}.\n")
            
    # --- GRAND TOTAL SUMMARY ---
    if all_trade_results:
        results_df = pd.DataFrame(all_trade_results)
        # results_df.to_csv("backtest_trade_results.csv", index=False)
        
        # total_trades = len(results_df)
        # winning_trades = len(results_df[results_df['PnL_Dollars'] > 0])
        # win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        # total_profit = results_df['PnL_Dollars'].sum()
        
        # print("========================================")
        # print("         GRAND TOTAL RESULTS            ")
        # print("========================================")
        # print(f"Total Trades Executed: {total_trades}")
        # print(f"Overall Win Rate:      {win_rate:.1f}%")
        # print(f"Total Net Profit:      ${total_profit:.2f}")
        # print("========================================")
        # print("✅ Trade log saved to 'backtest_trade_results.csv'")
        results_df.to_csv("backtest_trade_results.csv", index=False)
        
        # --- THE COMPOUNDING MATH TRICK ---
        # 1. Convert static dollar PnL into a percentage return of the base account
        results_df['Return_Pct'] = results_df['PnL_Dollars'] / ACCOUNT_SIZE
        
        # 2. Sort all trades across all tickers chronologically by Exit Time!
        results_df['Exit_Time'] = pd.to_datetime(results_df['Exit_Time'], utc=True)
        results_df = results_df.sort_values('Exit_Time').reset_index(drop=True)
        
        # 3. Calculate the compounded account balance over time
        results_df['Compounded_Balance'] = ACCOUNT_SIZE * (1 + results_df['Return_Pct']).cumprod()
        
        # Save a new CSV so you can see the account balance grow trade-by-trade!
        results_df.to_csv("compounded_results.csv", index=False)

        # --- GRAND TOTAL SUMMARY ---
        total_trades = len(results_df)
        winning_trades = len(results_df[results_df['PnL_Dollars'] > 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        static_profit = results_df['PnL_Dollars'].sum()
        compounded_profit = results_df['Compounded_Balance'].iloc[-1] - ACCOUNT_SIZE
        final_account_balance = results_df['Compounded_Balance'].iloc[-1]
        
        print("========================================")
        print("         GRAND TOTAL RESULTS            ")
        print("========================================")
        print(f"Total Trades Executed: {total_trades}")
        print(f"Overall Win Rate:      {win_rate:.1f}%")
        print(f"Static PnL (No Compounding):  ${static_profit:.2f}")
        print(f"Compounded PnL:               ${compounded_profit:.2f}")
        print(f"Final Account Balance:        ${final_account_balance:.2f}")
        print("========================================")
        print("✅ Trade logs saved to 'backtest_trade_results.csv' & 'compounded_results.csv'")
    else:
        print("✅ Backtests complete. (No trades were executed).")

