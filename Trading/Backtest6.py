import pandas as pd
import numpy as np
import alpaca_trade_api as tradeapi

# --- Configuration ---
ALPACA_API_KEY = "PKS6FFEPOBJVJ4SD7ERATDEA43"
ALPACA_SECRET_KEY = "HH4hKrMc5BNSSLn7kJ8QGWvKzcmZ7ASdBU1L7sCgnCJe"

START_DATE = "2021-01-01"
END_DATE = "2026-01-01"    


ACCOUNT_SIZE = 5000
TARGET_RISK = 25.00         # Risking $50 per trade
MAX_INVESTMENT = 2500.00    

alpaca_client = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, 'https://paper-api.alpaca.markets', api_version='v2')

def fetch_5m_data(ticker, start, end):
    print(f"Downloading 5-minute data for {ticker}...")
    start_iso = pd.to_datetime(start).tz_localize('America/New_York').isoformat()
    end_iso = pd.to_datetime(end).tz_localize('America/New_York').isoformat()
    
    bars = alpaca_client.get_bars(
        ticker,
        tradeapi.TimeFrame(5, tradeapi.TimeFrameUnit.Minute),
        start=start_iso,
        end=end_iso,
        adjustment='all'
    ).df
    
    if not bars.empty:
        bars.index = bars.index.tz_convert('US/Eastern')
    return bars

def run_orb_backtest(df, ticker):
    trade_log = []
    
    # Group the data by Day 
    grouped_by_day = df.groupby(df.index.date)
    
    for date, day_data in grouped_by_day:
        if len(day_data) < 10:
            continue
            
        # --- CALCULATE DAILY VWAP ---
        typical_price = (day_data['high'] + day_data['low'] + day_data['close']) / 3
        day_data = day_data.copy() 
        day_data['vwap'] = (typical_price * day_data['volume']).cumsum() / day_data['volume'].cumsum()
            
        # 1. DEFINE THE 30-MINUTE OPENING RANGE
        first_30_mins = day_data.between_time('09:30', '09:55')
        if first_30_mins.empty:
            continue
            
        orb_high = first_30_mins['high'].max()
        orb_low = first_30_mins['low'].min()
        orb_range = orb_high - orb_low
        
        # --- NEW: CALCULATE AVERAGE MORNING VOLUME ---
        avg_orb_volume = first_30_mins['volume'].mean()
        
        # Avoid trading if the morning was insanely volatile
        if orb_range > (day_data['close'].iloc[0] * 0.04): 
            continue 

        in_trade = False
        position_type = None 
        entry_price = 0.0
        shares = 0
        target_tp = 0.0
        target_sl = 0.0
        
        # 2. WATCH FOR THE BREAKOUT 
        trading_hours = day_data.between_time('10:00', '15:45')
        
        for row in trading_hours.itertuples():
            current_time = row.Index
            current_vwap = row.vwap
            current_volume = row.volume
            
            # --- NEW: THE INSTITUTIONAL VOLUME SURGE CHECK ---
            # Is this 5-minute candle's volume at least 1.5x bigger than the morning average?
            is_volume_surge = current_volume > (avg_orb_volume * 1.5)
            
            # --- ENTRY LOGIC ---
            # NEW: We ONLY accept entries BEFORE 11:00 AM!
            if not in_trade and current_time.hour < 11:
                
                # ==== LONG LOGIC (VWAP + Volume Filter) ====
                if row.high > orb_high and orb_high > current_vwap and is_volume_surge:
                    in_trade = True
                    position_type = 'LONG'
                    
                    entry_price = orb_high + 0.0005 
                    target_sl = orb_high - (orb_range / 2) 
                    risk_per_share = entry_price - target_sl
                    target_tp = entry_price + (risk_per_share * 2.0)
                    shares = min(TARGET_RISK / risk_per_share, MAX_INVESTMENT / entry_price)

                # ==== SHORT LOGIC (Hybrid VWAP + Volume Filter) ====
                # elif row.low < orb_low and is_volume_surge:
                #     in_trade = True
                #     position_type = 'SHORT'
                    
                #     entry_price = orb_low - 0.02 
                #     target_sl = orb_low + (orb_range / 2)
                #     risk_per_share = target_sl - entry_price
                #     target_tp = entry_price - (risk_per_share * 2.0)
                #     shares = min(TARGET_RISK / risk_per_share, MAX_INVESTMENT / entry_price)

            # --- EXIT LOGIC ---
            elif in_trade:
                # EOD FLATTEN
                if current_time.hour == 15 and current_time.minute >= 45:
                    exit_price = row.close
                    
                    if position_type == 'LONG':
                        pnl = (exit_price - entry_price) * shares
                    else: 
                        pnl = (entry_price - exit_price) * shares
                        
                    trade_log.append({'Ticker': ticker, 'Type': position_type, 'Entry_Time': current_time, 'PnL': pnl, 'Reason': 'End of Day Exit'})
                    in_trade = False
                    break 
                
                # LONG EXITS
                if position_type == 'LONG':
                    if row.high >= target_tp:
                        pnl = (target_tp - entry_price) * shares
                        trade_log.append({'Ticker': ticker, 'Type': 'LONG', 'Entry_Time': current_time, 'PnL': pnl, 'Reason': 'Take Profit'})
                        in_trade = False
                        break 
                    elif row.low <= target_sl:
                        pnl = (target_sl - entry_price) * shares
                        trade_log.append({'Ticker': ticker, 'Type': 'LONG', 'Entry_Time': current_time, 'PnL': pnl, 'Reason': 'Stop Loss'})
                        in_trade = False
                        break

                # SHORT EXITS
                elif position_type == 'SHORT':
                    if row.low <= target_tp:
                        pnl = (entry_price - target_tp) * shares
                        trade_log.append({'Ticker': ticker, 'Type': 'SHORT', 'Entry_Time': current_time, 'PnL': pnl, 'Reason': 'Take Profit'})
                        in_trade = False
                        break
                    elif row.high >= target_sl:
                        pnl = (entry_price - target_sl) * shares
                        trade_log.append({'Ticker': ticker, 'Type': 'SHORT', 'Entry_Time': current_time, 'PnL': pnl, 'Reason': 'Stop Loss'})
                        in_trade = False
                        break

    return trade_log

if __name__ == "__main__":
    # Removed the chop (AMD & META) - Only trading the High-Octane Tickers!
    # tickers_to_test = ["NVDA", "TSLA", "SPY", "QQQ"]
    tickers_to_test = [
        "COIN", "PLTR", "MU", "AVGO", "TSLA", "NVDA", "MSTR", "CRWD", "NFLX"
    ]
    
    all_trades = []
    for ticker in tickers_to_test:
        data = fetch_5m_data(ticker, START_DATE, END_DATE)
        if data is not None:
            trades = run_orb_backtest(data, ticker)
            all_trades.extend(trades)
            print(f"   -> Found {len(trades)} ORB trades for {ticker}.")
            
    if all_trades:
        df_results = pd.DataFrame(all_trades)
        df_results.to_csv("orb_backtest_master.csv", index=False)
        
        total_trades = len(df_results)
        winning_trades = df_results[df_results['PnL'] > 0]
        losing_trades = df_results[df_results['PnL'] <= 0]
        
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
        gross_profit = winning_trades['PnL'].sum()
        gross_loss = abs(losing_trades['PnL'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        
        print("\n========================================")
        print("  MASTER ORB RESULTS (VOL + TIME FILTER)  ")
        print("========================================")
        print(f"Total Trades:    {total_trades}")
        print(f"Win Rate:        {win_rate:.1f}%")
        print(f"Profit Factor:   {profit_factor:.2f}")
        print(f"Net Profit:      ${df_results['PnL'].sum():.2f}")
        print("========================================")
        print("✅ Trade log saved to 'orb_backtest_master.csv'")
    else:
        print("No trades found.")