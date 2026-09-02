import os
import json
import time
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# --- 設定區 ---
TOKEN = os.getenv('TG_TOKEN')
CHAT_ID = os.getenv('TG_CHAT_ID')
HISTORY_FILE = 'notify_history.json'

# 冷卻時間：96 小時
COOLDOWN_SECONDS = 96 * 3600  

def get_tw_now():
    return datetime.now(timezone(timedelta(hours=8)))

def send_bot_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def extract_coin(text):
    """
    專為 t.me/oi_detector 優化的幣名提取邏輯
    嘗試抓取如 $BTC, $ETH, BTCUSDT 或大寫代碼
    """
    try:
        # 1. 優先尋找帶有 $ 符號的幣名 (例如 $BTC)
        dollar_match = re.search(r'\$([A-Z0-9]{1,12})', text)
        if dollar_match:
            return dollar_match.group(1)

        # 2. 如果沒有 $，抓取第一行或第二行的大寫代碼
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        for line in lines[:2]:
            # 尋找包含 USDT / BUSD 的組合，或者純大寫代碼
            coin_match = re.search(r'\b([A-Z0-9]{1,12})(?:USDT|PERP)?\b', line)
            if coin_match:
                return coin_match.group(1)
    except:
        pass
    return None

def clean_info(text):
    """
    提取重點數據並去除廣告/無用連結
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    results = []
    
    for line in lines:
        # 過濾掉包含網址或推廣的行
        if any(bad in line.lower() for bad in ["http", "t.me", "join", "ref"]):
            continue
        # 保留含有數字、百分比或關鍵字 (OI, Vol, Price) 的內容
        if any(k in line.upper() for k in ["OI", "PRICE", "VOL", "%", "INCREASE", "DECREASE"]) or len(results) < 2:
            results.append(line)
            
    return "\n".join(results[:3]) # 精簡保留前 3 行重點

def main():
    print(f"=== 啟動檢查 (oi_detector): {get_tw_now().strftime('%H:%M:%S')} ===")
    
    # 1. 載入歷史紀錄
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try: history = json.load(f)
            except: history = {}

    # 2. 爬取新頻道
    url = "https://t.me/s/oi_detector"
    try:
        res = requests.get(url, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        messages = soup.find_all('div', class_='tgme_widget_message_text')
        print(f"找到 {len(messages)} 則訊息")
    except Exception as e:
        print(f"網頁讀取失敗: {e}")
        return

    now_ts = time.time()
    found_new = False
    seen_this_run = set()

    # 3. 從舊到新處理訊息
    for msg_div in reversed(messages):
        full_text = msg_div.get_text()
        coin = extract_coin(full_text)
        
        if coin and coin not in seen_this_run:
            last_time = history.get(coin, 0)
            
            # 4. 檢查 96 小時冷卻
            if (now_ts - last_time) > COOLDOWN_SECONDS:
                data_text = clean_info(full_text)
                tw_time = get_tw_now().strftime('%m/%d %H:%M')
                
                alert_text = (
                    f"💎 *{coin}* (96H首見)\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"{data_text}\n"
                    f"⏰ {tw_time}"
                )
                
                send_bot_msg(alert_text)
                print(f"✅ 已發送通知: {coin}")
                
                history[coin] = now_ts
                seen_this_run.add(coin)
                found_new = True

    # 5. 存回歷史檔案
    if found_new:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)

if __name__ == "__main__":
    main()
