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
        # 抓取 K 線
        bars = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=50)
        df = pd.DataFrame(bars, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        
        # 計算 RSI
        rsi_series = ta.rsi(df['c'], length=14)
        
        # 🔥【關鍵修正 1】抓取「倒數第二根」(iloc[-2])，也就是剛收盤的那根
        # 這樣數值才會穩定，不會亂跳
        closed_rsi = float(rsi_series.iloc[-2])
        
        print(f"檢查中: {symbol} ({tf}) 收盤 RSI = {closed_rsi:.2f}")

        # 觸發通知
        if closed_rsi >= config['upper']:
            msg = f"🔥 {symbol} ({tf}) RSI 確實站上 {config['upper']}！\n收盤數值：{closed_rsi:.2f}"
            send_telegram(msg)
        elif closed_rsi <= config['lower']:
            msg = f"❄️ {symbol} ({tf}) RSI 確實跌破 {config['lower']}！\n收盤數值：{closed_rsi:.2f}"
            send_telegram(msg)
            
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
