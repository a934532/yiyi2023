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
COOLDOWN_SECONDS = 48 * 3600  # 48 小時

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
    精確提取幣名，過濾掉長字串與雜訊
    """
    try:
        first_line = text.split('\n')[0]
        if '—' in first_line:
            potential = first_line.split('—')[-1].strip()
            # 只抓取長度 3~12 的大寫英數組合 (例如 XRP, 1000PEPE)
            match = re.search(r'([A-Z0-9]{3,12})', potential)
            if match:
                return match.group(1)
    except:
        pass
    return None

def clean_info(text):
    """
    提取 OI 與 價格 數據，過濾廣告
    """
    # 將常見符號強制換行，處理字串黏在一起的問題
    formatted = text.replace("📈", "\n📈").replace("💱", "\n💱")
    lines = [l.strip() for l in formatted.split('\n') if l.strip()]
    
    # 只保留包含關鍵數據的行
    results = []
    for line in lines:
        if any(k in line.upper() for k in ["OI ", "PRICE", "INCREASED", "DECREASED"]):
            # 移除廣告詞
            clean_line = re.sub(r'FULL ACCESS.*|THIS IS ONLY.*', '', line, flags=re.IGNORECASE)
            if clean_line.strip():
                results.append(clean_line.strip())
    
    return "\n".join(results[:2]) # 只取最重要的前兩行數據

def main():
    print(f"=== 啟動檢查: {get_tw_now().strftime('%H:%M:%S')} ===")
    
    # 1. 載入紀錄
    history = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            try: history = json.load(f)
            except: history = {}

    # 2. 爬取網頁
    try:
        res = requests.get("https://t.me/s/oiscreener", timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        messages = soup.find_all('div', class_='tgme_widget_message_text')
    except:
        return

    now_ts = time.time()
    found_new = False
    
    # 本次執行的「臨時去重表」，防止同一輪內重複發送
    seen_this_run = set()

    # 3. 逆序處理訊息（從舊到新，確保最新訊息的時間被記錄）
    for msg_div in reversed(messages):
        full_text = msg_div.get_text()
        coin = extract_coin(full_text)
        
        if coin and coin not in seen_this_run:
            last_time = history.get(coin, 0)
            
            # 4. 檢查 48 小時冷卻
            if (now_ts - last_time) > COOLDOWN_SECONDS:
                data_text = clean_info(full_text)
                tw_time = get_tw_now().strftime('%m/%d %H:%M')
                
                # 簡潔版排版
                alert_text = (
                    f"💎 *{coin}* (48H首見)\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"{data_text}\n"
                    f"⏰ {tw_time}"
                )
                
                send_bot_msg(alert_text)
                print(f"✅ 已通知: {coin}")
                
                # 更新狀態
                history[coin] = now_ts
                seen_this_run.add(coin)
                found_new = True

    # 5. 只有在有新通知時才更新檔案，減少 GitHub 的 Commit 壓力
    if found_new:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)

if __name__ == "__main__":
    main()
