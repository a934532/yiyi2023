import os
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# --- 從 GitHub Secrets 讀取資料 ---
TOKEN = os.getenv('TG_TOKEN')
CHAT_ID = os.getenv('TG_CHAT_ID')
HISTORY_FILE = 'notify_history.json'
COOLDOWN_SECONDS = 48 * 3600  # 48 小時

def get_tw_now():
    """取得台灣時間 (UTC+8)"""
    return datetime.now(timezone(timedelta(hours=8)))

def send_bot_msg(text):
    """發送訊息到 Telegram 機器人"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": text,
        "parse_mode": "Markdown" # 支援粗體格式
    }
    try:
        res = requests.post(url, json=payload)
        print(f"Telegram API 回應: {res.status_code}")
    except Exception as e:
        print(f"發送失敗: {e}")

def extract_coin(text):
    """提取幣種代碼 (例如 1000PEPE)"""
    try:
        first_line = text.split('\n')[0]
        for sep in ['—', '-']: # 同時支援長短橫線
            if sep in first_line:
                return first_line.split(sep)[-1].strip().upper()
    except:
        return None
    return None

def main():
    print(f"=== 執行開始: {get_tw_now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    # 1. 載入歷史紀錄
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try:
                history = json.load(f)
            except:
                history = {}

    # 2. 爬取 Telegram 公開頻道網頁
    url = "https://t.me/s/oiscreener"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"網頁抓取失敗: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    messages = soup.find_all('div', class_='tgme_widget_message_text')
    print(f"找到 {len(messages)} 則訊息")

    found_new = False
    tw_now = get_tw_now()

    # 3. 處理每則訊息
    for msg_div in messages:
        full_text = msg_div.get_text()
        coin = extract_coin(full_text)
        
        if coin:
            last_time = history.get(coin, 0)
            now_ts = time.time()
            
            # 檢查 48 小時冷卻
            if (now_ts - last_time) > COOLDOWN_SECONDS:
                # --- 精簡通知內容 ---
                lines = full_text.split('\n')
                # 只保留前三行重要數據 (交易所資訊、OI、價變)
                clean_info = "\n".join(lines[:3]) 
                
                tw_time_str = tw_now.strftime('%m/%d %H:%M')
                
                alert_text = (
                    f"🚀 *[{coin}] 48H首見訊號*\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"{clean_info}\n"
                    f"⏰ *時間*：{tw_time_str}"
                )
                
                print(f"✅ 符合通知條件: {coin}")
                send_bot_msg(alert_text)
                
                # 更新歷史
                history[coin] = now_ts
                found_new = True

    # 4. 存回紀錄檔
    if found_new:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)
        print("歷史紀錄已更新")

if __name__ == "__main__":
    main()
