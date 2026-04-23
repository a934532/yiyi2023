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
    精確提取幣名，支援 1~12 個字元的代碼 (例如 B, XRP, 1000PEPE)
    """
    try:
        # 取得第一行
        first_line = text.split('\n')[0]
        if '—' in first_line:
            # 取得最後一個分隔符號後的內容
            potential = first_line.split('—')[-1].strip()
            # 修改處：{1,12} 允許 1 個字以上的純大寫英數組合
            match = re.search(r'^([A-Z0-9]{1,12})', potential)
            if match:
                return match.group(1)
    except:
        pass
    return None

def clean_info(text):
    """
    提取 OI 與 價格 數據，過濾廣告
    """
    # 將標誌性符號強制換行，處理字串黏在一起的問題
    formatted = text.replace("📈", "\n📈").replace("💱", "\n💱")
    lines = [l.strip() for l in formatted.split('\n') if l.strip()]
    
    results = []
    for line in lines:
        # 尋找包含關鍵數據的行
        if any(k in line.upper() for k in ["OI ", "PRICE", "INCREASED", "DECREASED"]):
            # 移除常見廣告詞
            clean_line = re.sub(r'FULL ACCESS.*|THIS IS ONLY.*|PRO FOR 24.*', '', line, flags=re.IGNORECASE)
            if clean_line.strip():
                results.append(clean_line.strip())
    
    return "\n".join(results[:2])

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
        print("網頁讀取超時")
        return

    now_ts = time.time()
    found_new = False
    
    # 本次執行的去重表
    seen_this_run = set()

    # 3. 處理訊息 (逆序處理：從舊到新)
    for msg_div in reversed(messages):
        full_text = msg_div.get_text()
        coin = extract_coin(full_text)
        
        if coin and coin not in seen_this_run:
            last_time = history.get(coin, 0)
            
            # 4. 檢查 48 小時冷卻
            if (now_ts - last_time) > COOLDOWN_SECONDS:
                data_text = clean_info(full_text)
                tw_time = get_tw_now().strftime('%m/%d %H:%M')
                
                # 簡潔排版
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

    # 5. 更新檔案
    if found_new:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)

if __name__ == "__main__":
    main()
