import ccxt
import pandas_ta as ta
import pandas as pd
import requests
import os

# --- 從 GitHub Secrets 讀取設定 ---
SYMBOL = 'BTC/USDT'
TIMEFRAME = '15m'
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": message}
    requests.post(url, json=payload)

def run_monitor():
    exchange = ccxt.binanceus()
    # 抓取 15m K線
    bars = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=50)
    df = pd.DataFrame(bars, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
    
    # 計算 RSI
    rsi_series = ta.rsi(df['c'], length=14)
    current_rsi = float(rsi_series.iloc[-1])
    
    print(f"[{SYMBOL}] 當前 15m RSI: {current_rsi:.2f}")

    # 判斷邏輯
    if current_rsi >= 70:
        send_telegram(f"🔥 RSI 警告：{SYMBOL} 目前為 {current_rsi:.2f} (超買區)")
    elif current_rsi <= 30:
        send_telegram(f"❄️ RSI 警告：{SYMBOL} 目前為 {current_rsi:.2f} (超賣區)")

if __name__ == "__main__":
    run_monitor()
