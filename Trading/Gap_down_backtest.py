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

# High-Beta / Retail-Heavy Basket
TICKERS = [
    # The Crypto Proxies (The absolute best performers)
    "COIN", "MARA", "RIOT", "MSTR", "HOOD", 
    
    # The Retail "Cult" / Meme Stocks
    "GME", "AMC", "CVNA", "UPST", "SOFI",
    
    # The High-Beta Tech & EV
    "TSLA", "PLTR", "SMCI", "RIVN", "ARM"
]

START_DATE = "2026-01-01"
END_DATE = "2026-04-24"

# Strategy Parameters
GAP_THRESHOLD = -0.04     # Must gap down at least -4%
ENTRY_TIME = "09:45:00"   # Wait for the first 15 mins to settle
EXIT_TIME = "15:45:00"    # EOD Time Stop to avoid overnight risk

alpaca = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, 'https://paper-api.alpaca.markets', api_version='v2')

# ==========================================
# 2. FETCH INTRADAY DATA (5-Minute Bars)
# ==========================================
def fetch_intraday_data(ticker, start, end):
    start_iso = pd.to_datetime(start).tz_localize('America/New_York').isoformat()
    end_iso = pd.to_datetime(end).tz_localize('America/New_York').isoformat()
    
    try:
        bars = alpaca.get_bars(
            ticker,
            tradeapi.TimeFrame(5, tradeapi.TimeFrameUnit.Minute),
            start=start_iso,
            end=end_iso,
            adjustment='all'
        ).df
        
        if not bars.empty:
            bars.index = bars.index.tz_convert('US/Eastern')
            return bars
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        
    return pd.DataFrame()

# ==========================================
# 3. MULTI-TICKER BACKTEST ENGINE
# ==========================================
def run_master_backtest():
    all_trades = []
    
    print("========================================")
    print(" STARTING MULTI-TICKER GAP FADE SCAN")
    print("========================================\n")
    
    for ticker in TICKERS:
        print(f"📥 Pulling and processing 5-min data for {ticker}...")
        df = fetch_intraday_data(ticker, START_DATE, END_DATE)
        
        if df.empty:
            print(f"⚠️ No data found for {ticker}. Skipping.\n")
            continue
            
        df['Date'] = df.index.date
        df['Time'] = df.index.time
        
        # Calculate Intraday VWAP
        df['Typical_Price'] = (df['high'] + df['low'] + df['close']) / 3
        df['VP'] = df['Typical_Price'] * df['volume']
        df['Cum_Vol'] = df.groupby('Date')['volume'].cumsum()
        df['Cum_VP'] = df.groupby('Date')['VP'].cumsum()
        df['VWAP'] = df['Cum_VP'] / df['Cum_Vol']
        
        # Daily Close for Gap Calculation
        daily_close = df.groupby('Date')['close'].last().shift(1)
        grouped_days = df.groupby('Date')
        
        trades_for_ticker = 0
        
        for date, day_data in grouped_days:
            if date not in daily_close.index or pd.isna(daily_close[date]):
                continue
                
            prev_close = daily_close[date]
            
            if day_data.empty or day_data.index[0].time() > pd.to_datetime("09:35:00").time():
                continue 
                
            open_price = day_data.iloc[0]['open']
            gap_pct = (open_price - prev_close) / prev_close
            
            # RULE 1: Gap Threshold
            if gap_pct > GAP_THRESHOLD:
                continue
                
            morning_data = day_data.between_time("09:30:00", "09:40:00") 
            if morning_data.empty:
                continue
                
            # RULE 2: Set Target and Stop
            morning_low = morning_data['low'].min()
            target_price = prev_close 
            
            in_position = False
            entry_price = 0
            entry_time = None
            
            trading_hours = day_data.between_time(ENTRY_TIME, EXIT_TIME)
            
            for i in range(len(trading_hours)):
                bar = trading_hours.iloc[i]
                current_time = bar.name.time()
                
                # ENTRY
                if not in_position:
                    # BUG FIX: Ensure the gap hasn't already been filled before we buy!
                    if bar['close'] > bar['VWAP'] and bar['close'] > morning_low and bar['close'] < target_price:
                        in_position = True
                        entry_price = bar['close']
                        entry_time = bar.name
                        
                # EXIT
                else:
                    # Stop Loss
                    if bar['low'] <= morning_low:
                        pnl_pct = (morning_low / entry_price) - 1
                        all_trades.append({
                            'Ticker': ticker,
                            'Date': date,
                            'Entry_Time': entry_time.time(),
                            'Exit_Time': current_time,
                            'Entry_Price': round(entry_price, 2),
                            'Exit_Price': round(morning_low, 2),
                            'Gap_Pct': round(gap_pct * 100, 2),
                            'Exit_Reason': 'Stop Loss',
                            'PnL_Pct': round(pnl_pct * 100, 2)
                        })
                        trades_for_ticker += 1
                        break 
                        
                    # Take Profit
                    elif bar['high'] >= target_price:
                        pnl_pct = (target_price / entry_price) - 1
                        all_trades.append({
                            'Ticker': ticker,
                            'Date': date,
                            'Entry_Time': entry_time.time(),
                            'Exit_Time': current_time,
                            'Entry_Price': round(entry_price, 2),
                            'Exit_Price': round(target_price, 2),
                            'Gap_Pct': round(gap_pct * 100, 2),
                            'Exit_Reason': 'Take Profit',
                            'PnL_Pct': round(pnl_pct * 100, 2)
                        })
                        trades_for_ticker += 1
                        break 
                        
                    # Time Stop
                    elif current_time >= pd.to_datetime(EXIT_TIME).time():
                        exit_price = bar['close']
                        pnl_pct = (exit_price / entry_price) - 1
                        all_trades.append({
                            'Ticker': ticker,
                            'Date': date,
                            'Entry_Time': entry_time.time(),
                            'Exit_Time': current_time,
                            'Entry_Price': round(entry_price, 2),
                            'Exit_Price': round(exit_price, 2),
                            'Gap_Pct': round(gap_pct * 100, 2),
                            'Exit_Reason': 'Time Stop',
                            'PnL_Pct': round(pnl_pct * 100, 2)
                        })
                        trades_for_ticker += 1
                        break 
                        
        print(f"✅ {ticker} complete. Trades found: {trades_for_ticker}\n")

    # ==========================================
    # 4. MASTER RESULTS & CSV EXPORT
    # ==========================================
    if all_trades:
        master_df = pd.DataFrame(all_trades)
        master_df.to_csv("gap_fade_master_log.csv", index=False)
        
        print("========================================")
        print(" FINAL STRATEGY METRICS BY TICKER")
        print("========================================")
        
        # Build Summary Table
        summary = []
        for ticker, group in master_df.groupby('Ticker'):
            total = len(group)
            wins = len(group[group['PnL_Pct'] > 0])
            wr = (wins / total) * 100 if total > 0 else 0
            net_pnl = group['PnL_Pct'].sum()
            avg_win = group[group['PnL_Pct'] > 0]['PnL_Pct'].mean() if wins > 0 else 0
            avg_loss = group[group['PnL_Pct'] <= 0]['PnL_Pct'].mean() if (total - wins) > 0 else 0
            
            summary.append({
                'Ticker': ticker,
                'Trades': total,
                'Win_Rate': f"{wr:.1f}%",
                'Net_PnL': f"{net_pnl:.2f}%",
                'Avg_Win': f"{avg_win:.2f}%",
                'Avg_Loss': f"{avg_loss:.2f}%"
            })
            
        summary_df = pd.DataFrame(summary).sort_values(by='Net_PnL', ascending=False)
        print(summary_df.to_string(index=False))
        print("========================================")
        print("✅ Full trade data saved to 'gap_fade_master_log.csv'")
        
    else:
        print("No trades triggered for any tickers in the basket.")

if __name__ == "__main__":
    run_master_backtest()