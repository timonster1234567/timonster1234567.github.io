import pandas as pd
import numpy as np
import alpaca_trade_api as tradeapi
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. CONFIGURATION & API KEYS
# ==========================================
ALPACA_API_KEY = "PKS6FFEPOBJVJ4SD7ERATDEA43"
ALPACA_SECRET_KEY = "HH4hKrMc5BNSSLn7kJ8QGWvKzcmZ7ASdBU1L7sCgnCJe"

# Pairs to Trade
SYM_1 = "PEP"   
SYM_2 = "KO"  

START_DATE = "2021-01-01"
END_DATE = "2026-01-01"

# ==========================================
# NEW RISK MANAGEMENT PARAMETERS
# ==========================================
LOOKBACK = 20        
ENTRY_Z = 2.0        
EXIT_Z = 0.0         
STOP_Z = 3.5           # Hard Stop Loss: Cut if spread stretches to 3.5 standard deviations
MAX_HOLD_DAYS = 15     # Time Stop: Cut if we hold the trade for 15 days without reverting

alpaca = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, 'https://paper-api.alpaca.markets', api_version='v2')

def fetch_daily_data(ticker, start, end):
    print(f"Downloading daily data for {ticker}...")
    start_iso = pd.to_datetime(start).tz_localize('America/New_York').isoformat()
    end_iso = pd.to_datetime(end).tz_localize('America/New_York').isoformat()
    
    bars = alpaca.get_bars(
        ticker,
        tradeapi.TimeFrame(1, tradeapi.TimeFrameUnit.Day),
        start=start_iso,
        end=end_iso,
        adjustment='all'
    ).df
    
    if not bars.empty:
        bars.index = bars.index.tz_convert('US/Eastern')
        return bars[['close']].rename(columns={'close': ticker})
    return pd.DataFrame()

def run_pairs_backtest():
    df1 = fetch_daily_data(SYM_1, START_DATE, END_DATE)
    df2 = fetch_daily_data(SYM_2, START_DATE, END_DATE)
    df = df1.join(df2, how='inner')
    
    df['Ratio'] = df[SYM_1] / df[SYM_2]
    df['Mean'] = df['Ratio'].rolling(window=LOOKBACK).mean()
    df['Std'] = df['Ratio'].rolling(window=LOOKBACK).std()
    df['Z_Score'] = (df['Ratio'] - df['Mean']) / df['Std']
    
    df['Signal'] = 0
    df['Exit_Reason'] = ''
    
    in_position = 0 
    days_held = 0
    exit_reason = ''
    
    for i in range(len(df)):
        z = df['Z_Score'].iloc[i]
        
        # ENTRY LOGIC
        if in_position == 0:
            if z <= -ENTRY_Z:
                in_position = 1
                days_held = 0
            elif z >= ENTRY_Z:
                in_position = -1
                days_held = 0
                
        # EXIT LOGIC
        else:
            days_held += 1
            
            # 1. Broken Spread Stop Loss
            if (in_position == 1 and z <= -STOP_Z) or (in_position == -1 and z >= STOP_Z):
                in_position = 0
                exit_reason = 'Broken Spread Stop'
                
            # 2. Time Stop
            elif days_held >= MAX_HOLD_DAYS:
                in_position = 0
                exit_reason = '15-Day Time Stop'
                
            # 3. Take Profit (Reverted to Mean)
            elif (in_position == 1 and z >= EXIT_Z) or (in_position == -1 and z <= EXIT_Z):
                in_position = 0
                exit_reason = 'Take Profit'
                
        df['Signal'].iloc[i] = in_position
        if in_position == 0 and days_held > 0:
            df['Exit_Reason'].iloc[i] = exit_reason
            days_held = 0 # Reset for the next trade

    df['Position'] = df['Signal'].shift(1).fillna(0)
    df['Triggered_Exit'] = df['Exit_Reason'].shift(1).fillna('')
    
    df[f'{SYM_1}_Ret'] = df[SYM_1].pct_change()
    df[f'{SYM_2}_Ret'] = df[SYM_2].pct_change()
    df['Strategy_Ret'] = df['Position'] * (df[f'{SYM_1}_Ret'] - df[f'{SYM_2}_Ret'])
    df['Cumulative_Return'] = (1 + df['Strategy_Ret']).cumprod()
    
    # --- TRADE LOGGER ---
    trade_log = []
    current_trade = None
    
    for i in range(1, len(df)):
        pos = df['Position'].iloc[i]
        prev_pos = df['Position'].iloc[i-1]
        date = df.index[i]
        
        # Entry
        if pos != 0 and prev_pos == 0:
            current_trade = {
                'Entry_Date': date.date(),
                'Trade_Type': f"Long {SYM_1} / Short {SYM_2}" if pos == 1 else f"Short {SYM_1} / Long {SYM_2}",
                'Entry_Ratio': df['Ratio'].iloc[i],
                'Entry_Z_Score': df['Z_Score'].iloc[i-1]
            }
            
        # Exit
        elif pos == 0 and prev_pos != 0 and current_trade is not None:
            current_trade['Exit_Date'] = date.date()
            current_trade['Exit_Ratio'] = df['Ratio'].iloc[i]
            current_trade['Exit_Reason'] = df['Triggered_Exit'].iloc[i]
            
            if prev_pos == 1:
                pnl_pct = (current_trade['Exit_Ratio'] / current_trade['Entry_Ratio']) - 1
            else:
                pnl_pct = 1 - (current_trade['Exit_Ratio'] / current_trade['Entry_Ratio'])
                
            current_trade['PnL_Pct'] = round(pnl_pct * 100, 2)
            current_trade['Hold_Days'] = (current_trade['Exit_Date'] - current_trade['Entry_Date']).days
            
            trade_log.append(current_trade)
            current_trade = None
            
    if trade_log:
        log_df = pd.DataFrame(trade_log)
        log_df.to_csv("pairs_fixed_log.csv", index=False)
    
    total_return = (df['Cumulative_Return'].iloc[-1] - 1) * 100
    trades_taken = (df['Position'].diff() != 0).sum() // 2  
    win_rate_calc = df[df['Strategy_Ret'] != 0]
    total_active_days = len(win_rate_calc)
    win_days = len(win_rate_calc[win_rate_calc['Strategy_Ret'] > 0])
    win_rate = (win_days / total_active_days) * 100 if total_active_days > 0 else 0
    
    print("\n========================================")
    print(f" STAT-ARB PAIRS TRADING (WITH RISK MGMT)")
    print("========================================")
    print(f"Total Trades Taken: {trades_taken}")
    print(f"Days in the Market: {total_active_days}")
    print(f"Daily Win Rate:     {win_rate:.1f}%")
    print(f"Net Strategy Return: {total_return:.2f}%")
    print("========================================")

if __name__ == "__main__":
    run_pairs_backtest()