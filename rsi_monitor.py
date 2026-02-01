import ccxt
import pandas_ta as ta
import pandas as pd
import requests
import os
import time

# --- 從 GitHub Secrets 讀取 Telegram 設定 ---
TG_TOKEN = os.getenv('TG_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

# --- 🔥 監控清單設定區 (請在這裡修改) ---
# 格式：{'symbol': '幣種', 'timeframe': '週期', 'upper': 超買值, 'lower': 超賣值}
WATCHLIST = [
    {'symbol': 'DUSK/USDT', 'timeframe': '15m', 'upper': 70, 'lower': 30},
    {'symbol': 'LIT/USDT',  'timeframe': '15m', 'upper': 70, 'lower': 30},
    {'symbol': 'CHZ/USDT',  'timeframe': '15m', 'upper': 70, 'lower': 30},
    {'symbol': 'BTC/USDT',  'timeframe': '4h',  'upper': 70, 'lower': 10},

    
    # 你想加 5 分鐘或 1 小時的 RSI 也可以，格式如下：
    # {'symbol': 'BTC/USDT',  'timeframe': '4h',  'upper': 70, 'lower': 10},

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
        # 抓取 K 線 (50根就夠算 RSI 了)
        bars = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=50)
        df = pd.DataFrame(bars, columns=['ts', 'o', 'h', 'l', 'c', 'v'])
        
        # 計算 RSI
        rsi_series = ta.rsi(df['c'], length=14)
        current_rsi = float(rsi_series.iloc[-1])
        
        print(f"檢查中: {symbol} ({tf}) RSI = {current_rsi:.2f}")

        # 觸發通知判斷
        if current_rsi >= config['upper']:
            msg = f"🔥 {symbol} ({tf}) RSI 衝高警報！\n數值：{current_rsi:.2f} (高於 {config['upper']})"
            send_telegram(msg)
        elif current_rsi <= config['lower']:
            msg = f"❄️ {symbol} ({tf}) RSI 抄底警報！\n數值：{current_rsi:.2f} (低於 {config['lower']})"
            send_telegram(msg)
            
    except Exception as e:
        print(f"❌ 監控 {symbol} 發生錯誤 (可能是代號打錯或交易所沒上架): {e}")

def run_monitor():
    # 使用 Binance US 以符合 GitHub 地區限制
    exchange = ccxt.binanceus()
    
    print(f"--- 開始掃描 {len(WATCHLIST)} 個目標 ---")
    for config in WATCHLIST:
        check_coin(exchange, config)
        time.sleep(1) # 休息1秒，避免請求太快被交易所踢

if __name__ == "__main__":
    run_monitor()
