import ccxt
import pandas_ta as ta
import pandas as pd
import requests
import os
import time

# --- 設定區 ---
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

# 監控清單
WATCHLIST = [
    {'symbol': 'DUSK/USDT', 'timeframe': '15m', 'upper': 70, 'lower': 20},
    {'symbol': 'LIT/USDT',  'timeframe': '15m', 'upper': 70, 'lower': 20},
    {'symbol': 'CHZ/USDT',  'timeframe': '15m', 'upper': 70, 'lower': 20},
    {'symbol': 'ZEC/USDT',  'timeframe': '15m', 'upper': 65, 'lower': 20},
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
    
    try:
        # 抓取 K 線 (抓多一點，確保夠回頭看)
        bars = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=50)
        df = pd.DataFrame(bars, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        
        # 計算 RSI
        df['rsi'] = ta.rsi(df['c'], length=14)
        
        # 🔥【超級修正】回頭檢查最近 3 根收盤的 K 線
        # 這樣就算 GitHub 遲到 30 分鐘，我們也抓得到訊號！
        # iloc[-2] = 上一根 (剛收盤)
        # iloc[-3] = 上上根
        # iloc[-4] = 上上上根
        
        last_3_candles = df.iloc[-4:-1] # 取倒數第 4 到倒數第 2 根
        
        found_signal = False
        
        for index, row in last_3_candles.iterrows():
            rsi_val = float(row['rsi'])
            # 轉換時間戳記方便閱讀 (例如 19:15)
            time_str = pd.to_datetime(row['ts'], unit='ms').strftime('%H:%M')
            
            if rsi_val >= config['upper']:
                msg = f"🔥 {symbol} ({tf}) 補捉到訊號！\n時間：{time_str}\nRSI數值：{rsi_val:.2f} (高於 {config['upper']})"
                send_telegram(msg)
                found_signal = True
            elif rsi_val <= config['lower']:
                msg = f"❄️ {symbol} ({tf}) 補捉到訊號！\n時間：{time_str}\nRSI數值：{rsi_val:.2f} (低於 {config['lower']})"
                send_telegram(msg)
                found_signal = True

        if not found_signal:
            print(f"{symbol} ({tf}) 最近 3 根無訊號 (最新收盤 RSI: {df['rsi'].iloc[-2]:.2f})")
            
    except Exception as e:
        print(f"❌ 監控 {symbol} 錯誤: {e}")


def run_monitor():
    # 🔥【關鍵修正 2】改用 KuCoin，它的價格跟全球主流比較一致
    # 如果 KuCoin 也被擋，我們再換回 binanceus，但保留上面的 iloc[-2] 修正
    exchange = ccxt.kucoin()
 
    
    print(f"--- 開始掃描 (使用 KuCoin 數據) ---")
    for config in WATCHLIST:
        check_coin(exchange, config)
        time.sleep(1)

if __name__ == "__main__":
    run_monitor()
