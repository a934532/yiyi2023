import ccxt
import pandas_ta as ta
import pandas as pd
import requests
import os
import time

# --- 設定區 ---
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

# 🔥 監控清單
# 新增參數 'lookback': 你要回頭檢查幾根 K 線？
# 對於 1m (1分鐘) 建議設 20~30 (以免 GitHub 遲到漏單)
# 對於 15m (15分鐘) 建議設 3~5 就好 (不然同一根訊號會重複通知很久)
WATCHLIST = [
    # 範例 1: BTC 1分鐘，回頭檢查 30 根 (過去30分鐘)，門檻 5M USDT
    {'symbol': 'BTC/USDT', 'timeframe': '1m', 'mode': 'volume', 'threshold': 6000000, 'lookback': 30},
    
    # 範例 2: DUSK 15分鐘，回頭檢查 3 根 (過去45分鐘)
    {'symbol': 'DUSK/USDT', 'timeframe': '15m', 'mode': 'rsi', 'upper': 70, 'lower': 34, 'lookback': 3},
    {'symbol': 'CHZ/USDT',  'timeframe': '15m', 'mode': 'rsi', 'upper': 70, 'lower': 20, 'lookback': 3},
    {'symbol': 'LIT/USDT',  'timeframe': '15m', 'mode': 'rsi', 'upper': 70, 'lower': 20, 'lookback': 3},
    {'symbol': 'ZEC/USDT',  'timeframe': '15m', 'mode': 'rsi', 'upper': 65, 'lower': 20, 'lookback': 3},

]

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        payload = {"chat_id": TG_CHAT_ID, "text": message}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram 發送失敗: {e}")

def check_coin(exchange, config):
    symbol = config['symbol']
    tf = config['timeframe']
    mode = config.get('mode', 'rsi')
    lookback = config.get('lookback', 3) # 如果沒寫，預設檢查 3 根
    
    try:
        # 抓取 K 線 (為了檢查 30 根，我們抓 100 根比較安全)
        bars = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
        df = pd.DataFrame(bars, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        
        # 轉換時間為台灣時間
        df['dt'] = pd.to_datetime(df['ts'], unit='ms') + pd.Timedelta(hours=8)
        
        # --- 🔎 模式 A: 成交量監控 ---
        if mode == 'volume':
            threshold = config['threshold']
            df['vol_usdt'] = df['v'] * df['c']
            
            # 🔥【動態調整】根據設定的 lookback 決定檢查範圍
            # iloc[-31:-1] 代表檢查倒數第 31 根到倒數第 2 根
            check_range = df.iloc[-(lookback+1):-1]
            
            found = False
            for i, row in check_range.iterrows():
                vol = row['vol_usdt']
                if vol >= threshold:
                    time_str = row['dt'].strftime('%H:%M')
                    vol_m = vol / 1000000 
                    
                    msg = f"🚨 {symbol} ({tf}) 爆量警告！\n時間：{time_str}\n成交額：{vol_m:.2f} M\n(檢查範圍：過去 {lookback} 根)"
                    send_telegram(msg)
                    found = True
            
            if not found:
                last_vol = df['vol_usdt'].iloc[-2] / 1000000
                print(f"{symbol} ({tf}) 無爆量 (最新: {last_vol:.2f} M)")

        # --- 🔎 模式 B: RSI 監控 ---
        elif mode == 'rsi':
            df['rsi'] = ta.rsi(df['c'], length=14)
            check_range = df.iloc[-(lookback+1):-1]
            
            found = False
            for i, row in check_range.iterrows():
                rsi_val = float(row['rsi'])
                
                if rsi_val >= config['upper']:
                    time_str = row['dt'].strftime('%H:%M')
                    msg = f"🔥 {symbol} ({tf}) RSI 超買\n時間：{time_str}\n數值：{rsi_val:.2f}"
                    send_telegram(msg)
                    found = True
                elif rsi_val <= config['lower']:
                    time_str = row['dt'].strftime('%H:%M')
                    msg = f"❄️ {symbol} ({tf}) RSI 超賣\n時間：{time_str}\n數值：{rsi_val:.2f}"
                    send_telegram(msg)
                    found = True
            
            if not found:
                 print(f"{symbol} ({tf}) RSI 無訊號 (最新: {df['rsi'].iloc[-2]:.2f})")

    except Exception as e:
        print(f"❌ 監控 {symbol} 錯誤: {e}")

def run_monitor():
    exchange = ccxt.kucoin() 
    print(f"--- 開始掃描 ---")
    
    for config in WATCHLIST:
        check_coin(exchange, config)
        time.sleep(1)

if __name__ == "__main__":
    run_monitor()
