import os
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# --- 從 Secrets 讀取資料 ---
TOKEN = os.getenv('TG_TOKEN')
CHAT_ID = os.getenv('TG_CHAT_ID')
HISTORY_FILE = 'notify_history.json'
COOLDOWN_SECONDS = 48 * 3600  # 48 小時

def get_tw_now():
    return datetime.now(timezone(timedelta(hours=8)))

def send_bot_msg(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, json=payload)

def extract_coin(text):
    try:
        first_line = text.split('\n')[0]
        if '—' in first_line:
            return first_line.split('—')[-1].strip().upper()
    except:
        return None
    return None

def main():
    # 1. 載入歷史紀錄
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try: history = json.load(f)
            except: history = {}
    else:
        history = {}

    # 2. 爬取 Telegram 網頁版
    url = "https://t.me/s/oiscreener"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 找到所有的訊息區塊
    messages = soup.find_all('div', class_='tgme_widget_message_text')
    
    tw_now = get_tw_now()
    found_new = False

    for msg_div in messages:
        text = msg_div.get_text()
        coin = extract_coin(text)
        
        if coin:
            last_time = history.get(coin, 0)
            now_ts = time.time()
            
            # 3. 檢查 48 小時冷卻
            if (now_ts - last_time) > COOLDOWN_SECONDS:
                tw_time_str = tw_now.strftime('%m/%d %H:%M')
                alert_text = f"🔔 48H 首見訊號：{coin}\n⏰ 台灣時間：{tw_time_str}\n\n{text}"
                
                print(f"發送通知: {coin}")
                send_bot_msg(alert_text)
                
                # 更新紀錄
                history[coin] = now_ts
                found_new = True

    # 4. 存回紀錄
    if found_new:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)

if __name__ == "__main__":
    main()
